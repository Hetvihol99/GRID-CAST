"use client";

import { useState } from "react";
import { runForecastPipeline } from "@/lib/api";
import { OperatorUser } from "@/lib/auth";

interface HeaderProps {
  isLive?: boolean;
  currentUser: OperatorUser | null;
  onOpenAuth: () => void;
  onOpenRegisterPlant: () => void;
  onOpenAiBriefing?: () => void;
  onOpenExportReport?: () => void;
  onRefresh?: () => void;
}

export default function Header({
  isLive = false,
  currentUser,
  onOpenAuth,
  onOpenRegisterPlant,
  onOpenAiBriefing,
  onOpenExportReport,
  onRefresh,
}: HeaderProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  const handleRunForecast = async () => {
    setIsRunning(true);
    setRunMessage(null);
    try {
      const res = await runForecastPipeline(72);
      setRunMessage(res.message);
      if (onRefresh) {
        onRefresh();
      }
    } finally {
      setIsRunning(false);
      setTimeout(() => setRunMessage(null), 5000);
    }
  };

  return (
    <header className="px-6 md:px-10 py-5 bg-white border-b border-dark/15 sticky top-0 z-40 shadow-sm">
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-2xl bg-dark text-lime border border-dark shadow-positivus-sm">
            <svg width="24" height="24" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <circle cx="14" cy="14" r="11" stroke="#4CAF4F" strokeWidth="2.5" />
              <path d="M14 6 L14 14 L19.5 17" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-display font-bold text-xl leading-none text-dark tracking-tight">Grid Cast</p>
              <span
                className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md border border-dark ${
                  isLive
                    ? "bg-lime text-dark"
                    : "bg-card-gray text-dark"
                }`}
              >
                {isLive ? "FastAPI Connected" : "AI Solution Active"}
              </span>
            </div>
            <p className="text-xs text-ink-muted mt-1">Renewable Energy Intelligence &amp; BESS Dispatch</p>
          </div>
        </div>

        <nav className="hidden xl:flex items-center gap-6 text-sm font-medium text-dark">
          <a href="#forecast" className="hover:text-ink-muted hover:underline decoration-lime decoration-2 underline-offset-4 transition-all">Forecast</a>
          <a href="#battery" className="hover:text-ink-muted hover:underline decoration-lime decoration-2 underline-offset-4 transition-all">Battery Storage</a>
          <a href="#alerts" className="hover:text-ink-muted hover:underline decoration-lime decoration-2 underline-offset-4 transition-all">Alerts</a>
          <a href="#actions" className="hover:text-ink-muted hover:underline decoration-lime decoration-2 underline-offset-4 transition-all">Recommendations</a>
          <a href="#sites" className="hover:text-ink-muted hover:underline decoration-lime decoration-2 underline-offset-4 transition-all">Fleet Sites</a>
        </nav>

        <div className="flex flex-wrap items-center gap-2.5 w-full lg:w-auto justify-end">
          <button
            onClick={onOpenAuth}
            className="text-xs font-semibold px-3.5 py-2.5 rounded-xl bg-card-gray hover:bg-white border border-dark text-dark flex items-center gap-2 transition-all shadow-positivus-sm active:translate-y-0.5"
          >
            {currentUser ? (
              <>
                <span className="w-5 h-5 rounded-md bg-lime text-dark font-bold text-[10px] flex items-center justify-center border border-dark">
                  {currentUser.avatarInitials}
                </span>
                <span className="hidden sm:inline font-bold text-dark">{currentUser.name}</span>
                <span className="text-[10px] text-dark bg-lime px-1.5 py-0.5 rounded border border-dark hidden md:inline font-semibold">
                  {currentUser.roleTitle.split(" ")[0]}
                </span>
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
                Operator Login
              </>
            )}
          </button>

          <button
            onClick={onOpenRegisterPlant}
            className="text-xs font-bold px-4 py-2.5 rounded-xl bg-lime text-dark hover:bg-lime-hover border border-dark transition-all flex items-center gap-1.5 shadow-positivus-sm active:translate-y-0.5"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Register Plant
          </button>

          {onOpenAiBriefing && (
            <button
              onClick={onOpenAiBriefing}
              className="text-xs font-bold border border-dark text-dark bg-card-gray hover:bg-lime px-3.5 py-2.5 rounded-xl transition-all flex items-center gap-1.5 shadow-positivus-sm active:translate-y-0.5"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
              </svg>
              AI Solution
            </button>
          )}

          {onOpenExportReport && (
            <button
              onClick={onOpenExportReport}
              className="text-xs font-semibold border border-dark text-dark hover:bg-card-gray bg-white px-3.5 py-2.5 rounded-xl transition-all flex items-center gap-1.5 shadow-positivus-sm active:translate-y-0.5"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Export
            </button>
          )}

          <button
            onClick={handleRunForecast}
            disabled={isRunning}
            className="text-xs font-bold bg-dark text-white hover:bg-dark-secondary px-4 py-2.5 rounded-xl transition-all flex items-center gap-1.5 disabled:opacity-60 border border-dark shadow-positivus-sm active:translate-y-0.5"
          >
            {isRunning ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-lime" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                Forecasting...
              </>
            ) : (
              <>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Run Forecast
              </>
            )}
          </button>
        </div>
      </div>

      {runMessage && (
        <div className="mt-3 py-2.5 px-4 rounded-xl bg-lime border border-dark text-xs text-dark font-semibold flex items-center justify-between shadow-positivus-sm">
          <span>✓ {runMessage}</span>
          <button onClick={() => setRunMessage(null)} className="text-dark hover:opacity-75 font-bold ml-2">✕</button>
        </div>
      )}
    </header>
  );
}
