"use client";

import { useState } from "react";
import { DashboardSummary } from "@/lib/types";

interface FinancialTraderPanelProps {
  summary: DashboardSummary;
}

export default function FinancialTraderPanel({ summary }: FinancialTraderPanelProps) {
  const [peakTariff, setPeakTariff] = useState(7.5);
  const [offPeakTariff, setOffPeakTariff] = useState(2.8);
  const [carbonCreditRate, setCarbonCreditRate] = useState(1200);

  const total72hMWh = summary.hourly_balance.reduce((sum, h) => sum + h.total_generation_mw, 0);
  const avgDailyMWh = Math.round(total72hMWh / 3);

  const batteryCapacityMWh = summary.battery?.capacity_mwh || 200;
  const dailyDischargedMWh = batteryCapacityMWh * 1.5 * 0.90;
  const dailyArbitrageRevenueINR = dailyDischargedMWh * 1000 * (peakTariff - offPeakTariff);

  const dailyBaselineRevenueINR = avgDailyMWh * 1000 * 3.65;
  const dailyCurtailmentSavingsINR = 85 * 1000 * 3.65;

  const dailyCarbonOffsetTons = avgDailyMWh * 0.82;
  const dailyCarbonCreditINR = dailyCarbonOffsetTons * (carbonCreditRate / 1000);

  return (
    <section id="trading" className="px-6 md:px-10 py-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-lime text-dark font-bold text-2xl md:text-3xl px-3.5 py-1 rounded-xl border border-dark inline-block shadow-positivus-sm">
              Energy Trading &amp; Financial Desk
            </span>
          </div>
          <p className="text-xs text-ink-muted font-medium">
            Optimize Day-Ahead Market (DAM) bidding, BESS spread arbitrage, and curtailment loss recovery
          </p>
        </div>
        <span className="text-xs font-bold text-dark bg-card-gray px-3 py-1.5 rounded-xl border border-dark shadow-positivus-sm w-fit">
          DAM / Real-Time Market (RTM)
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="p-6 rounded-[28px] bg-card-gray border-2 border-dark space-y-4 shadow-positivus">
          <h3 className="text-xs font-bold text-dark uppercase tracking-wider flex items-center justify-between pb-2 border-b border-dark/20">
            <span>Market Tariff Controls</span>
            <span className="text-[10px] bg-lime text-dark font-mono px-2 py-0.5 rounded border border-dark font-bold">IEX Linked</span>
          </h3>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1 font-semibold">
                <span className="text-ink-muted">Peak Deficit Tariff (Discharge)</span>
                <span className="font-mono font-bold text-dark">₹{peakTariff.toFixed(2)}/kWh</span>
              </div>
              <input
                type="range"
                min="4.0"
                max="12.0"
                step="0.25"
                value={peakTariff}
                onChange={(e) => setPeakTariff(Number(e.target.value))}
                className="w-full accent-dark cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1 font-semibold">
                <span className="text-ink-muted">Off-Peak Tariff (Charge)</span>
                <span className="font-mono font-bold text-dark">₹{offPeakTariff.toFixed(2)}/kWh</span>
              </div>
              <input
                type="range"
                min="1.5"
                max="4.5"
                step="0.1"
                value={offPeakTariff}
                onChange={(e) => setOffPeakTariff(Number(e.target.value))}
                className="w-full accent-dark cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1 font-semibold">
                <span className="text-ink-muted">Carbon Credit (CERC / VCM)</span>
                <span className="font-mono font-bold text-dark">₹{carbonCreditRate}/ton</span>
              </div>
              <input
                type="range"
                min="500"
                max="2500"
                step="50"
                value={carbonCreditRate}
                onChange={(e) => setCarbonCreditRate(Number(e.target.value))}
                className="w-full accent-dark cursor-pointer"
              />
            </div>
          </div>

          <div className="p-3 bg-white rounded-xl border border-dark text-xs space-y-1">
            <span className="text-ink-muted block text-[10px] font-bold uppercase">Net Spread Arbitrage</span>
            <p className="text-lg font-bold text-dark font-mono">
              ₹{(peakTariff - offPeakTariff).toFixed(2)} / kWh
            </p>
          </div>
        </div>

        <div className="lg:col-span-2 p-6 rounded-[28px] bg-dark text-white border-2 border-dark space-y-5 shadow-positivus flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-gray-700">
              <span className="text-xs font-bold text-lime uppercase tracking-wider">
                Fleet Projected Daily Financial Yield
              </span>
              <span className="text-xs text-dark font-bold bg-lime px-2.5 py-0.5 rounded border border-dark">
                Simulated 72h Model
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-5">
              <div className="p-4 rounded-2xl bg-dark-secondary border border-gray-700">
                <span className="text-[10px] text-gray-400 block font-bold uppercase">Base Generation PPA</span>
                <p className="text-xl font-display font-bold text-white tabular font-mono mt-1">
                  ₹{(dailyBaselineRevenueINR / 100000).toFixed(1)} Lakhs
                </p>
                <span className="text-[10px] text-gray-400">₹3.65/kWh regulated benchmark</span>
              </div>

              <div className="p-4 rounded-2xl bg-dark-secondary border border-gray-700">
                <span className="text-[10px] text-lime block font-bold uppercase">BESS Spread Arbitrage</span>
                <p className="text-xl font-display font-bold text-lime tabular font-mono mt-1">
                  +₹{(dailyArbitrageRevenueINR / 100000).toFixed(1)} Lakhs
                </p>
                <span className="text-[10px] text-gray-400">Charge off-peak, sell at peak</span>
              </div>

              <div className="p-4 rounded-2xl bg-dark-secondary border border-gray-700">
                <span className="text-[10px] text-lime block font-bold uppercase">Curtailment Recovery</span>
                <p className="text-xl font-display font-bold text-lime tabular font-mono mt-1">
                  +₹{(dailyCurtailmentSavingsINR / 100000).toFixed(1)} Lakhs
                </p>
                <span className="text-[10px] text-gray-400">85 MWh/day saved via storage</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-dark-secondary border border-gray-700 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div>
              <span className="text-gray-400 block text-[10px] font-bold uppercase">Net Total Daily Grid Value Created</span>
              <span className="text-2xl font-bold font-mono text-lime">
                ₹{((dailyBaselineRevenueINR + dailyArbitrageRevenueINR + dailyCurtailmentSavingsINR + dailyCarbonCreditINR) / 100000).toFixed(2)} Lakhs / Day
              </span>
            </div>
            <div className="text-right text-[11px] text-gray-400">
              <span>CO₂ Offset: <strong>{Math.round(dailyCarbonOffsetTons)} tons/day</strong></span>
              <br />
              <span>Carbon Value: ₹{Math.round(dailyCarbonCreditINR).toLocaleString("en-IN")}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
