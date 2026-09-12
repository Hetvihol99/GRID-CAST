import os
import joblib
import numpy as np
import pandas as pd
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from ml.feature_engineering import (
    add_time_features,
    add_plant_features,
    fill_lag_features_at_inference,
    get_feature_columns,
    validate_features_for_prediction,
)
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class PredictionResult:
    timestamp: datetime
    predicted_generation_mw: float
    horizon_hours: int
    is_daylight: bool
    warnings: list

@dataclass
class ModelInfo:
    plant_type: str
    version: str
    file_path: str
    is_loaded: bool
    error: Optional[str] = None

class MLPredictor:
    def __init__(self):
        self._solar_model = None
        self._wind_model = None
        self._solar_scaler = None
        self._wind_scaler = None
        self._model_info: dict[str, ModelInfo] = {}

    def load_models(self) -> None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        model_dir = settings.MODEL_DIR
        if not os.path.isabs(model_dir):
            model_dir = os.path.join(base_dir, model_dir)

        solar_path = os.path.join(model_dir, settings.SOLAR_MODEL_FILE)
        solar_scaler_path = os.path.join(model_dir, settings.SOLAR_SCALER_FILE)
        self._load_single_model("solar", solar_path, solar_scaler_path)

        wind_path = os.path.join(model_dir, settings.WIND_MODEL_FILE)
        wind_scaler_path = os.path.join(model_dir, settings.WIND_SCALER_FILE)
        self._load_single_model("wind", wind_path, wind_scaler_path)

    def _ensure_loaded(self) -> None:
        if self._solar_model is None or self._wind_model is None:
            self.load_models()

    def _load_single_model(self, plant_type: str, model_path: str, scaler_path: str) -> None:
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found: {model_path}")

            model = joblib.load(model_path)

            scaler = None
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
            else:
                logger.warning(f"Scaler not found at {scaler_path} - proceeding without scaling")

            if plant_type == "solar":
                self._solar_model = model
                self._solar_scaler = scaler
            else:
                self._wind_model = model
                self._wind_scaler = scaler

            self._model_info[plant_type] = ModelInfo(
                plant_type=plant_type,
                version=os.path.basename(model_path),
                file_path=model_path,
                is_loaded=True,
            )
            logger.info(f"Loaded {plant_type} model from {model_path}")

        except Exception as e:
            self._model_info[plant_type] = ModelInfo(
                plant_type=plant_type,
                version="unknown",
                file_path=model_path,
                is_loaded=False,
                error=str(e),
            )
            logger.error(f"Failed to load {plant_type} model: {e}")

    def get_model(self, plant_type: str):
        self._ensure_loaded()
        if plant_type.lower() == "solar":
            if self._solar_model is None:
                raise RuntimeError("Solar model is not loaded.")
            return self._solar_model, self._solar_scaler
        elif plant_type.lower() == "wind":
            if self._wind_model is None:
                raise RuntimeError("Wind model is not loaded.")
            return self._wind_model, self._wind_scaler
        else:
            raise ValueError(f"Unknown plant type: {plant_type}. Expected 'solar' or 'wind'.")

    def get_model_info(self, plant_type: str) -> Optional[ModelInfo]:
        self._ensure_loaded()
        return self._model_info.get(plant_type.lower())

    def forecast_plant(
        self,
        plant_id: int,
        plant_type: str,
        capacity_mw: float,
        weather_forecast: pd.DataFrame,
        historical_generation: pd.DataFrame,
        horizon_hours: int = 72,
    ) -> list[PredictionResult]:
        model, scaler = self.get_model(plant_type)
        feature_cols = get_feature_columns(plant_type)
        results = []

        historical_generation = historical_generation.copy()
        historical_generation["timestamp"] = pd.to_datetime(
            historical_generation["timestamp"], utc=True
        )
        historical_generation = historical_generation.sort_values("timestamp")

        for idx, weather_row in weather_forecast.iterrows():
            forecast_ts = pd.Timestamp(weather_row["timestamp"]).tz_localize("UTC") \
                if weather_row["timestamp"].tzinfo is None \
                else pd.Timestamp(weather_row["timestamp"])

            feature_row = weather_row.copy()

            temp_df = pd.DataFrame([feature_row])
            temp_df["timestamp"] = forecast_ts
            temp_df = add_time_features(temp_df)
            feature_row = temp_df.iloc[0]

            temp_df = pd.DataFrame([feature_row])
            temp_df = add_plant_features(temp_df, capacity_mw, plant_type)
            feature_row = temp_df.iloc[0]

            feature_row = fill_lag_features_at_inference(
                feature_row, historical_generation, forecast_ts
            )

            horizon = idx + 1

            feature_df = pd.DataFrame([feature_row])
            feature_df, validation_warnings = validate_features_for_prediction(feature_df, plant_type)

            feature_df = feature_df.fillna(0)

            X = feature_df[feature_cols].values

            if scaler is not None:
                X = scaler.transform(X)

            predicted_mw = float(model.predict(X)[0])

            predicted_mw = max(0.0, min(predicted_mw, capacity_mw))

            is_daylight = bool(feature_row.get("is_daylight", 1))
            if plant_type.lower() == "solar" and not is_daylight:
                predicted_mw = 0.0

            results.append(PredictionResult(
                timestamp=forecast_ts.to_pydatetime(),
                predicted_generation_mw=round(predicted_mw, 2),
                horizon_hours=horizon,
                is_daylight=is_daylight,
                warnings=validation_warnings,
            ))

        return results

predictor = MLPredictor()
