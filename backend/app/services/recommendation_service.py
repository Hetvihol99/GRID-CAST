"""
Recommendation Engine
======================
WHAT: Deterministic rule-based decision engine.
WHY:  Recommendations must be explainable, auditable, and predictable.
      ML predictions answer "what will happen?" — this answers "what should be done?"
      Rule-based = judges can read the code and verify the logic.

RULES (in priority order):

SURPLUS SCENARIO:
  1. If surplus AND battery has charging headroom → CHARGE_STORAGE
  2. If surplus AND battery is full → CONSIDER_CURTAILMENT
  3. If small surplus → MONITOR

DEFICIT SCENARIO:
  1. If deficit AND battery can discharge → DISCHARGE_STORAGE
  2. If deficit > battery max coverage → PREPARE_BACKUP (in addition)
  3. If deficit AND battery empty → PREPARE_BACKUP immediately
  4. If small deficit → MONITOR

CRITICAL RULES:
  - Never say "AI will control the plant" — this is DECISION SUPPORT only.
  - Never recommend curtailment as first step — exhaust storage first.
  - Never claim battery will fully solve a problem it physically cannot.
  - All recommendations include a plain-English explanation.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from app.services.grid_analysis_service import HourlyBalance
from app.services.storage_service import BatteryActionResult
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Recommendation:
    """A single recommended action with explanation."""
    action: str             # RecommendationAction enum value
    priority: int           # 1 = highest
    description: str        # Plain English explanation
    estimated_impact_mw: Optional[float] = None
    is_feasible: bool = True


@dataclass
class RecommendationSet:
    """All recommendations for a given balance condition."""
    timestamp: datetime
    severity: str
    net_balance_mw: float
    recommendations: list = field(default_factory=list)


class RecommendationEngine:
    """
    Deterministic rule engine that maps grid balance conditions
    to actionable recommendations.

    Completely stateless — same inputs always produce same outputs.
    Easy to audit, explain, and extend.
    """

    def generate(
        self,
        balance: HourlyBalance,
        battery_result: Optional[BatteryActionResult] = None,
    ) -> RecommendationSet:
        """
        Generate recommendations for one hour's balance condition.

        INPUT:
          balance:        HourlyBalance from GridAnalysisService
          battery_result: BatteryActionResult from StorageService (optional)
        OUTPUT:
          RecommendationSet with prioritised, explained recommendations
        """
        recs = []

        if balance.severity == "normal":
            recs = self._handle_normal(balance, battery_result)
        elif balance.alert_type == "surplus":
            recs = self._handle_surplus(balance, battery_result)
        elif balance.alert_type == "deficit":
            recs = self._handle_deficit(balance, battery_result)
        else:
            recs = [self._monitor(balance)]

        return RecommendationSet(
            timestamp=balance.timestamp,
            severity=balance.severity,
            net_balance_mw=balance.net_balance_mw,
            recommendations=sorted(recs, key=lambda r: r.priority),
        )

    def _handle_normal(
        self, balance: HourlyBalance, battery_result: Optional[BatteryActionResult]
    ) -> list[Recommendation]:
        """Small or no imbalance — monitor only."""
        return [
            Recommendation(
                action="monitor",
                priority=1,
                description=(
                    f"Grid balance is within normal range "
                    f"(net: {balance.net_balance_mw:+.1f} MW). "
                    f"No immediate action required. Continue monitoring."
                ),
                is_feasible=True,
            )
        ]

    def _handle_surplus(
        self, balance: HourlyBalance, battery_result: Optional[BatteryActionResult]
    ) -> list[Recommendation]:
        """
        SURPLUS: Generation exceeds demand.
        Priority: Store excess → if can't store enough → consider curtailment.
        """
        surplus = balance.net_balance_mw  # Positive value
        recs = []
        priority = 1

        if battery_result is None:
            # No battery configured — can't evaluate storage
            recs.append(Recommendation(
                action="consider_curtailment",
                priority=priority,
                description=(
                    f"Renewable surplus of {surplus:.1f} MW expected. "
                    f"No battery storage configured. "
                    f"If surplus cannot be exported to adjacent regions, "
                    f"consider reducing generation from curtailable plants. "
                    f"⚠️ This is a recommendation for human review, not an automatic action."
                ),
                estimated_impact_mw=surplus,
                is_feasible=True,
            ))
            return recs

        # Battery available
        can_absorb = battery_result.battery_contribution_mw
        remaining = battery_result.remaining_imbalance_mw

        if can_absorb > 0.5:
            recs.append(Recommendation(
                action="charge_storage",
                priority=priority,
                description=(
                    f"Renewable surplus of {surplus:.1f} MW expected. "
                    f"Battery can absorb up to {can_absorb:.1f} MW "
                    f"(SOC: {battery_result.soc_before_pct:.0f}% → {battery_result.soc_after_pct:.0f}%). "
                    f"{battery_result.explanation}"
                ),
                estimated_impact_mw=can_absorb,
                is_feasible=True,
            ))
            priority += 1

        if remaining > 0.5:
            recs.append(Recommendation(
                action="consider_curtailment",
                priority=priority,
                description=(
                    f"After maximum battery charging, a surplus of {remaining:.1f} MW remains. "
                    f"Consider whether excess can be exported to neighbouring regions. "
                    f"If export is not possible, curtailment of renewable generation may be appropriate. "
                    f"⚠️ Curtailment recommendation requires manual operator decision. "
                    f"The system does not control generation assets."
                ),
                estimated_impact_mw=remaining,
                is_feasible=True,
            ))

        elif battery_result.limiting_factor == "soc_max":
            recs.append(Recommendation(
                action="consider_curtailment",
                priority=priority,
                description=(
                    f"Battery is fully charged (SOC: {battery_result.soc_before_pct:.0f}%). "
                    f"Cannot absorb surplus of {surplus:.1f} MW. "
                    f"Consider curtailment or export if available."
                ),
                estimated_impact_mw=surplus,
                is_feasible=True,
            ))

        return recs

    def _handle_deficit(
        self, balance: HourlyBalance, battery_result: Optional[BatteryActionResult]
    ) -> list[Recommendation]:
        """
        DEFICIT: Demand exceeds renewable generation.
        Priority: Discharge battery → if insufficient → prepare backup generation.
        """
        deficit = abs(balance.net_balance_mw)  # Convert to positive
        recs = []
        priority = 1

        if battery_result is None:
            recs.append(Recommendation(
                action="prepare_backup",
                priority=priority,
                description=(
                    f"Generation deficit of {deficit:.1f} MW expected. "
                    f"No battery storage configured. "
                    f"Backup generation (gas, hydro, imports) may need to be activated. "
                    f"Lead time for backup activation should be considered now."
                ),
                estimated_impact_mw=deficit,
                is_feasible=True,
            ))
            return recs

        can_provide = battery_result.battery_contribution_mw
        remaining = battery_result.remaining_imbalance_mw

        if can_provide > 0.5:
            recs.append(Recommendation(
                action="discharge_storage",
                priority=priority,
                description=(
                    f"Generation deficit of {deficit:.1f} MW expected. "
                    f"Battery can provide up to {can_provide:.1f} MW "
                    f"(SOC: {battery_result.soc_before_pct:.0f}% → {battery_result.soc_after_pct:.0f}%). "
                    f"{battery_result.explanation}"
                ),
                estimated_impact_mw=can_provide,
                is_feasible=True,
            ))
            priority += 1
        else:
            # Battery empty or at minimum SOC
            recs.append(Recommendation(
                action="discharge_storage",
                priority=priority,
                description=battery_result.explanation,
                estimated_impact_mw=0.0,
                is_feasible=False,  # Not feasible — battery unavailable
            ))
            priority += 1

        if remaining > 0.5:
            lead_time_note = ""
            if balance.severity == "critical":
                lead_time_note = (
                    " ⚠️ CRITICAL: Consider activating backup immediately given "
                    f"the {remaining:.1f} MW remaining deficit. "
                    f"Ensure backup ramp-up time is accounted for."
                )
            recs.append(Recommendation(
                action="prepare_backup",
                priority=priority,
                description=(
                    f"After maximum battery support, a deficit of {remaining:.1f} MW remains. "
                    f"Backup generation or grid import may be required. "
                    f"Prepare backup resources (gas peakers, hydro, interconnect imports) "
                    f"with sufficient lead time."
                    + lead_time_note
                ),
                estimated_impact_mw=remaining,
                is_feasible=True,
            ))

        return recs

    def _monitor(self, balance: HourlyBalance) -> Recommendation:
        return Recommendation(
            action="monitor",
            priority=1,
            description=f"Grid balance status: {balance.severity}. Continue monitoring.",
            is_feasible=True,
        )
