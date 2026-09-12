"""
Train Solar XGBoost Model
==========================
PURPOSE: Train a genuine XGBoost model on processed solar plant data.
         This is NOT a mock — features go in, model learns, predictions come out.

MODEL DESIGN:
  - Separate model for solar vs wind (different physics)
  - XGBoost regressor (not classifier)
  - Features: weather + time + lags + plant parameters
  - Target: generation_mw
  - Chronological train/val split — no shuffling

HYPERPARAMETERS: Practical starting config. Tune further if time permits.
  - n_estimators: 500 (with early stopping)
  - max_depth: 6 (moderate, avoids overfitting)
  - learning_rate: 0.05 (slow, more robust)
  - subsample: 0.8 (bagging-style)
  - colsample_bytree: 0.8 (feature subsampling)
  - reg_alpha: 0.1, reg_lambda: 1.0 (L1+L2 regularization)

RUN: python ml/scripts/train_solar.py
OUTPUT: ml/trained_models/solar_model.pkl, ml/trained_models/scaler_solar.pkl
"""

import os
import sys
import glob
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Allow import from parent backend dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.feature_engineering import SOLAR_MODEL_FEATURES, TARGET_COLUMN

# ── Paths ─────────────────────────────────────────────────────────────────────
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "trained_models")
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURE_COLS = SOLAR_MODEL_FEATURES
PLANT_TYPE = "solar"


def load_solar_data():
    """Load and combine all solar plant processed training/validation data."""
    train_files = glob.glob(os.path.join(PROCESSED_DIR, "solar_plant_*_train.csv"))
    val_files = glob.glob(os.path.join(PROCESSED_DIR, "solar_plant_*_val.csv"))

    if not train_files:
        raise FileNotFoundError(
            f"No solar training files found in {PROCESSED_DIR}. "
            "Run prepare_data.py first."
        )

    train_dfs = [pd.read_csv(f) for f in sorted(train_files)]
    val_dfs = [pd.read_csv(f) for f in sorted(val_files)]

    train = pd.concat(train_dfs, ignore_index=True)
    val = pd.concat(val_dfs, ignore_index=True)

    print(f"Loaded {len(train_files)} solar plant(s)")
    print(f"Train: {len(train):,} rows | Val: {len(val):,} rows")

    return train, val


def prepare_Xy(df: pd.DataFrame):
    """Extract feature matrix X and target vector y."""
    available_cols = [c for c in FEATURE_COLS if c in df.columns]
    missing_cols = set(FEATURE_COLS) - set(available_cols)
    if missing_cols:
        print(f"  ⚠️  Missing feature columns: {missing_cols} — filling with 0")
        for col in missing_cols:
            df[col] = 0

    X = df[FEATURE_COLS].fillna(0).values
    y = df[TARGET_COLUMN].values
    return X, y


def train_solar_model():
    print("\n" + "="*60)
    print("  TRAINING SOLAR XGBOOST MODEL")
    print("="*60)

    # ── Load data ─────────────────────────────────────────────────────────────
    train_df, val_df = load_solar_data()
    X_train, y_train = prepare_Xy(train_df)
    X_val, y_val = prepare_Xy(val_df)

    # ── Scale features ────────────────────────────────────────────────────────
    # XGBoost is tree-based and generally doesn't require scaling,
    # but we scale anyway for consistency with potential future models.
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # ── XGBoost configuration ─────────────────────────────────────────────────
    # Practical starting config for solar forecasting.
    # Do NOT blindly use default params — each choice is justified:
    #   n_estimators=500: enough trees; early stopping prevents overfitting
    #   max_depth=6: moderate depth, captures non-linear weather interactions
    #   learning_rate=0.05: slow learning → more robust generalisation
    #   subsample=0.8: row sampling reduces variance (bagging effect)
    #   colsample_bytree=0.8: feature sampling prevents over-reliance on one feature
    #   reg_alpha=0.1: L1 regularization → sparse, less overfitting
    #   reg_lambda=1.0: L2 regularization → smooth weights
    #   min_child_weight=3: prevents splits on very few samples
    model = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        min_child_weight=3,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,           # Use all CPU cores
        tree_method="hist",  # Faster for large datasets
        early_stopping_rounds=50,
        verbosity=0,
    )

    # ── Train with early stopping ─────────────────────────────────────────────
    # Early stopping monitors validation MAE and stops when it stops improving.
    # This prevents overfitting without manually tuning n_estimators.
    print("\nTraining XGBoost with early stopping (patience=50)...")
    model.fit(
        X_train_scaled,
        y_train,
        eval_set=[(X_val_scaled, y_val)],
        verbose=50,
    )

    print(f"  Best iteration: {model.best_iteration}")
    print(f"  Best val score: {model.best_score:.4f}")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    y_pred_train = model.predict(X_train_scaled)
    y_pred_val = model.predict(X_val_scaled)

    # Clip predictions to valid range
    capacity_max = train_df["capacity_mw"].max()
    y_pred_val = np.clip(y_pred_val, 0, capacity_max)

    mae = mean_absolute_error(y_val, y_pred_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
    r2 = r2_score(y_val, y_pred_val)

    # WAPE: Weighted Absolute Percentage Error (safer than MAPE for near-zero values)
    # WAPE = sum(|actual - predicted|) / sum(|actual|) × 100
    # More reliable than MAPE because it doesn't divide by near-zero denominators.
    total_actual = np.sum(np.abs(y_val))
    wape = (np.sum(np.abs(y_val - y_pred_val)) / total_actual) * 100 if total_actual > 0 else np.nan

    print("\n" + "-"*40)
    print("  VALIDATION METRICS (Solar)")
    print("-"*40)
    print(f"  MAE:   {mae:.3f} MW")
    print(f"  RMSE:  {rmse:.3f} MW")
    print(f"  R²:    {r2:.4f}")
    print(f"  WAPE:  {wape:.2f}% (Weighted Absolute Percentage Error)")
    print("-"*40)
    print("  NOTE: These metrics are on the VALIDATION set, not test set.")
    print("  Run evaluate.py on the test set for honest final metrics.")

    # ── Feature importance ────────────────────────────────────────────────────
    importance = dict(zip(FEATURE_COLS, model.feature_importances_))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]

    print("\n  Top 10 Features by Importance (XGBoost gain):")
    for i, (feat, imp) in enumerate(top_features, 1):
        print(f"  {i:2d}. {feat:<30} {imp:.4f}")

    # ── Save model ────────────────────────────────────────────────────────────
    version = f"v{datetime.now().strftime('%Y%m%d_%H%M')}"
    model_path = os.path.join(MODEL_DIR, "solar_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler_solar.pkl")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"\n✅ Solar model saved: {model_path}")
    print(f"✅ Solar scaler saved: {scaler_path}")

    # ── Save metadata ─────────────────────────────────────────────────────────
    metadata = {
        "model_name": "solar_xgboost",
        "plant_type": "solar",
        "version": version,
        "trained_at": datetime.now().isoformat(),
        "features": FEATURE_COLS,
        "n_features": len(FEATURE_COLS),
        "best_iteration": int(model.best_iteration),
        "metrics": {
            "mae": round(float(mae), 4),
            "rmse": round(float(rmse), 4),
            "r2": round(float(r2), 4),
            "wape": round(float(wape), 4) if not np.isnan(wape) else None,
        },
        "top_features": {str(feat): round(float(imp), 6) for feat, imp in top_features},
        "hyperparameters": {
            "n_estimators": 500,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
        },
        "data_source": "simulated — not real plant data",
    }

    meta_path = os.path.join(MODEL_DIR, "solar_model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Metadata saved: {meta_path}")

    return model, scaler, metadata


if __name__ == "__main__":
    train_solar_model()
