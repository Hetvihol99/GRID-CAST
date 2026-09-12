"""
SQLAlchemy ORM models — defines every table in the PostgreSQL database.

Schema relationships:
    Plant ──< WeatherData
    Plant ──< GenerationData
    Plant ──< Forecast
    BatteryStorage (one per region/system)
    DemandData (region-level, not per-plant)
    Alert ──< Recommendation
    ModelMetadata (tracks trained model versions)
"""

from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime,
    ForeignKey, Text, Enum, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database.connection import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class PlantType(str, enum.Enum):
    SOLAR = "solar"
    WIND = "wind"


class AlertSeverity(str, enum.Enum):
    NORMAL = "normal"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, enum.Enum):
    SURPLUS = "surplus"
    DEFICIT = "deficit"
    OUTAGE_RISK = "outage_risk"


class RecommendationAction(str, enum.Enum):
    CHARGE_STORAGE = "charge_storage"
    DISCHARGE_STORAGE = "discharge_storage"
    PREPARE_BACKUP = "prepare_backup"
    CONSIDER_CURTAILMENT = "consider_curtailment"
    MONITOR = "monitor"


class DataSource(str, enum.Enum):
    REAL = "real"
    SIMULATED = "simulated"
    CACHED = "cached"


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    """Operator accounts registered through the dashboard."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False, unique=True, index=True)
    role = Column(String(50), nullable=False)
    organization = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Plants ────────────────────────────────────────────────────────────────────

class Plant(Base):
    """
    Represents a renewable generation plant (solar or wind).
    Each plant has its own weather data, generation history, and forecasts.
    """
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    plant_type = Column(Enum(PlantType), nullable=False)  # solar | wind
    capacity_mw = Column(Float, nullable=False)           # Installed capacity (MW)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)

    # Optional technical details
    panel_efficiency = Column(Float, nullable=True)       # Solar: panel efficiency %
    turbine_cut_in_speed = Column(Float, nullable=True)   # Wind: cut-in speed m/s
    turbine_rated_speed = Column(Float, nullable=True)    # Wind: rated speed m/s
    turbine_cut_out_speed = Column(Float, nullable=True)  # Wind: cut-out speed m/s

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    weather_data = relationship("WeatherData", back_populates="plant", cascade="all, delete-orphan")
    generation_data = relationship("GenerationData", back_populates="plant", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="plant", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("capacity_mw > 0", name="check_capacity_positive"),
    )


# ── Weather Data ──────────────────────────────────────────────────────────────

class WeatherData(Base):
    """
    Weather observations or forecasts linked to a specific plant location.
    is_forecast=True means this is a future weather forecast (from API).
    is_forecast=False means this is a historical observation.
    """
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    is_forecast = Column(Boolean, default=False)          # True = future forecast

    # Weather variables
    temperature_c = Column(Float, nullable=True)          # Celsius
    humidity_pct = Column(Float, nullable=True)           # 0–100%
    cloud_cover_pct = Column(Float, nullable=True)        # 0–100%
    solar_irradiance_wm2 = Column(Float, nullable=True)   # W/m² (GHI)
    wind_speed_ms = Column(Float, nullable=True)          # m/s at hub height
    wind_direction_deg = Column(Float, nullable=True)     # 0–360 degrees
    pressure_hpa = Column(Float, nullable=True)           # hPa
    rainfall_mm = Column(Float, nullable=True)            # mm/hr
    visibility_km = Column(Float, nullable=True)          # km

    data_source = Column(Enum(DataSource), default=DataSource.REAL)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    plant = relationship("Plant", back_populates="weather_data")

    __table_args__ = (
        UniqueConstraint("plant_id", "timestamp", "is_forecast", name="uq_weather_plant_ts_type"),
        Index("idx_weather_plant_ts", "plant_id", "timestamp"),
        CheckConstraint("humidity_pct >= 0 AND humidity_pct <= 100", name="check_humidity_range"),
        CheckConstraint("cloud_cover_pct >= 0 AND cloud_cover_pct <= 100", name="check_cloud_range"),
        CheckConstraint("wind_direction_deg >= 0 AND wind_direction_deg <= 360", name="check_wind_dir"),
    )


# ── Generation Data ───────────────────────────────────────────────────────────

class GenerationData(Base):
    """
    Actual historical generation readings per plant.
    Used for model training and for lag feature calculation at inference.
    generation_mw must be >= 0 and <= plant.capacity_mw (enforced in service layer).
    """
    __tablename__ = "generation_data"

    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    generation_mw = Column(Float, nullable=False)

    # Quality flags
    is_valid = Column(Boolean, default=True)              # False if flagged as bad data
    flag_reason = Column(String(200), nullable=True)      # e.g., "above_capacity", "sensor_error"
    data_source = Column(Enum(DataSource), default=DataSource.REAL)

    # Relationship
    plant = relationship("Plant", back_populates="generation_data")

    __table_args__ = (
        UniqueConstraint("plant_id", "timestamp", name="uq_generation_plant_ts"),
        Index("idx_generation_plant_ts", "plant_id", "timestamp"),
        CheckConstraint("generation_mw >= 0", name="check_generation_non_negative"),
    )


# ── Demand Data ───────────────────────────────────────────────────────────────

class DemandData(Base):
    """
    Expected regional electricity demand.
    Region-level, not per-plant.
    For MVP: populated from synthetic/user-provided data.
    """
    __tablename__ = "demand_data"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String(100), nullable=False, default="default")
    timestamp = Column(DateTime(timezone=True), nullable=False)
    demand_mw = Column(Float, nullable=False)
    is_forecast = Column(Boolean, default=True)           # True = future expected demand
    data_source = Column(Enum(DataSource), default=DataSource.SIMULATED)

    __table_args__ = (
        UniqueConstraint("region", "timestamp", name="uq_demand_region_ts"),
        Index("idx_demand_region_ts", "region", "timestamp"),
        CheckConstraint("demand_mw > 0", name="check_demand_positive"),
    )


# ── Battery / Storage ─────────────────────────────────────────────────────────

class BatteryStorage(Base):
    """
    Battery/storage system parameters.
    One battery entry per grid region (can be extended to per-plant).
    Current SOC should be updated periodically from real data or simulation.
    """
    __tablename__ = "battery_storage"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String(100), nullable=False, default="default")
    name = Column(String(200), nullable=False)
    capacity_mwh = Column(Float, nullable=False)           # Total energy capacity (MWh)
    current_soc_pct = Column(Float, nullable=False)        # Current State of Charge (0–100%)
    max_charge_rate_mw = Column(Float, nullable=False)     # Max charge power (MW)
    max_discharge_rate_mw = Column(Float, nullable=False)  # Max discharge power (MW)
    min_soc_pct = Column(Float, default=10.0)              # Minimum safe SOC (%)
    max_soc_pct = Column(Float, default=95.0)              # Maximum safe SOC (%)
    efficiency = Column(Float, default=0.90)               # Round-trip efficiency (0–1)
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("capacity_mwh > 0", name="check_battery_capacity_positive"),
        CheckConstraint("current_soc_pct >= 0 AND current_soc_pct <= 100", name="check_soc_range"),
        CheckConstraint("min_soc_pct >= 0 AND max_soc_pct <= 100", name="check_soc_limits"),
        CheckConstraint("efficiency > 0 AND efficiency <= 1", name="check_efficiency_range"),
    )


# ── Forecasts ─────────────────────────────────────────────────────────────────

class Forecast(Base):
    """
    ML-generated generation forecasts per plant per timestamp.
    Each row is one hourly prediction for a specific plant.
    model_version links to ModelMetadata.
    """
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(Integer, ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    forecast_generated_at = Column(DateTime(timezone=True), nullable=False)  # When forecast was made
    forecast_timestamp = Column(DateTime(timezone=True), nullable=False)      # Which hour is predicted
    predicted_generation_mw = Column(Float, nullable=False)
    lower_bound_mw = Column(Float, nullable=True)   # Optional: prediction interval lower
    upper_bound_mw = Column(Float, nullable=True)   # Optional: prediction interval upper
    horizon_hours = Column(Integer, nullable=False) # e.g., 1 to 72
    model_version = Column(String(100), nullable=True)

    # Relationship
    plant = relationship("Plant", back_populates="forecasts")

    __table_args__ = (
        UniqueConstraint("plant_id", "forecast_generated_at", "forecast_timestamp", name="uq_forecast"),
        Index("idx_forecast_plant_ts", "plant_id", "forecast_timestamp"),
        CheckConstraint("predicted_generation_mw >= 0", name="check_forecast_non_negative"),
    )


# ── Alerts ────────────────────────────────────────────────────────────────────

class Alert(Base):
    """
    Grouped alert events.
    Multiple consecutive deficit/surplus hours are grouped into one alert.
    Avoids flooding the operator with 72 individual notifications.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String(100), nullable=False, default="default")
    alert_type = Column(Enum(AlertType), nullable=False)      # surplus | deficit
    severity = Column(Enum(AlertSeverity), nullable=False)    # normal | watch | warning | critical
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    peak_magnitude_mw = Column(Float, nullable=False)         # Worst-case imbalance in the window
    avg_magnitude_mw = Column(Float, nullable=False)          # Average imbalance in the window
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)                 # False once resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recommendations = relationship("Recommendation", back_populates="alert", cascade="all, delete-orphan")


# ── Recommendations ───────────────────────────────────────────────────────────

class Recommendation(Base):
    """
    Actionable recommendations linked to an alert.
    Generated by deterministic rule engine — NOT by ML.
    Always explainable.
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    action = Column(Enum(RecommendationAction), nullable=False)
    priority = Column(Integer, nullable=False)              # 1 = highest priority
    description = Column(Text, nullable=False)              # Human-readable explanation
    estimated_impact_mw = Column(Float, nullable=True)     # Quantified expected impact
    is_feasible = Column(Boolean, default=True)            # False if physically impossible (e.g., battery empty)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    alert = relationship("Alert", back_populates="recommendations")


# ── Model Metadata ────────────────────────────────────────────────────────────

class ModelMetadata(Base):
    """
    Tracks trained model versions.
    Allows API to report which model version was used for a forecast.
    Helps with debugging and model auditing.
    """
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)        # e.g., "solar_xgboost_v1"
    plant_type = Column(Enum(PlantType), nullable=False)
    version = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    mae = Column(Float, nullable=True)                      # Evaluation metrics
    rmse = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    wape = Column(Float, nullable=True)
    train_start = Column(DateTime(timezone=True), nullable=True)
    train_end = Column(DateTime(timezone=True), nullable=True)
    trained_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)               # Only one active per plant_type
    notes = Column(Text, nullable=True)
