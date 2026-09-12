"""Pydantic schemas for Alerts."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AlertSeverityEnum(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertTypeEnum(str, Enum):
    SURPLUS = "surplus"
    DEFICIT = "deficit"
    OUTAGE_RISK = "outage_risk"


class AlertResponse(BaseModel):
    id: int
    region: str
    alert_type: AlertTypeEnum
    severity: AlertSeverityEnum
    start_time: datetime
    end_time: datetime
    peak_magnitude_mw: float    # Worst imbalance in the window
    avg_magnitude_mw: float     # Average imbalance
    message: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    total: int
    active_count: int
    alerts: List[AlertResponse]
