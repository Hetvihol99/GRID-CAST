"""
Database Initialization and Seeding Script
============================================
PURPOSE: Creates all tables and seeds demo data for the hackathon.

RUN ORDER:
  1. python ml/scripts/generate_demo_data.py
  2. python ml/scripts/prepare_data.py
  3. python ml/scripts/train_solar.py
  4. python ml/scripts/train_wind.py
  5. python scripts/seed_db.py   ← THIS FILE

SEEDS:
  - 4 demo plants (2 solar, 2 wind)
  - 1 battery storage system
  - Historical generation (from simulated CSVs)
  - 72-hour demand profile

All data is clearly marked as SIMULATED.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.connection import engine, SessionLocal, create_tables
from app.database.models import Plant, BatteryStorage, GenerationData, DemandData, DataSource, PlantType
from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


DEMO_PLANTS = [
    {
        "name": "Rajasthan Solar Farm A",
        "plant_type": PlantType.SOLAR,
        "capacity_mw": 100.0,
        "latitude": 26.9124,
        "longitude": 75.7873,
        "location_name": "Jaipur, Rajasthan",
        "panel_efficiency": 0.18,
        "csv_file": "ml/data/raw/solar_plant_1.csv",
    },
    {
        "name": "Gujarat Solar Park B",
        "plant_type": PlantType.SOLAR,
        "capacity_mw": 150.0,
        "latitude": 23.0225,
        "longitude": 72.5714,
        "location_name": "Ahmedabad, Gujarat",
        "panel_efficiency": 0.20,
        "csv_file": "ml/data/raw/solar_plant_2.csv",
    },
    {
        "name": "Tamil Nadu Wind Farm I",
        "plant_type": PlantType.WIND,
        "capacity_mw": 200.0,
        "latitude": 8.7139,
        "longitude": 77.7567,
        "location_name": "Tirunelveli, Tamil Nadu",
        "turbine_cut_in_speed": 3.0,
        "turbine_rated_speed": 12.0,
        "turbine_cut_out_speed": 25.0,
        "csv_file": "ml/data/raw/wind_farm_1.csv",
    },
    {
        "name": "Andhra Pradesh Wind Farm II",
        "plant_type": PlantType.WIND,
        "capacity_mw": 100.0,
        "latitude": 15.9129,
        "longitude": 79.7400,
        "location_name": "Kurnool, Andhra Pradesh",
        "turbine_cut_in_speed": 3.5,
        "turbine_rated_speed": 13.0,
        "turbine_cut_out_speed": 28.0,
        "csv_file": "ml/data/raw/wind_farm_2.csv",
    },
]

DEMO_BATTERY = {
    "region": "default",
    "name": "Southern Grid Battery Storage",
    "capacity_mwh": 200.0,
    "current_soc_pct": 70.0,
    "max_charge_rate_mw": 80.0,
    "max_discharge_rate_mw": 100.0,
    "min_soc_pct": 10.0,
    "max_soc_pct": 95.0,
    "efficiency": 0.90,
}


def seed_plants(db) -> dict:
    """Create demo plants and return {csv_file: plant_id} mapping."""
    plant_map = {}
    for p in DEMO_PLANTS:
        existing = db.query(Plant).filter(Plant.name == p["name"]).first()
        if existing:
            logger.info(f"Plant already exists: {p['name']} (id={existing.id})")
            plant_map[p["csv_file"]] = existing.id
            continue

        plant = Plant(
            name=p["name"],
            plant_type=p["plant_type"],
            capacity_mw=p["capacity_mw"],
            latitude=p["latitude"],
            longitude=p["longitude"],
            location_name=p["location_name"],
            panel_efficiency=p.get("panel_efficiency"),
            turbine_cut_in_speed=p.get("turbine_cut_in_speed"),
            turbine_rated_speed=p.get("turbine_rated_speed"),
            turbine_cut_out_speed=p.get("turbine_cut_out_speed"),
        )
        db.add(plant)
        db.flush()  # Get the ID without committing
        plant_map[p["csv_file"]] = plant.id
        logger.info(f"Created plant: {p['name']} (id={plant.id})")

    db.commit()
    return plant_map


def seed_battery(db):
    """Create demo battery if not exists."""
    existing = db.query(BatteryStorage).filter(
        BatteryStorage.name == DEMO_BATTERY["name"]
    ).first()

    if existing:
        logger.info(f"Battery already exists: {existing.name}")
        return

    battery = BatteryStorage(**DEMO_BATTERY)
    db.add(battery)
    db.commit()
    logger.info(f"Created battery: {DEMO_BATTERY['name']}")


def seed_generation(db, plant_map: dict):
    """Load historical generation from CSVs into DB."""
    for csv_file, plant_id in plant_map.items():
        csv_path = os.path.join(os.path.dirname(__file__), "..", csv_file)
        if not os.path.exists(csv_path):
            logger.warning(f"CSV not found: {csv_path}. Skipping.")
            continue

        df = pd.read_csv(csv_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        # Take the most recent 720 hours (30 days) and align timestamps to today
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        df = df.tail(720).copy().reset_index(drop=True)
        start_ts = now - timedelta(hours=len(df) - 1)
        df["timestamp"] = [start_ts + timedelta(hours=i) for i in range(len(df))]

        # Get plant capacity for validation
        plant = db.query(Plant).filter(Plant.id == plant_id).first()

        records = []
        for _, row in df.iterrows():
            gen_mw = float(row["generation_mw"])
            is_valid = 0 <= gen_mw <= plant.capacity_mw

            records.append(GenerationData(
                plant_id=plant_id,
                timestamp=row["timestamp"].to_pydatetime() if hasattr(row["timestamp"], "to_pydatetime") else row["timestamp"],
                generation_mw=max(0, gen_mw),
                is_valid=is_valid,
                flag_reason="above_capacity" if gen_mw > plant.capacity_mw else None,
                data_source=DataSource.SIMULATED,
            ))

        # Bulk insert (skip existing due to unique constraint)
        try:
            db.bulk_save_objects(records)
            db.commit()
            logger.info(f"Seeded {len(records)} generation records for plant {plant_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to seed generation for plant {plant_id}: {e}")


def seed_demand(db):
    """Generate and seed a 14-day demand profile."""
    import numpy as np

    existing = db.query(DemandData).filter(DemandData.region == "default").count()
    if existing > 0:
        logger.info(f"Demand data already exists ({existing} records). Skipping.")
        return

    now = datetime.now(timezone.utc)
    timestamps = pd.date_range(
        start=now - timedelta(days=7),
        end=now + timedelta(hours=72),
        freq="h",
        tz="UTC",
    )

    np.random.seed(42)
    hours = timestamps.hour.values
    doy = timestamps.day_of_year.values

    # Realistic demand profile
    base = 800
    morning_peak = 150 * np.exp(-0.5 * ((hours - 9) / 2) ** 2)
    evening_peak = 200 * np.exp(-0.5 * ((hours - 19) / 2) ** 2)
    night_trough = -100 * np.exp(-0.5 * ((hours - 3) / 2) ** 2)
    seasonal = 100 * np.cos(2 * np.pi * (doy - 172) / 365) ** 2
    is_weekend = (timestamps.day_of_week >= 5).astype(int)
    noise = np.random.normal(0, 15, len(timestamps))

    demand = base + morning_peak + evening_peak + night_trough + seasonal - is_weekend * 80 + noise
    demand = np.clip(demand, 400, 1500)

    records = [
        DemandData(
            region="default",
            timestamp=ts.to_pydatetime(),
            demand_mw=round(float(mw), 1),
            is_forecast=True,
            data_source=DataSource.SIMULATED,
        )
        for ts, mw in zip(timestamps, demand)
    ]

    db.bulk_save_objects(records)
    db.commit()
    logger.info(f"Seeded {len(records)} demand records")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  DATABASE INITIALIZATION AND SEEDING")
    logger.info("=" * 60)

    create_tables()

    db = SessionLocal()
    try:
        logger.info("Seeding plants...")
        plant_map = seed_plants(db)

        logger.info("Seeding battery...")
        seed_battery(db)

        logger.info("Seeding generation history...")
        seed_generation(db, plant_map)

        logger.info("Seeding demand profile...")
        seed_demand(db)

        logger.info("=" * 60)
        logger.info("  ✅ Database seeding complete!")
        logger.info("  ⚠️  All data is SIMULATED for demo purposes.")
        logger.info("=" * 60)
    finally:
        db.close()
