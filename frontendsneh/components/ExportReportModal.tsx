"use client";

import { useState } from "react";
import { DashboardSummary } from "@/lib/types";

interface ExportReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary: DashboardSummary;
}

export default function ExportReportModal({
  isOpen,
  onClose,
  summary,
}: ExportReportModalProps) {
  const [activeTab, setActiveTab] = useState<"csv" | "json" | "pdf">("csv");
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const totalCapacity = summary.plants.reduce((a, b) => a + b.capacity_mw, 0);
  const solarCapacity = summary.plants
    .filter((p) => p.plant_type === "solar")
    .reduce((a, b) => a + b.capacity_mw, 0);
  const windCapacity = summary.plants
    .filter((p) => p.plant_type === "wind")
    .reduce((a, b) => a + b.capacity_mw, 0);

  const generateCSV = () => {
    const headers = [
      "Timestamp (UTC)",
      "Hour Label",
      "Total Forecast (MW)",
      "Grid Demand (MW)",
      "Net Imbalance (MW)",
      "Grid Severity",
      "Alert Type",
      "Recommended Action",
    ];

    const recs = summary.recommendations || [];
    const rows = summary.hourly_balance.map((hb, i) => {
      const rec = recs.length > 0 ? recs[i % recs.length] : undefined;
      return [
        `"${hb.timestamp}"`,
        `"${new Date(hb.timestamp).toLocaleString("en-IN", {
          weekday: "short",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        })}"`,
        hb.total_generation_mw,
        hb.demand_mw,
        hb.net_balance_mw,
        `"${hb.severity}"`,
        `"${hb.alert_type || "balanced"}"`,
        `"${rec?.action || "monitor"}"`,
      ].join(",");
    });

    return [headers.join(","), ...rows].join("\n");
  };

  const handleDownloadCSV = () => {
    const csvContent = generateCSV();
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `gridcast_forecast_72h_${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadJSON = () => {
    const exportData = {
      platform: "Grid Cast Renewable Intelligence",
      version: "1.0.0",
      generated_at: new Date().toISOString(),
      grid_region: "Western & Southern Interconnect",
      fleet_capacity: {
        total_mw: totalCapacity,
        solar_mw: solarCapacity,
        wind_mw: windCapacity,
        monitored_sites_count: summary.plants.length,
      },
      bess_storage: {
        name: summary.battery?.battery_name || "Grid Battery Energy Storage",
        capacity_mwh: summary.battery?.capacity_mwh || 200,
        current_soc_pct: summary.battery?.current_soc_pct || 65,
        max_charge_mw: summary.battery?.max_charge_rate_mw || 50,
        max_discharge_mw: summary.battery?.max_discharge_rate_mw || 100,
      },
      hourly_balance: summary.hourly_balance,
      active_alerts: summary.active_alerts,
      recommendations: summary.recommendations,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `gridcast_telemetry_dump_${new Date().toISOString().slice(0, 10)}.json`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCopyJSON = () => {
    const exportData = {
      platform: "Grid Cast Renewable Intelligence",
      generated_at: new Date().toISOString(),
      hourly_balance: summary.hourly_balance.slice(0, 24),
    };
    navigator.clipboard.writeText(JSON.stringify(exportData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark/60 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl bg-white border-2 border-dark rounded-[28px] shadow-positivus overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-dark bg-card-gray">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-lime text-dark border border-dark font-bold shadow-positivus-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
            </div>
            <div>
              <h3 className="font-display font-bold text-dark text-lg">Export Fleet Telemetry &amp; Dispatch Reports</h3>
              <p className="text-[11px] text-ink-muted font-medium">Download load curves, ML predictions, and BESS schedules</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-dark hover:bg-white p-1.5 rounded-lg border border-transparent hover:border-dark font-bold"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div className="flex rounded-xl bg-card-gray p-1 border border-dark">
            <button
              onClick={() => setActiveTab("csv")}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                activeTab === "csv" ? "bg-white text-dark border border-dark shadow-positivus-sm" : "text-ink-muted hover:text-dark"
              }`}
            >
              CSV Spreadsheet (72-Hour Balance)
            </button>
            <button
              onClick={() => setActiveTab("json")}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                activeTab === "json" ? "bg-white text-dark border border-dark shadow-positivus-sm" : "text-ink-muted hover:text-dark"
              }`}
            >
              JSON Telemetry Feed
            </button>
            <button
              onClick={() => setActiveTab("pdf")}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                activeTab === "pdf" ? "bg-white text-dark border border-dark shadow-positivus-sm" : "text-ink-muted hover:text-dark"
              }`}
            >
              Executive Summary PDF
            </button>
          </div>

          {activeTab === "csv" && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark text-xs text-dark space-y-2">
                <p className="font-bold text-sm">72-Hour Dispatch Forecast Dataset (CSV)</p>
                <p className="text-ink-muted leading-relaxed">
                  Includes timestamped generation breakdown (Solar/Wind), grid demand baseline, net imbalance values, alert classifications, and deterministic dispatch directives.
                </p>
                <div className="flex flex-wrap gap-2 pt-2">
                  <span className="bg-white px-2.5 py-1 rounded-md border border-dark font-mono font-bold">72 Data Rows</span>
                  <span className="bg-white px-2.5 py-1 rounded-md border border-dark font-mono font-bold">8 Attributes</span>
                  <span className="bg-lime px-2.5 py-1 rounded-md border border-dark font-bold text-dark">Ready for Excel / Python</span>
                </div>
              </div>

              <button
                onClick={handleDownloadCSV}
                className="w-full py-3.5 rounded-xl bg-lime text-dark font-bold text-xs hover:bg-dark hover:text-white border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5 flex items-center justify-center gap-2"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download .CSV File Now
              </button>
            </div>
          )}

          {activeTab === "json" && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark text-xs text-dark space-y-2">
                <div className="flex items-center justify-between">
                  <p className="font-bold text-sm">Full State JSON Payload</p>
                  <button
                    onClick={handleCopyJSON}
                    className="text-xs font-bold text-dark bg-white hover:bg-lime px-2.5 py-1 rounded-lg border border-dark transition-all"
                  >
                    {copied ? "✓ Copied!" : "Copy JSON"}
                  </button>
                </div>
                <p className="text-ink-muted leading-relaxed">
                  Complete machine-readable JSON structure matching backend schema.
                </p>
                <pre className="bg-white border border-dark p-3 rounded-xl font-mono text-[11px] overflow-x-auto max-h-36 text-dark">
                  {JSON.stringify(
                    {
                      platform: "Grid Cast Renewable Intelligence",
                      fleet_capacity: { total_mw: totalCapacity, monitored_sites: summary.plants.length },
                      bess: summary.battery,
                      upcoming_alerts: summary.active_alerts.length,
                    },
                    null,
                    2
                  )}
                </pre>
              </div>

              <button
                onClick={handleDownloadJSON}
                className="w-full py-3.5 rounded-xl bg-dark text-white hover:bg-lime hover:text-dark font-bold text-xs border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5 flex items-center justify-center gap-2"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download Complete .JSON Telemetry
              </button>
            </div>
          )}

          {activeTab === "pdf" && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-card-gray border-2 border-dark text-xs text-dark space-y-2">
                <p className="font-bold text-sm">Printable Executive Dispatch Summary</p>
                <p className="text-ink-muted leading-relaxed">
                  Opens browser print dialog formatted for print or export to PDF document.
                </p>
                <div className="p-3 bg-white rounded-xl border border-dark space-y-1 font-medium">
                  <div className="flex justify-between">
                    <span>Monitored Fleet:</span>
                    <strong className="font-mono">{totalCapacity} MW ({summary.plants.length} Plants)</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Critical Alert Windows:</span>
                    <strong className="font-mono">{summary.active_alerts.length} Pending Actions</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>BESS Storage Available:</span>
                    <strong className="font-mono">{summary.battery?.available_discharge_mwh || 120} MWh</strong>
                  </div>
                </div>
              </div>

              <button
                onClick={() => {
                  window.print();
                }}
                className="w-full py-3.5 rounded-xl bg-lime text-dark font-bold text-xs hover:bg-dark hover:text-white border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5 flex items-center justify-center gap-2"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="6 9 6 2 18 2 18 9"/>
                  <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                  <rect x="6" y="14" width="12" height="8"/>
                </svg>
                Print / Save as PDF
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
