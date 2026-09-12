"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PlantRegistrationInput, PlantType, PlantForecastResult, PlantStatusSummary } from "@/lib/types";
import { registerPlant, fetchLiveWeatherForCoords, calculatePlantForecastModel } from "@/lib/api";

interface PlantRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPlantRegistered: (newPlant: PlantStatusSummary, forecastResult: PlantForecastResult) => void;
}

const PRESETS = [
  {
    name: "Bhadla Solar Park Extension",
    plant_type: "solar" as PlantType,
    capacity_mw: 2245.0,
    latitude: 27.5342,
    longitude: 71.9167,
    location_name: "Phalodi, Rajasthan",
    panel_efficiency: 0.21,
  },
  {
    name: "Pavagada Mega Solar Park",
    plant_type: "solar" as PlantType,
    capacity_mw: 2050.0,
    latitude: 14.1018,
    longitude: 77.2789,
    location_name: "Tumkur, Karnataka",
    panel_efficiency: 0.20,
  },
  {
    name: "Jaisalmer Wind Energy Park",
    plant_type: "wind" as PlantType,
    capacity_mw: 1064.0,
    latitude: 26.9157,
    longitude: 70.9083,
    location_name: "Jaisalmer, Rajasthan",
    turbine_cut_in_speed: 3.0,
    turbine_rated_speed: 12.0,
    turbine_cut_out_speed: 25.0,
  },
  {
    name: "Khavda Hybrid Mega Park Stage 1",
    plant_type: "solar" as PlantType,
    capacity_mw: 3000.0,
    latitude: 23.8569,
    longitude: 69.7214,
    location_name: "Kutch, Gujarat",
    panel_efficiency: 0.22,
  },
  {
    name: "Muppandal Wind Farm Cluster",
    plant_type: "wind" as PlantType,
    capacity_mw: 1500.0,
    latitude: 8.2612,
    longitude: 77.5451,
    location_name: "Kanyakumari, Tamil Nadu",
    turbine_cut_in_speed: 3.2,
    turbine_rated_speed: 12.5,
    turbine_cut_out_speed: 26.0,
  },
];

export default function PlantRegistrationModal({
  isOpen,
  onClose,
  onPlantRegistered,
}: PlantRegistrationModalProps) {
  const router = useRouter();

  const [formData, setFormData] = useState<PlantRegistrationInput>({
    name: "",
    plant_type: "solar",
    capacity_mw: 250,
    latitude: 26.9124,
    longitude: 75.7873,
    location_name: "Jaipur, Rajasthan",
    panel_efficiency: 0.20,
    turbine_cut_in_speed: 3.0,
    turbine_rated_speed: 12.0,
    turbine_cut_out_speed: 25.0,
  });

  const [step, setStep] = useState<"form" | "preview">("form");
  const [isVerifying, setIsVerifying] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [previewResult, setPreviewResult] = useState<PlantForecastResult | null>(null);

  if (!isOpen) return null;

  const handleApplyPreset = (preset: typeof PRESETS[0]) => {
    setFormData((prev) => ({
      ...prev,
      ...preset,
    }));
  };

  const handleCheckWeatherAndSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || formData.capacity_mw <= 0) return;

    setIsVerifying(true);
    try {
      const weather = await fetchLiveWeatherForCoords(Number(formData.latitude), Number(formData.longitude));
      const simulatedPlant: PlantStatusSummary = {
        plant_id: Date.now(),
        plant_name: formData.name.trim(),
        plant_type: formData.plant_type,
        capacity_mw: Number(formData.capacity_mw),
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
        location_name: formData.location_name.trim(),
        panel_efficiency: formData.panel_efficiency,
        turbine_cut_in_speed: formData.turbine_cut_in_speed,
        turbine_rated_speed: formData.turbine_rated_speed,
        turbine_cut_out_speed: formData.turbine_cut_out_speed,
        status: "active",
        deviation_flag: false,
        is_custom: true,
      };

      const result = calculatePlantForecastModel(simulatedPlant, weather);
      setPreviewResult(result);
      setStep("preview");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleConfirmRegistration = async () => {
    setIsSubmitting(true);
    try {
      const res = await registerPlant(formData);
      onPlantRegistered(res.plant, res.forecastResult);
      onClose();
      router.push(`/plant/${res.plant.plant_id}`);
      setStep("form");
      setPreviewResult(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark/60 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl bg-white border-2 border-dark rounded-[28px] shadow-positivus overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-dark bg-card-gray">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-lime text-dark border border-dark font-bold shadow-positivus-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v8M12 18v4M4.93 4.93l5.66 5.66M13.41 13.41l5.66 5.66M2 12h8M18 12h4M4.93 19.07l5.66-5.66M13.41 10.59l5.66-5.66"/>
              </svg>
            </div>
            <div>
              <h3 className="font-display font-bold text-dark text-lg">
                {step === "form" ? "Connect Fleet Asset" : "Telemetry Verification & Preview"}
              </h3>
              <p className="text-[11px] text-ink-muted font-medium">
                {step === "form"
                  ? "Input plant specifications and GPS coordinates to sync with XGBoost pipeline"
                  : "Review live Open-Meteo atmospheric telemetry and launch plant model"}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-dark hover:bg-white p-1.5 rounded-lg border border-transparent hover:border-dark font-bold">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {step === "form" ? (
            <form onSubmit={handleCheckWeatherAndSimulate} className="space-y-4">
              <div>
                <label className="text-xs text-dark block mb-2 font-bold uppercase tracking-wider">
                  ⚡ Indian Renewable Hub Presets
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                  {PRESETS.map((p) => (
                    <button
                      key={p.name}
                      type="button"
                      onClick={() => handleApplyPreset(p)}
                      className="p-3 rounded-xl bg-card-gray hover:bg-lime/20 border border-dark text-left transition-all shadow-positivus-sm active:translate-y-0.5"
                    >
                      <p className="text-xs font-bold text-dark truncate">{p.name.split(" ")[0]} {p.plant_type === "solar" ? "☀️" : "💨"}</p>
                      <p className="text-[10px] text-ink-muted font-medium">{p.capacity_mw} MW · {p.location_name.split(",")[1] || p.location_name}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-dark/20">
                <div>
                  <label className="text-xs font-bold text-dark block mb-1">Plant Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Khavda Phase 2 Solar Park"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2 text-xs text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-lime font-medium"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-dark block mb-1">Generation Type</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, plant_type: "solar" })}
                      className={`flex-1 py-2 rounded-xl text-xs font-bold border-2 border-dark transition-all shadow-positivus-sm ${
                        formData.plant_type === "solar"
                          ? "bg-lime text-dark"
                          : "bg-white text-dark hover:bg-card-gray"
                      }`}
                    >
                      ☀️ Solar PV
                    </button>
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, plant_type: "wind" })}
                      className={`flex-1 py-2 rounded-xl text-xs font-bold border-2 border-dark transition-all shadow-positivus-sm ${
                        formData.plant_type === "wind"
                          ? "bg-dark text-white"
                          : "bg-white text-dark hover:bg-card-gray"
                      }`}
                    >
                      💨 Wind Turbine
                    </button>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-dark block mb-1">Installed Capacity (MW)</label>
                  <input
                    type="number"
                    min="1"
                    max="10000"
                    required
                    value={formData.capacity_mw}
                    onChange={(e) => setFormData({ ...formData, capacity_mw: Number(e.target.value) })}
                    className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2 text-xs text-dark focus:outline-none focus:ring-2 focus:ring-lime font-mono font-bold"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-dark block mb-1">Location / Regional Substation</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Khavda, Gujarat"
                    value={formData.location_name}
                    onChange={(e) => setFormData({ ...formData, location_name: e.target.value })}
                    className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2 text-xs text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-lime font-medium"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-dark block mb-1">Latitude (°N)</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={formData.latitude}
                    onChange={(e) => setFormData({ ...formData, latitude: Number(e.target.value) })}
                    className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2 text-xs text-dark focus:outline-none focus:ring-2 focus:ring-lime font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-dark block mb-1">Longitude (°E)</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={formData.longitude}
                    onChange={(e) => setFormData({ ...formData, longitude: Number(e.target.value) })}
                    className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2 text-xs text-dark focus:outline-none focus:ring-2 focus:ring-lime font-mono"
                  />
                </div>
              </div>

              {formData.plant_type === "solar" ? (
                <div className="p-4 rounded-xl bg-card-gray border border-dark space-y-2">
                  <span className="text-xs font-bold text-dark block uppercase">☀️ Solar Array Parameters</span>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] text-ink-muted block font-semibold">Panel Efficiency Rating</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0.10"
                        max="0.35"
                        value={formData.panel_efficiency || 0.20}
                        onChange={(e) => setFormData({ ...formData, panel_efficiency: Number(e.target.value) })}
                        className="w-full bg-white border border-dark rounded-lg px-2.5 py-1.5 text-xs text-dark font-mono font-bold"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] text-ink-muted block font-semibold">Inverter AC/DC Ratio</label>
                      <input
                        type="text"
                        disabled
                        value="1.25 (Standard Bi-facial)"
                        className="w-full bg-white border border-dark rounded-lg px-2.5 py-1.5 text-xs text-ink-muted font-mono"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-card-gray border border-dark space-y-2">
                  <span className="text-xs font-bold text-dark block uppercase">💨 Wind Turbine Parameters</span>
                  <div className="grid grid-cols-3 gap-2.5">
                    <div>
                      <label className="text-[10px] text-ink-muted block font-semibold">Cut-in (m/s)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.turbine_cut_in_speed || 3.0}
                        onChange={(e) => setFormData({ ...formData, turbine_cut_in_speed: Number(e.target.value) })}
                        className="w-full bg-white border border-dark rounded-lg px-2 py-1.5 text-xs text-dark font-mono font-bold"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-ink-muted block font-semibold">Rated (m/s)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.turbine_rated_speed || 12.0}
                        onChange={(e) => setFormData({ ...formData, turbine_rated_speed: Number(e.target.value) })}
                        className="w-full bg-white border border-dark rounded-lg px-2 py-1.5 text-xs text-dark font-mono font-bold"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-ink-muted block font-semibold">Cut-out (m/s)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={formData.turbine_cut_out_speed || 25.0}
                        onChange={(e) => setFormData({ ...formData, turbine_cut_out_speed: Number(e.target.value) })}
                        className="w-full bg-white border border-dark rounded-lg px-2 py-1.5 text-xs text-dark font-mono font-bold"
                      />
                    </div>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={isVerifying}
                className="w-full py-3 rounded-xl bg-lime text-dark font-bold text-xs hover:bg-dark hover:text-white border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5 mt-2 flex items-center justify-center gap-2"
              >
                {isVerifying ? (
                  <>
                    <svg className="animate-spin h-4 w-4 text-dark" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                    </svg>
                    Fetching Live Open-Meteo Telemetry &amp; Building Model...
                  </>
                ) : (
                  <>
                    <span>Verify Satellite Telemetry &amp; Preview 72h Output →</span>
                  </>
                )}
              </button>
            </form>
          ) : (
            previewResult && (
              <div className="space-y-4">
                <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark shadow-positivus-sm space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-dark/20">
                    <div>
                      <h4 className="font-bold text-dark text-base">{previewResult.plant.plant_name}</h4>
                      <p className="text-xs text-ink-muted font-medium">{previewResult.plant.capacity_mw} MW · {previewResult.plant.location_name}</p>
                    </div>
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-lime text-dark border border-dark">
                      Ready to Connect
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
                    <div className="p-3 bg-white rounded-xl border border-dark">
                      <span className="text-[10px] text-ink-muted block font-semibold">Live Temp</span>
                      <span className="text-sm font-bold font-mono text-dark">{previewResult.currentWeather.temperature_c}°C</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-dark">
                      <span className="text-[10px] text-ink-muted block font-semibold">{formData.plant_type === "solar" ? "Solar Irradiance" : "Wind Speed"}</span>
                      <span className="text-sm font-bold font-mono text-dark">
                        {formData.plant_type === "solar"
                          ? `${previewResult.currentWeather.solar_irradiance_wm2} W/m²`
                          : `${previewResult.currentWeather.wind_speed_ms} m/s`}
                      </span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-dark">
                      <span className="text-[10px] text-ink-muted block font-semibold">Peak Predicted</span>
                      <span className="text-sm font-bold font-mono text-dark">{previewResult.summaryStats.peak_mw} MW</span>
                    </div>
                    <div className="p-3 bg-white rounded-xl border border-dark">
                      <span className="text-[10px] text-ink-muted block font-semibold">Est. 24h Yield</span>
                      <span className="text-sm font-bold font-mono text-dark">{previewResult.summaryStats.est_daily_mwh} MWh</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setStep("form")}
                    className="flex-1 py-3 rounded-xl bg-white border-2 border-dark text-dark font-bold text-xs hover:bg-card-gray transition-all shadow-positivus-sm active:translate-y-0.5"
                  >
                    ← Edit Specifications
                  </button>
                  <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={handleConfirmRegistration}
                    className="flex-1 py-3 rounded-xl bg-lime text-dark hover:bg-dark hover:text-white font-bold text-xs border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5 flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? "Activating Fleet..." : "✓ Confirm & Launch AI Solution →"}
                  </button>
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
