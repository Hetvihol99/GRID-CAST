"use client";

import { useState, useEffect } from "react";
import {
  OperatorUser,
  OperatorRole,
  getRegisteredOperators,
  saveRegisteredOperator,
  deleteRegisteredOperator,
} from "@/lib/auth";
import { registerOperator } from "@/lib/api";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: OperatorUser | null;
  onLogin: (user: OperatorUser) => void;
  onLogout: () => void;
}

export default function AuthModal({
  isOpen,
  onClose,
  currentUser,
  onLogin,
  onLogout,
}: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const [operators, setOperators] = useState<OperatorUser[]>([]);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [org, setOrg] = useState("");
  const [role, setRole] = useState<OperatorRole>("dispatcher");
  const [registrationError, setRegistrationError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setOperators(getRegisteredOperators());
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCustomRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setRegistrationError(null);

    const roleMap: Record<OperatorRole, string> = {
      dispatcher: "Chief Grid Load Dispatcher",
      manager: "Renewable Plant Asset Manager",
      trader: "Power Trader & Market Dispatcher",
    };

    const userDetails = {
      name: name.trim() || email.split("@")[0] || "Operator",
      email: email.trim(),
      role,
      organization: org.trim() || "National Grid Operations",
    };

    let savedId = `op-${Date.now()}`;
    try {
      const savedUser = await registerOperator(userDetails);
      savedId = String(savedUser.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to save operator";
      if (message.includes("already exists")) {
        setRegistrationError("An operator with this email already exists.");
        return;
      }
      setRegistrationError("Backend unavailable. The profile was saved only in this browser.");
    }

    const user: OperatorUser = {
      id: savedId,
      ...userDetails,
      roleTitle: roleMap[role],
      avatarInitials: (name.trim() || email).slice(0, 2).toUpperCase(),
    };

    saveRegisteredOperator(user);
    setOperators(getRegisteredOperators());
    onLogin(user);
    onClose();
  };

  const handleSelectOperator = (user: OperatorUser) => {
    onLogin(user);
    onClose();
  };

  const handleDeleteOperator = (e: React.MouseEvent, opId: string) => {
    e.stopPropagation();
    deleteRegisteredOperator(opId);
    setOperators(getRegisteredOperators());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dark/60 backdrop-blur-sm">
      <div className="relative w-full max-w-md bg-white border-2 border-dark rounded-[28px] shadow-positivus overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b-2 border-dark bg-card-gray">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-lime border border-dark flex items-center justify-center text-dark font-bold shadow-positivus-sm">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div>
              <h3 className="font-display font-bold text-dark text-lg">Operator Portal</h3>
              <p className="text-[11px] text-ink-muted font-medium">Role-based dispatch &amp; telemetry access</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-dark hover:bg-white p-1.5 rounded-lg border border-transparent hover:border-dark transition-all font-bold"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-5">
          {currentUser ? (
            <div className="space-y-4">
              <div className="p-5 rounded-2xl bg-card-gray border-2 border-dark flex items-center gap-3.5 shadow-positivus-sm">
                <div className="w-12 h-12 rounded-xl bg-lime text-dark font-bold font-display text-lg flex items-center justify-center border border-dark shadow-sm">
                  {currentUser.avatarInitials}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-display font-bold text-dark text-base truncate">{currentUser.name}</p>
                  <p className="text-xs text-dark font-semibold">{currentUser.roleTitle}</p>
                  <p className="text-[11px] text-ink-muted truncate font-medium">{currentUser.organization}</p>
                </div>
              </div>

              <div className="text-xs text-dark space-y-1.5 bg-white p-4 rounded-xl border border-dark font-medium">
                <div className="flex justify-between">
                  <span className="text-ink-muted">Email:</span>
                  <span className="text-dark font-mono font-bold">{currentUser.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-muted">Access Level:</span>
                  <span className="text-dark font-bold bg-lime px-2 py-0.5 rounded border border-dark text-[10px]">SLDC Level 1 (Full)</span>
                </div>
              </div>

              <button
                onClick={() => {
                  onLogout();
                  onClose();
                }}
                className="w-full py-3 rounded-xl border-2 border-dark text-white bg-dark hover:bg-alert hover:border-dark transition-all text-xs font-bold uppercase tracking-wider shadow-positivus-sm active:translate-y-0.5"
              >
                Sign Out Operator Session
              </button>
            </div>
          ) : (
            <>
              <div className="flex rounded-xl bg-card-gray p-1 border border-dark">
                <button
                  onClick={() => setActiveTab("login")}
                  className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                    activeTab === "login" ? "bg-white text-dark border border-dark shadow-positivus-sm" : "text-ink-muted hover:text-dark"
                  }`}
                >
                  Quick Operator Sign-In
                </button>
                <button
                  onClick={() => setActiveTab("register")}
                  className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                    activeTab === "register" ? "bg-white text-dark border border-dark shadow-positivus-sm" : "text-ink-muted hover:text-dark"
                  }`}
                >
                  New Operator ID
                </button>
              </div>

              {activeTab === "login" ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-ink-muted font-medium">Select operator profile ({operators.length} saved):</p>
                    <span className="text-[10px] text-dark font-bold bg-lime px-2 py-0.5 rounded border border-dark">
                      Local DB Active
                    </span>
                  </div>
                  <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
                    {operators.map((op) => {
                      const isDefault = ["op-1", "op-2", "op-3"].includes(op.id);
                      return (
                        <div
                          key={op.id}
                          onClick={() => handleSelectOperator(op)}
                          className="w-full p-3.5 rounded-2xl bg-card-gray hover:bg-lime/20 border-2 border-dark flex items-center justify-between text-left transition-all shadow-positivus-sm active:translate-y-0.5 cursor-pointer group"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-9 h-9 rounded-xl bg-lime border border-dark text-dark font-bold text-xs flex items-center justify-center flex-shrink-0">
                              {op.avatarInitials}
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="text-xs font-bold text-dark group-hover:underline truncate">{op.name}</p>
                                {!isDefault && (
                                  <span className="text-[9px] font-bold bg-white text-dark px-1.5 py-0.2 rounded border border-dark">
                                    Saved
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] text-ink-muted font-medium truncate">{op.roleTitle}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 flex-shrink-0">
                            {!isDefault && (
                              <button
                                onClick={(e) => handleDeleteOperator(e, op.id)}
                                title="Remove operator profile"
                                className="p-1 rounded-lg text-ink-muted hover:text-alert hover:bg-white border border-transparent hover:border-dark font-bold text-xs"
                              >
                                ✕
                              </button>
                            )}
                            <span className="text-xs font-bold text-dark bg-white group-hover:bg-dark group-hover:text-white px-2 py-1 rounded-lg border border-dark transition-colors">
                              Select →
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCustomRegister} className="space-y-3">
                  {registrationError && (
                    <p className="text-xs font-bold text-alert" role="alert">{registrationError}</p>
                  )}
                  <div>
                    <label className="text-[11px] font-bold text-dark block mb-1">Operator Full Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Vikram Mehta"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2.5 text-xs text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-lime"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-dark block mb-1">Work Email Address</label>
                    <input
                      type="email"
                      required
                      placeholder="name@sldc.in"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2.5 text-xs text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-lime"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-dark block mb-1">Organization / Utility</label>
                    <input
                      type="text"
                      placeholder="e.g. Gujarat Urja Vikas Nigam (GUVNL)"
                      value={org}
                      onChange={(e) => setOrg(e.target.value)}
                      className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2.5 text-xs text-dark placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-lime"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-dark block mb-1">Operator Role</label>
                    <select
                      value={role}
                      onChange={(e) => setRole(e.target.value as OperatorRole)}
                      className="w-full bg-white border-2 border-dark rounded-xl px-3.5 py-2.5 text-xs text-dark font-medium focus:outline-none focus:ring-2 focus:ring-lime"
                    >
                      <option value="dispatcher">Chief Grid Load Dispatcher (SLDC)</option>
                      <option value="manager">Renewable Plant Asset Manager</option>
                      <option value="trader">Power Trader &amp; Market Dispatcher</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 rounded-xl bg-lime text-dark font-bold text-xs hover:bg-dark hover:text-white border-2 border-dark transition-all shadow-positivus-sm active:translate-y-0.5 mt-3 flex items-center justify-center gap-2"
                  >
                    <span>💾 Save to Storage &amp; Log In</span>
                  </button>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
