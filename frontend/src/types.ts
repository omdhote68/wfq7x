export type Quality = "ok" | "missing_actual" | "missing_forecast" | "missing_both";

export interface Meta {
  data_source: "real" | "sample" | "none";
  data_note: string;
  period_start: string;
  period_end: string;
  cutoff_hour: number;
  cutoff_minute: number;
  cutoff_tz: string;
  cutoff_rule: string;
  error_convention: string;
  mape_min_actual_mw: number;
  attribution: string;
}

export interface Metrics {
  data_source: string;
  cutoff_used: string;
  intervals_expected: number;
  intervals_matched: number;
  coverage_pct: number | null;
  actual_energy_mwh: number | null;
  forecast_energy_mwh: number | null;
  matched_actual_energy_mwh: number | null;
  matched_forecast_energy_mwh: number | null;
  mae_mw: number | null;
  rmse_mw: number | null;
  mape_pct: number | null;
  mape_n: number;
  mape_excluded: number;
  mape_min_actual_mw: number;
  bias_mw: number | null;
  bias_pct_of_actual: number | null;
  over_pct: number | null;
  under_pct: number | null;
  mean_over_mw: number | null;
  mean_under_mw: number | null;
  p90_abs_error_mw: number | null;
  sample_adequate: boolean;
  sample_note: string | null;
}

export interface TSPoint {
  t: string;
  actual_mw: number | null;
  forecast_mw: number | null;
  error_mw: number | null;
  publish_time: string | null;
  n: number;
}
export interface TimeSeries {
  data_source: string;
  granularity: Granularity;
  unit: string;
  points: TSPoint[];
}
export type Granularity = "half_hour" | "day" | "week";

export interface TrendRow {
  period?: string;
  hour?: number;
  n: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  mape_pct: number | null;
  actual_mean_mw: number | null;
  forecast_mean_mw: number | null;
}
export interface Accuracy {
  data_source: string;
  daily: TrendRow[];
  weekly: TrendRow[];
  by_hour: TrendRow[];
  distribution: { bin_start_mw: number; bin_end_mw: number; count: number }[];
}

export interface MatchedRow {
  start_time: string;
  actual_mw: number | null;
  forecast_mw: number | null;
  publish_time: string | null;
  cutoff: string | null;
  horizon_h: number | null;
  error_mw: number | null;
  abs_error_mw: number | null;
  pct_error: number | null;
  quality: Quality;
}
export interface MatchedPage {
  total: number;
  page: number;
  page_size: number;
  data_source: string;
  items: MatchedRow[];
}

export interface Vintage {
  publish_time: string;
  is_day_ahead_vintage: boolean;
  after_cutoff: boolean;
  mae_mw: number | null;
  bias_mw: number | null;
  n: number;
  points: { t: string; forecast_mw: number; horizon_h?: number }[];
}
export interface Revisions {
  data_source: string;
  delivery_date: string;
  cutoff: string;
  mode: "day" | "interval";
  actual: { t: string; actual_mw: number }[];
  vintages: Vintage[];
}

export interface Filters {
  start: string;
  end: string;
  cutoffHour: number;
  cutoffMinute: number;
}
