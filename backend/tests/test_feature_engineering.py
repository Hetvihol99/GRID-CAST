"""Tests for feature engineering — especially leakage prevention."""

import pytest
import pandas as pd
import numpy as np
from ml.feature_engineering import (
    add_time_features,
    add_lag_features,
    build_training_features,
    get_feature_columns,
)


def make_test_df(n=200, plant_type="solar", capacity_mw=100):
    """Create a minimal test DataFrame."""
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "generation_mw": np.random.uniform(0, capacity_mw, n),
        "capacity_mw": capacity_mw,
        "temperature_c": np.random.normal(25, 5, n),
        "humidity_pct": np.random.uniform(30, 80, n),
        "cloud_cover_pct": np.random.uniform(0, 100, n),
        "solar_irradiance_wm2": np.random.uniform(0, 800, n),
        "wind_speed_ms": np.random.uniform(0, 15, n),
        "wind_direction_deg": np.random.uniform(0, 360, n),
        "pressure_hpa": np.random.normal(1013, 5, n),
        "rainfall_mm": np.zeros(n),
    })
    return df


class TestTimeFeatures:
    def test_hour_range(self):
        df = make_test_df()
        df = add_time_features(df)
        assert df["hour"].between(0, 23).all()

    def test_month_range(self):
        df = make_test_df()
        df = add_time_features(df)
        assert df["month"].between(1, 12).all()

    def test_cyclical_encoding_range(self):
        df = make_test_df()
        df = add_time_features(df)
        assert df["hour_sin"].between(-1, 1).all()
        assert df["hour_cos"].between(-1, 1).all()

    def test_is_daylight_binary(self):
        df = make_test_df()
        df = add_time_features(df)
        assert set(df["is_daylight"].unique()).issubset({0, 1})


class TestLagFeatures:
    def test_lag_1_is_shifted(self):
        """lag_1 should equal generation_mw from previous row."""
        df = make_test_df(50)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df_lagged = add_lag_features(df)
        # Row 5's lag_1 should equal row 4's generation
        assert df_lagged.loc[5, "generation_lag_1"] == pytest.approx(
            df.loc[4, "generation_mw"], abs=0.001
        )

    def test_no_future_leakage(self):
        """lag_1 at row i should use row i-1, never row i+1."""
        df = make_test_df(50)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df_lagged = add_lag_features(df)

        # If there were future leakage, lag_1[i] == generation[i+1]
        # Verify this is NOT the case for a known row
        for i in range(1, 10):
            assert df_lagged.loc[i, "generation_lag_1"] != pytest.approx(
                df.loc[i + 1, "generation_mw"], abs=0.001
            )

    def test_first_rows_are_nan(self):
        """First row should have NaN lag_1 (no prior data)."""
        df = make_test_df(200)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df_lagged = add_lag_features(df)
        assert pd.isna(df_lagged.loc[0, "generation_lag_1"])


class TestBuildTrainingFeatures:
    def test_drops_nan_lag_rows(self):
        """build_training_features should drop rows with NaN lags."""
        df = make_test_df(300)  # Need enough rows for lag_168
        result = build_training_features(df, capacity_mw=100, plant_type="solar")
        # No NaN in lag columns
        assert not result["generation_lag_1"].isna().any()
        assert not result["generation_lag_24"].isna().any()

    def test_feature_columns_present(self):
        """All expected feature columns should be in result."""
        df = make_test_df(300)
        result = build_training_features(df, capacity_mw=100, plant_type="solar")
        expected = get_feature_columns("solar")
        for col in expected:
            assert col in result.columns, f"Missing feature: {col}"

    def test_positive_generation_only(self):
        """No negative generation in training data."""
        df = make_test_df(300)
        result = build_training_features(df, capacity_mw=100, plant_type="solar")
        assert (result["generation_mw"] >= 0).all()
