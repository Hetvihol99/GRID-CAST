"use client";

import { useState } from "react";
import { askAiCopilot, getAiBriefing } from "@/lib/api";
import { DashboardSummary } from "@/lib/types";

interface AiCopilotModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary: DashboardSummary;
}

export default function AiCopilotModal({ isOpen, onClose, summary }: AiCopilotModalProps) {
  const [messages, setMessages] = useState<Array<{ sender: "user" | "ai"; text: string }>>([
    {
      sender: "ai",
      text: "Hello! I am your AI Solution Grid Dispatch Copilot. I analyze plant predictions, demand profiles, and BESS storage capacity to advise on optimal grid balancing. Ask me anything or request an instant executive briefing.",
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [briefingText, setBriefingText] = useState<string | null>(null);
  const [isBriefingLoading, setIsBriefingLoading] = useState(false);

  if (!isOpen) return null;

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputQuery.trim() || isLoading) return;

    const userText = inputQuery.trim();
    setInputQuery("");
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setIsLoading(true);

    try {
      const response = await askAiCopilot(userText, summary);
      setMessages((prev) => [...prev, { sender: "ai", text: response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "ai", text: "Unable to query AI engine at this moment. Please check backend connection." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchBriefing = async () => {
    setIsBriefingLoading(true);
    try {
      const briefing = await getAiBriefing();
      setBriefingText(briefing);
    } catch {
      setBriefingText("Unable to generate briefing.");
    } finally {
      setIsBriefingLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark/60 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl bg-white border-2 border-dark rounded-[28px] shadow-positivus overflow-hidden flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-dark bg-card-gray">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-lime text-dark border border-dark font-bold shadow-positivus-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
              </svg>
            </div>
            <div>
              <h3 className="font-display font-bold text-dark text-lg">AI Solution Dispatch Copilot</h3>
              <p className="text-[11px] text-ink-muted font-medium">Real-time advisory grounded in live grid telemetry</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-dark hover:bg-white p-1.5 rounded-lg border border-transparent hover:border-dark font-bold"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="p-5 rounded-2xl bg-card-gray border-2 border-dark shadow-positivus-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-dark uppercase tracking-wider">Executive Dispatch Briefing</span>
              <button
                onClick={handleFetchBriefing}
                disabled={isBriefingLoading}
                className="text-xs font-bold px-3 py-1.5 rounded-xl bg-lime text-dark hover:bg-dark hover:text-white border border-dark transition-all shadow-positivus-sm active:translate-y-0.5"
              >
                {isBriefingLoading ? "Generating Briefing..." : briefingText ? "Regenerate" : "Generate Briefing"}
              </button>
            </div>

            {briefingText ? (
              <div className="text-xs md:text-sm text-dark font-medium leading-relaxed whitespace-pre-line mt-3 pt-3 border-t border-dark/20">
                {briefingText}
              </div>
            ) : (
              <p className="text-xs text-ink-muted font-medium mt-1">
                Click &quot;Generate Briefing&quot; to synthesize current solar/wind output, critical peak deficit windows, and battery dispatch directives into an executive report.
              </p>
            )}
          </div>

          <div className="space-y-3 pt-2">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-3 text-xs md:text-sm leading-relaxed border border-dark shadow-positivus-sm ${
                    m.sender === "user"
                      ? "bg-lime text-dark font-bold rounded-br-none"
                      : "bg-white text-dark font-medium rounded-bl-none"
                  }`}
                >
                  {m.text}
                </div>
                <span className="text-[10px] text-ink-muted font-semibold mt-1 px-1">
                  {m.sender === "user" ? "You (Operator)" : "AI Solution"}
                </span>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 text-xs text-dark font-bold p-2 bg-card-gray rounded-xl border border-dark w-fit shadow-positivus-sm">
                <span className="animate-pulse">●</span>
                <span className="animate-pulse delay-100">●</span>
                <span className="animate-pulse delay-200">●</span>
                <span className="text-xs ml-1">Analyzing telemetry &amp; forecasting models...</span>
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleSendMessage} className="p-4 border-t-2 border-dark bg-card-gray flex gap-2.5">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask about peak deficit, BESS charge strategy, solar ramp..."
            className="flex-1 bg-white border-2 border-dark rounded-xl px-4 py-2.5 text-xs md:text-sm text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-lime font-medium"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || isLoading}
            className="bg-dark text-white hover:bg-lime hover:text-dark font-bold text-xs md:text-sm px-5 py-2.5 rounded-xl border-2 border-dark transition-all disabled:opacity-50 shadow-positivus-sm active:translate-y-0.5"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
