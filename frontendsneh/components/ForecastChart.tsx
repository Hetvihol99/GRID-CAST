"use client";

import { useMemo, useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { DashboardSummary } from "@/lib/types";
import { buildForecastFromBalance } from "@/lib/defaultData";

const RANGES = [24, 48, 72] as const;

interface ForecastChartProps {
  summary: DashboardSummary;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload;
  if (!p) return null;

  const solar = p.solarMW ?? 0;
  const wind = p.windMW ?? 0;
  const total = p.totalGenMW ?? solar + wind;
  const demand = p.demandMW ?? 0;
  const net = p.netMW ?? total - demand;
  const severity = p.severity ?? "normal";

  const isSurplus = net >= 0;

  return (
    <div className="bg-white border-2 border-dark rounded-2xl px-5 py-4 text-xs shadow-positivus min-w-[220px]">
      <div className="flex items-center justify-between gap-3 mb-2 pb-2 border-b border-dark/20">
        <p className="text-dark font-bold text-sm">{label}</p>
        <span
          className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border border-dark ${
            severity === "critical"
              ? "bg-alert text-white"
              : severity === "warning"
              ? "bg-lime text-dark"
              : severity === "watch"
              ? "bg-card-gray text-dark"
              : "bg-white text-dark"
          }`}
        >
          {severity}
        </span>
      </div>

      <div className="space-y-1.5 font-medium">
        <div className="flex justify-between items-center text-dark">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-lime border border-dark inline-block" /> Solar PV:</span>
          <span className="font-bold font-mono tabular">{solar} MW</span>
        </div>
        <div className="flex justify-between items-center text-dark">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-dark inline-block" /> Wind Turbines:</span>
          <span className="font-bold font-mono tabular">{wind} MW</span>
        </div>
        <div className="flex justify-between items-center text-dark font-bold pt-1 border-t border-dark/20">
          <span>⚡ Total Output:</span>
          <span className="tabular font-mono">{total} MW</span>
        </div>
        <div className="flex justify-between items-center text-ink-muted">
          <span>📈 Demand:</span>
          <span className="tabular font-mono">{demand} MW</span>
        </div>
        <div
          className={`flex justify-between items-center pt-1.5 font-bold border-t-2 border-dark ${
            isSurplus ? "text-dark" : "text-alert"
          }`}
        >
          <span>{isSurplus ? "Surplus (+):" : "Deficit (-):"}</span>
          <span className="tabular font-mono text-sm">{net > 0 ? `+${net}` : net} MW</span>
        </div>
      </div>
    </div>
  );
}

export default function ForecastChart({ summary }: ForecastChartProps) {
  const [rangeHours, setRangeHours] = useState<(typeof RANGES)[number]>(72);
  const data = useMemo(() => buildForecastFromBalance(summary, rangeHours), [summary, rangeHours]);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-4 text-xs md:text-sm font-medium">
          <span className="flex items-center gap-2 text-dark">
            <span className="w-3.5 h-3.5 rounded-md bg-lime border border-dark inline-block" />
            <strong>Solar Generation</strong>
          </span>
          <span className="flex items-center gap-2 text-dark">
            <span className="w-3.5 h-3.5 rounded-md bg-dark inline-block" />
            <strong>Wind Generation</strong>
          </span>
          <span className="flex items-center gap-2 text-dark">
            <span className="w-3.5 h-1 border-t-2 border-dashed border-dark inline-block" />
            <strong className="text-ink-muted">Grid Demand Base</strong>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-dark">Horizon:</span>
          <div className="flex gap-1.5 bg-white border border-dark rounded-xl p-1 shadow-positivus-sm">
            {RANGES.map((h) => (
              <button
                key={h}
                onClick={() => setRangeHours(h)}
                className={`text-xs px-3.5 py-1.5 rounded-lg font-bold transition-all ${
                  rangeHours === h
                    ? "bg-lime text-dark border border-dark shadow-sm"
                    : "text-dark hover:bg-card-gray"
                }`}
              >
                {h}h
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="w-full h-80 md:h-96">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="colorSolarPositivus" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4CAF4F" stopOpacity={0.85} />
                <stop offset="95%" stopColor="#4CAF4F" stopOpacity={0.15} />
              </linearGradient>
              <linearGradient id="colorWindPositivus" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2196F3" stopOpacity={0.75} />
                <stop offset="95%" stopColor="#2196F3" stopOpacity={0.12} />
              </linearGradient>
            </defs>

            <CartesianGrid stroke="#ABBED1" strokeDasharray="3 3" vertical={false} opacity={0.35} />

            <XAxis
              dataKey="hour"
              tick={{ fill: "#4D4D4D", fontSize: 11, fontWeight: 500 }}
              axisLine={{ stroke: "#ABBED1", strokeWidth: 1 }}
              tickLine={false}
              interval={Math.floor(data.length / 8)}
            />
            <YAxis
              tick={{ fill: "#4D4D4D", fontSize: 11, fontWeight: 500 }}
              axisLine={false}
              tickLine={false}
              width={50}
              label={{ value: "MW", position: "insideTopLeft", fill: "#263238", fontSize: 11, fontWeight: 600, dx: 10, dy: -6 }}
            />

            <Tooltip content={<CustomTooltip />} />

            <Area
              type="monotone"
              dataKey="solarMW"
              name="Solar PV"
              stackId="gen"
              stroke="#4CAF4F"
              strokeWidth={2}
              fill="url(#colorSolarPositivus)"
            />

            <Area
              type="monotone"
              dataKey="windMW"
              name="Wind Turbines"
              stackId="gen"
              stroke="#2196F3"
              strokeWidth={2}
              fill="url(#colorWindPositivus)"
            />

            <Line
              type="monotone"
              dataKey="demandMW"
              name="Demand"
              stroke="#717171"
              strokeWidth={2.5}
              strokeDasharray="5 5"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 pt-4 border-t border-dark/20 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-bold text-dark">Grid Status Bands:</span>
          <span className="bg-lime text-dark font-bold px-2 py-0.5 rounded border border-dark">Surplus (+MW)</span>
          <span className="bg-white text-dark font-medium px-2 py-0.5 rounded border border-dark">Balanced</span>
          <span className="bg-alert text-white font-bold px-2 py-0.5 rounded border border-dark">Deficit (-MW)</span>
        </div>
        <span className="text-ink-muted font-medium">
          Deterministic 72h XGBoost Model Pipeline
        </span>
      </div>
    </div>
  );
}
