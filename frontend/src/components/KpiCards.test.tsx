import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KpiCards, buildKpis } from "./KpiCards";
import type { Metrics } from "../types";

const M: Metrics = {
  data_source: "sample", cutoff_used: "09:00 Europe/London on the day before delivery",
  intervals_expected: 1488, intervals_matched: 1400, coverage_pct: 94.1,
  actual_energy_mwh: 3_000_000, forecast_energy_mwh: 3_100_000,
  matched_actual_energy_mwh: 2_900_000, matched_forecast_energy_mwh: 3_000_000,
  mae_mw: 812.4, rmse_mw: 1043.2, mape_pct: 9.87, mape_n: 1390, mape_excluded: 10, mape_min_actual_mw: 100,
  bias_mw: 120.5, bias_pct_of_actual: 1.4, over_pct: 55, under_pct: 45, mean_over_mw: 700, mean_under_mw: -650,
  p90_abs_error_mw: 1900, sample_adequate: true, sample_note: null,
};

describe("KpiCards", () => {
  it("renders all seven KPIs with units", () => {
    render(<KpiCards metrics={M} />);
    expect(screen.getAllByTestId(/^kpi-(actual|forecast|mae|rmse|mape|bias|coverage)$/)).toHaveLength(7);
    expect(screen.getByTestId("kpi-actual")).toHaveTextContent("3,000.0");
    expect(screen.getByTestId("kpi-actual")).toHaveTextContent("GWh");
    expect(screen.getByTestId("kpi-mae")).toHaveTextContent(/812\s*MW/);
    expect(screen.getByTestId("kpi-bias")).toHaveTextContent(/\+121\s*MW/);
    expect(screen.getByTestId("kpi-mape")).toHaveTextContent("9.9%");
    expect(screen.getByText(/^Error = forecast − actual/)).toBeInTheDocument();
  });
  it("shows a warning when the sample is small", () => {
    render(<KpiCards metrics={{ ...M, sample_adequate: false, sample_note: "Only 10 matched intervals" }} />);
    expect(screen.getByRole("note")).toHaveTextContent("Only 10 matched intervals");
  });
  it("renders dashes for missing metrics", () => {
    const k = buildKpis({ ...M, mae_mw: null, mape_pct: null });
    expect(k.find((x) => x.id === "mae")?.value).toBe("—");
    expect(k.find((x) => x.id === "mape")?.value).toBe("—");
  });
});
