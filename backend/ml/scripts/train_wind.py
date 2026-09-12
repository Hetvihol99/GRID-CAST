"""
Train Wind XGBoost Model
=========================
PURPOSE: Train a separate XGBoost model on wind farm data.

WHY SEPARATE MODEL FROM SOLAR?
  Solar: primary driver is solar irradiance, which is zero at night (hard zero).
         Cloud cover and hour-of-day dominate.
  Wind:  primary driver is wind speed (cubic relationship to power).
         24/7 generation possible. Cut-in/cut-out speeds create non-linearities.
  → Same feature set, but learned relationships are fundamentally different.
    Training separately lets each model specialise.

RUN: python ml/scripts/train_wind.py
OUTPUT: ml/trained_models/wind_model.pkl, ml/trained_models/scaler_wind.pkl
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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.feature_engineering import WIND_MODEL_FEATURES, TARGET_COLUMN

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "trained_models")
os.makedirs(MODEL_DIR, exist_ok=True)

FEATURE_COLS = WIND_MODEL_FEATURES
PLANT_TYPE = "wind"


def load_wind_data():
    """Load and combine all wind farm processed training/validation data."""
    train_files = glob.glob(os.path.join(PROCESSED_DIR, "wind_farm_*_train.csv"))
    val_files = glob.glob(os.path.join(PROCESSED_DIR, "wind_farm_*_val.csv"))

    if not train_files:
        raise FileNotFoundError(
            f"No wind training files found in {PROCESSED_DIR}. "
            "Run prepare_data.py first."
        )

    train = pd.concat([pd.read_csv(f) for f in sorted(train_files)], ignore_index=True)
    val = pd.concat([pd.read_csv(f) for f in sorted(val_files)], ignore_index=True)

    print(f"Loaded {len(train_files)} wind farm(s)")
    print(f"Train: {len(train):,} rows | Val: {len(val):,} rows")

    return train, val


def prepare_Xy(df: pd.DataFrame):
    available_cols = [c for c in FEATURE_COLS if c in df.columns]
    missing_cols = set(FEATURE_COLS) - set(available_cols)
    if missing_cols:
        print(f"  ⚠️  Missing feature columns: {missing_cols} — filling with 0")
        for col in missing_cols:
            df[col] = 0

    X = df[FEATURE_COLS].fillna(0).values
    y = df[TARGET_COLUMN].values
    return X, y


def train_wind_model():
    print("\n" + "="*60)
    print("  TRAINING WIND XGBOOST MODEL")
    print("="*60)

    train_df, val_df = load_wind_data()
    X_train, y_train = prepare_Xy(train_df)
    X_val, y_val = prepare_Xy(val_df)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Wind model may benefit from slightly deeper trees because
    # the cubic power curve creates more complex non-linearities
    model = xgb.XGBRegressor(
        n_estimators=500,
        max_depth=7,         # Slightly deeper for wind power curve non-linearity
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.05,
        reg_lambda=1.0,
        min_child_weight=3,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
        early_stopping_rounds=50,
        verbosity=0,
    )

    print("\nTraining XGBoost with early stopping (patience=50)...")
    model.fit(
        X_train_scaled,
        y_train,
        eval_set=[(X_val_scaled, y_val)],
        verbose=50,
    )

    print(f"  Best iteration: {model.best_iteration}")
    print(f"  Best val score: {model.best_score:.4f}")

    y_pred_val = np.clip(model.predict(X_val_scaled), 0, train_df["capacity_mw"].max())

    mae = mean_absolute_error(y_val, y_pred_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
    r2 = r2_score(y_val, y_pred_val)

    total_actual = np.sum(np.abs(y_val))
    wape = (np.sum(np.abs(y_val - y_pred_val)) / total_actual) * 100 if total_actual > 0 else np.nan

    print("\n" + "-"*40)
    print("  VALIDATION METRICS (Wind)")
    print("-"*40)
    print(f"  MAE:   {mae:.3f} MW")
    print(f"  RMSE:  {rmse:.3f} MW")
    print(f"  R²:    {r2:.4f}")
    print(f"  WAPE:  {wape:.2f}%")
    print("-"*40)

    importance = dict(zip(FEATURE_COLS, model.feature_importances_))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]

    print("\n  Top 10 Features by Importance:")
    for i, (feat, imp) in enumerate(top_features, 1):
        print(f"  {i:2d}. {feat:<30} {imp:.4f}")

    model_path = os.path.join(MODEL_DIR, "wind_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler_wind.pkl")
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    version = f"v{datetime.now().strftime('%Y%m%d_%H%M')}"
    metadata = {
        "model_name": "wind_xgboost",
        "plant_type": "wind",
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
        "data_source": "simulated — not real plant data",
    }

    meta_path = os.path.join(MODEL_DIR, "wind_model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✅ Wind model saved: {model_path}")
    print(f"✅ Wind scaler saved: {scaler_path}")
    print(f"✅ Metadata saved:   {meta_path}")

    return model, scaler, metadata


if __name__ == "__main__":
    train_wind_model()
