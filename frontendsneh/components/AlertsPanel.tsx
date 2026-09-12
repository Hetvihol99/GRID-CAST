"use client";

import { useState } from "react";
import { AlertResponse } from "@/lib/types";

interface AlertsPanelProps {
  alerts: AlertResponse[];
  onAcknowledgeAlert?: (id: number) => void;
}

export default function AlertsPanel({ alerts, onAcknowledgeAlert }: AlertsPanelProps) {
  const [acknowledgedIds, setAcknowledgedIds] = useState<number[]>([]);

  const handleToggleAcknowledge = (id: number) => {
    if (acknowledgedIds.includes(id)) {
      setAcknowledgedIds(acknowledgedIds.filter((item) => item !== id));
    } else {
      setAcknowledgedIds([...acknowledgedIds, id]);
    }
    if (onAcknowledgeAlert) {
      onAcknowledgeAlert(id);
    }
  };

  const formatTimeWindow = (start: string, end: string) => {
    try {
      const s = new Date(start);
      const e = new Date(end);
      const dayStr = s.toLocaleDateString("en-IN", { weekday: "short", month: "short", day: "numeric" });
      const startTime = s.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
      const endTime = e.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
      return `${dayStr}, ${startTime}–${endTime}`;
    } catch {
      return `${start} – ${end}`;
    }
  };

  return (
    <section id="alerts" className="px-6 md:px-10 py-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-lime text-dark font-bold text-2xl md:text-3xl px-3.5 py-1 rounded-xl border border-dark inline-block shadow-positivus-sm">
              Grid Imbalance Alerts
            </span>
          </div>
          <p className="text-xs text-ink-muted font-medium">
            Multi-hour forecast notices requiring load dispatcher attention and automated mitigation
          </p>
        </div>
        <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-card-gray border border-dark text-dark shadow-positivus-sm w-fit">
          {alerts.length} Active Notice{alerts.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="space-y-3">
        {alerts.length === 0 ? (
          <div className="p-8 text-center text-sm font-semibold text-dark bg-card-gray border-2 border-dark rounded-[24px] shadow-positivus">
            ✓ No active grid imbalance alerts. Generation and demand are within nominal operating bands.
          </div>
        ) : (
          alerts.map((a) => {
            const isCritical = a.severity === "critical";
            const isWarning = a.severity === "warning";
            const isAck = acknowledgedIds.includes(a.id);

            return (
              <div
                key={a.id}
                className={`flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-5 rounded-2xl border-2 border-dark transition-all shadow-positivus ${
                  isAck
                    ? "bg-card-gray opacity-80"
                    : isCritical
                    ? "bg-alert-bg"
                    : isWarning
                    ? "bg-lime-light"
                    : "bg-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`text-xs font-bold px-3 py-1 rounded-full border border-dark w-fit uppercase tracking-wider ${
                      isCritical
                        ? "bg-alert text-white"
                        : isWarning
                        ? "bg-lime text-dark"
                        : "bg-white text-dark"
                    }`}
                  >
                    {a.severity} · {a.alert_type}
                  </span>
                  <span className="text-xs text-dark font-mono font-semibold">
                    {formatTimeWindow(a.start_time, a.end_time)}
                  </span>
                </div>

                <div className="flex-1 lg:mx-6 min-w-0">
                  <p className="text-sm font-bold text-dark leading-snug">{a.message}</p>
                </div>

                <div className="flex items-center gap-4 lg:text-right text-xs">
                  <div>
                    <span className="text-ink-muted block text-[11px] font-semibold">Peak Imbalance</span>
                    <span className="font-bold text-base font-mono text-dark">
                      {a.peak_magnitude_mw > 0 ? `+${a.peak_magnitude_mw}` : a.peak_magnitude_mw} MW
                    </span>
                  </div>

                  <button
                    onClick={() => handleToggleAcknowledge(a.id)}
                    className={`px-4 py-2 rounded-xl text-xs font-bold border border-dark transition-all shadow-positivus-sm active:translate-y-0.5 ${
                      isAck
                        ? "bg-lime text-dark border-dark"
                        : "bg-white text-dark hover:bg-lime"
                    }`}
                  >
                    {isAck ? "✓ Acknowledged" : "Acknowledge"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
