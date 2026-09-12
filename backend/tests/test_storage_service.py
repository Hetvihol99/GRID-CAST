"""
Test suite for Battery/Storage service.
These are the most critical calculation tests — judges will ask about battery logic.
"""

import pytest
from unittest.mock import MagicMock
from app.services.storage_service import StorageService
from app.database.models import BatteryStorage


def make_battery(**kwargs):
    """Helper to create a mock BatteryStorage object."""
    defaults = {
        "id": 1,
        "region": "default",
        "name": "Test Battery",
        "capacity_mwh": 100.0,
        "current_soc_pct": 70.0,
        "max_charge_rate_mw": 50.0,
        "max_discharge_rate_mw": 100.0,
        "min_soc_pct": 10.0,
        "max_soc_pct": 95.0,
        "efficiency": 0.90,
        "is_active": True,
    }
    defaults.update(kwargs)
    battery = MagicMock(spec=BatteryStorage)
    for k, v in defaults.items():
        setattr(battery, k, v)
    return battery


class TestStorageServiceSurplus:
    def setup_method(self):
        self.service = StorageService()

    def test_surplus_rate_limited(self):
        """Battery can only absorb up to max_charge_rate even if surplus is larger."""
        battery = make_battery(
            capacity_mwh=100, current_soc_pct=70, max_soc_pct=95,
            max_charge_rate_mw=50, efficiency=0.90,
        )
        result = self.service.analyze_surplus(battery, surplus_mw=200)

        # Max charge = 50 MW (rate limited, not capacity limited here)
        # Headroom = (95-70)/100 * 100 = 25 MWh
        # min(50, 25) = 25 MW absorbed
        assert result.battery_contribution_mw == pytest.approx(25.0, abs=0.1)
        assert result.remaining_imbalance_mw == pytest.approx(175.0, abs=0.1)
        assert result.is_fully_covered is False

    def test_surplus_battery_full(self):
        """When battery is at max SOC, contribution should be 0."""
        battery = make_battery(
            current_soc_pct=95, max_soc_pct=95, max_charge_rate_mw=50
        )
        result = self.service.analyze_surplus(battery, surplus_mw=100)

        assert result.battery_contribution_mw == pytest.approx(0.0, abs=0.1)
        assert result.remaining_imbalance_mw == pytest.approx(100.0, abs=0.1)
        assert result.limiting_factor == "soc_max"

    def test_surplus_fully_covered(self):
        """Small surplus fully absorbed by battery with plenty of headroom."""
        battery = make_battery(
            capacity_mwh=100, current_soc_pct=50, max_soc_pct=95,
            max_charge_rate_mw=50, efficiency=0.90,
        )
        result = self.service.analyze_surplus(battery, surplus_mw=10)

        assert result.battery_contribution_mw == pytest.approx(10.0, abs=0.1)
        assert result.is_fully_covered is True

    def test_surplus_soc_increases_correctly(self):
        """SOC after charging should increase by (energy_stored / capacity) * 100."""
        battery = make_battery(
            capacity_mwh=100, current_soc_pct=70, max_soc_pct=95,
            max_charge_rate_mw=50, efficiency=0.90,
        )
        result = self.service.analyze_surplus(battery, surplus_mw=20)

        # 20 MW absorbed × 0.90 efficiency = 18 MWh stored
        # SOC increase = (18/100) * 100 = 18%
        # Expected SOC = min(70 + 18, 95) = 88%
        assert result.soc_after_pct == pytest.approx(88.0, abs=1.0)


class TestStorageServiceDeficit:
    def setup_method(self):
        self.service = StorageService()

    def test_deficit_rate_limited(self):
        """Battery discharge is limited by max_discharge_rate."""
        battery = make_battery(
            capacity_mwh=200, current_soc_pct=70, min_soc_pct=10,
            max_discharge_rate_mw=100, efficiency=0.90,
        )
        # Deficit = 300 MW but battery can only discharge 100 MW (available energy = 120 MWh > 100 MW)
        result = self.service.analyze_deficit(battery, deficit_mw=300)

        assert result.battery_contribution_mw == pytest.approx(100.0, abs=0.1)
        assert result.remaining_imbalance_mw == pytest.approx(200.0, abs=0.1)
        assert result.is_fully_covered is False
        assert result.limiting_factor == "rate"

    def test_deficit_battery_empty(self):
        """When battery is at min SOC, contribution is 0."""
        battery = make_battery(
            current_soc_pct=10, min_soc_pct=10, max_discharge_rate_mw=100
        )
        result = self.service.analyze_deficit(battery, deficit_mw=50)

        assert result.battery_contribution_mw == pytest.approx(0.0, abs=0.1)
        assert result.remaining_imbalance_mw == pytest.approx(50.0, abs=0.1)
        assert result.limiting_factor == "soc_min"
        assert result.is_fully_covered is False

    def test_deficit_capacity_limited(self):
        """Deficit limited by available stored energy, not rate."""
        battery = make_battery(
            capacity_mwh=100, current_soc_pct=20, min_soc_pct=10,
            max_discharge_rate_mw=100, efficiency=0.90,
        )
        # Available energy = (20-10)/100 * 100 = 10 MWh
        # Discharge = min(100, 10) = 10 MW
        result = self.service.analyze_deficit(battery, deficit_mw=80)

        assert result.battery_contribution_mw == pytest.approx(10.0, abs=0.1)
        assert result.remaining_imbalance_mw == pytest.approx(70.0, abs=0.1)

    def test_deficit_soc_decreases_correctly(self):
        """SOC after discharging should decrease correctly."""
        battery = make_battery(
            capacity_mwh=100, current_soc_pct=70, min_soc_pct=10,
            max_discharge_rate_mw=100, efficiency=0.90,
        )
        result = self.service.analyze_deficit(battery, deficit_mw=20)

        # 20 MW discharged → SOC decrease = (20/100)*100 = 20%
        # Expected SOC = max(70 - 20, 10) = 50%
        assert result.soc_after_pct == pytest.approx(50.0, abs=1.0)

    def test_deficit_fully_covered(self):
        """Small deficit fully covered by battery."""
        battery = make_battery(
            capacity_mwh=200, current_soc_pct=80, min_soc_pct=10,
            max_discharge_rate_mw=100,
        )
        result = self.service.analyze_deficit(battery, deficit_mw=30)

        assert result.is_fully_covered is True
        assert result.remaining_imbalance_mw == pytest.approx(0.0, abs=0.5)
