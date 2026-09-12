<div align="center">

# ⚡ CONCIOUS
### *Autonomous Multi-Nodal Renewable Microgrid & Intelligent Energy Orchestrator*

[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20TimescaleDB-336791.svg?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%20Flash-8E75B2.svg?style=for-the-badge&logo=google)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Deployment-Docker%20Compose-2496ED.svg?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>An enterprise-grade, edge-ready platform that harmonizes distributed solar PV, wind generation, battery storage systems (BESS), and real-time grid loads using deterministic convex optimization and generative AI advisory.</b>
</p>

</div>

---

## 📖 Table of Contents

- [Executive Summary](#-executive-summary)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Mathematical Formulations](#-mathematical-formulations)
  - [1. Solar PV Temperature Derating](#1-solar-pv-temperature-derating)
  - [2. Wind Aerodynamic Power Modeling](#2-wind-aerodynamic-power-modeling)
  - [3. BESS State-of-Charge Dynamics](#3-bess-state-of-charge-dynamics)
  - [4. MILP Dispatch Optimization Objective](#4-milp-dispatch-optimization-objective)
- [Repository Structure](#-repository-structure)
- [API Reference](#-api-reference)
- [AI Copilot & Advisory System](#-ai-copilot--advisory-system)
- [Installation & Quickstart](#-installation--quickstart)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
  - [Docker Compose Deployment](#docker-compose-deployment)
- [Environment Configuration](#-environment-configuration)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License & Contact](#-license--contact)

---

## 📌 Executive Summary

Modern commercial and industrial (C&I) microgrids face acute challenges balancing dynamic, intermittent renewable supplies against fluctuating wholesale electricity tariffs and critical demand curves. 

**CONCIOUS** provides an end-to-end platform for autonomous microgrid dispatch, operational monitoring, and risk management. By linking **machine learning forecast models (Solar PV & Wind)**, **Mixed-Integer Linear Programming (MILP) battery dispatch**, **high-speed anomaly alerting**, and **Google Gemini 2.5/Flash generative advisory**, CONCIOUS transforms passive power systems into resilient, self-balancing energy nodes that:
- Maximize renewable self-consumption ($>90\%$).
- Minimize demand-charge penalties and time-of-use (ToU) electricity costs.
- Preserve battery lifecycle health through thermal and depth-of-discharge (DoD) constraint bounding.
- Deliver real-time, context-aware operational directives to plant managers.

---

## 🏛️ System Architecture

CONCIOUS uses an asynchronous, decoupled architecture that connects sensor edge-telemetry, database persistence, analytical solver pipelines, and LLM reasoning engines.

```
                           ┌─────────────────────────────────────────┐
                           │      Field Telemetry & Weather APIs     │
                           │   • Solar Arrays (Inverters & POA)      │
                           │   • Wind Turbines (Anemometer & Hub)    │
                           │   • Open-Meteo & Grid Import Meters     │
                           └────────────────────┬────────────────────┘
                                                │ REST / WebSockets / Modbus
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │        FastAPI Gateway & Router         │
                           │       (Validation & Rate Limiting)      │
                           └──────────────┬──────────────────┬───────┘
                                          │                  │
               Telemetry Ingestion Events │                  │ Asynchronous Dispatch
                                          ▼                  ▼
                           ┌───────────────────────┐  ┌───────────────────────┐
                           │  PostgreSQL / Redis   │  │  Inference Engine     │
                           │  Time-Series Records  │  │  (LightGBM / XGBoost) │
                           └──────────────┬────────┘  └──────────┬────────────┘
                                          │                      │
                                          └───────────┬──────────┘
                                                      ▼
                           ┌─────────────────────────────────────────┐
                           │       MILP Dispatch Optimizer Engine    │
                           │   (PuLP / SciPy HiGHS Convex Solver)    │
                           │    • Cost-Minimization Objective        │
                           │    • Physical BESS & Grid Constraints   │
                           └────────────────────┬────────────────────┘
                                                │
                          Optimal Trajectories  │ Alert Context & Anomaly Flags
                          & Operational Vectors │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │      Google Gemini Advisory Layer       │
                           │    • Dynamic Prompt Engineering         │
                           │    • Strategic Intervention Synthesizer │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                           ┌─────────────────────────────────────────┐
                           │      Operator Dashboards & Actuators    │
                           │     (Web UI / Edge Inverter Registers)  │
                           └─────────────────────────────────────────┘
```

---

## ✨ Key Features

- **Multi-Nodal Asset Ingestion**: Parallel data processing from distributed solar strings, wind turbine hubs, and smart meters.
- **Physics-Informed ML Forecasting**: Temperature-compensated solar yield prediction and cubic wind-speed kinetic curve modeling.
- **Convex BESS Optimization**: Rolling 24-hour horizon ($T = 96$, 15-minute intervals) battery dispatch schedules resolving grid price arbitrage and peak shaving.
- **Automated Health & Anomaly Alerts**: Real-time alerts for inverter tripping, thermal runaway warning signs, and unexpected clipping.
- **Context-Enriched GenAI Copilot**: Automated root-cause analysis, dispatch auditing, and natural language executive reports using Google Gemini.
- **Production-Ready Architecture**: Asynchronous SQLAlchemy 2.0, Pydantic v2 data contracts, Docker Compose virtualization, and comprehensive `pytest` test suites.

---

## 🔬 Mathematical Formulations

### 1. Solar PV Temperature Derating
Solar photovoltaic cell efficiency diminishes as cell temperatures exceed Standard Test Conditions ($\text{STC}: 25^\circ\text{C}, 1000\text{ W/m}^2$). Real-time plant yield is modeled as:

$$P_{\text{solar}}(t) = P_{\text{STC}} \cdot \left( \frac{G(t)}{G_{\text{STC}}} \right) \cdot \left[ 1 + \gamma \cdot (T_{\text{cell}}(t) - T_{\text{STC}}) \right] \cdot \eta_{\text{inv}}$$

Where:
- $G(t)$: Plane of Array (POA) irradiance ($\text{W/m}^2$)
- $\gamma$: Temperature coefficient of maximum power ($\approx -0.0039\text{ }^\circ\text{C}^{-1}$)
- $T_{\text{cell}}(t) = T_{\text{amb}}(t) + \left( \frac{\text{NOCT} - 20}{800} \right) \cdot G(t)$
- $\eta_{\text{inv}}$: Inverter DC-to-AC conversion efficiency ($\approx 0.97$)

### 2. Wind Aerodynamic Power Modeling
Wind power follows a cubic velocity profile, bounded by aerodynamic limits ($C_p$) and operational thresholds:

$$P_{\text{wind}}(v) = \begin{cases} 
0, & v < v_{\text{cut-in}} \quad \text{or} \quad v \ge v_{\text{cut-out}} \\
\frac{1}{2} \rho A C_p(\lambda, \beta) v^3, & v_{\text{cut-in}} \le v < v_{\text{rated}} \\
P_{\text{rated}}, & v_{\text{rated}} \le v < v_{\text{cut-out}}
\end{cases}$$

Where:
- $\rho$: Local air density corrected for ambient temperature and elevation ($\text{kg/m}^3$)
- $A$: Rotor swept area ($\pi R^2$)
- $C_p$: Power aerodynamic coefficient ($C_p \le 0.593$, the Betz limit)
- $v_{\text{cut-in}}, v_{\text{rated}}, v_{\text{cut-out}}$: Cut-in ($3\text{ m/s}$), rated ($12\text{ m/s}$), and cut-out ($25\text{ m/s}$) speeds

### 3. BESS State-of-Charge Dynamics
The energy evolution of the Battery Energy Storage System across interval $\Delta t$ is governed by:

$$\text{SOC}(t+1) = \text{SOC}(t) + \left( P_{\text{ch}}(t) \cdot \eta_{\text{ch}} - \frac{P_{\text{dis}}(t)}{\eta_{\text{dis}}} \right) \frac{\Delta t}{E_{\text{nom}}}$$

Subject to operational boundaries:
$$\text{SOC}_{\min} \le \text{SOC}(t) \le \text{SOC}_{\max} \quad \forall t$$
$$0 \le P_{\text{ch}}(t) \le P_{\text{ch}}^{\max} \cdot u_{\text{ch}}(t), \quad 0 \le P_{\text{dis}}(t) \le P_{\text{dis}}^{\max} \cdot u_{\text{dis}}(t)$$
$$u_{\text{ch}}(t) + u_{\text{dis}}(t) \le 1, \quad u_{\text{ch}}(t), u_{\text{dis}}(t) \in \{0, 1\}$$

### 4. MILP Dispatch Optimization Objective
The system minimizes net operational expenses (OPEX) over rolling lookahead horizon $T$:

$$\min \sum_{t=1}^{T} \left( C_{\text{grid}}(t) P_{\text{import}}(t) \Delta t - R_{\text{feed}}(t) P_{\text{export}}(t) \Delta t + C_{\text{deg}} (P_{\text{ch}}(t) + P_{\text{dis}}(t)) \Delta t + \lambda_{\text{def}} P_{\text{deficit}}(t) \right)$$

**Subject to the instantaneous nodal power balance constraint:**
$$P_{\text{load}}(t) = P_{\text{solar}}(t) + P_{\text{wind}}(t) + P_{\text{dis}}(t) - P_{\text{ch}}(t) + P_{\text{import}}(t) - P_{\text{export}}(t) + P_{\text{deficit}}(t)$$

---

## 🗂️ Repository Structure

```plaintext
concious-microgrid/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── ai.py                  # Gemini AI Copilot interactive endpoints
│   │   │   │   ├── alerts.py              # Anomaly detection & active alert routes
│   │   │   │   ├── dashboard.py           # Real-time aggregated system telemetry
│   │   │   │   ├── forecasts.py           # Generation & demand forecasting horizons
│   │   │   │   ├── generation.py          # Plant-level telemetry ingestion
│   │   │   │   ├── plants.py              # Plant configurations and assets metadata
│   │   │   │   ├── users.py               # Authentication and permission checks
│   │   │   │   └── weather.py             # Open-Meteo integration and weather reads
│   │   │   └── __init__.py
│   │   ├── core/
│   │   │   ├── config.py                  # Pydantic BaseSettings management
│   │   │   └── logging_config.py          # Structured logging definitions
│   │   ├── database/
│   │   │   ├── connection.py              # Async SQLAlchemy engine & session factory
│   │   │   └── models.py                  # Relational DB models (Readings, Plans, Alerts)
│   │   ├── schemas/
│   │   │   ├── alert.py                   # Alert validation schemas
│   │   │   ├── battery.py                 # Storage parameters & optimization DTOs
│   │   │   ├── dashboard.py               # Aggregated response schemas
│   │   │   ├── forecast.py                # Prediction request and horizon schemas
│   │   │   ├── generation.py              # Generation payload contracts
│   │   │   ├── plant.py                   # Plant metadata schemas
│   │   │   ├── recommendation.py          # AI response structured formats
│   │   │   ├── user.py                    # User authentication DTOs
│   │   │   └── weather.py                 # Environmental schemas
│   │   ├── services/
│   │   │   ├── alert_service.py           # Rule-based and statistical anomaly evaluation
│   │   │   ├── forecast_service.py        # ML model prediction orchestration
│   │   │   ├── gemini_service.py          # Context-builder & Google Gemini LLM caller
│   │   │   ├── grid_analysis_service.py    # Frequency, stability, and headroom analysis
│   │   │   ├── recommendation_service.py  # Dispatch heuristic rule processor
│   │   │   ├── storage_service.py         # MILP / LP BESS dispatch optimizer
│   │   │   └── weather_service.py         # Environmental client integration
│   │   └── main.py                        # FastAPI entrypoint, middleware, and lifespans
│   ├── ml/
│   │   └── data/
│   │       ├── processed/                 # Training, validation, and testing splits
│   │       └── raw/                       # Raw sensor time-series data
│   ├── tests/
│   │   ├── conftest.py                    # Fixtures and test database setup
│   │   ├── test_api.py                    # API route validation
│   │   ├── test_optimizer.py              # BESS mass-balance & optimization tests
│   │   └── test_services.py               # Unit tests for forecasting & alerts
│   ├── .env.example                       # Base template for environment variables
│   ├── Dockerfile                         # Production-grade multi-stage container
│   ├── requirements.txt                   # Dependency definitions
│   └── README.md
├── docker-compose.yml                     # Multi-container local orchestration
├── LICENSE                                # Project license file
└── README.md                              # Project documentation
```

---

## 🌐 API Reference

### Key Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/dashboard/summary` | Real-time aggregate plant telemetry, generation, SOC, and grid balance. |
| `POST` | `/api/v1/generation/record` | Ingest real-time asset telemetry (irradiance, wind speed, power). |
| `GET` | `/api/v1/forecasts/{plant_id}` | Retrieve 24-hour predictive generation horizon vectors. |
| `POST` | `/api/v1/storage/optimize` | Solve MILP BESS schedule for target lookahead horizon. |
| `POST` | `/api/v1/ai/recommendations` | Query Google Gemini Copilot for operational and dispatch directives. |
| `GET` | `/api/v1/alerts/active` | List open anomalies, grid limit warnings, and thermal alarms. |

### OpenAPI Documentation
Once running, the interactive Swagger UI and ReDoc are available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🤖 AI Copilot & Advisory System

The AI Advisory Layer provides human operators with clear, context-aware operational recommendations. It packages system telemetry—including generation metrics, BESS charge states, wholesale tariffs, and active alerts—into a structured prompt for the Gemini LLM.

#### Request Example (`POST /api/v1/ai/recommendations`)
```json
{
  "current_load_kw": 480.0,
  "solar_forecast_kw": 310.0,
  "wind_forecast_kw": 80.0,
  "battery_soc_percent": 32.5,
  "grid_tariff_inr_per_kwh": 8.50,
  "curtailment_risk": false
}
```

#### Response Example
```json
{
  "status": "success",
  "data": {
    "recommended_action": "BATTERY_DISCHARGE_PEAK_SHAVING",
    "dispatch_mw": 0.090,
    "projected_cost_savings_inr": 765.00,
    "system_resiliency_score": 0.94,
    "justification": "Peak tariff window active (8.50 INR/kWh). Total renewable supply (390 kW) leaves a 90 kW shortfall against building demand (480 kW). Discharging storage at 0.18C avoids expensive grid power while maintaining battery SOC safely above the 20% limit.",
    "contingency_alert": "Wind speed approaching gust limits; monitor farm 2 over next 45 minutes."
  }
}
```

---

## ⚙️ Installation & Quickstart

### Prerequisites
- **Python**: Version 3.11 or higher
- **PostgreSQL**: Version 14+ (or local SQLite for development)
- **Docker & Docker Compose** (optional for containerized setup)
- **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

---

### Local Development Setup

#### 1. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/your-username/concious-microgrid.git
cd concious-microgrid/backend

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Setup Environment Variables
```bash
cp .env.example .env
# Open and populate .env with your credentials (see configuration section)
```

#### 4. Initialize Database
```bash
python -c "import asyncio; from app.database.connection import init_db; asyncio.run(init_db())"
```

#### 5. Launch Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Docker Compose Deployment

Run the complete multi-container stack (API, PostgreSQL database, and Redis cache):

```bash
docker compose up -d --build
```

Verify service status:
```bash
docker compose ps
docker compose logs -f api
```

---

## 🔐 Environment Configuration

Create a `.env` file in the `backend/` directory based on the following template:

```ini
# Application Configuration
PROJECT_NAME="CONCIOUS Renewable Microgrid Orchestrator"
ENVIRONMENT="development"
DEBUG=True

# Database Connections
# PostgreSQL Example:
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/concious_db"
# Local SQLite fallback:
# DATABASE_URL="sqlite+aiosqlite:///./concious.db"

# Google Gemini API Settings
GEMINI_API_KEY="AIzaSyYourGeminiApiKeyHere"
GEMINI_MODEL="gemini-2.5-flash"

# Physical Hardware Safety Parameters
BATTERY_MIN_SOC=20.0
BATTERY_MAX_SOC=90.0
BATTERY_CAPACITY_KWH=1000.0
BATTERY_MAX_CHARGE_KW=500.0
BATTERY_MAX_DISCHARGE_KW=500.0
GRID_EXPORT_LIMIT_KW=750.0

# CORS Configuration (JSON-encoded array)
BACKEND_CORS_ORIGINS='["http://localhost:3000", "http://localhost:8000"]'
```

---

## 🧪 Testing & Quality Assurance

Run the test suite using `pytest`:

```bash
cd backend

# Execute unit and integration tests with coverage reporting
pytest -v --cov=app tests/
```

Test coverage includes:
- **Optimization Conservation**: Verifies battery charge/discharge operations follow energy balance laws without thermodynamic violations.
- **API Endpoints**: Validates payload schemas, status codes, and error handlers across all router endpoints.
- **Advisory Robustness**: Verifies fallback mechanisms and schema parsing when interfacing with the Gemini API.

---

## 🗺️ Roadmap

- [x] Multi-source renewable telemetry ingestion (Solar, Wind, Load, Grid).
- [x] MILP battery storage dispatch with time-of-use cost minimization.
- [x] GenAI context integration with Google Gemini Flash.
- [ ] Integration of Open Automated Demand Response (OpenADR 2.0b).
- [ ] Multi-objective Pareto optimization balancing battery degradation with carbon reduction.
- [ ] Sub-second primary frequency response (synthetic inertia emulation).
- [ ] Edge hardware support via Modbus RTU / RS-485 micro-controllers.

---

## 🤝 Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/NewCapability`.
3. Commit your changes: `git commit -m 'feat: Add NewCapability'`.
4. Push to the branch: `git push origin feature/NewCapability`.
5. Open a Pull Request with a description of your changes and test coverage.

---

## 📄 License & Contact

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Developed with pride by **TEAM CONCIOUS**.  
*Empowering reliable, carbon-neutral, autonomous microgrids.*