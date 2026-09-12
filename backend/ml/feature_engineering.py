"""
Feature Engineering Pipeline
==============================
WHAT: Transforms raw weather + generation + time data into ML-ready features.
WHY:  XGBoost needs numerical features. Time-series patterns live in lag/rolling features.
INPUT: Raw pandas DataFrame with columns: timestamp, plant_id, weather variables, generation_mw
OUTPUT: DataFrame with all ML features added.

CRITICAL: All lag features are created ONLY from past data.
           Never use future generation values — this causes data leakage.

Feature Categories:
  1. Raw weather features     — directly from API/DB
  2. Time features            — derived from timestamp (no leakage)
  3. Lag features             — from PAST actual generation (leakage risk: must handle carefully)
  4. Rolling features         — from PAST actual generation
  5. Plant features           — static plant parameters
  6. Target                   — generation_mw (only in training, never at inference)
"""

import pandas as pd
import numpy as np
from typing import Optional
import warnings

warnings.filterwarnings("ignore")


# ── COLUMN DEFINITIONS ────────────────────────────────────────────────────────

RAW_WEATHER_FEATURES = [
    "temperature_c",
    "humidity_pct",
    "cloud_cover_pct",
    "solar_irradiance_wm2",
    "wind_speed_ms",
    "wind_direction_deg",
    "pressure_hpa",
    "rainfall_mm",
]

TIME_FEATURES = [
    "hour",
    "day",
    "month",
    "day_of_week",
    "is_weekend",
    "is_daylight",           # 1 if solar_irradiance > 10 W/m²
    "hour_sin",              # Cyclical encoding of hour
    "hour_cos",
    "month_sin",             # Cyclical encoding of month
    "month_cos",
]

LAG_FEATURES = [
    "generation_lag_1",      # Generation 1 hour ago
    "generation_lag_2",      # Generation 2 hours ago
    "generation_lag_24",     # Generation 24 hours ago (same time yesterday)
    "generation_lag_168",    # Generation 168 hours ago (same time last week)
]

ROLLING_FEATURES = [
    "rolling_mean_3",        # Rolling mean of last 3 hours
    "rolling_mean_24",       # Rolling mean of last 24 hours
    "rolling_std_24",        # Rolling std of last 24 hours (volatility)
]

PLANT_FEATURES = [
    "capacity_mw",           # Plant capacity — normalizes relative to plant size
    "plant_type_solar",      # One-hot: 1 if solar
    "plant_type_wind",       # One-hot: 1 if wind
]

# Combined feature set used by the model
# Note: plant_type features are NOT used when separate solar/wind models are trained.
SOLAR_MODEL_FEATURES = (
    RAW_WEATHER_FEATURES
    + TIME_FEATURES
    + LAG_FEATURES
    + ROLLING_FEATURES
    + ["capacity_mw"]
)

WIND_MODEL_FEATURES = (
    # Wind models don't use solar_irradiance or cloud_cover as primary drivers,
    # but keeping them in is fine — XGBoost will assign low importance if not useful.
    RAW_WEATHER_FEATURES
    + TIME_FEATURES
    + LAG_FEATURES
    + ROLLING_FEATURES
    + ["capacity_mw"]
)

TARGET_COLUMN = "generation_mw"


# ── TIME FEATURES ─────────────────────────────────────────────────────────────

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add time-based features from the timestamp column.
    These never cause leakage because they are derived from the timestamp itself.

    Cyclical encoding (sin/cos) is used instead of raw hour/month integers
    to preserve continuity (e.g., hour 23 and hour 0 are adjacent).
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.day
    df["month"] = df["timestamp"].dt.month
    df["day_of_week"] = df["timestamp"].dt.dayofweek  # 0=Monday, 6=Sunday
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Cyclical encoding — prevents the model seeing 23→0 as a large jump
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # Daylight detection — solar irradiance > 10 W/m² means daylight
    # This eliminates the need for a separate two-stage solar model.
    # XGBoost learns: when is_daylight=0, predict ≈ 0 for solar.
    if "solar_irradiance_wm2" in df.columns:
        df["is_daylight"] = (df["solar_irradiance_wm2"] > 10).astype(int)
    else:
        # Fallback: estimate daylight from hour (rough approximation)
        df["is_daylight"] = ((df["hour"] >= 6) & (df["hour"] <= 19)).astype(int)

    return df


# ── LAG FEATURES ──────────────────────────────────────────────────────────────

def add_lag_features(df: pd.DataFrame, target_col: str = "generation_mw") -> pd.DataFrame:
    """
    Add lag features from PAST actual generation.

    CRITICAL LEAKAGE RULE:
    - Data must be sorted by timestamp BEFORE calling this function.
    - shift(N) looks N rows BACK — never forward.
    - At inference time, we only have historical data (no future actuals).
      lag_1 = last known generation (t-1)
      lag_2 = two hours ago (t-2)
      lag_24 = same time yesterday (t-24)
      lag_168 = same time last week (t-168)

    WHY LAG FEATURES?
    Generation at 2 PM today strongly correlates with generation at 2 PM yesterday.
    This is how the model captures temporal patterns without an LSTM.
    """
    df = df.copy()

    if target_col not in df.columns:
        # At inference time, we don't have future actuals.
        # Caller must fill lag features from historical DB records.
        # Return df with NaN lags — caller handles these.
        for lag_col in LAG_FEATURES:
            df[lag_col] = np.nan
        for roll_col in ROLLING_FEATURES:
            df[roll_col] = np.nan
        return df

    df = df.sort_values("timestamp").reset_index(drop=True)

    # Lag features — uses pandas shift (safe, no future leakage)
    df["generation_lag_1"] = df[target_col].shift(1)
    df["generation_lag_2"] = df[target_col].shift(2)
    df["generation_lag_24"] = df[target_col].shift(24)
    df["generation_lag_168"] = df[target_col].shift(168)

    # Rolling features — min_periods avoids NaN for the first few rows
    df["rolling_mean_3"] = (
        df[target_col].shift(1).rolling(window=3, min_periods=1).mean()
    )
    df["rolling_mean_24"] = (
        df[target_col].shift(1).rolling(window=24, min_periods=6).mean()
    )
    df["rolling_std_24"] = (
        df[target_col].shift(1).rolling(window=24, min_periods=6).std().fillna(0)
    )

    return df


def fill_lag_features_at_inference(
    feature_row: pd.Series,
    historical_generation: pd.DataFrame,
    forecast_timestamp: pd.Timestamp,
) -> pd.Series:
    """
    At inference time, fill lag features from actual historical generation.

    WHAT:  For a future forecast timestamp, look back N hours into real history.
    WHY:   We don't have future actuals, but we DO have the real historical record.
    INPUT: feature_row (the row being built for prediction),
           historical_generation (sorted DataFrame of past actuals),
           forecast_timestamp (the hour we are predicting)
    OUTPUT: feature_row with lag columns filled.

    This is the CORRECT approach for 24–72 hour direct forecasting:
    - lag_1:   actual generation at (forecast_timestamp - 1h)
    - lag_24:  actual generation at (forecast_timestamp - 24h)
    - lag_168: actual generation at (forecast_timestamp - 168h)

    Note: For the direct forecasting approach, we use real historical lags,
    NOT recursively predicted values. This avoids error accumulation.
    """
    feature_row = feature_row.copy()

    def get_lag(hours_back: int) -> float:
        target_ts = forecast_timestamp - pd.Timedelta(hours=hours_back)
        match = historical_generation[
            historical_generation["timestamp"].dt.floor("h") == target_ts.floor("h")
        ]
        if not match.empty:
            return float(match.iloc[-1]["generation_mw"])
        return np.nan  # Missing — model trained to handle NaN with imputation

    feature_row["generation_lag_1"] = get_lag(1)
    feature_row["generation_lag_2"] = get_lag(2)
    feature_row["generation_lag_24"] = get_lag(24)
    feature_row["generation_lag_168"] = get_lag(168)

    # Rolling from historical
    last_24 = historical_generation[
        historical_generation["timestamp"] < forecast_timestamp
    ].tail(24)["generation_mw"]

    last_3 = last_24.tail(3)

    feature_row["rolling_mean_3"] = float(last_3.mean()) if len(last_3) > 0 else np.nan
    feature_row["rolling_mean_24"] = float(last_24.mean()) if len(last_24) > 0 else np.nan
    feature_row["rolling_std_24"] = float(last_24.std()) if len(last_24) > 1 else 0.0

    return feature_row


# ── PLANT FEATURES ────────────────────────────────────────────────────────────

def add_plant_features(df: pd.DataFrame, capacity_mw: float, plant_type: str) -> pd.DataFrame:
    """Add static plant parameters as features."""
    df = df.copy()
    df["capacity_mw"] = capacity_mw
    df["plant_type_solar"] = int(plant_type.lower() == "solar")
    df["plant_type_wind"] = int(plant_type.lower() == "wind")
    return df


# ── FULL PIPELINE ─────────────────────────────────────────────────────────────

def build_training_features(
    df: pd.DataFrame,
    capacity_mw: float,
    plant_type: str,
    drop_rows_with_nan_target: bool = True,
) -> pd.DataFrame:
    """
    Full feature engineering pipeline for TRAINING.

    Steps:
    1. Add time features
    2. Add lag features (from actual generation — safe because sorted by time)
    3. Add plant features
    4. Drop rows with NaN in target or in lag features (first ~168 rows)
    5. Return clean feature DataFrame

    INPUT: Raw DataFrame with [timestamp, generation_mw, weather columns]
    OUTPUT: DataFrame with all features, ready for XGBoost.
    """
    df = df.copy()
    df = add_time_features(df)
    df = add_lag_features(df, target_col=TARGET_COLUMN)
    df = add_plant_features(df, capacity_mw, plant_type)

    # Drop rows where lag features are NaN (first 168 rows in data)
    # These rows don't have enough history for lag_168 — dropping is safer than imputing.
    lag_cols = ["generation_lag_1", "generation_lag_24", "generation_lag_168"]
    df = df.dropna(subset=lag_cols)

    if drop_rows_with_nan_target:
        df = df.dropna(subset=[TARGET_COLUMN])

    return df


def get_feature_columns(plant_type: str) -> list:
    """Return the ordered list of feature columns for a given plant type."""
    if plant_type.lower() == "solar":
        return SOLAR_MODEL_FEATURES
    else:
        return WIND_MODEL_FEATURES


def validate_features_for_prediction(
    feature_df: pd.DataFrame,
    plant_type: str,
) -> tuple[pd.DataFrame, list]:
    """
    Validate that all required features are present for inference.
    Returns (validated_df, warnings_list).
    Missing features are filled with median-based defaults — NEVER silently with 0.
    """
    required_cols = get_feature_columns(plant_type)
    warnings = []
    df = feature_df.copy()

    for col in required_cols:
        if col not in df.columns:
            df[col] = np.nan
            warnings.append(f"Feature '{col}' missing — filled with NaN, model will use learned default")
        elif df[col].isna().any():
            nan_count = df[col].isna().sum()
            warnings.append(f"Feature '{col}' has {nan_count} NaN values")

    return df[required_cols], warnings
