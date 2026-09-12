"""
End-to-end API route tests for the FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["models"]["solar"]["loaded"] is True
    assert data["models"]["wind"]["loaded"] is True


def test_get_plants():
    response = client.get("/api/plants")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 4
    names = [p["name"] for p in data]
    assert "Rajasthan Solar Farm A" in names


def test_weather_providers():
    response = client.get("/api/weather/providers")
    assert response.status_code == 200
    data = response.json()
    providers = {p["name"]: p["status"] for p in data["providers"]}
    assert "Open-Meteo" in providers
    assert "Visual Crossing" in providers
    assert "OpenWeatherMap" in providers
    assert providers["OpenWeatherMap"] == "active"
    assert providers["Visual Crossing"] == "active"


def test_openweathermap_live_endpoint():
    response = client.get("/api/weather/live/openweathermap?latitude=26.9124&longitude=75.7873")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "temperature_c" in data["data"]
    assert data["data"]["provider"] == "OpenWeatherMap"


def test_openweathermap_5day_forecast_endpoint():
    response = client.get("/api/weather/live/5day-forecast?latitude=26.9124&longitude=75.7873")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["count"] > 0
    assert "cloud_cover_pct" in data["data"][0]


def test_visual_crossing_historical_endpoint():
    response = client.get(
        "/api/weather/historical/visual-crossing?latitude=26.9124&longitude=75.7873&start_date=2023-01-01&end_date=2023-01-02"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["provider"] == "Visual Crossing"
    assert len(data["data"]) > 0


def test_run_forecast():
    response = client.post("/api/forecasts/run", json={"horizon_hours": 24})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["plants_forecasted"] >= 4


def test_dashboard_summary():
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "forecast_horizon_hours" in data
    assert "plants" in data
    assert len(data["plants"]) >= 4
    assert "hourly_balance" in data
