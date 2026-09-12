from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.database.connection import create_tables
from ml.predictor import predictor
from app.api.routes import plants, forecasts, alerts, dashboard, generation, weather, ai, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger(__name__)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    create_tables()

    logger.info("Loading ML models...")
    predictor.load_models()

    solar_info = predictor.get_model_info("solar")
    wind_info = predictor.get_model_info("wind")

    if solar_info and not solar_info.is_loaded:
        logger.warning(
            f"Solar model NOT loaded: {solar_info.error}. "
            f"Run: python ml/scripts/train_solar.py"
        )
    if wind_info and not wind_info.is_loaded:
        logger.warning(
            f"Wind model NOT loaded: {wind_info.error}. "
            f"Run: python ml/scripts/train_wind.py"
        )

    logger.info("Application startup complete")

    yield

    logger.info("Application shutting down...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI Solution for Renewable Generation Forecasting & Grid Decision Support. "
        "Forecasts solar and wind generation for the next 24–72 hours using XGBoost, "
        "identifies surplus/deficit periods, and provides actionable grid recommendations."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

API_PREFIX = "/api"

app.include_router(plants.router, prefix=API_PREFIX)
app.include_router(forecasts.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(generation.router, prefix=API_PREFIX)
app.include_router(weather.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)

@app.get("/health", tags=["Health"])
def health_check():
    solar_info = predictor.get_model_info("solar")
    wind_info = predictor.get_model_info("wind")

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "models": {
            "solar": {
                "loaded": solar_info.is_loaded if solar_info else False,
                "error": solar_info.error if solar_info else "Not initialized",
            },
            "wind": {
                "loaded": wind_info.is_loaded if wind_info else False,
                "error": wind_info.error if wind_info else "Not initialized",
            },
        },
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    }
