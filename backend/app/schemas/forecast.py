"""Pydantic schemas for Forecast output."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ForecastPoint(BaseModel):
    """A single forecasted hourly generation value for one plant."""
    timestamp: datetime
    predicted_generation_mw: float = Field(..., ge=0)
    lower_bound_mw: Optional[float] = Field(None, ge=0, description="Lower prediction interval (future)")
    upper_bound_mw: Optional[float] = Field(None, ge=0, description="Upper prediction interval (future)")
    horizon_hours: int = Field(..., ge=1, le=72)
    is_daylight: Optional[bool] = None  # For solar: indicates if this hour is daylight


class PlantForecastResponse(BaseModel):
    """Complete forecast for a single plant."""
    plant_id: int
    plant_name: str
    plant_type: str
    capacity_mw: float
    forecast_generated_at: datetime
    model_version: Optional[str] = None
    data_source: str = "ml_prediction"  # Always "ml_prediction" — never hardcoded values
    hourly_forecast: List[ForecastPoint]

    @property
    def total_forecasted_mwh(self) -> float:
        """Total energy (MWh) over the forecast horizon (sum of hourly MWs)."""
        return sum(p.predicted_generation_mw for p in self.hourly_forecast)


class RegionalForecastResponse(BaseModel):
    """Aggregated forecast across all plants in a region."""
    region: str
    forecast_generated_at: datetime
    plant_forecasts: List[PlantForecastResponse]

    # Aggregated hourly totals
    hourly_totals: List[dict]   # [{timestamp, total_generation_mw, demand_mw, net_balance_mw}]


class ForecastRunRequest(BaseModel):
    """Request body for POST /api/forecast/run"""
    plant_ids: Optional[List[int]] = Field(
        None,
        description="Specific plant IDs to forecast. If empty/None, forecast all active plants."
    )
    horizon_hours: int = Field(72, ge=1, le=72, description="Forecast horizon in hours (default 72)")


class ForecastRunResponse(BaseModel):
    """Response after triggering a forecast run."""
    status: str
    message: str
    plants_forecasted: int
    forecast_generated_at: datetime
    horizon_hours: int
