"use client";

import { useMemo, useState } from "react";
import { PlantStatusSummary, PlantForecastResult } from "@/lib/types";
import { calculatePlantForecastModel } from "@/lib/api";
import {
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface PlantDetailInspectorProps {
  plant: PlantStatusSummary | null;
  onClose: () => void;
}

export default function PlantDetailInspector({ plant, onClose }: PlantDetailInspectorProps) {
  const [horizon, setHorizon] = useState<24 | 48 | 72>(48);

  const forecastData = useMemo<PlantForecastResult | null>(() => {
    if (!plant) return null;
    return calculatePlantForecastModel(plant);
  }, [plant]);

  if (!plant || !forecastData) return null;

  const isSolar = plant.plant_type === "solar";
  const displayedPoints = forecastData.hourlyPoints.slice(0, horizon);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark/60 backdrop-blur-sm">
      <div className="relative w-full max-w-3xl bg-white border-2 border-dark rounded-[28px] shadow-positivus overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-dark bg-card-gray">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-xl border border-dark font-bold shadow-positivus-sm ${
              isSolar ? "bg-lime text-dark" : "bg-dark text-white"
            }`}>
              {isSolar ? "☀️" : "💨"}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-display font-bold text-dark text-lg">{plant.plant_name}</h3>
                <span className={`text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full border border-dark ${
                  isSolar ? "bg-lime text-dark" : "bg-dark text-white"
                }`}>
                  {plant.capacity_mw} MW · {isSolar ? "Solar PV" : "Wind Farm"}
                </span>
              </div>
              <p className="text-xs text-ink-muted mt-0.5 font-medium">
                {plant.location_name || "Regional Substation"} · Lat: {plant.latitude || 26.9}°N, Lon: {plant.longitude || 75.8}°E
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-dark hover:bg-white p-1.5 rounded-lg border border-transparent hover:border-dark font-bold">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div className="p-5 rounded-2xl bg-card-gray border-2 border-dark shadow-positivus-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-dark uppercase tracking-wider flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-lime border border-dark" />
                Live Atmospheric Telemetry (Open-Meteo Feed)
              </span>
              <span className="text-[11px] text-ink-muted font-bold font-mono">Real-time Ground Sensor</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-white border border-dark">
                <span className="text-[10px] text-ink-muted block font-semibold">{isSolar ? "Solar GHI" : "Hub Wind Speed"}</span>
                <span className="text-base font-bold font-mono tabular text-dark">
                  {isSolar
                    ? `${forecastData.currentWeather.solar_irradiance_wm2} W/m²`
                    : `${forecastData.currentWeather.wind_speed_ms} m/s`}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white border border-dark">
                <span className="text-[10px] text-ink-muted block font-semibold">Cloud Cover</span>
                <span className="text-base font-bold text-dark font-mono tabular">
                  {forecastData.currentWeather.cloud_cover_pct}%
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white border border-dark">
                <span className="text-[10px] text-ink-muted block font-semibold">Temperature</span>
                <span className="text-base font-bold text-dark font-mono tabular">
                  {forecastData.currentWeather.temperature_c}°C
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white border border-dark">
                <span className="text-[10px] text-ink-muted block font-semibold">Pressure</span>
                <span className="text-base font-bold text-dark font-mono tabular">
                  {forecastData.currentWeather.pressure_hpa} hPa
                </span>
              </div>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-card-gray border-2 border-dark shadow-positivus-sm">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold text-dark uppercase tracking-wider">
                Predicted Multi-Step Generation Output (MW)
              </span>

              <div className="flex gap-1 bg-white p-1 rounded-xl border border-dark text-xs">
                {[24, 48, 72].map((h) => (
                  <button
                    key={h}
                    onClick={() => setHorizon(h as any)}
                    className={`px-3 py-1 rounded-lg font-bold transition-all ${
                      horizon === h ? "bg-lime text-dark border border-dark shadow-sm" : "text-dark hover:bg-card-gray"
                    }`}
                  >
                    {h}h
                  </button>
                ))}
              </div>
            </div>

            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={displayedPoints} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="inspectAreaPositivus" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4CAF4F" stopOpacity={0.85} />
                    <stop offset="100%" stopColor="#4CAF4F" stopOpacity={0.15} />
                  </linearGradient>
                </defs>

                <CartesianGrid stroke="#ABBED1" strokeDasharray="3 3" vertical={false} opacity={0.35} />
                <XAxis dataKey="hour" tick={{ fill: "#4D4D4D", fontSize: 10, fontWeight: 500 }} axisLine={{ stroke: "#ABBED1" }} tickLine={false} interval={Math.floor(displayedPoints.length / 6)} />
                <YAxis tick={{ fill: "#4D4D4D", fontSize: 10, fontWeight: 500 }} axisLine={false} tickLine={false} width={40} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const p = payload[0]?.payload;
                    return (
                      <div className="bg-white border border-dark/20 rounded-xl px-4 py-2 text-xs shadow-positivus">
                        <p className="text-dark font-bold">{label}</p>
                        <p className="text-dark font-mono font-bold mt-1">Output: {p.predicted_mw} MW</p>
                        <p className="text-ink-muted text-[10px]">Utilization: {p.utilization_pct}%</p>
                      </div>
                    );
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="predicted_mw"
                  stroke="#4CAF4F"
                  strokeWidth={2}
                  fill="url(#inspectAreaPositivus)"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="p-4 rounded-2xl bg-lime border border-dark text-dark shadow-positivus-sm">
              <span className="text-[10px] text-dark font-bold uppercase block">Peak Forecast</span>
              <p className="text-2xl font-bold font-mono tabular">{forecastData.summaryStats.peak_mw} MW</p>
            </div>
            <div className="p-4 rounded-2xl bg-white border border-dark shadow-positivus-sm">
              <span className="text-[10px] text-ink-muted font-bold uppercase block">Average Output</span>
              <p className="text-2xl font-bold font-mono tabular text-dark">{forecastData.summaryStats.avg_mw} MW</p>
            </div>
            <div className="p-4 rounded-2xl bg-card-gray border border-dark shadow-positivus-sm">
              <span className="text-[10px] text-ink-muted font-bold uppercase block">Capacity Factor</span>
              <p className="text-2xl font-bold font-mono tabular text-dark">{forecastData.summaryStats.capacity_factor_pct}%</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
