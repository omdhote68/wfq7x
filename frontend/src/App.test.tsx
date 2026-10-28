import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const META = {
  data_source: "sample", data_note: "SYNTHETIC", period_start: "2026-01-01", period_end: "2026-01-31",
  cutoff_hour: 9, cutoff_minute: 0, cutoff_tz: "Europe/London", cutoff_rule: "ASSUMPTION rule",
  error_convention: "forecast error = forecast - actual (MW)", mape_min_actual_mw: 100, attribution: "Contains BMRS data © Elexon Limited",
};

function mockFetch(handler: (url: string) => { ok: boolean; status?: number; body: unknown }) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const r = handler(url);
    return { ok: r.ok, status: r.status ?? 200, json: async () => r.body } as Response;
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("App states", () => {
  it("shows a loading indicator first", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent(/Connecting/);
  });

  it("shows a recoverable error when the API is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("network"); }));
    render(<App />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/Cannot reach the analytics API/));
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("shows the synthetic-data banner and filters when meta loads", async () => {
    mockFetch((url) => url.includes("/api/meta") ? { ok: true, body: META }
      : { ok: false, status: 400, body: { detail: "Date range must lie within 2026-01-01 to 2026-01-31" } });
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("sample-banner")).toHaveTextContent(/SYNTHETIC DEMO DATA/));
    expect(screen.getByLabelText("Delivery from")).toHaveValue("2026-01-01");
    await waitFor(() => expect(screen.getAllByRole("alert").some((a) => /Date range must lie within/.test(a.textContent ?? ""))).toBe(true));
  });
});
