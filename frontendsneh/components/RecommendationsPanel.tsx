import { RecommendationResponse } from "@/lib/types";

interface RecommendationsPanelProps {
  recommendations?: RecommendationResponse[];
}

const ACTION_META: Record<
  string,
  { label: string; icon: JSX.Element; badgeClass: string; cardBg: string }
> = {
  charge_storage: {
    label: "Charge Battery Storage",
    badgeClass: "bg-lime text-dark border-dark",
    cardBg: "bg-card-gray",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#191A23" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="7" width="16" height="12" rx="2"/>
        <path d="M22 11v4M10 11l-2 3h4l-2 3"/>
      </svg>
    ),
  },
  discharge_storage: {
    label: "Discharge Battery Storage",
    badgeClass: "bg-lime text-dark border-dark",
    cardBg: "bg-lime-light",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#191A23" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="7" width="16" height="12" rx="2"/>
        <path d="M22 11v4M7 13h6"/>
      </svg>
    ),
  },
  prepare_backup: {
    label: "Prepare Backup Generation",
    badgeClass: "bg-alert text-white border-dark",
    cardBg: "bg-alert-bg",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF4D4D" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
      </svg>
    ),
  },
  consider_curtailment: {
    label: "Consider Curtailment",
    badgeClass: "bg-card-gray text-dark border-dark",
    cardBg: "bg-white",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#191A23" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
      </svg>
    ),
  },
  monitor: {
    label: "System Monitoring",
    badgeClass: "bg-white text-dark border-dark",
    cardBg: "bg-card-gray",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#191A23" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
    ),
  },
};

export default function RecommendationsPanel({ recommendations = [] }: RecommendationsPanelProps) {
  return (
    <section id="actions" className="px-6 md:px-10 py-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-lime text-dark font-bold text-2xl md:text-3xl px-3.5 py-1 rounded-xl border border-dark inline-block shadow-positivus-sm">
              Deterministic Recommendations
            </span>
          </div>
          <p className="text-xs text-ink-muted font-medium">
            Explainable decision support: BESS dispatch first, backup peakers second, curtailment as last resort
          </p>
        </div>
        <span className="text-xs font-bold text-dark bg-card-gray px-3 py-1.5 rounded-xl border border-dark shadow-positivus-sm w-fit">
          Prioritized by Grid Urgency
        </span>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        {recommendations.map((r) => {
          const meta = ACTION_META[r.action] || ACTION_META.monitor;

          return (
            <div
              key={r.id}
              className={`border-2 border-dark rounded-[24px] p-6 ${meta.cardBg} hover:-translate-y-1 transition-transform flex flex-col justify-between shadow-positivus relative overflow-hidden`}
            >
              <div>
                <div className="flex items-center justify-between gap-3 mb-4">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-xl bg-lime border border-dark text-dark shadow-positivus-sm">
                      {meta.icon}
                    </div>
                    <span className="text-dark font-bold text-base">{meta.label}</span>
                  </div>

                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border ${meta.badgeClass}`}>
                    Priority {r.priority}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-xs font-semibold text-ink-muted mb-2">
                  <span>{r.site || "Grid Node"}</span>
                  <span>•</span>
                  <span>{r.window || "Upcoming Window"}</span>
                </div>

                <p className="text-xs md:text-sm text-dark font-medium leading-relaxed">{r.description}</p>
              </div>

              <div className="mt-5 pt-3.5 border-t border-dark/20 flex items-center justify-between text-xs">
                <span className="text-dark font-bold">
                  {r.estimated_impact_mw ? `Impact: ${r.estimated_impact_mw} MW` : "Status: Monitored"}
                </span>

                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md border ${
                  r.is_feasible ? "bg-lime text-dark border-dark" : "bg-alert text-white border-dark"
                }`}>
                  {r.is_feasible ? "✓ Physically Feasible" : "⚠️ Constraint Limited"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
