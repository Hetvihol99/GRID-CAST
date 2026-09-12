from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Grid Cast"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENV: str = "development"

    DATABASE_URL: str = "sqlite:///./renewable.db"

    WEATHER_API_BASE_URL: str = "https://api.open-meteo.com/v1"
    WEATHER_API_KEY: str = ""

    VISUAL_CROSSING_API_KEY: str = ""
    VISUAL_CROSSING_BASE_URL: str = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

    OPENWEATHERMAP_API_KEY: str = ""
    SOLAR_ENERGY_API_KEY: str = ""
    OPENWEATHERMAP_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    MODEL_DIR: str = "ml/trained_models"
    SOLAR_MODEL_FILE: str = "solar_model.pkl"
    WIND_MODEL_FILE: str = "wind_model.pkl"
    SOLAR_SCALER_FILE: str = "scaler_solar.pkl"
    WIND_SCALER_FILE: str = "scaler_wind.pkl"

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    WATCH_THRESHOLD_FRACTION: float = 0.05
    WARNING_THRESHOLD_FRACTION: float = 0.15
    CRITICAL_THRESHOLD_FRACTION: float = 0.30

    FORECAST_HORIZON_HOURS: int = 72
    FORECAST_CACHE_TTL_SECONDS: int = 1800

    WEATHER_REFRESH_INTERVAL_SECONDS: int = 3600

    BATTERY_EFFICIENCY: float = 0.90

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
