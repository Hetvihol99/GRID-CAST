export type OperatorRole = "dispatcher" | "manager" | "trader";

export interface OperatorUser {
  id: string;
  name: string;
  email: string;
  role: OperatorRole;
  roleTitle: string;
  organization: string;
  avatarInitials: string;
}

export const VERIFIED_OPERATORS: OperatorUser[] = [
  {
    id: "op-1",
    name: "Dr. Rajesh Sharma",
    email: "rajesh.sharma@sldc.in",
    role: "dispatcher",
    roleTitle: "Chief Grid Load Dispatcher",
    organization: "State Load Despatch Centre (SLDC)",
    avatarInitials: "RS",
  },
  {
    id: "op-2",
    name: "Pooja Varma",
    email: "pooja.varma@gridcast.com",
    role: "manager",
    roleTitle: "Renewable Plant Asset Manager",
    organization: "Grid Cast Asset Operations",
    avatarInitials: "PV",
  },
  {
    id: "op-3",
    name: "Arjun Patel",
    email: "arjun.patel@energyexchange.in",
    role: "trader",
    roleTitle: "Power Trader & Market Dispatcher",
    organization: "Indian Power Exchange Desk",
    avatarInitials: "AP",
  },
];

const AUTH_STORAGE_KEY = "gridcast_operator_session";
const REGISTERED_OPERATORS_KEY = "gridcast_registered_operators";

export function getRegisteredOperators(): OperatorUser[] {
  if (typeof window === "undefined") return VERIFIED_OPERATORS;
  try {
    const raw = localStorage.getItem(REGISTERED_OPERATORS_KEY);
    if (raw) {
      const customOps: OperatorUser[] = JSON.parse(raw);
      // Merge with default verified operators, custom operators first
      const existingIds = new Set(customOps.map((o) => o.id));
      const defaults = VERIFIED_OPERATORS.filter((o) => !existingIds.has(o.id));
      return [...customOps, ...defaults];
    }
  } catch {}
  return VERIFIED_OPERATORS;
}

export function saveRegisteredOperator(user: OperatorUser): void {
  if (typeof window === "undefined") return;
  try {
    const current = getRegisteredOperators();
    const filtered = current.filter((u) => u.id !== user.id && u.email.toLowerCase() !== user.email.toLowerCase());
    const updated = [user, ...filtered];
    localStorage.setItem(REGISTERED_OPERATORS_KEY, JSON.stringify(updated));
    saveOperatorSession(user);
  } catch {}
}

export function deleteRegisteredOperator(id: string): void {
  if (typeof window === "undefined") return;
  try {
    const current = getRegisteredOperators();
    const updated = current.filter((u) => u.id !== id);
    localStorage.setItem(REGISTERED_OPERATORS_KEY, JSON.stringify(updated));
  } catch {}
}

export function getStoredOperator(): OperatorUser | null {
  if (typeof window === "undefined") return null;
  try {
    const data = localStorage.getItem(AUTH_STORAGE_KEY);
    if (data) {
      return JSON.parse(data);
    }
  } catch {}
  const all = getRegisteredOperators();
  return all.length > 0 ? all[0] : VERIFIED_OPERATORS[0];
}

export function saveOperatorSession(user: OperatorUser): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  } catch {}
}

export function clearOperatorSession(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {}
}
