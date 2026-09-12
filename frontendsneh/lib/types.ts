export type PlantType = "solar" | "wind";
export type AlertSeverity = "normal" | "watch" | "warning" | "critical";
export type AlertType = "surplus" | "deficit" | "outage_risk";
export type RecommendationAction =
  | "charge_storage"
  | "discharge_storage"
  | "prepare_backup"
  | "consider_curtailment"
  | "monitor";

export interface PlantStatusSummary {
  plant_id: number;
  plant_name: string;
  plant_type: PlantType;
  capacity_mw: number;
  latitude?: number;
  longitude?: number;
  location_name?: string;
  panel_efficiency?: number;
  turbine_cut_in_speed?: number;
  turbine_rated_speed?: number;
  turbine_cut_out_speed?: number;
  latest_forecast_mw?: number | null;
  status: string;
  deviation_flag: boolean;
  is_custom?: boolean;
}

export interface HourlyBalance {
  timestamp: string;
  total_generation_mw: number;
  demand_mw: number;
  net_balance_mw: number;
  severity: AlertSeverity;
  alert_type?: string;
}

export interface BatterySummary {
  battery_id: number;
  battery_name: string;
  capacity_mwh: number;
  current_soc_pct: number;
  available_discharge_mwh: number;
  available_charge_mwh: number;
  max_discharge_rate_mw: number;
  max_charge_rate_mw: number;
}

export interface AlertResponse {
  id: number;
  region: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  start_time: string;
  end_time: string;
  peak_magnitude_mw: number;
  avg_magnitude_mw: number;
  message: string;
  is_active: boolean;
  is_acknowledged?: boolean;
  created_at?: string;
}

export interface RecommendationResponse {
  id: number;
  alert_id?: number;
  action: RecommendationAction;
  priority: number;
  description: string;
  estimated_impact_mw?: number | null;
  is_feasible: boolean;
  created_at?: string;
  site?: string;
  window?: string;
}

export interface DashboardSummary {
  generated_at: string;
  region: string;
  forecast_horizon_hours: number;
  total_forecast_mw_next_hour: number;
  total_demand_mw_next_hour: number;
  net_balance_mw_next_hour: number;
  overall_severity: AlertSeverity;
  plants: PlantStatusSummary[];
  hourly_balance: HourlyBalance[];
  battery?: BatterySummary | null;
  active_alerts: AlertResponse[];
  upcoming_critical_periods: HourlyBalance[];
  recommendations?: RecommendationResponse[];
  data_source_note?: string;
  model_version?: string | null;
}

export interface ForecastPoint {
  hour: string;
  timestamp: number;
  isoTime: string;
  solarMW: number;
  windMW: number;
  totalGenMW: number;
  demandMW: number;
  netMW: number;
  severity: AlertSeverity;
  confidenceLowMW: number;
  confidenceHighMW: number;
}

export interface WeatherProvider {
  name: string;
  role: string;
  status: string;
  requires_key: boolean;
}

export interface BackendHealth {
  status: string;
  version?: string;
  models?: {
    solar?: { loaded: boolean; error?: string };
    wind?: { loaded: boolean; error?: string };
  };
}

export interface LiveWeatherTelemetry {
  timestamp: string;
  temperature_c: number;
  humidity_pct: number;
  cloud_cover_pct: number;
  solar_irradiance_wm2: number;
  wind_speed_ms: number;
  wind_direction_deg: number;
  pressure_hpa: number;
  rainfall_mm: number;
}

export interface PlantRegistrationInput {
  name: string;
  plant_type: PlantType;
  capacity_mw: number;
  latitude: number;
  longitude: number;
  location_name: string;
  panel_efficiency?: number;
  turbine_cut_in_speed?: number;
  turbine_rated_speed?: number;
  turbine_cut_out_speed?: number;
}

export interface PlantForecastResult {
  plant: PlantStatusSummary;
  currentWeather: LiveWeatherTelemetry;
  hourlyPoints: Array<{
    hour: string;
    timestamp: number;
    predicted_mw: number;
    solar_ghi?: number;
    wind_speed?: number;
    utilization_pct: number;
    upper_bound_mw: number;
    lower_bound_mw: number;
  }>;
  summaryStats: {
    peak_mw: number;
    avg_mw: number;
    capacity_factor_pct: number;
    est_daily_mwh: number;
  };
}
