"""
Model Evaluation — Honest Test Set Assessment
===============================================
PURPOSE: Evaluate trained models on the HELD-OUT TEST SET.
         These are the numbers you report to judges.
         Do NOT report validation metrics as final results.

ALSO: Compare against persistence baseline to prove ML adds value.

WHY BASELINE?
  A judge will ask: "How do you know XGBoost is better than a simple rule?"
  Comparing against a persistence model gives honest evidence.
  If XGBoost barely beats the baseline, your ML claim is weak.

METRICS USED:
  MAE   — intuitive, same units as generation (MW)
  RMSE  — penalises large errors more than MAE
  R²    — proportion of variance explained (1.0 = perfect, 0 = baseline)
  WAPE  — safer than MAPE for near-zero solar values

  DO NOT USE MAPE for solar: when generation → 0 (nights), MAPE → infinity.
  WAPE avoids this by dividing by sum of actuals, not individual values.

RUN: python ml/scripts/evaluate.py
"""

import os
import sys
import glob
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.feature_engineering import SOLAR_MODEL_FEATURES, WIND_MODEL_FEATURES, TARGET_COLUMN

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "trained_models")


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, label: str) -> dict:
    """Compute all evaluation metrics."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    total = np.sum(np.abs(y_true))
    wape = (np.sum(np.abs(y_true - y_pred)) / total) * 100 if total > 0 else np.nan

    print(f"\n  {label}")
    print(f"  {'─' * 40}")
    print(f"  MAE:   {mae:.3f} MW")
    print(f"  RMSE:  {rmse:.3f} MW")
    print(f"  R²:    {r2:.4f}")
    print(f"  WAPE:  {wape:.2f}%")

    return {"mae": mae, "rmse": rmse, "r2": r2, "wape": wape}


def persistence_baseline(y_true: np.ndarray, lag: int = 24) -> np.ndarray:
    """
    Persistence baseline: predict tomorrow = same time yesterday.
    lag=24 → 24-hour persistence (same time yesterday).
    This is the simplest possible forecast — if XGBoost can't beat this, ML isn't helping.
    """
    y_pred = np.roll(y_true, lag)
    y_pred[:lag] = y_true[:lag].mean()  # Fill first `lag` points with mean
    return y_pred


def evaluate_plant_type(plant_type: str, feature_cols: list):
    print(f"\n{'=' * 60}")
    print(f"  EVALUATING {plant_type.upper()} MODEL ON TEST SET")
    print(f"{'=' * 60}")

    # Load test data
    test_files = glob.glob(os.path.join(PROCESSED_DIR, f"{plant_type}*_test.csv"))
    if not test_files:
        print(f"  ⚠️  No test files found for {plant_type}")
        return

    test_df = pd.concat([pd.read_csv(f) for f in sorted(test_files)], ignore_index=True)
    print(f"  Test rows: {len(test_df):,}")

    # Load model
    model_path = os.path.join(MODEL_DIR, f"{plant_type}_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, f"scaler_{plant_type}.pkl")

    if not os.path.exists(model_path):
        print(f"  ❌ Model not found: {model_path}")
        print(f"     Run train_{plant_type}.py first.")
        return

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None

    # Prepare test data
    for col in feature_cols:
        if col not in test_df.columns:
            test_df[col] = 0

    X_test = test_df[feature_cols].fillna(0).values
    y_test = test_df[TARGET_COLUMN].values

    if scaler:
        X_test = scaler.transform(X_test)

    y_pred = np.clip(model.predict(X_test), 0, test_df["capacity_mw"].max())

    # ── XGBoost metrics ───────────────────────────────────────────────────────
    xgb_metrics = compute_metrics(y_test, y_pred, "XGBoost (Test Set)")

    # ── Persistence baseline ──────────────────────────────────────────────────
    y_baseline_24h = persistence_baseline(y_test, lag=24)
    y_baseline_168h = persistence_baseline(y_test, lag=168)

    baseline_24h = compute_metrics(y_test, y_baseline_24h, "Persistence Baseline (24h lag)")
    baseline_168h = compute_metrics(y_test, y_baseline_168h, "Persistence Baseline (168h lag)")

    # ── Improvement over baseline ─────────────────────────────────────────────
    mae_improvement = (1 - xgb_metrics["mae"] / baseline_24h["mae"]) * 100
    print(f"\n  ✅ XGBoost MAE improvement over 24h persistence: {mae_improvement:.1f}%")

    if mae_improvement < 5:
        print("  ⚠️  WARNING: XGBoost barely beats baseline. Consider more training data or features.")
    elif mae_improvement > 20:
        print("  🎯 Strong improvement — ML is clearly adding value.")

    # ── Horizon analysis ──────────────────────────────────────────────────────
    # Evaluate by forecast horizon bins to show how error grows with time
    print(f"\n  Horizon Breakdown (every 24h):")
    print(f"  {'Hours':>10} | {'MAE':>10} | {'RMSE':>10}")
    print(f"  {'-'*35}")

    if "horizon_hours" in test_df.columns:
        for h_start in range(1, 73, 24):
            h_end = min(h_start + 23, 72)
            mask = (test_df.get("horizon_hours", pd.Series([1]*len(test_df))) >= h_start) & \
                   (test_df.get("horizon_hours", pd.Series([1]*len(test_df))) <= h_end)
            if mask.sum() > 0:
                mae_h = mean_absolute_error(y_test[mask], y_pred[mask])
                rmse_h = np.sqrt(mean_squared_error(y_test[mask], y_pred[mask]))
                print(f"  h={h_start:2d}–{h_end:2d}         | {mae_h:>10.3f} | {rmse_h:>10.3f}")

    # ── Daytime-only solar metrics ─────────────────────────────────────────────
    if plant_type == "solar" and "is_daylight" in test_df.columns:
        daylight_mask = test_df["is_daylight"] == 1
        if daylight_mask.sum() > 0:
            print(f"\n  Daytime-only Solar Metrics (is_daylight=1):")
            compute_metrics(y_test[daylight_mask], y_pred[daylight_mask], "Solar Daytime Only")


def main():
    print("\n⚡ MODEL EVALUATION REPORT")
    print("  " + "="*58)
    print("  Evaluating on HELD-OUT TEST SET (most recent data)")
    print("  This simulates real deployment — models trained on past,")
    print("  evaluated on future.")
    print()

    evaluate_plant_type("solar", SOLAR_MODEL_FEATURES)
    evaluate_plant_type("wind", WIND_MODEL_FEATURES)

    print("\n" + "="*60)
    print("  NOTES FOR JUDGES")
    print("="*60)
    print("  1. All data is SIMULATED — models trained on synthetic data")
    print("  2. Metrics reflect genuine ML learning, not hardcoded values")
    print("  3. WAPE is used instead of MAPE (safer for near-zero solar)")
    print("  4. Separate models for solar and wind (different physics)")
    print("  5. Chronological split — no data leakage from future")
    print()


if __name__ == "__main__":
    main()
