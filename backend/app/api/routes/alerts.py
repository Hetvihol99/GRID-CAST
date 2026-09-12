"""Alerts API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database.connection import get_db
from app.database.models import Alert, AlertSeverity
from app.schemas.alert import AlertListResponse, AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=AlertListResponse)
def list_alerts(
    region: str = "default",
    active_only: bool = True,
    severity: Optional[str] = Query(None, description="Filter by severity: watch|warning|critical"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """
    List alerts for a region.
    Alerts are pre-grouped (consecutive hours = one alert).
    """
    query = db.query(Alert).filter(Alert.region == region)

    if active_only:
        query = query.filter(Alert.is_active == True)

    if severity:
        query = query.filter(Alert.severity == severity)

    query = query.order_by(Alert.start_time.desc()).limit(limit)
    alerts = query.all()

    active_count = db.query(Alert).filter(
        Alert.region == region, Alert.is_active == True
    ).count()

    return AlertListResponse(
        total=len(alerts),
        active_count=active_count,
        alerts=alerts,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get a specific alert by ID."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert
