"""
Pydantic schemas for Plant — request/response validation.
Separate from ORM models (schemas = API contract, models = DB contract).
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class PlantTypeEnum(str, Enum):
    SOLAR = "solar"
    WIND = "wind"


class PlantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Plant display name")
    plant_type: PlantTypeEnum = Field(..., description="Type: solar or wind")
    capacity_mw: float = Field(..., gt=0, description="Installed capacity in MW (must be > 0)")
    latitude: float = Field(..., ge=-90, le=90, description="Plant latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Plant longitude")
    location_name: Optional[str] = Field(None, max_length=200, description="Human-readable location")

    # Optional technical details
    panel_efficiency: Optional[float] = Field(None, gt=0, lt=1, description="Solar panel efficiency (0–1)")
    turbine_cut_in_speed: Optional[float] = Field(None, ge=0, description="Wind cut-in speed m/s")
    turbine_rated_speed: Optional[float] = Field(None, ge=0, description="Wind rated speed m/s")
    turbine_cut_out_speed: Optional[float] = Field(None, ge=0, description="Wind cut-out speed m/s")


class PlantCreate(PlantBase):
    """Schema used when creating a new plant (POST /api/plants)."""
    pass


class PlantUpdate(BaseModel):
    """Schema for partial update (PATCH /api/plants/{id})."""
    name: Optional[str] = None
    capacity_mw: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    panel_efficiency: Optional[float] = Field(None, gt=0, lt=1)
    turbine_cut_in_speed: Optional[float] = Field(None, ge=0)
    turbine_rated_speed: Optional[float] = Field(None, ge=0)
    turbine_cut_out_speed: Optional[float] = Field(None, ge=0)


class PlantResponse(PlantBase):
    """Schema returned from API — includes DB-generated fields."""
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Pydantic v2: replaces orm_mode


class PlantSummary(BaseModel):
    """Lightweight plant info for lists."""
    id: int
    name: str
    plant_type: PlantTypeEnum
    capacity_mw: float
    is_active: bool

    model_config = {"from_attributes": True}
