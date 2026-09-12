"""
Weather API Routes
===================
Exposes weather data endpoints for the React dashboard.

GET /api/weather/plant/{plant_id}/current   → latest weather from Open-Meteo
GET /api/weather/plant/{plant_id}/forecast  → full 72-hour forecast
GET /api/weather/plant/{plant_id}/history   → stored historical observations
GET /api/weather/test                       → test Open-Meteo connectivity
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.database.connection import get_db
from app.database.models import Plant, WeatherData
from app.schemas.weather import WeatherResponse, WeatherForecastPoint
from app.services.weather_service import WeatherService, WeatherUnavailableError
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/weather", tags=["Weather"])

_weather_service = WeatherService()


# ── Live API call ──────────────────────────────────────────────────────────────

@router.get("/plant/{plant_id}/forecast", response_model=List[WeatherForecastPoint])
def get_plant_weather_forecast(
    plant_id: int,
    horizon_hours: int = Query(72, ge=1, le=168, description="Forecast horizon in hours (max 168 = 7 days)"),
    force_refresh: bool = Query(False, description="Bypass cache and fetch fresh data from Open-Meteo"),
    db: Session = Depends(get_db),
):
    """
    Get live weather forecast for a plant's location from Open-Meteo API.

    - Uses the plant's latitude/longitude to query Open-Meteo
    - Results are cached for 30 minutes (configurable)
    - On API failure, falls back to last cached DB forecast
    - Returns one WeatherForecastPoint per hour

    Open-Meteo is free, no API key required.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")

    try:
        forecast = _weather_service.get_forecast(
            plant=plant,
            db=db,
            horizon_hours=horizon_hours,
            force_refresh=force_refresh,
        )
        return forecast

    except WeatherUnavailableError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Weather data unavailable: {str(e)}. "
                f"Check internet connectivity and try again."
            ),
        )
    except Exception as e:
        logger.error(f"Unexpected weather error for plant {plant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Weather service error: {str(e)}")


@router.get("/plant/{plant_id}/current", response_model=WeatherForecastPoint)
def get_plant_current_weather(
    plant_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the current hour's weather for a plant.
    Returns the first entry from the 72-hour forecast (i.e., now → next hour).
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")

    try:
        forecast = _weather_service.get_forecast(plant=plant, db=db, horizon_hours=2)
        if not forecast:
            raise HTTPException(status_code=503, detail="No weather data available")
        return forecast[0]

    except WeatherUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/plant/{plant_id}/history", response_model=List[WeatherResponse])
def get_plant_weather_history(
    plant_id: int,
    hours: int = Query(48, ge=1, le=720, description="How many hours of history to return"),
    db: Session = Depends(get_db),
):
    """
    Get stored historical weather observations for a plant.
    These are the actual weather readings saved to DB during past forecast runs.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail=f"Plant {plant_id} not found")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = (
        db.query(WeatherData)
        .filter(
            WeatherData.plant_id == plant_id,
            WeatherData.timestamp >= cutoff,
            WeatherData.is_forecast == False,  # Historical only
        )
        .order_by(WeatherData.timestamp.desc())
        .limit(hours)
        .all()
    )

    return records


# ── Connectivity test ──────────────────────────────────────────────────────────

@router.get("/test")
def test_weather_api(
    latitude: float = Query(26.9124, description="Test latitude (default: Jaipur, India)"),
    longitude: float = Query(75.7873, description="Test longitude (default: Jaipur, India)"),
):
    """
    Test Open-Meteo API connectivity.
    Fetches the next 3 hours of weather for any latitude/longitude.
    Use this to verify the weather API is reachable from the server.

    Example: GET /api/weather/test?latitude=26.91&longitude=75.78
    """
    try:
        points = _weather_service.test_connectivity(latitude, longitude, hours=3)
        if not points:
            raise WeatherUnavailableError("No data returned")

        # Return summary of what we got
        first = points[0]
        return {
            "status": "ok",
            "api": "Open-Meteo (https://open-meteo.com)",
            "api_key_required": False,
            "location": {"latitude": latitude, "longitude": longitude},
            "points_received": len(points),
            "first_timestamp": first.timestamp.isoformat(),
            "sample": {
                "timestamp": first.timestamp.isoformat(),
                "temperature_c": first.temperature_c,
                "cloud_cover_pct": first.cloud_cover_pct,
                "solar_irradiance_wm2": first.solar_irradiance_wm2,
                "wind_speed_ms": first.wind_speed_ms,
                "wind_direction_deg": first.wind_direction_deg,
                "humidity_pct": first.humidity_pct,
                "pressure_hpa": first.pressure_hpa,
                "rainfall_mm": first.rainfall_mm,
            },
        }

    except WeatherUnavailableError as e:
        return {
            "status": "error",
            "api": "Open-Meteo",
            "error": str(e),
            "suggestion": "Check server internet connectivity",
        }
    except Exception as e:
        return {
            "status": "error",
            "api": "Open-Meteo",
            "error": str(e),
        }


# ── Multi-plant bulk fetch ─────────────────────────────────────────────────────

@router.post("/fetch-all")
def fetch_weather_for_all_plants(
    region: str = Query("default"),
    horizon_hours: int = Query(72, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """
    Fetch and cache weather forecasts for ALL active plants in a region.
    Useful to pre-warm the cache before running a forecast.

    Returns status per plant — partial success is allowed
    (some plants may succeed even if one fails).
    """
    plants = db.query(Plant).filter(Plant.is_active == True).all()
    if not plants:
        raise HTTPException(status_code=404, detail="No active plants found")

    results = []
    for plant in plants:
        try:
            points = _weather_service.get_forecast(
                plant=plant, db=db, horizon_hours=horizon_hours, force_refresh=True
            )
            results.append({
                "plant_id": plant.id,
                "plant_name": plant.name,
                "status": "ok",
                "points_fetched": len(points),
                "first_timestamp": points[0].timestamp.isoformat() if points else None,
                "last_timestamp": points[-1].timestamp.isoformat() if points else None,
            })
        except WeatherUnavailableError as e:
            results.append({
                "plant_id": plant.id,
                "plant_name": plant.name,
                "status": "error",
                "error": str(e),
            })
            logger.warning(f"Weather fetch failed for plant {plant.id}: {e}")

    success_count = sum(1 for r in results if r["status"] == "ok")
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_plants": len(plants),
        "success": success_count,
        "failed": len(plants) - success_count,
        "plants": results,
    }


# ── Live OpenWeatherMap Endpoint ──────────────────────────────────────────────

@router.get("/live/openweathermap")
def get_live_openweathermap(
    latitude: float = Query(26.9124, description="Latitude (default Jaipur)"),
    longitude: float = Query(75.7873, description="Longitude (default Jaipur)"),
):
    """
    Fetch live present-moment weather data via OpenWeatherMap API.
    """
    try:
        data = _weather_service.fetch_current_openweathermap(latitude, longitude)
        return {"status": "ok", "data": data}
    except Exception as e:
        logger.error(f"OpenWeatherMap live query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/5day-forecast")
def get_live_5day_forecast(
    latitude: float = Query(26.9124, description="Latitude (default Jaipur)"),
    longitude: float = Query(75.7873, description="Longitude (default Jaipur)"),
):
    """
    Fetch 5-day / 3-hour solar and weather forecast via OpenWeatherMap API.
    """
    try:
        data = _weather_service.fetch_5day_forecast_openweathermap(latitude, longitude)
        return {"status": "ok", "count": len(data), "data": data}
    except Exception as e:
        logger.error(f"OpenWeatherMap 5-day forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Historical Visual Crossing Endpoint ───────────────────────────────────────

@router.get("/historical/visual-crossing")
def get_historical_visual_crossing(
    latitude: float = Query(26.9124, description="Latitude (default Jaipur)"),
    longitude: float = Query(75.7873, description="Longitude (default Jaipur)"),
    start_date: str = Query("2023-01-01", description="Start date YYYY-MM-DD"),
    end_date: str = Query("2023-01-07", description="End date YYYY-MM-DD"),
):
    """
    Fetch historical weather observations via Visual Crossing Weather API.
    """
    try:
        points = _weather_service.fetch_visual_crossing_history(latitude, longitude, start_date, end_date)
        return {
            "status": "ok",
            "provider": "Visual Crossing",
            "count": len(points),
            "data": points,
        }
    except Exception as e:
        logger.error(f"Visual Crossing query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Multi-Provider Status ─────────────────────────────────────────────────────

@router.get("/providers")
def get_weather_providers():
    """
    Check the connectivity and configuration status of all 3 weather API integrations.
    """
    return {
        "providers": [
            {
                "name": "Open-Meteo",
                "role": "High-Resolution 72h Forecasting",
                "status": "active",
                "requires_key": False,
            },
            {
                "name": "Visual Crossing",
                "role": "Historical Hourly Dataset & Deep Re-analysis",
                "status": "active" if bool(_weather_service.vc_key) else "unconfigured",
                "requires_key": True,
            },
            {
                "name": "OpenWeatherMap",
                "role": "Real-time Current Atmospheric Conditions & Telemetry",
                "status": "active" if bool(_weather_service.owm_key) else "unconfigured",
                "requires_key": True,
            },
        ]
    }
