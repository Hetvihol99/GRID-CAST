"""
Weather Service
================
WHAT: Abstraction layer for all weather data fetching.
WHY:  Weather API calls should never be scattered across routes or services.
      All external HTTP requests go through this single service.

API: Open-Meteo (https://open-meteo.com)
  - Free, no API key required
  - Provides hourly weather forecasts up to 7 days
  - Variables: temperature, humidity, cloud cover, solar irradiance,
               wind speed, wind direction, pressure, precipitation

FALLBACK STRATEGY:
  If API call fails → use cached forecast from database (latest stored)
  If no cache → raise WeatherUnavailableError with clear message

NEVER silently return fabricated weather data.
"""

import httpx
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.database.models import WeatherData, Plant, DataSource
from app.schemas.weather import WeatherForecastPoint

logger = get_logger(__name__)

# In-memory cache: {plant_id: (fetched_at, [WeatherForecastPoint])}
_weather_cache: dict = {}
CACHE_TTL_SECONDS = settings.FORECAST_CACHE_TTL_SECONDS


class WeatherUnavailableError(Exception):
    """Raised when weather data cannot be obtained from API or cache."""
    pass


class WeatherService:
    """
    Fetches, caches, and serves weather forecast data.

    Usage:
        service = WeatherService()
        forecast = service.get_forecast(plant, db)
    """

    def __init__(self):
        self.base_url = settings.WEATHER_API_BASE_URL
        self.vc_key = settings.VISUAL_CROSSING_API_KEY
        self.vc_base_url = settings.VISUAL_CROSSING_BASE_URL
        self.owm_key = settings.OPENWEATHERMAP_API_KEY
        self.solar_key = settings.SOLAR_ENERGY_API_KEY or settings.OPENWEATHERMAP_API_KEY
        self.owm_base_url = settings.OPENWEATHERMAP_BASE_URL

    def fetch_current_openweathermap(self, latitude: float, longitude: float) -> dict:
        """
        Fetch real-time current weather from OpenWeatherMap API.
        """
        key = self.solar_key or self.owm_key
        if not key:
            raise WeatherUnavailableError("OpenWeatherMap / Solar Energy API key is not configured.")

        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": key,
            "units": "metric",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.owm_base_url}/weather", params=params)

        if resp.status_code != 200:
            raise WeatherUnavailableError(f"OpenWeatherMap API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        weather_desc = data.get("weather", [{}])[0].get("description", "")

        return {
            "provider": "OpenWeatherMap",
            "city": data.get("name"),
            "temperature_c": main.get("temp"),
            "feels_like_c": main.get("feels_like"),
            "humidity_pct": main.get("humidity"),
            "pressure_hpa": main.get("pressure"),
            "wind_speed_ms": wind.get("speed"),
            "wind_direction_deg": wind.get("deg"),
            "cloud_cover_pct": clouds.get("all"),
            "condition": weather_desc,
            "timestamp": datetime.fromtimestamp(data.get("dt", 0), tz=timezone.utc).isoformat(),
        }

    def fetch_5day_forecast_openweathermap(self, latitude: float, longitude: float) -> list[dict]:
        """
        Fetch 5-day / 3-hour forecast from OpenWeatherMap API.
        """
        key = self.solar_key or self.owm_key
        if not key:
            raise WeatherUnavailableError("Solar Energy / OpenWeatherMap API key is not configured.")

        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": key,
            "units": "metric",
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{self.owm_base_url}/forecast", params=params)

        if resp.status_code != 200:
            raise WeatherUnavailableError(f"OpenWeatherMap 5-day forecast error ({resp.status_code}): {resp.text}")

        data = resp.json()
        entries = []
        for item in data.get("list", []):
            dt_txt = item.get("dt_txt")
            main = item.get("main", {})
            wind = item.get("wind", {})
            clouds = item.get("clouds", {})
            entries.append({
                "timestamp": dt_txt,
                "temperature_c": main.get("temp"),
                "humidity_pct": main.get("humidity"),
                "pressure_hpa": main.get("pressure"),
                "cloud_cover_pct": clouds.get("all"),
                "wind_speed_ms": wind.get("speed"),
                "wind_direction_deg": wind.get("deg"),
                "pop": item.get("pop", 0),  # Probability of precipitation
            })
        return entries

    def fetch_visual_crossing_history(
        self, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> list[WeatherForecastPoint]:
        """
        Fetch historical hourly weather data from Visual Crossing API.
        Dates in 'YYYY-MM-DD' format.
        """
        if not self.vc_key:
            raise WeatherUnavailableError("Visual Crossing API key is not configured.")

        url = f"{self.vc_base_url}/{latitude},{longitude}/{start_date}/{end_date}"
        params = {
            "unitGroup": "metric",
            "key": self.vc_key,
            "include": "hours",
            "contentType": "json",
        }
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, params=params)

        if resp.status_code != 200:
            raise WeatherUnavailableError(f"Visual Crossing API error ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        points: list[WeatherForecastPoint] = []

        for day in data.get("days", []):
            day_date = day.get("datetime")
            for h in day.get("hours", []):
                time_str = h.get("datetime")
                ts_iso = f"{day_date}T{time_str}Z"
                try:
                    ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
                except Exception:
                    continue

                solar_rad = float(h.get("solarradiation", 0.0) or 0.0)
                points.append(
                    WeatherForecastPoint(
                        timestamp=ts,
                        temperature_c=float(h.get("temp", 20.0) or 20.0),
                        humidity_pct=float(h.get("humidity", 50.0) or 50.0),
                        cloud_cover_pct=float(h.get("cloudcover", 0.0) or 0.0),
                        solar_irradiance_wm2=max(0.0, solar_rad),
                        wind_speed_ms=max(0.0, float(h.get("windspeed", 3.0) or 3.0) / 3.6), # km/h to m/s if needed or metric
                        wind_direction_deg=float(h.get("winddir", 180.0) or 180.0),
                        pressure_hpa=float(h.get("pressure", 1013.0) or 1013.0),
                        rainfall_mm=float(h.get("precip", 0.0) or 0.0),
                    )
                )

        return points

    def get_forecast(
        self,
        plant: "Plant",
        db: Session,
        horizon_hours: int = 72,
        force_refresh: bool = False,
    ) -> list["WeatherForecastPoint"]:
        """
        Get weather forecast for a plant location.

        Steps:
        1. Check in-memory cache (30-min TTL)
        2. If cache miss → fetch from Open-Meteo API
        3. Validate response
        4. Save to database (for historical record + fallback)
        5. If API fails → load from database cache

        Returns list of WeatherForecastPoint, one per hour.
        """
        plant_id = plant.id

        # ── Check in-memory cache ─────────────────────────────────────────────
        if not force_refresh and plant_id in _weather_cache:
            cached_at, cached_data = _weather_cache[plant_id]
            age_seconds = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age_seconds < CACHE_TTL_SECONDS:
                logger.debug(f"Weather cache hit for plant {plant_id} (age: {age_seconds:.0f}s)")
                return cached_data[:horizon_hours]

        # ── Fetch from API ────────────────────────────────────────────────────
        try:
            forecast_points = self._fetch_from_api(plant.latitude, plant.longitude, horizon_hours)

            # Store to DB (best-effort — don't fail if DB write fails)
            try:
                self._save_to_db(forecast_points, plant_id, db)
            except Exception as db_err:
                logger.warning(f"Failed to save weather to DB for plant {plant_id}: {db_err}")

            # Update cache
            _weather_cache[plant_id] = (datetime.now(timezone.utc), forecast_points)

            logger.info(f"Fetched {len(forecast_points)} weather points for plant {plant_id}")
            return forecast_points[:horizon_hours]

        except Exception as api_err:
            logger.error(f"Weather API failed for plant {plant_id}: {api_err}")

            # ── Fallback to database cache ────────────────────────────────────
            return self._load_from_db_cache(plant_id, horizon_hours, db, api_err)

    def _fetch_from_api(
        self, latitude: float, longitude: float, hours: int = 72
    ) -> list[WeatherForecastPoint]:
        """
        Fetch weather forecast from Open-Meteo API.
        Open-Meteo is free, no API key needed, and provides reliable 7-day forecasts.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "cloud_cover",
                "direct_normal_irradiance",        # DNI: W/m² (beam radiation)
                "global_tilted_irradiance",        # GTI: total on tilted surface
                "shortwave_radiation",             # GHI: Global Horizontal Irradiance
                "wind_speed_10m",
                "wind_direction_10m",
                "surface_pressure",
                "precipitation",
                "wind_gusts_10m",                 # Gust data for wind safety
            ]),
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "cloud_cover",
                "shortwave_radiation",
                "wind_speed_10m",
                "wind_direction_10m",
                "surface_pressure",
                "precipitation",
            ]),
            "forecast_days": min(7, (hours // 24) + 1),
            "timezone": "UTC",
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.base_url}/forecast", params=params)

        if response.status_code != 200:
            raise WeatherUnavailableError(
                f"Open-Meteo API returned {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        return self._parse_api_response(data, hours)

    def _parse_api_response(self, data: dict, hours: int) -> list[WeatherForecastPoint]:
        """
        Parse Open-Meteo JSON response into WeatherForecastPoint list.

        Solar irradiance strategy:
          Primary:  shortwave_radiation (GHI — Global Horizontal Irradiance)
                    Best overall measure for solar panel output under all sky conditions.
          Fallback: direct_normal_irradiance (DNI) if GHI unavailable.
          Why GHI over DNI? GHI includes diffuse radiation — panels still generate
          under overcast skies from diffuse light. DNI drops to 0 under clouds.
        """
        hourly = data.get("hourly", {})

        timestamps     = hourly.get("time", [])
        temperatures   = hourly.get("temperature_2m", [])
        humidity       = hourly.get("relative_humidity_2m", [])
        cloud_cover    = hourly.get("cloud_cover", [])
        ghi            = hourly.get("shortwave_radiation", [])       # GHI: preferred
        dni            = hourly.get("direct_normal_irradiance", [])  # DNI: fallback
        wind_speed     = hourly.get("wind_speed_10m", [])
        wind_direction = hourly.get("wind_direction_10m", [])
        pressure       = hourly.get("surface_pressure", [])
        precipitation  = hourly.get("precipitation", [])

        def safe(arr, idx, default):
            """Safely extract value from list, return default if None or missing."""
            try:
                v = arr[idx]
                return float(v) if v is not None else default
            except (IndexError, TypeError, ValueError):
                return default

        points = []
        for i in range(min(hours, len(timestamps))):
            try:
                # Use GHI if available, fall back to DNI, else 0
                solar_wm2 = safe(ghi, i, None)
                if solar_wm2 is None:
                    solar_wm2 = safe(dni, i, 0.0)
                solar_wm2 = max(0.0, solar_wm2)

                point = WeatherForecastPoint(
                    timestamp=pd.Timestamp(timestamps[i], tz="UTC").to_pydatetime(),
                    temperature_c=safe(temperatures, i, 20.0),
                    humidity_pct=safe(humidity, i, 60.0),
                    cloud_cover_pct=safe(cloud_cover, i, 30.0),
                    solar_irradiance_wm2=solar_wm2,
                    wind_speed_ms=max(0.0, safe(wind_speed, i, 5.0)),
                    wind_direction_deg=safe(wind_direction, i, 180.0),
                    pressure_hpa=safe(pressure, i, 1013.0),
                    rainfall_mm=max(0.0, safe(precipitation, i, 0.0)),
                )
                points.append(point)
            except (IndexError, TypeError, ValueError) as e:
                logger.warning(f"Skipping malformed weather point at index {i}: {e}")
                continue

        if not points:
            raise WeatherUnavailableError("API response contained no valid weather points")

        logger.debug(
            f"Parsed {len(points)} weather points | "
            f"Solar: {min(p.solar_irradiance_wm2 for p in points):.0f}–"
            f"{max(p.solar_irradiance_wm2 for p in points):.0f} W/m² | "
            f"Wind: {min(p.wind_speed_ms for p in points):.1f}–"
            f"{max(p.wind_speed_ms for p in points):.1f} m/s"
        )

        return points

    def _save_to_db(
        self, points: list[WeatherForecastPoint], plant_id: int, db: Session
    ) -> None:
        """Save weather forecast to database for historical record and fallback."""
        for point in points:
            existing = (
                db.query(WeatherData)
                .filter(
                    WeatherData.plant_id == plant_id,
                    WeatherData.timestamp == point.timestamp,
                    WeatherData.is_forecast == True,
                )
                .first()
            )

            if existing:
                # Update existing forecast
                existing.temperature_c = point.temperature_c
                existing.cloud_cover_pct = point.cloud_cover_pct
                existing.solar_irradiance_wm2 = point.solar_irradiance_wm2
                existing.wind_speed_ms = point.wind_speed_ms
                existing.wind_direction_deg = point.wind_direction_deg
                existing.data_source = DataSource.REAL
            else:
                db.add(WeatherData(
                    plant_id=plant_id,
                    timestamp=point.timestamp,
                    is_forecast=True,
                    temperature_c=point.temperature_c,
                    humidity_pct=point.humidity_pct,
                    cloud_cover_pct=point.cloud_cover_pct,
                    solar_irradiance_wm2=point.solar_irradiance_wm2,
                    wind_speed_ms=point.wind_speed_ms,
                    wind_direction_deg=point.wind_direction_deg,
                    pressure_hpa=point.pressure_hpa,
                    rainfall_mm=point.rainfall_mm,
                    data_source=DataSource.REAL,
                ))

        db.commit()

    def _load_from_db_cache(
        self,
        plant_id: int,
        horizon_hours: int,
        db: Session,
        original_error: Exception,
    ) -> list[WeatherForecastPoint]:
        """Load most recent forecast from database as fallback."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=2)  # Accept cache up to 2 hours old

        cached_records = (
            db.query(WeatherData)
            .filter(
                WeatherData.plant_id == plant_id,
                WeatherData.is_forecast == True,
                WeatherData.timestamp >= now,
                WeatherData.fetched_at >= cutoff,
            )
            .order_by(WeatherData.timestamp)
            .limit(horizon_hours)
            .all()
        )

        if not cached_records:
            raise WeatherUnavailableError(
                f"Weather API failed ({original_error}) and no usable cache found for plant {plant_id}. "
                f"Cannot generate forecast without weather data."
            )

        logger.warning(
            f"Using cached weather for plant {plant_id} "
            f"(API failed: {original_error}). "
            f"Cache age may be up to 2 hours."
        )

        return [
            WeatherForecastPoint(
                timestamp=r.timestamp,
                temperature_c=r.temperature_c or 20.0,
                humidity_pct=r.humidity_pct or 60.0,
                cloud_cover_pct=r.cloud_cover_pct or 30.0,
                solar_irradiance_wm2=r.solar_irradiance_wm2 or 0.0,
                wind_speed_ms=r.wind_speed_ms or 5.0,
                wind_direction_deg=r.wind_direction_deg or 180.0,
                pressure_hpa=r.pressure_hpa or 1013.0,
                rainfall_mm=r.rainfall_mm or 0.0,
            )
            for r in cached_records
        ]
