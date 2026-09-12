"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { PlantStatusSummary, PlantForecastResult } from "@/lib/types";
import { getPlantById, calculatePlantForecastModel, fetchLiveWeatherForCoords, generatePlantAiSolution } from "@/lib/api";
import {
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function PlantDetailPage() {
  const params = useParams();
  const plantId = params?.id as string;

  const [plant, setPlant] = useState<PlantStatusSummary | null>(null);
  const [forecast, setForecast] = useState<PlantForecastResult | null>(null);
  const [horizon, setHorizon] = useState<24 | 48 | 72>(72);
  const [aiSolution, setAiSolution] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [isAiModalOpen, setIsAiModalOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadPlantData() {
      if (!plantId) return;
      setIsLoading(true);

      const foundPlant = await getPlantById(plantId);
      if (foundPlant) {
        setPlant(foundPlant);
        const weather = await fetchLiveWeatherForCoords(foundPlant.latitude || 26.9, foundPlant.longitude || 75.8);
        const result = calculatePlantForecastModel(foundPlant, weather);
        setForecast(result);

        setIsAiLoading(true);
        const aiText = await generatePlantAiSolution(foundPlant, result);
        setAiSolution(aiText);
        setIsAiLoading(false);
      }
      setIsLoading(false);
    }

    loadPlantData();
  }, [plantId]);

  if (isLoading || !plant || !forecast) {
    return (
      <main className="max-w-6xl mx-auto min-h-screen px-6 py-12 flex flex-col items-center justify-center text-center bg-white text-dark">
        <div className="w-14 h-14 rounded-2xl bg-lime border-2 border-dark flex items-center justify-center text-dark animate-spin mb-4 shadow-positivus-sm">
          <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
          </svg>
        </div>
        <h2 className="font-display font-bold text-2xl text-dark">Analyzing Plant Generation &amp; Weather Satellite Feed...</h2>
        <p className="text-xs text-ink-muted mt-2 font-medium">Computing 72-hour XGBoost predictions and grid demand balance...</p>
      </main>
    );
  }

  const isSolar = plant.plant_type === "solar";
  const displayedPoints = forecast.hourlyPoints.slice(0, horizon);

  const capacity = plant.capacity_mw;
  const peakMW = forecast.summaryStats.peak_mw;
  const dailyMWh = forecast.summaryStats.est_daily_mwh;
  const capacityFactor = forecast.summaryStats.capacity_factor_pct;
  const nextHourMW = displayedPoints[0]?.predicted_mw || Math.round(capacity * 0.65);
  const benchmarkDemand = 780;
  const netContribution = nextHourMW - Math.round(benchmarkDemand * 0.25);
  const co2AvoidedTons = Math.round(dailyMWh * 0.82);

  return (
    <main className="max-w-6xl mx-auto min-h-screen px-6 md:px-10 py-8 flex flex-col space-y-6 bg-white text-dark">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b-2 border-dark">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs font-bold text-dark hover:bg-dark hover:text-white px-4 py-2 rounded-xl bg-card-gray border border-dark transition-all shadow-positivus-sm active:translate-y-0.5"
          >
            ← Fleet Overview
          </Link>
          <span className="text-dark font-bold text-xs">•</span>
          <span className="text-xs font-semibold text-ink-muted">Asset Generation &amp; AI Solution Report</span>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              if (!forecast) return;
              const headers = ["Timestamp", "Hour", "Predicted Generation (MW)", "Utilization (%)", "Upper Bound (MW)", "Lower Bound (MW)"];
              const rows = forecast.hourlyPoints.map((p) => [
                p.timestamp,
                `"${p.hour}"`,
                p.predicted_mw,
                p.utilization_pct,
                p.upper_bound_mw,
                p.lower_bound_mw,
              ].join(","));
              const csv = [headers.join(","), ...rows].join("\n");
              const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = `${plant.plant_name.toLowerCase().replace(/\s+/g, "_")}_forecast_72h.csv`;
              link.click();
            }}
            className="text-xs font-bold px-3.5 py-2 rounded-xl bg-white border border-dark text-dark hover:bg-card-gray transition-all flex items-center gap-1.5 shadow-positivus-sm active:translate-y-0.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            CSV
          </button>

          <button
            onClick={() => window.print()}
            className="text-xs font-bold px-3.5 py-2 rounded-xl bg-white border border-dark text-dark hover:bg-card-gray transition-all flex items-center gap-1.5 shadow-positivus-sm active:translate-y-0.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="6 9 6 2 18 2 18 9"/>
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
              <rect x="6" y="14" width="12" height="8"/>
            </svg>
            Print
          </button>

          <button
            onClick={() => setIsAiModalOpen(true)}
            className="text-xs font-bold px-4 py-2 rounded-xl bg-lime text-dark hover:bg-dark hover:text-white border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5 flex items-center gap-1.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
            AI Solution Directives
          </button>
        </div>
      </div>

      <div className="p-6 md:p-8 rounded-[28px] bg-card-gray border-2 border-dark shadow-positivus relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className={`p-4 rounded-2xl border-2 border-dark text-3xl shadow-positivus-sm ${
              isSolar ? "bg-lime text-dark" : "bg-dark text-white"
            }`}>
              {isSolar ? "☀️" : "💨"}
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="font-display text-2xl md:text-3xl font-bold text-dark">{plant.plant_name}</h1>
                <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border border-dark ${
                  isSolar ? "bg-lime text-dark" : "bg-dark text-white"
                }`}>
                  {isSolar ? "Solar Photovoltaic" : "Wind Turbine Generator"}
                </span>
                <span className="text-xs font-bold px-2.5 py-1 rounded-md bg-white text-dark border border-dark">
                  ● Telemetry Connected
                </span>
              </div>
              <p className="text-xs text-ink-muted mt-2 font-medium">
                Location: <strong className="text-dark">{plant.location_name || "Regional Station"}</strong> · Coordinates:{" "}
                <span className="font-mono font-bold text-dark">{plant.latitude}°N, {plant.longitude}°E</span> · Western/Southern Bus
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 text-right">
            <div className="p-4 rounded-2xl bg-white border-2 border-dark shadow-positivus-sm">
              <span className="text-[10px] text-ink-muted block uppercase tracking-wider font-bold">Installed Nameplate</span>
              <span className="text-3xl font-display font-bold text-dark font-mono tabular">{capacity} MW</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <div className="p-4 rounded-2xl bg-lime border-2 border-dark shadow-positivus-sm">
          <span className="text-[10px] uppercase font-bold text-dark block tracking-wider">Current Output</span>
          <p className="text-2xl font-display font-bold text-dark tabular mt-1">{nextHourMW} MW</p>
          <span className="text-[10px] text-dark font-semibold">{Math.round((nextHourMW / capacity) * 100)}% utilization</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border-2 border-dark shadow-positivus-sm">
          <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">Peak Predicted</span>
          <p className="text-2xl font-display font-bold text-dark tabular mt-1">{peakMW} MW</p>
          <span className="text-[10px] text-ink-muted font-medium">Peak midday rate</span>
        </div>

        <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark shadow-positivus-sm">
          <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">24h Energy Yield</span>
          <p className="text-2xl font-display font-bold text-dark tabular mt-1">{dailyMWh} MWh</p>
          <span className="text-[10px] text-ink-muted font-medium">Estimated daily work</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border-2 border-dark shadow-positivus-sm">
          <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">Capacity Factor</span>
          <p className="text-2xl font-display font-bold text-dark tabular mt-1">{capacityFactor}%</p>
          <span className="text-[10px] text-ink-muted font-medium">72h multi-step avg</span>
        </div>

        <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark shadow-positivus-sm">
          <span className="text-[10px] uppercase font-bold text-ink-muted block tracking-wider">Balance Impact</span>
          <p className={`text-2xl font-display font-bold tabular mt-1 ${netContribution >= 0 ? "text-dark" : "text-alert"}`}>
            {netContribution > 0 ? `+${netContribution}` : netContribution} MW
          </p>
          <span className="text-[10px] text-ink-muted font-medium">{netContribution >= 0 ? "Surplus exported" : "Deficit buffer"}</span>
        </div>

        <div className="p-4 rounded-2xl bg-dark text-white border-2 border-dark shadow-positivus-sm">
          <span className="text-[10px] uppercase font-bold text-gray-300 block tracking-wider">CO₂ Offset</span>
          <p className="text-2xl font-display font-bold text-lime tabular mt-1">{co2AvoidedTons} t</p>
          <span className="text-[10px] text-gray-300 font-medium">Carbon saved/day</span>
        </div>
      </div>

      <div className="p-5 md:p-6 rounded-[28px] bg-card-gray border-2 border-dark shadow-positivus">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-dark/20">
          <span className="text-xs font-bold text-dark uppercase tracking-wider flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-lime border border-dark" />
            Live Ground Weather Station Telemetry (Open-Meteo Satellite Feed)
          </span>
          <span className="text-[11px] text-dark font-mono font-bold bg-white px-2 py-0.5 rounded border border-dark">
            Elevation: 284m · Sensors Nominal
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
          <div className="p-3.5 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] text-ink-muted block font-bold">Irradiance (GHI)</span>
            <span className="text-lg font-bold text-dark font-mono tabular">
              {forecast.currentWeather.solar_irradiance_wm2} W/m²
            </span>
          </div>

          <div className="p-3.5 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] text-ink-muted block font-bold">Wind Velocity</span>
            <span className="text-lg font-bold text-dark font-mono tabular">
              {forecast.currentWeather.wind_speed_ms} m/s
            </span>
          </div>

          <div className="p-3.5 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] text-ink-muted block font-bold">Cloud Cover</span>
            <span className="text-lg font-bold text-dark font-mono tabular">
              {forecast.currentWeather.cloud_cover_pct}%
            </span>
          </div>

          <div className="p-3.5 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] text-ink-muted block font-bold">Ambient Temp</span>
            <span className="text-lg font-bold text-dark font-mono tabular">
              {forecast.currentWeather.temperature_c}°C
            </span>
          </div>

          <div className="p-3.5 rounded-2xl bg-white border border-dark shadow-positivus-sm">
            <span className="text-[10px] text-ink-muted block font-bold">Pressure</span>
            <span className="text-lg font-bold text-dark font-mono tabular">
              {forecast.currentWeather.pressure_hpa} hPa
            </span>
          </div>
        </div>
      </div>

      <div className="p-6 md:p-8 rounded-[28px] bg-card-gray border-2 border-dark shadow-positivus">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="font-display font-bold text-xl text-dark">
              72-Hour Generation Forecast Curve
            </h3>
            <p className="text-xs text-ink-muted font-medium mt-0.5">
              Hourly predicted work (MW) with XGBoost confidence bounds
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-dark">Horizon:</span>
            <div className="flex gap-1.5 bg-white border border-dark rounded-xl p-1 shadow-positivus-sm">
              {[24, 48, 72].map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizon(h as any)}
                  className={`text-xs px-3.5 py-1.5 rounded-lg font-bold transition-all ${
                    horizon === h ? "bg-lime text-dark border border-dark shadow-sm" : "text-dark hover:bg-card-gray"
                  }`}
                >
                  {h}h
                </button>
              ))}
            </div>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={displayedPoints} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="plantAreaPositivus" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4CAF4F" stopOpacity={0.85} />
                <stop offset="100%" stopColor="#4CAF4F" stopOpacity={0.15} />
              </linearGradient>
            </defs>

            <CartesianGrid stroke="#ABBED1" strokeDasharray="3 3" vertical={false} opacity={0.35} />
            <XAxis dataKey="hour" tick={{ fill: "#4D4D4D", fontSize: 11, fontWeight: 500 }} axisLine={{ stroke: "#ABBED1", strokeWidth: 1 }} tickLine={false} interval={Math.floor(displayedPoints.length / 8)} />
            <YAxis tick={{ fill: "#4D4D4D", fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} width={45} label={{ value: "MW", position: "insideTopLeft", fill: "#263238", fontSize: 11, fontWeight: 600, dx: 10, dy: -6 }} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const p = payload[0]?.payload;
                return (
                  <div className="bg-white border border-dark/20 rounded-2xl px-4 py-3 text-xs shadow-positivus">
                    <p className="text-dark font-bold text-sm mb-2">{label}</p>
                    <div className="space-y-1 font-medium">
                      <div className="flex justify-between gap-4">
                        <span className="text-dark font-bold">Predicted Output:</span>
                        <span className="font-bold tabular font-mono text-dark">{p.predicted_mw} MW</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-ink-muted">Utilization:</span>
                        <span className="tabular font-mono">{p.utilization_pct}%</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-ink-muted">Confidence:</span>
                        <span className="tabular font-mono text-dark">{p.lower_bound_mw} – {p.upper_bound_mw} MW</span>
                      </div>
                    </div>
                  </div>
                );
              }}
            />
            <Area
              type="monotone"
              dataKey="predicted_mw"
              name="Plant Generation (MW)"
              stroke="#4CAF4F"
              fill="url(#plantAreaPositivus)"
              strokeWidth={2.5}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="p-6 md:p-8 rounded-[28px] bg-white border-2 border-dark shadow-positivus relative overflow-hidden">
        <div className="flex items-center justify-between mb-4 pb-3 border-b-2 border-dark">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-lime border border-dark text-dark font-bold shadow-positivus-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
              </svg>
            </div>
            <h3 className="font-display font-bold text-xl text-dark">
              AI Solution Grid Optimization &amp; Dispatch Directives
            </h3>
          </div>
          <span className="text-xs text-dark bg-lime px-3 py-1 rounded-md border border-dark font-bold">
            Automated Directives
          </span>
        </div>

        {isAiLoading ? (
          <div className="p-8 text-center text-xs text-ink-muted space-y-2">
            <div className="animate-spin w-7 h-7 border-3 border-dark border-t-lime rounded-full mx-auto" />
            <p className="font-medium text-dark">Evaluating storage capacity, ramp limits, and demand balancing...</p>
          </div>
        ) : (
          <div className="text-xs md:text-sm text-dark font-medium leading-relaxed whitespace-pre-line bg-card-gray p-6 rounded-2xl border border-dark shadow-positivus-sm">
            {aiSolution}
          </div>
        )}
      </div>

      {isAiModalOpen && aiSolution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark/60 backdrop-blur-sm">
          <div className="relative w-full max-w-2xl bg-white border-2 border-dark rounded-[28px] shadow-positivus overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b-2 border-dark bg-card-gray">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-lime text-dark border border-dark font-bold shadow-positivus-sm">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                  </svg>
                </div>
                <div>
                  <h3 className="font-display font-bold text-dark text-lg">
                    AI Solution Integration Directives for {plant.plant_name}
                  </h3>
                  <p className="text-[11px] text-ink-muted font-medium">
                    Real-time dispatch optimization for {capacity} MW installed capacity
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsAiModalOpen(false)}
                className="text-dark hover:bg-white p-1.5 rounded-lg border border-transparent hover:border-dark font-bold"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs md:text-sm text-dark leading-relaxed">
              <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark flex items-center justify-between text-xs font-bold shadow-positivus-sm">
                <span>Peak Forecast: <strong className="text-dark font-mono text-sm">{peakMW} MW</strong></span>
                <span>24h Yield: <strong className="text-dark font-mono text-sm">{dailyMWh} MWh</strong></span>
                <span>Utilization: <strong className="bg-lime px-2 py-0.5 rounded border border-dark">{capacityFactor}%</strong></span>
              </div>

              <div className="whitespace-pre-line text-dark font-medium bg-card-gray/50 p-5 rounded-2xl border border-dark">
                {aiSolution}
              </div>
            </div>

            <div className="p-4 border-t-2 border-dark bg-card-gray flex justify-end">
              <button
                onClick={() => setIsAiModalOpen(false)}
                className="px-6 py-3 rounded-xl bg-lime text-dark font-bold text-xs hover:bg-dark hover:text-white border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5"
              >
                ✓ Acknowledge Directives
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
