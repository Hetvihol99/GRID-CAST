import { DashboardSummary } from "@/lib/types";

interface KpiRowProps {
  summary: DashboardSummary;
}

export default function KpiRow({ summary }: KpiRowProps) {
  const nextGen = Math.round(summary.total_forecast_mw_next_hour);
  const nextDemand = Math.round(summary.total_demand_mw_next_hour);
  const netBalance = Math.round(summary.net_balance_mw_next_hour);
  const isSurplus = netBalance >= 0;

  const totalCapacity = summary.plants.reduce((acc, p) => acc + p.capacity_mw, 0);
  const battery = summary.battery;

  const kpis = [
    {
      label: "Next-Hour Generation",
      value: `${nextGen} MW`,
      sub: `${Math.round((nextGen / (totalCapacity || 1)) * 100)}% of ${totalCapacity} MW capacity`,
      cardBg: "bg-card-gray text-dark",
      badgeBg: "bg-white text-dark border-dark",
      valueClass: "text-dark",
      subClass: "text-ink-muted",
    },
    {
      label: "Regional Grid Demand",
      value: `${nextDemand} MW`,
      sub: "Western & Southern interconnect base",
      cardBg: "bg-lime text-dark",
      badgeBg: "bg-dark text-lime border-dark",
      valueClass: "text-dark",
      subClass: "text-dark font-medium",
    },
    {
      label: "Net Balance",
      value: `${isSurplus ? "+" : ""}${netBalance} MW`,
      sub: isSurplus ? "Surplus (Charging / Export)" : "Deficit (BESS Dispatch)",
      cardBg: "bg-dark text-white",
      badgeBg: isSurplus ? "bg-lime text-dark border-dark" : "bg-alert text-white border-white",
      badge: summary.overall_severity,
      valueClass: isSurplus ? "text-lime" : "text-alert",
      subClass: "text-gray-300",
    },
    {
      label: "BESS State of Charge",
      value: battery ? `${battery.current_soc_pct}%` : "70%",
      sub: battery ? `${Math.round(battery.available_discharge_mwh)} MWh discharge headroom` : "120 MWh available",
      cardBg: "bg-white text-dark",
      badgeBg: "bg-lime text-dark border-dark",
      valueClass: "text-dark",
      subClass: "text-ink-muted",
    },
  ];

  return (
    <section className="px-6 md:px-10 py-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className={`border-2 border-dark rounded-[24px] p-6 ${kpi.cardBg} transition-transform hover:-translate-y-1 shadow-positivus relative overflow-hidden flex flex-col justify-between`}
        >
          <div>
            <div className="flex items-start justify-between gap-2 mb-3">
              <span className="text-xs font-bold uppercase tracking-wider">{kpi.label}</span>
              {kpi.badge && (
                <span
                  className={`text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full border ${kpi.badgeBg}`}
                >
                  {kpi.badge}
                </span>
              )}
            </div>
            <p className={`text-3xl md:text-4xl font-display font-bold tabular ${kpi.valueClass}`}>
              {kpi.value}
            </p>
          </div>
          <p className={`text-xs mt-3 pt-3 border-t border-dark/20 ${kpi.subClass}`}>{kpi.sub}</p>
        </div>
      ))}
    </section>
  );
}
