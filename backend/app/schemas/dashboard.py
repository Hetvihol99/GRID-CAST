from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.schemas.alert import AlertResponse

class PlantStatusSummary(BaseModel):
    plant_id: int
    plant_name: str
    plant_type: str
    capacity_mw: float
    latest_forecast_mw: Optional[float] = None
    status: str = "active"
    deviation_flag: bool = False

class HourlyBalance(BaseModel):
    timestamp: datetime
    total_generation_mw: float
    demand_mw: float
    net_balance_mw: float
    severity: str

class BatterySummary(BaseModel):
    battery_id: int
    battery_name: str
    capacity_mwh: float
    current_soc_pct: float
    available_discharge_mwh: float
    available_charge_mwh: float
    max_discharge_rate_mw: float
    max_charge_rate_mw: float

class DashboardSummary(BaseModel):
    generated_at: datetime
    region: str
    forecast_horizon_hours: int

    total_forecast_mw_next_hour: float
    total_demand_mw_next_hour: float
    net_balance_mw_next_hour: float
    overall_severity: str

    plants: List[PlantStatusSummary]
    hourly_balance: List[HourlyBalance]
    battery: Optional[BatterySummary] = None
    active_alerts: List[AlertResponse]
    upcoming_critical_periods: List[HourlyBalance]

    data_source_note: str = (
        "Grid Cast platform provides renewable generation intelligence. "
        "Weather telemetry from Open-Meteo API. ML models trained on historical physics datasets."
    )
    model_version: Optional[str] = None
