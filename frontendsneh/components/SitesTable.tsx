"use client";

import Link from "next/link";
import { PlantStatusSummary } from "@/lib/types";

interface SitesTableProps {
  plants: PlantStatusSummary[];
  onSelectPlant: (plant: PlantStatusSummary) => void;
  onOpenRegisterPlant: () => void;
  onDeletePlant?: (plantId: number) => void;
}

export default function SitesTable({
  plants,
  onOpenRegisterPlant,
  onDeletePlant,
}: SitesTableProps) {
  const totalCapacity = plants.reduce((sum, p) => sum + p.capacity_mw, 0);

  return (
    <section id="sites" className="px-6 md:px-10 py-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-lime text-dark font-bold text-2xl md:text-3xl px-3.5 py-1 rounded-xl border border-dark inline-block shadow-positivus-sm">
              Monitored Fleet Assets
            </span>
            <span className="text-xs px-2.5 py-1 rounded-lg bg-card-gray border border-dark text-dark font-bold">
              {plants.length} Plants Active
            </span>
          </div>
          <p className="text-xs text-ink-muted font-medium">
            All registered assets are saved in your persistent database and included in multi-step AI load balancing.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-dark font-semibold hidden sm:inline">
            Total Nameplate: <strong className="text-dark font-mono font-bold">{totalCapacity} MW</strong>
          </span>
          <button
            onClick={onOpenRegisterPlant}
            className="text-xs font-bold px-4 py-2.5 rounded-xl bg-lime text-dark hover:bg-lime-hover border border-dark transition-all flex items-center gap-1.5 shadow-positivus-sm active:translate-y-0.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Connect Site
          </button>
        </div>
      </div>

      <div className="border-2 border-dark rounded-[28px] overflow-hidden overflow-x-auto bg-white shadow-positivus">
        <table className="w-full text-xs md:text-sm min-w-[750px]">
          <thead>
            <tr className="text-left text-dark border-b-2 border-dark bg-card-gray font-bold">
              <th className="px-6 py-4">Plant Name</th>
              <th className="px-6 py-4">Type</th>
              <th className="px-6 py-4">Location</th>
              <th className="px-6 py-4 text-right">Installed Capacity</th>
              <th className="px-6 py-4 text-right">Next Output</th>
              <th className="px-6 py-4 text-right">Utilization</th>
              <th className="px-6 py-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark/15 font-medium">
            {plants.map((p) => {
              const isSolar = p.plant_type === "solar";
              const forecastMW = p.latest_forecast_mw ?? (isSolar ? p.capacity_mw * 0.68 : p.capacity_mw * 0.74);
              const utilPct = Math.round((forecastMW / (p.capacity_mw || 1)) * 100);

              return (
                <tr
                  key={p.plant_id}
                  className="bg-white hover:bg-lime/10 transition-colors group"
                >
                  <td className="px-6 py-4 text-dark font-bold flex items-center gap-3">
                    <span
                      className={`w-3 h-3 rounded-full border border-dark ${
                        isSolar ? "bg-lime" : "bg-dark"
                      }`}
                    />
                    <div className="min-w-0">
                      <Link
                        href={`/plant/${p.plant_id}`}
                        className="group-hover:underline font-bold text-dark truncate block text-sm"
                      >
                        {p.plant_name}
                      </Link>
                      {p.is_custom && (
                        <span className="text-[9px] uppercase font-bold text-dark bg-lime px-1.5 py-0.2 rounded border border-dark">
                          Custom Saved
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`text-[11px] font-bold uppercase px-3 py-1 rounded-full border border-dark ${
                        isSolar ? "bg-lime text-dark" : "bg-card-gray text-dark"
                      }`}
                    >
                      {isSolar ? "☀️ Solar PV" : "💨 Wind Turbine"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-ink-muted font-medium">{p.location_name || "Regional Substation"}</td>
                  <td className="px-6 py-4 text-dark font-mono font-bold text-right tabular">{p.capacity_mw} MW</td>
                  <td className="px-6 py-4 text-right font-mono font-bold text-dark tabular">
                    {Math.round(forecastMW)} MW
                  </td>
                  <td className="px-6 py-4 text-right font-mono tabular">
                    <span className="font-bold text-dark bg-card-gray px-2 py-0.5 rounded border border-dark">
                      {utilPct}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Link
                        href={`/plant/${p.plant_id}`}
                        className="text-[11px] font-bold px-3 py-1.5 rounded-xl bg-lime text-dark hover:bg-dark hover:text-white border border-dark transition-all shadow-positivus-sm active:translate-y-0.5"
                      >
                        View Analysis →
                      </Link>
                      {p.is_custom && onDeletePlant && (
                        <button
                          onClick={() => onDeletePlant(p.plant_id)}
                          title="Remove plant from database"
                          className="text-[11px] font-bold px-2 py-1.5 rounded-xl bg-white text-ink-muted hover:text-alert hover:border-alert border border-dark transition-all shadow-positivus-sm active:translate-y-0.5"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
