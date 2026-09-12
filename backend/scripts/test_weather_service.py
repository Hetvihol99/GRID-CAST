"""
End-to-end test of the WeatherService with real Open-Meteo API.
Run: python scripts/test_weather_service.py
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_temp.db")
os.environ.setdefault("WEATHER_API_BASE_URL", "https://api.open-meteo.com/v1")
os.environ.setdefault("WEATHER_API_KEY", "")
os.environ.setdefault("MODEL_DIR", "ml/trained_models")
os.environ.setdefault("SOLAR_MODEL_FILE", "solar_model.pkl")
os.environ.setdefault("WIND_MODEL_FILE", "wind_model.pkl")
os.environ.setdefault("SOLAR_SCALER_FILE", "scaler_solar.pkl")
os.environ.setdefault("WIND_SCALER_FILE", "scaler_wind.pkl")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("FORECAST_CACHE_TTL_SECONDS", "1800")

from app.services.weather_service import WeatherService, WeatherUnavailableError

print("=" * 60)
print("  WeatherService - Live Open-Meteo Integration Test")
print("=" * 60)

service = WeatherService()

test_locations = [
    ("Rajasthan Solar Farm A",  26.9124, 75.7873, "solar"),
    ("Gujarat Solar Park B",    23.0225, 72.5714, "solar"),
    ("Tamil Nadu Wind Farm I",   8.7139, 77.7567, "wind"),
    ("AP Wind Farm II",         15.9129, 79.7400, "wind"),
]

all_pass = True
for name, lat, lon, plant_type in test_locations:
    print(f"\n[{plant_type.upper()}] {name} ({lat}, {lon})")
    try:
        points = service.test_connectivity(lat, lon, hours=72)
        t0 = points[0].timestamp.strftime("%Y-%m-%d %H:%M")
        t1 = points[-1].timestamp.strftime("%Y-%m-%d %H:%M")
        print(f"  Points:      {len(points)}")
        print(f"  Time range:  {t0} -> {t1} UTC")

        temps  = [p.temperature_c for p in points]
        winds  = [p.wind_speed_ms for p in points]
        solar  = [p.solar_irradiance_wm2 for p in points]
        clouds = [p.cloud_cover_pct for p in points]

        print(f"  Temp C:      {min(temps):.1f} - {max(temps):.1f}  (avg {sum(temps)/len(temps):.1f})")
        print(f"  Wind m/s:    {min(winds):.1f} - {max(winds):.1f}  (avg {sum(winds)/len(winds):.1f})")
        print(f"  Solar W/m2:  {min(solar):.0f} - {max(solar):.0f}  (avg {sum(solar)/len(solar):.0f})")
        print(f"  Cloud %:     {min(clouds):.0f} - {max(clouds):.0f}  (avg {sum(clouds)/len(clouds):.0f})")

        print(f"\n  Next 6 hours:")
        print(f"  {'Time':>6}  {'Temp C':>7}  {'Wind':>6}  {'Solar':>7}  {'Cloud':>6}")
        print(f"  {'-'*42}")
        for p in points[:6]:
            print(f"  {p.timestamp.strftime('%H:%M'):>6}  {p.temperature_c:>7.1f}  {p.wind_speed_ms:>6.1f}  {p.solar_irradiance_wm2:>7.1f}  {p.cloud_cover_pct:>6.0f}")

        print(f"  PASS")

    except WeatherUnavailableError as e:
        print(f"  FAIL: {e}")
        all_pass = False
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        all_pass = False

print("\n" + "=" * 60)
if all_pass:
    print("  ALL TESTS PASSED")
    print("  Open-Meteo API: FREE, no API key needed")
    print("  Variables: GHI, DNI, wind, temp, humidity, cloud, pressure")
else:
    print("  SOME TESTS FAILED - check internet connectivity")
print("=" * 60)
