"""Pydantic schemas for Generation data."""

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime


class GenerationBase(BaseModel):
    timestamp: datetime
    generation_mw: float = Field(..., ge=0, description="Actual generation in MW (cannot be negative)")


class GenerationCreate(GenerationBase):
    plant_id: int
    data_source: str = "real"

    @model_validator(mode="after")
    def check_non_negative(self) -> "GenerationCreate":
        if self.generation_mw < 0:
            raise ValueError("generation_mw cannot be negative")
        return self


class GenerationResponse(GenerationBase):
    id: int
    plant_id: int
    is_valid: bool
    flag_reason: Optional[str] = None
    data_source: str

    model_config = {"from_attributes": True}


class GenerationBulkCreate(BaseModel):
    """For bulk ingestion of historical generation records."""
    plant_id: int
    records: list[GenerationCreate]
