"""Pydantic schemas for Recommendations."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RecommendationActionEnum(str, Enum):
    CHARGE_STORAGE = "charge_storage"
    DISCHARGE_STORAGE = "discharge_storage"
    PREPARE_BACKUP = "prepare_backup"
    CONSIDER_CURTAILMENT = "consider_curtailment"
    MONITOR = "monitor"


class RecommendationResponse(BaseModel):
    id: int
    alert_id: int
    action: RecommendationActionEnum
    priority: int = Field(..., ge=1, description="1 = highest priority")
    description: str            # Plain English explanation of WHY this action is recommended
    estimated_impact_mw: Optional[float] = None
    is_feasible: bool           # False if physically impossible (e.g., empty battery)
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationListResponse(BaseModel):
    alert_id: int
    recommendations: List[RecommendationResponse]
