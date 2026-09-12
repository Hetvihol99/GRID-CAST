"""
Forecast Service
=================
WHAT: Orchestrates the full end-to-end forecast pipeline for one or all plants.
WHY:  Routes should be thin — they call this service, which coordinates all other services.

FLOW:
  1. For each active plant:
     a. Fetch weather forecast (WeatherService)
     b. Load historical generation from DB
     c. Call MLPredictor → hourly generation forecasts
     d. Save forecasts to DB
  2. Aggregate all plant forecasts → regional total
  3. Load demand profile
  4. Compute balance (GridAnalysisService)
  5. Run battery analysis (StorageService)
  6. Generate recommendations (RecommendationEngine)
  7. Process alerts (AlertService)
  8. Return full result
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.database.models import Plant, GenerationData, Forecast, DemandData, BatteryStorage
from app.services.weather_service import WeatherService
from app.services.grid_analysis_service import GridAnalysisService, HourlyBalance
from app.services.storage_service import StorageService
from app.services.recommendation_service import RecommendationEngine
from app.services.alert_service import AlertService
from ml.predictor import predictor as ml_predictor
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ForecastService:
    def __init__(self):
        self.weather_svc = WeatherService()
        self.grid_svc = GridAnalysisService()
        self.storage_svc = StorageService()
        self.rec_engine = RecommendationEngine()
        self.alert_svc = AlertService()

    def run_forecast(
        self,
        db: Session,
        plant_ids: Optional[list[int]] = None,
        horizon_hours: int = 72,
        region: str = "default",
    ) -> dict:
        """
        Run the full forecast pipeline.

        This is the central orchestrator — it coordinates all services.
        Routes call this single method.
        """
        now = datetime.now(timezone.utc)
        logger.info(f"Starting forecast run: horizon={horizon_hours}h, plants={plant_ids}")

        # ── 1. Load plants ────────────────────────────────────────────────────
        query = db.query(Plant).filter(Plant.is_active == True)
        if plant_ids:
            query = query.filter(Plant.id.in_(plant_ids))
        plants = query.all()

        if not plants:
            raise ValueError("No active plants found to forecast")

        # ── 2. Forecast each plant ────────────────────────────────────────────
        all_plant_forecasts = []
        for plant in plants:
            try:
                plant_forecast = self._forecast_single_plant(plant, db, horizon_hours, now)
                all_plant_forecasts.append(plant_forecast)
            except Exception as e:
                logger.error(f"Forecast failed for plant {plant.id} ({plant.name}): {e}")
                # Continue with remaining plants — partial forecast is better than none

        if not all_plant_forecasts:
            raise RuntimeError("All plant forecasts failed — cannot generate regional summary")

        # ── 3. Aggregate regional totals ──────────────────────────────────────
        hourly_totals = self._aggregate_forecasts(all_plant_forecasts, horizon_hours, now)

        # ── 4. Load demand ────────────────────────────────────────────────────
        demand_series = self._load_demand(db, region, horizon_hours, now)

        # ── 5. Compute grid balance ───────────────────────────────────────────
        balance_series = []
        for ts_str, gen_mw in hourly_totals.items():
            ts = pd.Timestamp(ts_str).to_pydatetime()
            demand_mw = demand_series.get(ts_str, 800.0)  # Fallback demand
            balance = self.grid_svc.compute_balance(ts, gen_mw, demand_mw)
            balance_series.append(balance)

        # ── 6. Battery analysis ───────────────────────────────────────────────
        battery = self._load_battery(db, region)
        battery_results = []
        if battery:
            for balance in balance_series:
                if balance.alert_type == "surplus":
                    result = self.storage_svc.analyze_surplus(battery, balance.net_balance_mw)
                elif balance.alert_type == "deficit":
                    result = self.storage_svc.analyze_deficit(battery, abs(balance.net_balance_mw))
                else:
                    result = None
                battery_results.append(result)

        # ── 7. Generate recommendations ───────────────────────────────────────
        recommendations = []
        for i, balance in enumerate(balance_series):
            bat_result = battery_results[i] if battery_results else None
            rec_set = self.rec_engine.generate(balance, bat_result)
            recommendations.append(rec_set)

        # ── 8. Process alerts ─────────────────────────────────────────────────
        alerts = self.alert_svc.process_balance_series(balance_series, region, db)

        logger.info(
            f"Forecast complete: {len(plants)} plants, "
            f"{len(balance_series)} hours, {len(alerts)} alerts"
        )

        return {
            "generated_at": now,
            "plants_forecasted": len(plants),
            "plant_forecasts": all_plant_forecasts,
            "balance_series": balance_series,
            "battery": battery,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    def _forecast_single_plant(
        self, plant: Plant, db: Session, horizon_hours: int, now: datetime
    ) -> dict:
        """Forecast a single plant and save results to DB."""
        # Get weather forecast
        weather_points = self.weather_svc.get_forecast(plant, db, horizon_hours)

        # Get historical generation (last 7 days = 168 hours for lag features)
        history_cutoff = pd.Timestamp(now) - pd.Timedelta(hours=168)
        gen_records = (
            db.query(GenerationData)
            .filter(
                GenerationData.plant_id == plant.id,
                GenerationData.timestamp >= history_cutoff.to_pydatetime(),
                GenerationData.is_valid == True,
            )
            .order_by(GenerationData.timestamp)
            .all()
        )

        historical_df = pd.DataFrame([
            {"timestamp": r.timestamp, "generation_mw": r.generation_mw}
            for r in gen_records
        ])

        if historical_df.empty:
            raise ValueError(
                f"No historical generation data found for plant {plant.id} ({plant.name}). "
                f"Load generation data before running forecasts."
            )

        # Convert weather to DataFrame
        weather_df = pd.DataFrame([
            {
                "timestamp": p.timestamp,
                "temperature_c": p.temperature_c,
                "humidity_pct": p.humidity_pct,
                "cloud_cover_pct": p.cloud_cover_pct,
                "solar_irradiance_wm2": p.solar_irradiance_wm2,
                "wind_speed_ms": p.wind_speed_ms,
                "wind_direction_deg": p.wind_direction_deg,
                "pressure_hpa": p.pressure_hpa,
                "rainfall_mm": p.rainfall_mm,
            }
            for p in weather_points
        ])

        # Run ML prediction
        predictions = ml_predictor.forecast_plant(
            plant_id=plant.id,
            plant_type=plant.plant_type.value,
            capacity_mw=plant.capacity_mw,
            weather_forecast=weather_df,
            historical_generation=historical_df,
            horizon_hours=horizon_hours,
        )

        # Save forecasts to DB
        self._save_forecasts(predictions, plant.id, now, db)

        return {
            "plant_id": plant.id,
            "plant_name": plant.name,
            "plant_type": plant.plant_type.value,
            "capacity_mw": plant.capacity_mw,
            "predictions": predictions,
        }

    def _aggregate_forecasts(
        self, plant_forecasts: list[dict], horizon_hours: int, now: datetime
    ) -> dict:
        """Sum all plant forecasts by timestamp to get regional total."""
        totals = {}
        for pf in plant_forecasts:
            for pred in pf["predictions"]:
                ts_key = pred.timestamp.isoformat()
                totals[ts_key] = totals.get(ts_key, 0) + pred.predicted_generation_mw
        return totals

    def _load_demand(
        self, db: Session, region: str, horizon_hours: int, now: datetime
    ) -> dict:
        """Load demand data — returns {timestamp_iso: demand_mw} dict."""
        end_time = pd.Timestamp(now) + pd.Timedelta(hours=horizon_hours)
        records = (
            db.query(DemandData)
            .filter(
                DemandData.region == region,
                DemandData.timestamp >= now,
                DemandData.timestamp <= end_time.to_pydatetime(),
            )
            .order_by(DemandData.timestamp)
            .all()
        )
        return {r.timestamp.isoformat(): r.demand_mw for r in records}

    def _load_battery(self, db: Session, region: str) -> Optional[BatteryStorage]:
        """Load active battery for the region."""
        return (
            db.query(BatteryStorage)
            .filter(BatteryStorage.region == region, BatteryStorage.is_active == True)
            .first()
        )

    def _save_forecasts(self, predictions, plant_id: int, now: datetime, db: Session):
        """Save forecast results to DB (upsert)."""
        for pred in predictions:
            existing = (
                db.query(Forecast)
                .filter(
                    Forecast.plant_id == plant_id,
                    Forecast.forecast_generated_at == now,
                    Forecast.forecast_timestamp == pred.timestamp,
                )
                .first()
            )
            if existing:
                existing.predicted_generation_mw = pred.predicted_generation_mw
                existing.horizon_hours = pred.horizon_hours
            else:
                db.add(Forecast(
                    plant_id=plant_id,
                    forecast_generated_at=now,
                    forecast_timestamp=pred.timestamp,
                    predicted_generation_mw=pred.predicted_generation_mw,
                    horizon_hours=pred.horizon_hours,
                ))
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save forecasts for plant {plant_id}: {e}")
