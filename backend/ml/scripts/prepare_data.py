"""
Data Preparation Pipeline
==========================
PURPOSE: Load raw CSVs, clean data, engineer features, and save processed datasets.
RUN AFTER: generate_demo_data.py
RUN BEFORE: train_solar.py, train_wind.py

This is the cleaning + preprocessing stage.
All cleaning decisions are documented and intentional.
"""

import pandas as pd
import numpy as np
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Allow importing from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.feature_engineering import build_training_features, TARGET_COLUMN

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


# ── CLEANING FUNCTIONS ────────────────────────────────────────────────────────

def standardize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert all timestamps to UTC and round to nearest hour.
    Handles multiple common timestamp formats.
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])  # Drop rows where timestamp couldn't be parsed
    df["timestamp"] = df["timestamp"].dt.floor("h")  # Round to hourly
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate timestamp entries.
    Strategy: keep the last entry (most recent reading is more likely correct).
    """
    before = len(df)
    df = df.sort_values("timestamp")
    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    after = len(df)
    if before != after:
        print(f"    Removed {before - after} duplicate timestamps")
    return df


def fix_generation_bounds(df: pd.DataFrame, capacity_mw: float) -> pd.DataFrame:
    """
    Fix generation values that violate physical bounds.

    Strategy:
    - Negative generation: Set to 0 (physically impossible, likely sensor error)
    - Above capacity: Clip to capacity (physically impossible, likely sensor error)
    - Do NOT silently interpolate — flag and correct.
    """
    df = df.copy()

    # Negative generation
    neg_mask = df[TARGET_COLUMN] < 0
    if neg_mask.any():
        print(f"    Fixing {neg_mask.sum()} negative generation values → clipped to 0")
        df.loc[neg_mask, TARGET_COLUMN] = 0

    # Above capacity
    above_mask = df[TARGET_COLUMN] > capacity_mw
    if above_mask.any():
        print(f"    Fixing {above_mask.sum()} above-capacity values → clipped to {capacity_mw} MW")
        df.loc[above_mask, TARGET_COLUMN] = capacity_mw

    return df


def handle_missing_weather(df: pd.DataFrame, plant_type: str) -> pd.DataFrame:
    """
    Handle missing weather values with appropriate strategies.

    Rules:
    - solar_irradiance_wm2 at night: fill with 0 (not missing — just dark)
    - temperature, pressure: interpolate (slow-changing, interpolation is valid)
    - humidity, cloud_cover: interpolate (slow-changing)
    - wind_speed, wind_direction: forward-fill (wind persists for short gaps)
    - rainfall: fill with 0 (absence of data ≠ rainfall)
    - Gaps > 3 hours in key features: flag as unreliable, do NOT interpolate blindly

    DO NOT randomly fill everything with 0 or with mean — that distorts the model.
    """
    df = df.copy()

    # Solar irradiance: zero at night is correct, not missing
    if "solar_irradiance_wm2" in df.columns:
        if "hour" in df.columns:
            night_mask = (df["hour"] < 6) | (df["hour"] > 19)
        else:
            night_mask = (df["timestamp"].dt.hour < 6) | (df["timestamp"].dt.hour > 19)
        df.loc[night_mask & df["solar_irradiance_wm2"].isna(), "solar_irradiance_wm2"] = 0
        # Daytime missing: interpolate
        df["solar_irradiance_wm2"] = df["solar_irradiance_wm2"].interpolate(
            method="linear", limit=3, limit_direction="both"
        )

    # Slow-changing: interpolate with limit of 3 hours
    for col in ["temperature_c", "pressure_hpa", "humidity_pct", "cloud_cover_pct"]:
        if col in df.columns:
            df[col] = df[col].interpolate(method="linear", limit=3, limit_direction="both")

    # Wind: forward-fill short gaps (wind state persists)
    for col in ["wind_speed_ms", "wind_direction_deg"]:
        if col in df.columns:
            df[col] = df[col].fillna(method="ffill", limit=2)
            df[col] = df[col].fillna(method="bfill", limit=2)

    # Rainfall: missing ≈ 0 (no data = no rain sensor event)
    if "rainfall_mm" in df.columns:
        df["rainfall_mm"] = df["rainfall_mm"].fillna(0)

    return df


def handle_missing_generation(df: pd.DataFrame, plant_type: str) -> pd.DataFrame:
    """
    Handle missing generation values.

    Strategy:
    - If solar + nighttime: fill with 0 (correct, not missing)
    - Short gaps (≤ 2 hours): interpolate (generation is smooth)
    - Long gaps (> 3 hours): do NOT interpolate — too much uncertainty
      These rows will have NaN target and be dropped in feature engineering.

    We never fabricate generation values for large gaps.
    """
    df = df.copy()

    if plant_type == "solar":
        if "hour" in df.columns:
            night_mask = (df["hour"] < 6) | (df["hour"] > 19)
        else:
            night_mask = (df["timestamp"].dt.hour < 6) | (df["timestamp"].dt.hour > 19)
        df.loc[night_mask & df[TARGET_COLUMN].isna(), TARGET_COLUMN] = 0

    # Short gap interpolation
    df[TARGET_COLUMN] = df[TARGET_COLUMN].interpolate(
        method="linear", limit=2, limit_direction="forward"
    )

    # Remaining NaN: will be dropped by build_training_features

    return df


def detect_outliers(df: pd.DataFrame, capacity_mw: float) -> pd.DataFrame:
    """
    Detect generation outliers using IQR method per hour-of-day.
    Flag suspicious values — do not automatically drop them.
    Only values that also violate physical bounds are corrected.
    """
    df = df.copy()
    df["outlier_flag"] = False

    # Per-hour IQR outlier detection
    for hour in range(24):
        hour_mask = df["timestamp"].dt.hour == hour
        hour_data = df.loc[hour_mask, TARGET_COLUMN]

        if len(hour_data) < 10:
            continue

        Q1 = hour_data.quantile(0.25)
        Q3 = hour_data.quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 3 * IQR
        upper = Q3 + 3 * IQR

        outlier_mask = hour_mask & ((df[TARGET_COLUMN] < lower) | (df[TARGET_COLUMN] > upper))
        df.loc[outlier_mask, "outlier_flag"] = True

    n_outliers = df["outlier_flag"].sum()
    if n_outliers > 0:
        print(f"    Flagged {n_outliers} potential outliers (IQR method, per hour-of-day)")

    return df


# ── TRAIN/VALIDATION/TEST SPLIT ────────────────────────────────────────────────

def chronological_split(df: pd.DataFrame) -> tuple:
    """
    Split data chronologically — NEVER shuffle time-series data.

    WHY?
    Shuffling causes data leakage: future values appear in training set.
    Lag features would include future actuals — model would appear to predict perfectly.

    Split:
      Training:   First 70% (oldest data) — model learns patterns
      Validation: Next 15%                — hyperparameter tuning
      Test:       Last 15% (newest data)  — final honest evaluation

    This simulates real-world deployment: train on past, evaluate on future.
    """
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    print(f"    Train: {len(train):,} rows ({train['timestamp'].min().date()} → {train['timestamp'].max().date()})")
    print(f"    Val:   {len(val):,} rows ({val['timestamp'].min().date()} → {val['timestamp'].max().date()})")
    print(f"    Test:  {len(test):,} rows ({test['timestamp'].min().date()} → {test['timestamp'].max().date()})")

    return train, val, test


# ── MAIN PIPELINE ─────────────────────────────────────────────────────────────

def process_plant_file(csv_path: str, plant_type: str, plant_name: str, capacity_mw: float):
    """Full preprocessing pipeline for one plant's raw CSV."""
    print(f"\nProcessing: {plant_name} ({plant_type}, {capacity_mw} MW)")

    df = pd.read_csv(csv_path)
    print(f"  Raw rows: {len(df):,}")

    # Step 1: Standardize timestamps
    df = standardize_timestamps(df)

    # Step 2: Remove duplicates
    df = remove_duplicates(df)

    # Step 3: Sort by timestamp (REQUIRED before lag feature creation)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Step 4: Fix generation bounds
    df = fix_generation_bounds(df, capacity_mw)

    # Step 5: Handle missing weather
    df = handle_missing_weather(df, plant_type)

    # Step 6: Handle missing generation
    df = handle_missing_generation(df, plant_type)

    # Step 7: Detect outliers (flag only — not dropped here)
    df = detect_outliers(df, capacity_mw)

    # Step 8: Build full feature set
    print(f"  Building ML features...")
    df_features = build_training_features(df, capacity_mw=capacity_mw, plant_type=plant_type)
    print(f"  Feature rows after cleaning: {len(df_features):,}")

    # Step 9: Chronological split
    train, val, test = chronological_split(df_features)

    # Step 10: Save
    out_prefix = os.path.join(PROCESSED_DIR, plant_name)
    train.to_csv(f"{out_prefix}_train.csv", index=False)
    val.to_csv(f"{out_prefix}_val.csv", index=False)
    test.to_csv(f"{out_prefix}_test.csv", index=False)

    print(f"  ✅ Saved: {plant_name}_train/val/test.csv")
    return train, val, test


if __name__ == "__main__":
    plants = [
        ("solar_plant_1.csv", "solar", "solar_plant_1", 100),
        ("solar_plant_2.csv", "solar", "solar_plant_2", 150),
        ("wind_farm_1.csv", "wind", "wind_farm_1", 200),
        ("wind_farm_2.csv", "wind", "wind_farm_2", 100),
    ]

    for csv_file, plant_type, plant_name, capacity in plants:
        csv_path = os.path.join(RAW_DIR, csv_file)
        if not os.path.exists(csv_path):
            print(f"⚠️  {csv_file} not found. Run generate_demo_data.py first.")
            continue
        process_plant_file(csv_path, plant_type, plant_name, capacity)

    print("\n✅ Data preparation complete. Ready for training.")
