# Renewable Generation Forecasting Platform — Backend

AI-powered 24–72 hour renewable generation forecasting with grid decision support.

## ⚠️ Important Disclaimer
All generation data in this demo is **SIMULATED**. Weather data is real (Open-Meteo API).
This platform is a **decision-support tool** and does not control real grid assets.

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your DATABASE_URL
```

### 3. Generate demo data & train models
```bash
python ml/scripts/generate_demo_data.py
python ml/scripts/prepare_data.py
python ml/scripts/train_solar.py
python ml/scripts/train_wind.py
python ml/scripts/evaluate.py
```

### 4. Seed database
```bash
python scripts/seed_db.py
```

### 5. Start API server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. API docs
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## Run Forecast
```bash
curl -X POST http://localhost:8000/api/forecasts/run \
  -H "Content-Type: application/json" \
  -d '{"horizon_hours": 72}'
```

## Dashboard
```bash
curl http://localhost:8000/api/dashboard/summary
```

---

## Run Tests
```bash
pytest tests/ -v --cov=app --cov=ml
```

---

## Architecture

```
React Frontend
      ↓ REST
FastAPI (app/main.py)
      ↓
┌─── WeatherService ────→ Open-Meteo API
├─── ForecastService ───→ MLPredictor (XGBoost)
├─── GridAnalysisService → surplus/deficit/severity
├─── StorageService ────→ battery physics
├─── RecommendationEngine → deterministic rules
└─── AlertService ──────→ event grouping
      ↓
PostgreSQL
```

## ML Pipeline
```
generate_demo_data.py → raw CSVs
prepare_data.py       → cleaned + feature-engineered CSVs
train_solar.py        → solar_model.pkl
train_wind.py         → wind_model.pkl
evaluate.py           → MAE, RMSE, R², WAPE vs baseline
```

## Key Design Decisions
- **Separate solar/wind models**: different generation physics
- **Direct multi-step forecasting**: avoids recursive error accumulation
- **Historical lags at inference**: lag_1/24/168 from real DB records, not predicted values
- **Deterministic recommendations**: fully explainable, no ML black box
- **WAPE not MAPE**: safe for near-zero solar values
- **Chronological train/val/test split**: no data leakage
