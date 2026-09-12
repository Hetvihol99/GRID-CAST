"use client";

import { useState, useEffect } from "react";

export default function LiveGridTicker() {
  const [frequency, setFrequency] = useState(50.01);
  const [bhadlaGhi, setBhadlaGhi] = useState(865);
  const [muppandalWind, setMuppandalWind] = useState(7.8);
  const [activeInterconnect] = useState("WR-SR Corridor 1,420 MW");

  useEffect(() => {
    const interval = setInterval(() => {
      const freqNoise = (Math.random() - 0.5) * 0.04;
      setFrequency(Number((50.0 + freqNoise).toFixed(2)));

      setBhadlaGhi((prev) => Math.max(700, Math.min(980, prev + Math.floor((Math.random() - 0.48) * 8))));
      setMuppandalWind((prev) => Number((Math.max(5.5, Math.min(11.0, prev + (Math.random() - 0.5) * 0.2))).toFixed(1)));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const freqDelta = (frequency - 50.0).toFixed(2);
  const isFreqStable = Math.abs(frequency - 50.0) <= 0.05;

  return (
    <div className="mx-6 md:mx-10 my-3 px-5 py-3 rounded-2xl bg-card-gray border border-dark flex flex-wrap items-center justify-between gap-3 text-xs shadow-positivus-sm">
      <div className="flex items-center gap-2.5">
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-lime opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-lime border border-dark"></span>
        </span>
        <span className="font-bold text-dark uppercase tracking-wider text-xs">
          Live Grid Telemetry
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-4 sm:gap-6 text-dark font-medium">
        <div className="flex items-center gap-1.5 font-mono">
          <span className="text-ink-muted">Freq:</span>
          <strong className={`px-1.5 py-0.5 rounded border border-dark text-xs ${isFreqStable ? "bg-lime text-dark" : "bg-alert-bg text-alert border-alert"}`}>
            {frequency.toFixed(2)} Hz
          </strong>
          <span className="text-[10px] text-ink-faint">({Number(freqDelta) >= 0 ? `+${freqDelta}` : freqDelta})</span>
        </div>

        <div className="flex items-center gap-1.5 font-mono">
          <span>☀️ Bhadla GHI:</span>
          <strong className="text-dark bg-white px-1.5 py-0.5 rounded border border-dark text-xs">{bhadlaGhi} W/m²</strong>
        </div>

        <div className="flex items-center gap-1.5 font-mono">
          <span>💨 Muppandal Wind:</span>
          <strong className="text-dark bg-white px-1.5 py-0.5 rounded border border-dark text-xs">{muppandalWind} m/s</strong>
        </div>

        <div className="hidden lg:flex items-center gap-1.5 font-mono">
          <span className="text-ink-muted">Flow:</span>
          <strong className="text-dark">{activeInterconnect}</strong>
        </div>
      </div>
    </div>
  );
}
