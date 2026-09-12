"""Tests for recommendation engine — verifies correct actions for each scenario."""

import pytest
from datetime import datetime, timezone
from app.services.recommendation_service import RecommendationEngine
from app.services.grid_analysis_service import HourlyBalance
from app.services.storage_service import BatteryActionResult

NOW = datetime.now(timezone.utc)


def make_balance(net_mw: float, severity: str = "warning") -> HourlyBalance:
    demand = 1000.0
    gen = demand + net_mw
    alert_type = "surplus" if net_mw > 0 else ("deficit" if net_mw < 0 else None)
    return HourlyBalance(
        timestamp=NOW,
        total_generation_mw=gen,
        demand_mw=demand,
        net_balance_mw=net_mw,
        severity=severity,
        alert_type=alert_type,
    )


def make_battery_result(scenario, contribution, remaining, limiting=None) -> BatteryActionResult:
    return BatteryActionResult(
        scenario=scenario,
        imbalance_mw=contribution + remaining,
        battery_contribution_mw=contribution,
        remaining_imbalance_mw=remaining,
        soc_before_pct=70,
        soc_after_pct=75,
        is_fully_covered=(remaining < 0.5),
        limiting_factor=limiting,
        explanation="Test explanation.",
    )


class TestRecommendationEngine:
    def setup_method(self):
        self.engine = RecommendationEngine()

    def test_normal_gives_monitor(self):
        """Normal balance should recommend MONITOR."""
        balance = make_balance(0, severity="normal")
        result = self.engine.generate(balance)
        assert len(result.recommendations) == 1
        assert result.recommendations[0].action == "monitor"

    def test_surplus_with_battery_gives_charge(self):
        """Surplus with available battery → CHARGE_STORAGE as first action."""
        balance = make_balance(+200, severity="warning")
        battery_result = make_battery_result("surplus", contribution=80, remaining=120)
        result = self.engine.generate(balance, battery_result)

        actions = [r.action for r in result.recommendations]
        assert "charge_storage" in actions
        # Charge should be priority 1
        charge_rec = next(r for r in result.recommendations if r.action == "charge_storage")
        assert charge_rec.priority == 1

    def test_surplus_with_full_battery_gives_curtailment(self):
        """Surplus with full battery → CONSIDER_CURTAILMENT."""
        balance = make_balance(+200, severity="warning")
        battery_result = make_battery_result("surplus", contribution=0, remaining=200, limiting="soc_max")
        result = self.engine.generate(balance, battery_result)

        actions = [r.action for r in result.recommendations]
        assert "consider_curtailment" in actions

    def test_curtailment_not_automatic(self):
        """Curtailment recommendation text must include human review disclaimer."""
        balance = make_balance(+300, severity="critical")
        battery_result = make_battery_result("surplus", contribution=0, remaining=300, limiting="soc_max")
        result = self.engine.generate(balance, battery_result)

        curtailment = next(
            (r for r in result.recommendations if r.action == "consider_curtailment"), None
        )
        assert curtailment is not None
        # Should NOT say "AI will shut down" — should say "human review" or "operator"
        assert "operator" in curtailment.description.lower() or "human" in curtailment.description.lower() \
            or "recommendation" in curtailment.description.lower()

    def test_deficit_gives_discharge_then_backup(self):
        """Deficit partially covered by battery → DISCHARGE then PREPARE_BACKUP."""
        balance = make_balance(-300, severity="critical")
        battery_result = make_battery_result("deficit", contribution=100, remaining=200)
        result = self.engine.generate(balance, battery_result)

        actions = [r.action for r in result.recommendations]
        assert "discharge_storage" in actions
        assert "prepare_backup" in actions

        # Discharge should be priority 1
        discharge = next(r for r in result.recommendations if r.action == "discharge_storage")
        assert discharge.priority < next(r for r in result.recommendations if r.action == "prepare_backup").priority

    def test_deficit_empty_battery_gives_backup_only(self):
        """Deficit with empty battery → PREPARE_BACKUP, discharge marked infeasible."""
        balance = make_balance(-200, severity="critical")
        battery_result = make_battery_result("deficit", contribution=0, remaining=200, limiting="soc_min")
        result = self.engine.generate(balance, battery_result)

        discharge = next((r for r in result.recommendations if r.action == "discharge_storage"), None)
        backup = next((r for r in result.recommendations if r.action == "prepare_backup"), None)

        assert discharge is not None
        assert discharge.is_feasible is False  # Battery empty — not feasible
        assert backup is not None
        assert backup.is_feasible is True
