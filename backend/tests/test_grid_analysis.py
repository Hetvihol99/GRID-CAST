"""Tests for grid analysis service — severity classification."""

import pytest
from datetime import datetime, timezone
from app.services.grid_analysis_service import GridAnalysisService


NOW = datetime.now(timezone.utc)


class TestGridAnalysis:
    def setup_method(self):
        self.svc = GridAnalysisService()

    def test_normal_small_surplus(self):
        """1% surplus should be NORMAL."""
        balance = self.svc.compute_balance(NOW, total_generation_mw=1010, demand_mw=1000)
        assert balance.severity == "normal"
        assert balance.net_balance_mw == pytest.approx(10.0, abs=0.1)
        assert balance.alert_type == "surplus"

    def test_watch_moderate_surplus(self):
        """8% surplus should be WATCH."""
        balance = self.svc.compute_balance(NOW, total_generation_mw=1080, demand_mw=1000)
        assert balance.severity == "watch"

    def test_warning_large_deficit(self):
        """20% deficit should be WARNING."""
        balance = self.svc.compute_balance(NOW, total_generation_mw=800, demand_mw=1000)
        assert balance.severity == "warning"
        assert balance.alert_type == "deficit"

    def test_critical_extreme_deficit(self):
        """35% deficit should be CRITICAL."""
        balance = self.svc.compute_balance(NOW, total_generation_mw=650, demand_mw=1000)
        assert balance.severity == "critical"
        assert balance.net_balance_mw == pytest.approx(-350.0, abs=0.1)

    def test_exact_balance(self):
        """Exact match: generation == demand → NORMAL."""
        balance = self.svc.compute_balance(NOW, total_generation_mw=1000, demand_mw=1000)
        assert balance.severity == "normal"
        assert balance.net_balance_mw == pytest.approx(0.0, abs=0.1)
        assert balance.alert_type is None

    def test_invalid_demand_handled(self):
        """Zero or negative demand should not cause division by zero."""
        # Should not raise — uses 1 MW fallback
        balance = self.svc.compute_balance(NOW, total_generation_mw=500, demand_mw=0)
        assert balance is not None
