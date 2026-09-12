"""
Storage / Battery Analysis Service
=====================================
WHAT: Physics-based battery calculations for surplus/deficit scenarios.
WHY:  Battery cannot magically solve all imbalances.
      We must respect: capacity, SOC limits, charge/discharge rate, efficiency.

CRITICAL: Never overclaim battery coverage.
  If deficit = 300 MW and max discharge = 100 MW:
    → Battery contributes 100 MW (max rate limited)
    → Remaining deficit = 200 MW
    → This must be reported accurately.

Battery constraints:
  1. Rate limit:  battery can only charge/discharge up to max_rate_mw per hour
  2. SOC limits:  cannot discharge below min_soc, cannot charge above max_soc
  3. Efficiency:  charging takes more energy than discharging returns
  4. Duration:    these are 1-hour time windows
"""

from dataclasses import dataclass
from typing import Optional

from app.core.logging_config import get_logger
from app.database.models import BatteryStorage

logger = get_logger(__name__)


@dataclass
class BatteryActionResult:
    """Result of battery action calculation for one hour."""
    scenario: str                           # "surplus" or "deficit"
    imbalance_mw: float                     # The problem to solve
    battery_contribution_mw: float          # How much battery can actually provide
    remaining_imbalance_mw: float           # What's left after battery
    soc_before_pct: float
    soc_after_pct: float
    is_fully_covered: bool
    limiting_factor: Optional[str]          # What caused the limit
    explanation: str                        # Plain English for the dashboard


class StorageService:
    """
    Physics-based battery analysis.
    All calculations are for a 1-hour time window.

    Usage:
        service = StorageService()
        result = service.analyze_surplus(battery, surplus_mw=200.0)
        result = service.analyze_deficit(battery, deficit_mw=300.0)
    """

    def analyze_surplus(
        self, battery: BatteryStorage, surplus_mw: float
    ) -> BatteryActionResult:
        """
        Calculate how much surplus can be absorbed by charging the battery.

        PHYSICS:
          energy_to_charge (MWh) = min(surplus_mw, max_charge_rate) × 1 hour
          but also: can't exceed available headroom = (max_soc - current_soc) / 100 × capacity_mwh
          accounting for efficiency: actual energy stored = energy_in × efficiency

        Example:
          Battery: 100 MWh, SOC=70%, max_charge=50 MW, max_soc=95%, efficiency=0.90
          Surplus: 200 MW

          Rate limit:          min(200, 50) = 50 MW
          Available headroom:  (95-70)/100 × 100 = 25 MWh
          Max chargeable:      min(50 MWh, 25 MWh) = 25 MWh → 25 MW for 1 hour
          Energy stored:       25 × 0.90 = 22.5 MWh
          New SOC:             70 + (22.5/100) × 100 = 92.5%
          Remaining surplus:   200 - 25 = 175 MW
        """
        if surplus_mw <= 0:
            return self._zero_action("surplus", surplus_mw, battery, "no_surplus")

        # Step 1: Rate limit
        rate_limited_mw = min(surplus_mw, battery.max_charge_rate_mw)

        # Step 2: Headroom limit (how much space is available in battery)
        headroom_mwh = (battery.max_soc_pct - battery.current_soc_pct) / 100.0 * battery.capacity_mwh
        headroom_limited_mw = min(rate_limited_mw, headroom_mwh)  # 1-hour window

        # Determine limiting factor
        if headroom_mwh <= 0:
            limiting_factor = "soc_max"
        elif rate_limited_mw < surplus_mw and headroom_limited_mw == rate_limited_mw:
            limiting_factor = "rate"
        elif headroom_limited_mw < rate_limited_mw:
            limiting_factor = "capacity"
        else:
            limiting_factor = None

        battery_contribution = headroom_limited_mw

        # Step 3: Calculate new SOC (accounting for efficiency)
        energy_actually_stored = battery_contribution * battery.efficiency
        soc_increase_pct = (energy_actually_stored / battery.capacity_mwh) * 100
        soc_after = min(battery.current_soc_pct + soc_increase_pct, battery.max_soc_pct)

        remaining_surplus = max(0, surplus_mw - battery_contribution)
        is_fully_covered = remaining_surplus < 0.5  # <0.5 MW tolerance

        explanation = self._build_surplus_explanation(
            surplus_mw, battery_contribution, remaining_surplus,
            battery, soc_after, limiting_factor
        )

        return BatteryActionResult(
            scenario="surplus",
            imbalance_mw=surplus_mw,
            battery_contribution_mw=round(battery_contribution, 2),
            remaining_imbalance_mw=round(remaining_surplus, 2),
            soc_before_pct=battery.current_soc_pct,
            soc_after_pct=round(soc_after, 1),
            is_fully_covered=is_fully_covered,
            limiting_factor=limiting_factor,
            explanation=explanation,
        )

    def analyze_deficit(
        self, battery: BatteryStorage, deficit_mw: float
    ) -> BatteryActionResult:
        """
        Calculate how much of the deficit can be covered by discharging the battery.

        PHYSICS:
          discharge_limited_mw = min(deficit_mw, max_discharge_rate)
          available_energy_mwh = (current_soc - min_soc) / 100 × capacity_mwh
          actual_discharge_mw = min(discharge_limited_mw, available_energy_mwh)
          energy delivered to grid = discharge_mw × efficiency (round-trip losses)
          new_soc = current_soc - (actual_discharge / capacity) × 100

        Example:
          Battery: 100 MWh, SOC=70%, max_discharge=100 MW, min_soc=10%, efficiency=0.90
          Deficit: 300 MW

          Rate limit:          min(300, 100) = 100 MW
          Available energy:    (70-10)/100 × 100 = 60 MWh
          Discharge window:    min(100 MWh, 60 MWh) = 60 MW for 1 hour
          Energy to grid:      60 × 0.90 = 54 MWh delivered
          New SOC:             70 - (60/100) × 100 = 10% (at minimum)
          Remaining deficit:   300 - 60 = 240 MW → PREPARE BACKUP
        """
        if deficit_mw <= 0:
            return self._zero_action("deficit", deficit_mw, battery, "no_deficit")

        # Step 1: Rate limit
        rate_limited_mw = min(deficit_mw, battery.max_discharge_rate_mw)

        # Step 2: Available energy (respecting minimum SOC)
        available_energy_mwh = (
            (battery.current_soc_pct - battery.min_soc_pct) / 100.0 * battery.capacity_mwh
        )

        if available_energy_mwh <= 0:
            return BatteryActionResult(
                scenario="deficit",
                imbalance_mw=deficit_mw,
                battery_contribution_mw=0.0,
                remaining_imbalance_mw=deficit_mw,
                soc_before_pct=battery.current_soc_pct,
                soc_after_pct=battery.current_soc_pct,
                is_fully_covered=False,
                limiting_factor="soc_min",
                explanation=(
                    f"Battery is at minimum SOC ({battery.current_soc_pct:.0f}%). "
                    f"No energy available for discharge. "
                    f"Full deficit of {deficit_mw:.1f} MW requires backup generation."
                ),
            )

        actual_discharge_mw = min(rate_limited_mw, available_energy_mwh)

        # Determine limiting factor
        if rate_limited_mw < deficit_mw and actual_discharge_mw == rate_limited_mw:
            limiting_factor = "rate"
        elif actual_discharge_mw < rate_limited_mw:
            limiting_factor = "capacity"
        else:
            limiting_factor = None

        # Energy delivered to grid (after efficiency losses)
        energy_delivered_mwh = actual_discharge_mw * battery.efficiency
        soc_decrease_pct = (actual_discharge_mw / battery.capacity_mwh) * 100
        soc_after = max(battery.current_soc_pct - soc_decrease_pct, battery.min_soc_pct)

        remaining_deficit = max(0, deficit_mw - actual_discharge_mw)
        is_fully_covered = remaining_deficit < 0.5

        explanation = self._build_deficit_explanation(
            deficit_mw, actual_discharge_mw, remaining_deficit,
            battery, soc_after, limiting_factor, energy_delivered_mwh
        )

        return BatteryActionResult(
            scenario="deficit",
            imbalance_mw=deficit_mw,
            battery_contribution_mw=round(actual_discharge_mw, 2),
            remaining_imbalance_mw=round(remaining_deficit, 2),
            soc_before_pct=battery.current_soc_pct,
            soc_after_pct=round(soc_after, 1),
            is_fully_covered=is_fully_covered,
            limiting_factor=limiting_factor,
            explanation=explanation,
        )

    def _zero_action(
        self, scenario: str, imbalance_mw: float, battery: BatteryStorage, reason: str
    ) -> BatteryActionResult:
        return BatteryActionResult(
            scenario=scenario,
            imbalance_mw=imbalance_mw,
            battery_contribution_mw=0.0,
            remaining_imbalance_mw=max(0, imbalance_mw),
            soc_before_pct=battery.current_soc_pct,
            soc_after_pct=battery.current_soc_pct,
            is_fully_covered=True,
            limiting_factor=reason,
            explanation=f"No significant {scenario} to address.",
        )

    def _build_surplus_explanation(
        self, surplus, contribution, remaining, battery, soc_after, limiting_factor
    ) -> str:
        parts = [
            f"Surplus of {surplus:.1f} MW detected. "
            f"Battery can absorb {contribution:.1f} MW (charge rate: {battery.max_charge_rate_mw} MW, "
            f"SOC: {battery.current_soc_pct:.0f}% → {soc_after:.0f}%). "
        ]
        if limiting_factor == "soc_max":
            parts.append(f"Battery is at maximum SOC ({battery.max_soc_pct:.0f}%). Cannot charge further.")
        elif limiting_factor == "rate":
            parts.append(f"Limited by max charge rate ({battery.max_charge_rate_mw} MW).")
        elif limiting_factor == "capacity":
            parts.append("Limited by remaining storage headroom.")

        if remaining > 0.5:
            parts.append(
                f"Remaining surplus of {remaining:.1f} MW cannot be stored. "
                f"Consider curtailment if other flexibility is unavailable."
            )
        return " ".join(parts)

    def _build_deficit_explanation(
        self, deficit, contribution, remaining, battery, soc_after, limiting_factor, energy_delivered
    ) -> str:
        parts = [
            f"Deficit of {deficit:.1f} MW detected. "
            f"Battery can provide {contribution:.1f} MW "
            f"(delivering ~{energy_delivered:.1f} MWh after {battery.efficiency*100:.0f}% efficiency losses). "
            f"SOC: {battery.current_soc_pct:.0f}% → {soc_after:.0f}%. "
        ]
        if limiting_factor == "rate":
            parts.append(f"Limited by max discharge rate ({battery.max_discharge_rate_mw} MW).")
        elif limiting_factor == "capacity":
            parts.append("Limited by available stored energy.")

        if remaining > 0.5:
            parts.append(
                f"Remaining deficit of {remaining:.1f} MW after maximum battery support. "
                f"Backup generation preparation recommended."
            )
        else:
            parts.append("Battery can fully cover this deficit.")
        return " ".join(parts)
