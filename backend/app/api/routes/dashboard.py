"""
Dashboard API route — single endpoint for full dashboard data.
The React frontend calls GET /api/dashboard/summary to render the entire UI.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.database.connection import get_db
from app.database.models import Plant, Forecast, Alert, BatteryStorage, DemandData
from app.schemas.dashboard import DashboardSummary, PlantStatusSummary, HourlyBalance, BatterySummary
from app.schemas.alert import AlertResponse
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    region: str = "default",
    db: Session = Depends(get_db),
):
    """
    Returns everything the React dashboard needs in one API call.
    Includes: plant statuses, 72-hour balance timeline, battery state, active alerts.

    This endpoint assembles data from DB — the heavy ML work happens in POST /forecasts/run.
    """
    now = datetime.now(timezone.utc)
    horizon = settings.FORECAST_HORIZON_HOURS

    # ── Plant statuses ────────────────────────────────────────────────────────
    plants = db.query(Plant).filter(Plant.is_active == True).all()
    plant_statuses = []

    for plant in plants:
        # Get most recent forecast for next hour
        next_forecast = (
            db.query(Forecast)
            .filter(
                Forecast.plant_id == plant.id,
                Forecast.forecast_timestamp >= now,
            )
            .order_by(Forecast.forecast_timestamp.asc())
            .first()
        )

        plant_statuses.append(PlantStatusSummary(
            plant_id=plant.id,
            plant_name=plant.name,
            plant_type=plant.plant_type.value,
            capacity_mw=plant.capacity_mw,
            latest_forecast_mw=next_forecast.predicted_generation_mw if next_forecast else None,
            status="active" if plant.is_active else "inactive",
            deviation_flag=False,
        ))

    # ── 72-hour balance timeline ──────────────────────────────────────────────
    end_time = now + timedelta(hours=horizon)

    # Get latest forecast run timestamp
    latest_run = (
        db.query(Forecast.forecast_generated_at)
        .filter(Forecast.forecast_timestamp >= now)
        .order_by(Forecast.forecast_generated_at.desc())
        .first()
    )

    hourly_balance_list = []
    next_hour_gen = 0.0
    next_hour_demand = 800.0

    if latest_run:
        # Get all forecasts for all plants for the latest run
        all_forecasts = (
            db.query(Forecast)
            .filter(
                Forecast.forecast_generated_at == latest_run[0],
                Forecast.forecast_timestamp.between(now, end_time),
            )
            .order_by(Forecast.forecast_timestamp)
            .all()
        )

        # Aggregate by timestamp
        ts_gen: dict = {}
        for f in all_forecasts:
            ts_key = f.forecast_timestamp.replace(minute=0, second=0, microsecond=0)
            ts_gen[ts_key] = ts_gen.get(ts_key, 0) + f.predicted_generation_mw

        # Get demand
        demand_records = (
            db.query(DemandData)
            .filter(
                DemandData.region == region,
                DemandData.timestamp.between(now, end_time),
            )
            .all()
        )
        ts_demand = {
            r.timestamp.replace(minute=0, second=0, microsecond=0): r.demand_mw
            for r in demand_records
        }

        from app.services.grid_analysis_service import GridAnalysisService
        grid_svc = GridAnalysisService()

        for ts, gen_mw in sorted(ts_gen.items()):
            demand_mw = ts_demand.get(ts, 800.0)
            balance = grid_svc.compute_balance(ts, gen_mw, demand_mw)
            hourly_balance_list.append(HourlyBalance(
                timestamp=ts,
                total_generation_mw=balance.total_generation_mw,
                demand_mw=balance.demand_mw,
                net_balance_mw=balance.net_balance_mw,
                severity=balance.severity,
            ))

        if hourly_balance_list:
            next_hour_gen = hourly_balance_list[0].total_generation_mw
            next_hour_demand = hourly_balance_list[0].demand_mw

    # ── Battery state ─────────────────────────────────────────────────────────
    battery_db = (
        db.query(BatteryStorage)
        .filter(BatteryStorage.region == region, BatteryStorage.is_active == True)
        .first()
    )

    battery_summary = None
    if battery_db:
        available_discharge = (
            (battery_db.current_soc_pct - battery_db.min_soc_pct) / 100
            * battery_db.capacity_mwh
        )
        available_charge = (
            (battery_db.max_soc_pct - battery_db.current_soc_pct) / 100
            * battery_db.capacity_mwh
        )
        battery_summary = BatterySummary(
            battery_id=battery_db.id,
            battery_name=battery_db.name,
            capacity_mwh=battery_db.capacity_mwh,
            current_soc_pct=battery_db.current_soc_pct,
            available_discharge_mwh=max(0, available_discharge),
            available_charge_mwh=max(0, available_charge),
            max_discharge_rate_mw=battery_db.max_discharge_rate_mw,
            max_charge_rate_mw=battery_db.max_charge_rate_mw,
        )

    # ── Active alerts ─────────────────────────────────────────────────────────
    active_alerts = (
        db.query(Alert)
        .filter(Alert.region == region, Alert.is_active == True)
        .order_by(Alert.start_time)
        .limit(20)
        .all()
    )

    # ── Overall severity ──────────────────────────────────────────────────────
    severity_order = {"normal": 0, "watch": 1, "warning": 2, "critical": 3}
    all_severities = [b.severity for b in hourly_balance_list[:24]]  # Next 24h
    overall_severity = max(all_severities, key=lambda s: severity_order.get(s, 0)) \
        if all_severities else "normal"

    # ── Upcoming critical periods ─────────────────────────────────────────────
    upcoming_critical = [
        b for b in hourly_balance_list
        if b.severity in ("warning", "critical")
    ][:10]

    net_next = round(next_hour_gen - next_hour_demand, 2)

    return DashboardSummary(
        generated_at=now,
        region=region,
        forecast_horizon_hours=horizon,
        total_forecast_mw_next_hour=round(next_hour_gen, 2),
        total_demand_mw_next_hour=round(next_hour_demand, 2),
        net_balance_mw_next_hour=net_next,
        overall_severity=overall_severity,
        plants=plant_statuses,
        hourly_balance=hourly_balance_list,
        battery=battery_summary,
        active_alerts=[AlertResponse.model_validate(a) for a in active_alerts],
        upcoming_critical_periods=upcoming_critical,
        model_version=latest_run[0].strftime("run_%Y%m%d_%H%M") if latest_run else None,
    )
