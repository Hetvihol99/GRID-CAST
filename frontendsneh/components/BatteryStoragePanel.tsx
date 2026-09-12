"use client";

import { useState } from "react";
import { BatterySummary } from "@/lib/types";

interface BatteryStoragePanelProps {
  battery?: BatterySummary | null;
}

export default function BatteryStoragePanel({ battery }: BatteryStoragePanelProps) {
  const defaultBattery = {
    battery_id: 1,
    battery_name: "Southern Grid Battery Storage (BESS)",
    capacity_mwh: 200.0,
    current_soc_pct: 70.0,
    available_discharge_mwh: 120.0,
    available_charge_mwh: 50.0,
    max_discharge_rate_mw: 100.0,
    max_charge_rate_mw: 80.0,
  };

  const b = battery || defaultBattery;

  const [simulatedSoc, setSimulatedSoc] = useState<number>(b.current_soc_pct);
  const [dispatchMode, setDispatchMode] = useState<"auto" | "charge" | "discharge">("auto");

  const minSoc = 10;
  const maxSoc = 95;
  const currentDischargeMWh = Math.max(0, Math.round(((simulatedSoc - minSoc) / 100) * b.capacity_mwh));
  const currentChargeMWh = Math.max(0, Math.round(((maxSoc - simulatedSoc) / 100) * b.capacity_mwh));

  return (
    <section id="battery" className="px-6 md:px-10 py-6">
      <div className="border-2 border-dark rounded-[28px] md:rounded-[36px] p-6 md:p-8 bg-card-gray shadow-positivus">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-5 border-b border-dark/20">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-lime border border-dark text-dark shadow-positivus-sm">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="7" width="16" height="12" rx="2"/>
                  <path d="M22 11v4"/>
                  <path d="M6 11v4M10 11v4M14 11v4"/>
                </svg>
              </div>
              <h2 className="font-display text-2xl font-bold text-dark">{b.battery_name}</h2>
            </div>
            <p className="text-xs text-ink-muted mt-1 font-medium">
              Deterministic BESS Dispatch Model · 200 MWh Utility Storage Buffer
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-dark hidden sm:inline">Strategy:</span>
            <div className="flex bg-white p-1 rounded-xl border border-dark text-xs shadow-positivus-sm">
              <button
                onClick={() => {
                  setDispatchMode("auto");
                  setSimulatedSoc(70);
                }}
                className={`px-3 py-1.5 rounded-lg transition-all font-bold ${
                  dispatchMode === "auto" ? "bg-dark text-white shadow-sm" : "text-dark hover:bg-card-gray"
                }`}
              >
                Auto (Deterministic)
              </button>
              <button
                onClick={() => {
                  setDispatchMode("charge");
                  setSimulatedSoc(92);
                }}
                className={`px-3 py-1.5 rounded-lg transition-all font-bold ${
                  dispatchMode === "charge" ? "bg-lime text-dark border border-dark shadow-sm" : "text-dark hover:bg-card-gray"
                }`}
              >
                Charge (Midday)
              </button>
              <button
                onClick={() => {
                  setDispatchMode("discharge");
                  setSimulatedSoc(25);
                }}
                className={`px-3 py-1.5 rounded-lg transition-all font-bold ${
                  dispatchMode === "discharge" ? "bg-alert text-white border border-dark shadow-sm" : "text-dark hover:bg-card-gray"
                }`}
              >
                Peak Discharge
              </button>
            </div>
          </div>
        </div>

        <div className="mb-6 bg-white p-5 rounded-2xl border border-dark shadow-positivus-sm">
          <div className="flex justify-between items-baseline mb-2">
            <span className="text-xs font-bold text-dark uppercase tracking-wider">
              State of Charge (SOC) Status
            </span>
            <span className="text-2xl font-display font-bold text-dark tabular font-mono">
              {simulatedSoc}% <span className="text-sm font-normal text-ink-muted">({Math.round((simulatedSoc / 100) * b.capacity_mwh)} / {b.capacity_mwh} MWh)</span>
            </span>
          </div>

          <div className="w-full bg-card-gray h-6 rounded-xl border-2 border-dark overflow-hidden p-0.5">
            <div
              className="h-full rounded-lg bg-lime border border-dark transition-all duration-300"
              style={{ width: `${simulatedSoc}%` }}
            />
          </div>

          <div className="mt-4 flex items-center gap-4">
            <span className="text-xs text-ink-muted font-bold">Adjust SOC:</span>
            <input
              type="range"
              min="10"
              max="95"
              value={simulatedSoc}
              onChange={(e) => setSimulatedSoc(Number(e.target.value))}
              className="flex-1 accent-dark cursor-pointer"
            />
            <span className="text-xs font-mono font-bold text-dark w-10 text-right">{simulatedSoc}%</span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">Discharge Headroom</span>
            <p className="text-xl font-display font-bold text-dark tabular font-mono mt-1">
              {currentDischargeMWh} MWh
            </p>
            <span className="text-[10px] text-ink-muted font-medium">Available for evening peak</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">Charging Headroom</span>
            <p className="text-xl font-display font-bold text-dark tabular font-mono mt-1">
              {currentChargeMWh} MWh
            </p>
            <span className="text-[10px] text-ink-muted font-medium">Absorption for solar surplus</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">Max Discharge Rate</span>
            <p className="text-xl font-display font-bold text-dark tabular font-mono mt-1">
              {b.max_discharge_rate_mw} MW
            </p>
            <span className="text-[10px] text-ink-muted font-medium">4-hour duration rating</span>
          </div>

          <div className="p-4 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">Max Charge Rate</span>
            <p className="text-xl font-display font-bold text-dark tabular font-mono mt-1">
              {b.max_charge_rate_mw} MW
            </p>
            <span className="text-[10px] text-ink-muted font-medium">Inverter charging limit</span>
          </div>
        </div>
      </div>
    </section>
  );
}
