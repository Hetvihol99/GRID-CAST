export type ForecastPoint = {
  hour: string;
  timestamp: number;
  solarMW: number;
  windMW: number;
  demandMW: number;
  confidenceLowMW: number;
  confidenceHighMW: number;
};

export type Alert = {
  id: string;
  type: "over-generation" | "under-generation";
  site: string;
  window: string;
  magnitude: string;
  action: string;
  severity: "high" | "medium";
};

export type Recommendation = {
  id: string;
  kind: "Curtailment" | "Storage Dispatch" | "Backup Activation";
  site: string;
  window: string;
  detail: string;
  impact: string;
};

export type Site = {
  id: string;
  name: string;
  type: "Solar" | "Wind" | "Hybrid";
  capacityMW: number;
  region: string;
  forecastConfidence: number;
  status: "Nominal" | "Watch" | "Action needed";
};

function seededWave(i: number, period: number, phase: number, amplitude: number) {
  return amplitude * Math.max(0, Math.sin(((i + phase) / period) * Math.PI));
}

export function buildForecast(hours = 72): ForecastPoint[] {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  const points: ForecastPoint[] = [];

  for (let i = 0; i < hours; i++) {
    const t = new Date(start.getTime() + i * 60 * 60 * 1000);
    const hourOfDay = t.getHours();

    const solarBase = seededWave(hourOfDay, 24, -6, 42);
    const cloudNoise = Math.sin(i * 0.7) * 4 + Math.sin(i * 1.9) * 2;
    const solarMW = Math.max(0, Math.round(solarBase + cloudNoise));

    const windBase = 18 + 10 * Math.sin(i / 9 + 1) + 6 * Math.sin(i / 3.3);
    const windMW = Math.max(2, Math.round(windBase));

    const demandMW = Math.round(
      55 + 20 * Math.sin(((hourOfDay - 8) / 24) * Math.PI * 2) + 10 * Math.sin(((hourOfDay - 19) / 6))
    );

    const total = solarMW + windMW;
    const band = 4 + Math.round(total * 0.08);

    points.push({
      hour: t.toLocaleString("en-IN", { weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false }),
      timestamp: t.getTime(),
      solarMW,
      windMW,
      demandMW,
      confidenceLowMW: Math.max(0, total - band),
      confidenceHighMW: total + band,
    });
  }

  return points;
}

export const alerts: Alert[] = [
  {
    id: "a1",
    type: "over-generation",
    site: "Bhuj Solar Park",
    window: "Tomorrow, 11:00–14:00",
    magnitude: "+38 MW above scheduled demand",
    action: "Curtail 22 MW or dispatch to storage",
    severity: "high",
  },
  {
    id: "a2",
    type: "under-generation",
    site: "Jaisalmer Wind Cluster",
    window: "Tonight, 02:00–05:00",
    magnitude: "−17 MW below firm commitment",
    action: "Stage backup generation, notify trading desk",
    severity: "high",
  },
  {
    id: "a3",
    type: "over-generation",
    site: "Kutch Hybrid Site",
    window: "Thu, 12:00–13:00",
    magnitude: "+9 MW above scheduled demand",
    action: "Monitor — within storage buffer",
    severity: "medium",
  },
  {
    id: "a4",
    type: "under-generation",
    site: "Rajkot Solar Farm",
    window: "Wed, 06:00–08:00",
    magnitude: "−6 MW, cloud cover forecast",
    action: "No action — within tolerance",
    severity: "medium",
  },
];

export const recommendations: Recommendation[] = [
  {
    id: "r1",
    kind: "Curtailment",
    site: "Bhuj Solar Park",
    window: "Tomorrow, 11:00–14:00",
    detail: "Expected output exceeds grid absorption capacity by 38 MW at peak.",
    impact: "Avoids voltage rise risk; 22 MW curtailed vs. 38 MW unmanaged surplus",
  },
  {
    id: "r2",
    kind: "Storage Dispatch",
    site: "Kutch Hybrid Site",
    window: "Thu, 12:00–13:00",
    detail: "Surplus fits within the site's 15 MWh battery buffer — no curtailment needed.",
    impact: "16 MWh charged, released back during the 19:00 demand peak",
  },
  {
    id: "r3",
    kind: "Backup Activation",
    site: "Jaisalmer Wind Cluster",
    window: "Tonight, 02:00–05:00",
    detail: "Wind speeds forecast to drop below cut-in threshold for 3 hours.",
    impact: "51 MW gas peaker staged on standby to hold firm commitment",
  },
];

export const sites: Site[] = [
  { id: "s1", name: "Bhuj Solar Park", type: "Solar", capacityMW: 120, region: "Gujarat", forecastConfidence: 94, status: "Action needed" },
  { id: "s2", name: "Jaisalmer Wind Cluster", type: "Wind", capacityMW: 85, region: "Rajasthan", forecastConfidence: 88, status: "Action needed" },
  { id: "s3", name: "Kutch Hybrid Site", type: "Hybrid", capacityMW: 60, region: "Gujarat", forecastConfidence: 91, status: "Watch" },
  { id: "s4", name: "Rajkot Solar Farm", type: "Solar", capacityMW: 45, region: "Gujarat", forecastConfidence: 96, status: "Watch" },
  { id: "s5", name: "Kayathar Wind Farm", type: "Wind", capacityMW: 70, region: "Tamil Nadu", forecastConfidence: 90, status: "Nominal" },
];

export const kpis = [
  { label: "Forecast accuracy (MAPE)", value: "5.4%", sub: "trailing 30 days" },
  { label: "Curtailment avoided", value: "412 MWh", sub: "last 7 days" },
  { label: "Sites monitored", value: "5", sub: "3 states" },
  { label: "Active alerts", value: "2", sub: "high severity" },
];
