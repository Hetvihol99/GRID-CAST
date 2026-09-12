import ForecastChart from "./ForecastChart";
import { DashboardSummary } from "@/lib/types";

interface HeroForecastProps {
  summary: DashboardSummary;
}

export default function HeroForecast({ summary }: HeroForecastProps) {
  const totalCapacity = summary.plants.reduce((acc, p) => acc + p.capacity_mw, 0);
  const solarCapacity = summary.plants.filter((p) => p.plant_type === "solar").reduce((acc, p) => acc + p.capacity_mw, 0);
  const windCapacity = summary.plants.filter((p) => p.plant_type === "wind").reduce((acc, p) => acc + p.capacity_mw, 0);

  return (
    <section id="forecast" className="px-6 md:px-10 pt-8 pb-4">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="bg-lime text-dark font-bold text-xs uppercase tracking-wider px-3 py-1 rounded-md border border-dark">
              72-Hour Horizon · Western &amp; Southern Grid
            </span>
            <span className="bg-card-gray text-dark text-xs font-bold px-3 py-1 rounded-md border border-dark">
              {totalCapacity} MW Fleet ({solarCapacity} MW Solar + {windCapacity} MW Wind)
            </span>
          </div>

          <h1 className="font-display text-3xl md:text-5xl font-bold leading-tight text-dark tracking-tight">
            Navigating the digital energy landscape for grid dispatch
          </h1>
        </div>

        <p className="text-ink-muted text-sm md:text-base leading-relaxed max-w-md font-medium">
          Multi-step XGBoost forecasting fed by Open-Meteo atmospheric telemetry and plant generation history. Identifies imbalances and computes deterministic BESS directives.
        </p>
      </div>

      <div className="mt-6 bg-card-gray border-2 border-dark rounded-[28px] md:rounded-[40px] p-6 md:p-8 shadow-positivus">
        <ForecastChart summary={summary} />
      </div>
    </section>
  );
}
