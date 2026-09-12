import httpx, json

params = {
    "latitude": 26.9124,
    "longitude": 75.7873,
    "hourly": "temperature_2m,relative_humidity_2m,cloud_cover,direct_normal_irradiance,wind_speed_10m,wind_direction_10m,surface_pressure,precipitation",
    "forecast_days": 3,
    "timezone": "UTC"
}

print("Testing Open-Meteo API...")
with httpx.Client(timeout=15.0) as client:
    r = client.get("https://api.open-meteo.com/v1/forecast", params=params)

print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    h = data["hourly"]
    n = len(h["time"])
    print(f"Timestamps returned: {n}")
    print(f"First hour: {h['time'][0]}")
    print(f"Last hour:  {h['time'][-1]}")
    print()
    print("Sample (hour 0):")
    print(f"  Temperature:    {h['temperature_2m'][0]} C")
    print(f"  Humidity:       {h['relative_humidity_2m'][0]} %")
    print(f"  Cloud cover:    {h['cloud_cover'][0]} %")
    print(f"  Solar irrad.:   {h['direct_normal_irradiance'][0]} W/m2")
    print(f"  Wind speed:     {h['wind_speed_10m'][0]} m/s")
    print(f"  Wind direction: {h['wind_direction_10m'][0]} deg")
    print(f"  Pressure:       {h['surface_pressure'][0]} hPa")
    print(f"  Precipitation:  {h['precipitation'][0]} mm")
    print()
    # Show a daytime hour
    print("Sample (hour 12 — likely daytime):")
    print(f"  Temperature:    {h['temperature_2m'][12]} C")
    print(f"  Solar irrad.:   {h['direct_normal_irradiance'][12]} W/m2")
    print(f"  Wind speed:     {h['wind_speed_10m'][12]} m/s")
    print(f"  Cloud cover:    {h['cloud_cover'][12]} %")
    print()
    print("SUCCESS: Open-Meteo API is fully operational.")
    print("No API key needed. Free forever.")
else:
    print(f"ERROR: {r.text[:300]}")
