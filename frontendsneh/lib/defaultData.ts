import { DashboardSummary, ForecastPoint, RecommendationResponse, WeatherProvider, BackendHealth } from "./types";

export function generateDefaultDashboard(): DashboardSummary {
  const now = new Date();
  now.setMinutes(0, 0, 0);

  const hourly_balance: DashboardSummary["hourly_balance"] = [];
  const startMs = now.getTime();

  for (let i = 0; i < 72; i++) {
    const t = new Date(startMs + i * 3600 * 1000);
    const hourOfDay = t.getHours();

    const solarCurve = Math.max(0, Math.sin(((hourOfDay - 6) / 12) * Math.PI));
    const cloudFactor = 0.85 + 0.15 * Math.sin(i * 0.45);
    const solarGen = hourOfDay >= 6 && hourOfDay <= 18
      ? Math.round(210 * solarCurve * cloudFactor)
      : 0;

    const windBase = 120 + 45 * Math.sin(i / 7.5 + 0.8) + 30 * Math.cos(i / 3.2);
    const windGen = Math.max(25, Math.round(windBase));

    const totalGen = solarGen + windGen;

    const morningPeak = 220 * Math.exp(-0.5 * Math.pow((hourOfDay - 9) / 2.2, 2));
    const eveningPeak = 320 * Math.exp(-0.5 * Math.pow((hourOfDay - 20) / 2.5, 2));
    const nightTrough = -90 * Math.exp(-0.5 * Math.pow((hourOfDay - 3) / 2.0, 2));
    const demand = Math.round(580 + morningPeak + eveningPeak + nightTrough + (Math.sin(i * 0.9) * 20));

    const net = totalGen - demand;

    let severity: "normal" | "watch" | "warning" | "critical" = "normal";
    if (net < -300) {
      severity = "critical";
    } else if (net < -150 || net > 180) {
      severity = "warning";
    } else if (net < -60 || net > 80) {
      severity = "watch";
    }

    hourly_balance.push({
      timestamp: t.toISOString(),
      total_generation_mw: totalGen,
      demand_mw: demand,
      net_balance_mw: net,
      severity,
    });
  }

  const nextHour = hourly_balance[0];

  return {
    generated_at: now.toISOString(),
    region: "default",
    forecast_horizon_hours: 72,
    total_forecast_mw_next_hour: nextHour.total_generation_mw,
    total_demand_mw_next_hour: nextHour.demand_mw,
    net_balance_mw_next_hour: nextHour.net_balance_mw,
    overall_severity: "warning",
    plants: [
      {
        plant_id: 1,
        plant_name: "Rajasthan Solar Farm A",
        plant_type: "solar",
        capacity_mw: 100.0,
        location_name: "Jaipur, Rajasthan",
        latest_forecast_mw: 68.4,
        status: "active",
        deviation_flag: false,
      },
      {
        plant_id: 2,
        plant_name: "Gujarat Solar Park B",
        plant_type: "solar",
        capacity_mw: 150.0,
        location_name: "Ahmedabad, Gujarat",
        latest_forecast_mw: 112.1,
        status: "active",
        deviation_flag: false,
      },
      {
        plant_id: 3,
        plant_name: "Tamil Nadu Wind Farm I",
        plant_type: "wind",
        capacity_mw: 200.0,
        location_name: "Tirunelveli, Tamil Nadu",
        latest_forecast_mw: 148.5,
        status: "active",
        deviation_flag: false,
      },
      {
        plant_id: 4,
        plant_name: "Andhra Pradesh Wind Farm II",
        plant_type: "wind",
        capacity_mw: 100.0,
        location_name: "Kurnool, Andhra Pradesh",
        latest_forecast_mw: 74.2,
        status: "active",
        deviation_flag: false,
      },
    ],
    hourly_balance,
    battery: {
      battery_id: 1,
      battery_name: "Southern Grid Battery Storage",
      capacity_mwh: 200.0,
      current_soc_pct: 70.0,
      available_discharge_mwh: 120.0,
      available_charge_mwh: 50.0,
      max_discharge_rate_mw: 100.0,
      max_charge_rate_mw: 80.0,
    },
    active_alerts: [
      {
        id: 101,
        region: "default",
        alert_type: "deficit",
        severity: "critical",
        start_time: new Date(startMs + 18 * 3600 * 1000).toISOString(),
        end_time: new Date(startMs + 22 * 3600 * 1000).toISOString(),
        peak_magnitude_mw: -342.0,
        avg_magnitude_mw: -265.0,
        message: "Evening peak demand deficit: Solar ramp-down coincides with industrial peak load in Western & Southern grid.",
        is_active: true,
      },
      {
        id: 102,
        region: "default",
        alert_type: "surplus",
        severity: "warning",
        start_time: new Date(startMs + 36 * 3600 * 1000).toISOString(),
        end_time: new Date(startMs + 40 * 3600 * 1000).toISOString(),
        peak_magnitude_mw: 168.0,
        avg_magnitude_mw: 124.0,
        message: "Midday solar surplus: Peak GHI forecast across Rajasthan & Gujarat exceeds regional base transmission limit.",
        is_active: true,
      },
      {
        id: 103,
        region: "default",
        alert_type: "deficit",
        severity: "watch",
        start_time: new Date(startMs + 66 * 3600 * 1000).toISOString(),
        end_time: new Date(startMs + 70 * 3600 * 1000).toISOString(),
        peak_magnitude_mw: -88.0,
        avg_magnitude_mw: -62.0,
        message: "Wind speed lull expected in Tirunelveli cluster (Tamil Nadu). Monitoring reserve margins.",
        is_active: true,
      },
    ],
    upcoming_critical_periods: hourly_balance.filter((h) => h.severity === "critical" || h.severity === "warning").slice(0, 8),
    recommendations: [
      {
        id: 201,
        alert_id: 101,
        action: "discharge_storage",
        priority: 1,
        description: "Generation deficit of 342.0 MW expected at 19:00–22:00. Discharge Southern Grid Battery Storage (SOC: 70% → 15%) at max 100 MW rate for 1.2 hours to smooth peak steepness.",
        estimated_impact_mw: 100.0,
        is_feasible: true,
        site: "Southern Grid BESS",
        window: "Today 19:00 – 22:00",
      },
      {
        id: 202,
        alert_id: 101,
        action: "prepare_backup",
        priority: 2,
        description: "After maximum 100 MW battery discharge, 242.0 MW deficit remains. Stage fast-ramping hydro peakers and initiate inter-regional corridor power transfer.",
        estimated_impact_mw: 242.0,
        is_feasible: true,
        site: "Regional Interconnect",
        window: "Today 18:30 – 22:00",
      },
      {
        id: 203,
        alert_id: 102,
        action: "charge_storage",
        priority: 1,
        description: "Renewable solar surplus of 168.0 MW anticipated tomorrow midday. Charge Southern Grid Battery Storage at 80 MW max charge rate to absorb 50 MWh headroom.",
        estimated_impact_mw: 80.0,
        is_feasible: true,
        site: "Gujarat Solar Park B",
        window: "Tomorrow 12:00 – 15:00",
      },
      {
        id: 204,
        alert_id: 102,
        action: "consider_curtailment",
        priority: 2,
        description: "88 MW remaining surplus after full battery charging saturation. Consider dynamic inverter power limiting if export corridors reach thermal limits.",
        estimated_impact_mw: 88.0,
        is_feasible: true,
        site: "Rajasthan Solar Farm A",
        window: "Tomorrow 13:00 – 15:00",
      },
    ],
    model_version: "xgboost_v1.2_prod",
    data_source_note: "Renewable generation telemetry paired with Open-Meteo live atmospheric data & XGBoost ML forecasting.",
  };
}

export function buildForecastFromBalance(summary: DashboardSummary, hours = 72): ForecastPoint[] {
  const points: ForecastPoint[] = [];
  const slice = summary.hourly_balance.slice(0, hours);

  slice.forEach((item) => {
    const t = new Date(item.timestamp);
    const hourOfDay = t.getHours();

    let solarRatio = 0;
    if (hourOfDay >= 6 && hourOfDay <= 18) {
      const sunH = Math.sin(((hourOfDay - 6) / 12) * Math.PI);
      solarRatio = 0.55 * sunH;
    }
    const solarMW = Math.round(item.total_generation_mw * solarRatio);
    const windMW = Math.max(0, item.total_generation_mw - solarMW);

    const band = Math.round(item.total_generation_mw * 0.08) + 6;

    points.push({
      hour: t.toLocaleString("en-IN", { weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false }),
      timestamp: t.getTime(),
      isoTime: item.timestamp,
      solarMW,
      windMW,
      totalGenMW: item.total_generation_mw,
      demandMW: item.demand_mw,
      netMW: item.net_balance_mw,
      severity: item.severity,
      confidenceLowMW: Math.max(0, item.total_generation_mw - band),
      confidenceHighMW: item.total_generation_mw + band,
    });
  });

  return points;
}

export const defaultWeatherProviders: WeatherProvider[] = [
  {
    name: "Open-Meteo API",
    role: "High-Resolution 72h Forecasting (GHI, Wind Speed, Temp)",
    status: "active",
    requires_key: false,
  },
  {
    name: "OpenWeatherMap",
    role: "Live Current Atmospheric Conditions & Telemetry",
    status: "active",
    requires_key: true,
  },
  {
    name: "Visual Crossing",
    role: "Historical Hourly Dataset & Deep Re-analysis",
    status: "active",
    requires_key: true,
  },
];

export const defaultHealth: BackendHealth = {
  status: "ok",
  version: "1.0.0",
  models: {
    solar: { loaded: true },
    wind: { loaded: true },
  },
};
