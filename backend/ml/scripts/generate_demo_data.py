"""
Generate Realistic Demo Data
==============================
PURPOSE: Creates synthetic but physically plausible renewable generation data.
         This is used to TRAIN a real XGBoost model, not to fake predictions.

WHY SYNTHETIC?
  Real plant datasets require NDAs or subscriptions.
  Synthetic data with realistic physics patterns lets the model genuinely learn.
  All output is clearly labeled as SIMULATED.

GENERATED DATA:
  - 2 Solar plants (100 MW, 150 MW)
  - 2 Wind farms (200 MW, 100 MW)
  - 2 years of hourly data (17,520 rows per plant)
  - Realistic solar irradiance curve (Gaussian peak at solar noon)
  - Realistic wind speed patterns (Weibull distribution + seasonal)
  - Actual generation = f(weather) + noise (not just random)

OUTPUT FILES:
  ml/data/raw/solar_plant_1.csv
  ml/data/raw/solar_plant_2.csv
  ml/data/raw/wind_farm_1.csv
  ml/data/raw/wind_farm_2.csv
  ml/data/raw/demand_profile.csv
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Fix seed for reproducibility
np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Date range: 2 years hourly ────────────────────────────────────────────────
START = "2023-01-01"
END = "2024-12-31"
timestamps = pd.date_range(start=START, end=END, freq="h", tz="UTC")
N = len(timestamps)

print(f"Generating {N} hourly records ({START} to {END})")

hours = timestamps.hour
days = timestamps.day
months = timestamps.month
day_of_year = timestamps.day_of_year.values


# ══════════════════════════════════════════════════════════════════════════════
# SOLAR GENERATION MODEL
# Physics: Generation ≈ GHI × panel_efficiency × capacity × (1 - cloud_cover) × temperature_factor
# ══════════════════════════════════════════════════════════════════════════════

def generate_solar_irradiance(hours, day_of_year, latitude=22.5):
    """
    Simulate Global Horizontal Irradiance (GHI) in W/m².
    Peak at solar noon, zero at night, seasonal variation via declination.
    """
    solar_noon = 12  # Approximate
    hour_arr = hours.values if hasattr(hours, "values") else np.array(hours)
    doy = np.array(day_of_year)

    # Declination: solar angle varies by season (-23.5° to +23.5°)
    declination = 23.5 * np.sin(2 * np.pi * (doy - 81) / 365)

    # Day length approximation (longer in summer, shorter in winter)
    day_length = 12 + 4 * np.sin(2 * np.pi * (doy - 80) / 365)
    sunrise = solar_noon - day_length / 2
    sunset = solar_noon + day_length / 2

    # Clear-sky irradiance: Gaussian curve centered at solar noon
    irradiance = np.zeros(len(hour_arr))
    daylight_mask = (hour_arr >= sunrise) & (hour_arr <= sunset)

    peak_irradiance = 900 + 50 * np.sin(2 * np.pi * (doy - 172) / 365)  # ~900 W/m² peak, seasonal
    sigma = day_length / 5  # Width of the bell curve

    irradiance[daylight_mask] = (
        peak_irradiance[daylight_mask]
        * np.exp(-0.5 * ((hour_arr[daylight_mask] - solar_noon) / sigma[daylight_mask]) ** 2)
    )

    # Add random cloud attenuation
    cloud_attenuation = np.random.beta(2, 1, size=len(hour_arr))  # Skewed toward clear sky
    irradiance = irradiance * cloud_attenuation
    irradiance = np.clip(irradiance, 0, 1361)

    return irradiance


def generate_solar_plant(name: str, capacity_mw: float, panel_efficiency: float = 0.18):
    """Generate a realistic solar plant dataset."""
    print(f"  Generating solar plant: {name} ({capacity_mw} MW)")

    irradiance = generate_solar_irradiance(hours, day_of_year)

    # Cloud cover derived from irradiance attenuation (inverse relationship)
    clear_sky_irr = np.where(hours.values >= 6, 900 * np.maximum(0, np.sin(np.pi * (hours.values - 6) / 14)), 0)
    cloud_cover = np.clip(1 - irradiance / (clear_sky_irr + 1), 0, 1) * 100

    # Temperature: seasonal + daily variation
    temp_base = 25 + 10 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    temp_daily = 5 * np.sin(2 * np.pi * (hours.values - 6) / 24)
    temperature = temp_base + temp_daily + np.random.normal(0, 2, N)

    # Temperature coefficient: efficiency drops at high temperatures
    temp_factor = 1 - 0.004 * np.maximum(0, temperature - 25)

    # Generation: irradiance × efficiency × area × temp_factor
    # Simplified: generation_mw = (irradiance / 1000) × capacity × panel_efficiency × temp_factor × (1 - cloud_factor)
    cloud_factor = cloud_cover / 100
    generation_mw = (
        (irradiance / 1000)  # Normalize to kW/m²
        * capacity_mw
        * panel_efficiency
        * temp_factor
        * (1 - 0.5 * cloud_factor)  # Cloud reduces generation
    )

    # Add realistic noise and clamp
    noise = np.random.normal(0, 0.02 * capacity_mw, N)  # ±2% noise
    generation_mw = np.clip(generation_mw + noise, 0, capacity_mw)

    # Humidity, pressure, rainfall
    humidity = 60 + 20 * np.random.beta(2, 2, N)
    pressure = 1013 + np.random.normal(0, 5, N)
    rainfall = np.where(cloud_cover > 70, np.random.exponential(2, N), 0)
    wind_speed = np.abs(np.random.normal(3, 2, N))  # Low wind at solar sites
    wind_direction = np.random.uniform(0, 360, N)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "plant_id": name,
        "plant_type": "solar",
        "capacity_mw": capacity_mw,
        "temperature_c": np.round(temperature, 2),
        "humidity_pct": np.round(np.clip(humidity, 0, 100), 1),
        "cloud_cover_pct": np.round(np.clip(cloud_cover, 0, 100), 1),
        "solar_irradiance_wm2": np.round(np.clip(irradiance, 0, 1400), 1),
        "wind_speed_ms": np.round(np.clip(wind_speed, 0, 50), 2),
        "wind_direction_deg": np.round(wind_direction, 1),
        "pressure_hpa": np.round(np.clip(pressure, 900, 1100), 1),
        "rainfall_mm": np.round(np.clip(rainfall, 0, 100), 2),
        "generation_mw": np.round(generation_mw, 3),
        "data_source": "simulated",
    })

    return df


# ══════════════════════════════════════════════════════════════════════════════
# WIND GENERATION MODEL
# Physics: P = 0.5 × ρ × A × Cp × v³, with cut-in and cut-out speeds
# ══════════════════════════════════════════════════════════════════════════════

def generate_wind_speed(n, seasonal_factor=1.0):
    """
    Generate realistic wind speeds using Weibull distribution.
    k=2 (Rayleigh) is standard for wind energy analysis.
    """
    # Seasonal pattern: higher wind in winter
    seasonal = 1 + 0.3 * np.cos(2 * np.pi * (day_of_year - 350) / 365)
    scale = 8 * seasonal * seasonal_factor  # Mean wind speed ~8 m/s

    wind = np.random.weibull(2, n) * scale

    # Daily variation: slightly higher during daytime
    daily_boost = 1 + 0.1 * np.sin(2 * np.pi * (hours.values - 6) / 24)
    wind = wind * daily_boost

    # Autocorrelation: wind persists (don't change drastically each hour)
    smoothed = pd.Series(wind).ewm(span=3).mean().values

    return np.clip(smoothed, 0, 40)


def generate_wind_plant(
    name: str,
    capacity_mw: float,
    cut_in: float = 3.0,
    rated: float = 12.0,
    cut_out: float = 25.0,
):
    """Generate a realistic wind farm dataset using turbine power curve."""
    print(f"  Generating wind farm: {name} ({capacity_mw} MW)")

    wind_speed = generate_wind_speed(N)

    # Power curve:
    # v < cut_in: 0 (turbine stalled)
    # cut_in <= v <= rated: cubic increase (P ∝ v³)
    # rated < v < cut_out: rated power (100% capacity)
    # v >= cut_out: 0 (turbine protection shutdown)
    generation_fraction = np.zeros(N)

    in_range = (wind_speed >= cut_in) & (wind_speed <= rated)
    rated_range = (wind_speed > rated) & (wind_speed < cut_out)

    generation_fraction[in_range] = (
        (wind_speed[in_range] - cut_in) / (rated - cut_in)
    ) ** 3

    generation_fraction[rated_range] = 1.0
    generation_mw = generation_fraction * capacity_mw

    # Add realistic noise
    noise = np.random.normal(0, 0.015 * capacity_mw, N)
    generation_mw = np.clip(generation_mw + noise, 0, capacity_mw)

    # Associated weather
    temperature = 20 + 8 * np.sin(2 * np.pi * (day_of_year - 80) / 365) + np.random.normal(0, 3, N)
    cloud_cover = np.random.beta(1.5, 2, N) * 100
    irradiance = np.where(hours.values >= 6,
                          600 * (1 - cloud_cover / 100) * np.maximum(0, np.sin(np.pi * (hours.values - 6) / 14)),
                          0)
    humidity = 55 + 20 * np.random.beta(2, 2, N)
    pressure = 1010 + np.random.normal(0, 8, N)
    rainfall = np.where(cloud_cover > 65, np.random.exponential(1.5, N), 0)
    wind_direction = np.random.uniform(0, 360, N)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "plant_id": name,
        "plant_type": "wind",
        "capacity_mw": capacity_mw,
        "temperature_c": np.round(temperature, 2),
        "humidity_pct": np.round(np.clip(humidity, 0, 100), 1),
        "cloud_cover_pct": np.round(np.clip(cloud_cover, 0, 100), 1),
        "solar_irradiance_wm2": np.round(np.clip(irradiance, 0, 1400), 1),
        "wind_speed_ms": np.round(wind_speed, 2),
        "wind_direction_deg": np.round(wind_direction, 1),
        "pressure_hpa": np.round(np.clip(pressure, 900, 1100), 1),
        "rainfall_mm": np.round(np.clip(rainfall, 0, 100), 2),
        "generation_mw": np.round(generation_mw, 3),
        "data_source": "simulated",
    })

    return df


# ══════════════════════════════════════════════════════════════════════════════
# DEMAND PROFILE
# Realistic demand: daily peak at 9 AM and 7 PM, lower at night, seasonal
# ══════════════════════════════════════════════════════════════════════════════

def generate_demand():
    """
    Generate a realistic regional electricity demand profile.
    Base demand: 800 MW
    Peaks: morning (9 AM) and evening (7 PM)
    Seasonal: higher in summer (cooling) and winter (heating)
    """
    print("  Generating demand profile...")

    base = 800  # MW

    # Daily pattern: two peaks
    morning_peak = 150 * np.exp(-0.5 * ((hours.values - 9) / 2) ** 2)
    evening_peak = 200 * np.exp(-0.5 * ((hours.values - 19) / 2) ** 2)
    night_trough = -100 * np.exp(-0.5 * ((hours.values - 3) / 2) ** 2)

    daily_pattern = morning_peak + evening_peak + night_trough

    # Seasonal: higher in summer and winter
    seasonal = 100 * np.cos(2 * np.pi * (day_of_year - 172) / 365) ** 2

    # Weekend reduction
    is_weekend = (timestamps.day_of_week >= 5).astype(int)
    weekend_reduction = is_weekend * 80

    demand = base + daily_pattern + seasonal - weekend_reduction
    demand = demand + np.random.normal(0, 20, N)  # Random noise
    demand = np.clip(demand, 400, 1500)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "region": "default",
        "demand_mw": np.round(demand, 1),
        "data_source": "simulated",
    })

    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🌞 Generating Solar Plants...")
    solar1 = generate_solar_plant("solar_plant_1", capacity_mw=100, panel_efficiency=0.18)
    solar2 = generate_solar_plant("solar_plant_2", capacity_mw=150, panel_efficiency=0.20)

    print("\n💨 Generating Wind Farms...")
    wind1 = generate_wind_plant("wind_farm_1", capacity_mw=200, cut_in=3.0, rated=12.0, cut_out=25.0)
    wind2 = generate_wind_plant("wind_farm_2", capacity_mw=100, cut_in=3.5, rated=13.0, cut_out=28.0)

    print("\n⚡ Generating Demand Profile...")
    demand = generate_demand()

    # Save to CSV
    solar1.to_csv(os.path.join(OUTPUT_DIR, "solar_plant_1.csv"), index=False)
    solar2.to_csv(os.path.join(OUTPUT_DIR, "solar_plant_2.csv"), index=False)
    wind1.to_csv(os.path.join(OUTPUT_DIR, "wind_farm_1.csv"), index=False)
    wind2.to_csv(os.path.join(OUTPUT_DIR, "wind_farm_2.csv"), index=False)
    demand.to_csv(os.path.join(OUTPUT_DIR, "demand_profile.csv"), index=False)

    print(f"\n✅ Demo data saved to: {OUTPUT_DIR}")
    print(f"   solar_plant_1.csv  → {len(solar1):,} rows, generation range: {solar1['generation_mw'].min():.1f}–{solar1['generation_mw'].max():.1f} MW")
    print(f"   solar_plant_2.csv  → {len(solar2):,} rows, generation range: {solar2['generation_mw'].min():.1f}–{solar2['generation_mw'].max():.1f} MW")
    print(f"   wind_farm_1.csv    → {len(wind1):,} rows, generation range: {wind1['generation_mw'].min():.1f}–{wind1['generation_mw'].max():.1f} MW")
    print(f"   wind_farm_2.csv    → {len(wind2):,} rows, generation range: {wind2['generation_mw'].min():.1f}–{wind2['generation_mw'].max():.1f} MW")
    print(f"   demand_profile.csv → {len(demand):,} rows, demand range: {demand['demand_mw'].min():.1f}–{demand['demand_mw'].max():.1f} MW")
    print("\n⚠️  NOTE: All data is SIMULATED. Do not use for real grid operations.")
