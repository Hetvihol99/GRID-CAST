"""Pydantic schemas for Battery/Storage."""

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime


class BatteryBase(BaseModel):
    region: str = "default"
    name: str = Field(..., min_length=1, max_length=200)
    capacity_mwh: float = Field(..., gt=0, description="Total energy capacity in MWh")
    current_soc_pct: float = Field(..., ge=0, le=100, description="Current State of Charge (0–100%)")
    max_charge_rate_mw: float = Field(..., gt=0, description="Maximum charge power in MW")
    max_discharge_rate_mw: float = Field(..., gt=0, description="Maximum discharge power in MW")
    min_soc_pct: float = Field(10.0, ge=0, le=100, description="Minimum safe SOC (%)")
    max_soc_pct: float = Field(95.0, ge=0, le=100, description="Maximum safe SOC (%)")
    efficiency: float = Field(0.90, gt=0, le=1.0, description="Round-trip efficiency (0–1)")

    @model_validator(mode="after")
    def check_soc_limits(self) -> "BatteryBase":
        if self.min_soc_pct >= self.max_soc_pct:
            raise ValueError("min_soc_pct must be less than max_soc_pct")
        if not (self.min_soc_pct <= self.current_soc_pct <= self.max_soc_pct):
            raise ValueError(
                f"current_soc_pct ({self.current_soc_pct}) must be between "
                f"min_soc_pct ({self.min_soc_pct}) and max_soc_pct ({self.max_soc_pct})"
            )
        return self


class BatteryCreate(BatteryBase):
    pass


class BatteryUpdate(BaseModel):
    current_soc_pct: Optional[float] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class BatteryResponse(BatteryBase):
    id: int
    is_active: bool
    last_updated: datetime

    model_config = {"from_attributes": True}


class BatteryAnalysisResult(BaseModel):
    """Result of battery analysis for a specific imbalance scenario."""
    battery_id: int
    battery_name: str
    scenario: str                           # "surplus" or "deficit"
    imbalance_mw: float                     # The imbalance being addressed
    battery_contribution_mw: float          # How much battery can actually provide/absorb
    remaining_imbalance_mw: float           # Imbalance after battery action
    soc_before_pct: float
    soc_after_pct: float                    # Estimated SOC after action (for 1-hour window)
    is_fully_covered: bool                  # True only if battery can cover entire imbalance
    limiting_factor: Optional[str] = None   # What limited battery: "rate", "soc_min", "soc_max", "capacity"
    explanation: str                        # Human-readable explanation of the calculation
