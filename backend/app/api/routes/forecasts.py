"""
Forecasts API routes.

POST /api/forecasts/run  → trigger full forecast pipeline
GET  /api/forecasts/{plant_id}  → get latest forecast for a plant
GET  /api/forecasts/region/{region}  → get regional aggregated forecast
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List

from app.database.connection import get_db
from app.database.models import Plant, Forecast
from app.services.forecast_service import ForecastService
from app.schemas.forecast import (
    ForecastRunRequest, ForecastRunResponse, PlantForecastResponse, ForecastPoint
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

_forecast_service = ForecastService()


@router.post("/run", response_model=ForecastRunResponse)
def run_forecast(
    payload: ForecastRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger a forecast run.
    - Fetches weather from Open-Meteo
    - Runs XGBoost predictions for all (or specified) plants
    - Computes grid balance, alerts, recommendations
    - Saves results to database

    For the hackathon MVP, runs synchronously and returns immediately.
    Background tasks can be added for production.
    """
    try:
        result = _forecast_service.run_forecast(
            db=db,
            plant_ids=payload.plant_ids,
            horizon_hours=payload.horizon_hours,
        )
        return ForecastRunResponse(
            status="success",
            message=f"Forecast complete for {result['plants_forecasted']} plant(s)",
            plants_forecasted=result["plants_forecasted"],
            forecast_generated_at=result["generated_at"],
            horizon_hours=payload.horizon_hours,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected forecast error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Forecast pipeline error: {str(e)}")


@router.get("/plant/{plant_id}", response_model=PlantForecastResponse)
def get_plant_forecast(
    plant_id: int,
    horizon_hours: int = 72,
    db: Session = Depends(get_db),
):
    """Get the most recent forecast for a specific plant."""
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")

    now = datetime.now(timezone.utc)

    # Get most recent forecast run
    latest_run = (
        db.query(Forecast.forecast_generated_at)
        .filter(
            Forecast.plant_id == plant_id,
            Forecast.forecast_timestamp >= now,
        )
        .order_by(Forecast.forecast_generated_at.desc())
        .first()
    )

    if not latest_run:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No forecast found for plant {plant_id}. "
                f"Run POST /api/forecasts/run first."
            ),
        )

    forecasts = (
        db.query(Forecast)
        .filter(
            Forecast.plant_id == plant_id,
            Forecast.forecast_generated_at == latest_run[0],
            Forecast.forecast_timestamp >= now,
        )
        .order_by(Forecast.forecast_timestamp)
        .limit(horizon_hours)
        .all()
    )

    hourly = [
        ForecastPoint(
            timestamp=f.forecast_timestamp,
            predicted_generation_mw=f.predicted_generation_mw,
            horizon_hours=f.horizon_hours,
            lower_bound_mw=f.lower_bound_mw,
            upper_bound_mw=f.upper_bound_mw,
        )
        for f in forecasts
    ]

    return PlantForecastResponse(
        plant_id=plant.id,
        plant_name=plant.name,
        plant_type=plant.plant_type.value,
        capacity_mw=plant.capacity_mw,
        forecast_generated_at=latest_run[0],
        model_version=forecasts[0].model_version if forecasts else None,
        data_source="ml_prediction",
        hourly_forecast=hourly,
    )
