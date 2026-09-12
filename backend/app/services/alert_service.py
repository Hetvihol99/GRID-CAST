"""
Alert Service
==============
WHAT: Groups consecutive deficit/surplus hours into single alert events.
WHY:  Without grouping, 72 individual hourly alerts would flood the operator UI.
      An "18:00–20:00 deficit" is one event, not three.

ALERT GROUPING ALGORITHM:
  1. For each balance period, check if it's alertable (>= WATCH severity)
  2. Consecutive alertable hours with same alert_type are grouped into one alert
  3. A gap of even one NORMAL hour breaks the group
  4. Peak magnitude = worst hour in the group
  5. Average magnitude = mean of all hours in the group

DEDUPLICATION:
  If an alert with the same start_time + alert_type already exists in DB,
  update it rather than creating a duplicate.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.database.models import Alert, AlertSeverity, AlertType
from app.services.grid_analysis_service import HourlyBalance
from app.core.logging_config import get_logger

logger = get_logger(__name__)

ALERTABLE_SEVERITIES = {"watch", "warning", "critical"}


class AlertService:
    """
    Groups hourly balance results into alert events and persists them.
    """

    def process_balance_series(
        self,
        balances: list[HourlyBalance],
        region: str,
        db: Session,
    ) -> list[Alert]:
        """
        Process a full 72-hour balance series and create/update alerts.

        INPUT:  List of HourlyBalance objects (from GridAnalysisService)
        OUTPUT: List of Alert DB objects (created or updated)
        """
        grouped_events = self._group_consecutive(balances)
        created_alerts = []

        for event in grouped_events:
            alert = self._upsert_alert(event, region, db)
            if alert:
                created_alerts.append(alert)

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save alerts: {e}")

        return created_alerts

    def _group_consecutive(self, balances: list[HourlyBalance]) -> list[dict]:
        """
        Group consecutive alertable hours into event windows.

        Example:
          17:00 — surplus/watch
          18:00 — surplus/warning
          19:00 — surplus/warning
          20:00 — surplus/critical
          21:00 — normal           ← breaks the group
          22:00 — deficit/watch    ← new group starts

          → Group 1: 17:00–20:00, surplus, peak_magnitude=largest of those 4 hours
          → Group 2: 22:00–22:00, deficit
        """
        groups = []
        current_group = None

        for balance in balances:
            is_alertable = balance.severity in ALERTABLE_SEVERITIES

            if not is_alertable:
                if current_group:
                    groups.append(self._finalize_group(current_group))
                    current_group = None
                continue

            # Alertable — check if it extends the current group
            if (
                current_group is not None
                and current_group["alert_type"] == balance.alert_type
            ):
                # Extend existing group
                current_group["hours"].append(balance)
            else:
                # Start a new group (different alert type, or first alert)
                if current_group:
                    groups.append(self._finalize_group(current_group))
                current_group = {
                    "alert_type": balance.alert_type,
                    "hours": [balance],
                }

        if current_group:
            groups.append(self._finalize_group(current_group))

        return groups

    def _finalize_group(self, group: dict) -> dict:
        """Compute summary statistics for an alert group."""
        hours = group["hours"]
        magnitudes = [abs(h.net_balance_mw) for h in hours]
        severities = [h.severity for h in hours]

        # Worst severity in the group
        severity_order = ["normal", "watch", "warning", "critical"]
        peak_severity = max(severities, key=lambda s: severity_order.index(s))

        return {
            "alert_type": group["alert_type"],
            "start_time": hours[0].timestamp,
            "end_time": hours[-1].timestamp,
            "peak_magnitude_mw": max(magnitudes),
            "avg_magnitude_mw": sum(magnitudes) / len(magnitudes),
            "severity": peak_severity,
            "duration_hours": len(hours),
        }

    def _upsert_alert(self, event: dict, region: str, db: Session) -> Optional[Alert]:
        """
        Create a new alert or update existing one to avoid duplicates.
        Deduplication key: region + alert_type + start_time (floored to hour).
        """
        start = event["start_time"].replace(minute=0, second=0, microsecond=0)

        existing = (
            db.query(Alert)
            .filter(
                Alert.region == region,
                Alert.alert_type == event["alert_type"],
                Alert.start_time == start,
            )
            .first()
        )

        # Build human-readable alert message
        direction = "surplus" if event["alert_type"] == "surplus" else "deficit"
        duration_str = f"{event['duration_hours']} hour(s)"
        message = (
            f"Expected renewable {direction} from "
            f"{start.strftime('%H:%M')} to "
            f"{event['end_time'].strftime('%H:%M')} ({duration_str}). "
            f"Peak imbalance: {event['peak_magnitude_mw']:.1f} MW. "
            f"Average: {event['avg_magnitude_mw']:.1f} MW. "
            f"Severity: {event['severity'].upper()}."
        )

        if existing:
            # Update: the latest forecast may refine the alert
            existing.end_time = event["end_time"]
            existing.peak_magnitude_mw = event["peak_magnitude_mw"]
            existing.avg_magnitude_mw = event["avg_magnitude_mw"]
            existing.severity = event["severity"]
            existing.message = message
            existing.is_active = True
            logger.debug(f"Updated existing alert id={existing.id}")
            return existing
        else:
            alert = Alert(
                region=region,
                alert_type=event["alert_type"],
                severity=event["severity"],
                start_time=start,
                end_time=event["end_time"],
                peak_magnitude_mw=event["peak_magnitude_mw"],
                avg_magnitude_mw=event["avg_magnitude_mw"],
                message=message,
                is_active=True,
            )
            db.add(alert)
            logger.info(
                f"New alert: {event['alert_type']} {event['severity']} "
                f"{start} → {event['end_time']}"
            )
            return alert

    def resolve_stale_alerts(self, region: str, db: Session) -> int:
        """
        Mark alerts as inactive if their end_time has passed.
        Called periodically to keep dashboard alert list current.
        Returns count of resolved alerts.
        """
        now = datetime.now(timezone.utc)
        stale = (
            db.query(Alert)
            .filter(
                Alert.region == region,
                Alert.is_active == True,
                Alert.end_time < now,
            )
            .all()
        )

        for alert in stale:
            alert.is_active = False

        if stale:
            db.commit()
            logger.info(f"Resolved {len(stale)} stale alerts for region '{region}'")

        return len(stale)
