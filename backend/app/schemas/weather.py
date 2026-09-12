"""Pydantic schemas for Weather data."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class WeatherBase(BaseModel):
    timestamp: datetime
    temperature_c: Optional[float] = Field(None, ge=-60, le=60)
    humidity_pct: Optional[float] = Field(None, ge=0, le=100)
    cloud_cover_pct: Optional[float] = Field(None, ge=0, le=100)
    solar_irradiance_wm2: Optional[float] = Field(None, ge=0, le=1500)  # Max theoretical ~1361 W/m²
    wind_speed_ms: Optional[float] = Field(None, ge=0, le=100)
    wind_direction_deg: Optional[float] = Field(None, ge=0, le=360)
    pressure_hpa: Optional[float] = Field(None, ge=800, le=1100)
    rainfall_mm: Optional[float] = Field(None, ge=0)
    visibility_km: Optional[float] = Field(None, ge=0)
    is_forecast: bool = False


class WeatherCreate(WeatherBase):
    plant_id: int


class WeatherResponse(WeatherBase):
    id: int
    plant_id: int
    data_source: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


class WeatherForecastPoint(BaseModel):
    """A single hour of weather forecast — used in forecast pipeline."""
    timestamp: datetime
    temperature_c: float
    humidity_pct: float
    cloud_cover_pct: float
    solar_irradiance_wm2: float
    wind_speed_ms: float
    wind_direction_deg: float
    pressure_hpa: float
    rainfall_mm: float
