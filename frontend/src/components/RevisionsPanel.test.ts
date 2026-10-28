import { describe, expect, it } from "vitest";
import { mergeRevisions, vintageStyle } from "./RevisionsPanel";
import type { Revisions } from "../types";

const R: Revisions = {
  data_source: "sample", delivery_date: "2026-01-10", cutoff: "2026-01-09T09:00:00Z", mode: "day",
  actual: [{ t: "2026-01-10T00:00:00Z", actual_mw: 100 }, { t: "2026-01-10T00:30:00Z", actual_mw: 110 }],
  vintages: [
    { publish_time: "2026-01-09T09:00:00Z", is_day_ahead_vintage: true, after_cutoff: false, mae_mw: 5, bias_mw: 1, n: 2,
      points: [{ t: "2026-01-10T00:00:00Z", forecast_mw: 105 }] },
    { publish_time: "2026-01-09T12:00:00Z", is_day_ahead_vintage: false, after_cutoff: true, mae_mw: 2, bias_mw: 0, n: 2,
      points: [{ t: "2026-01-10T00:30:00Z", forecast_mw: 111 }] },
  ],
};

describe("revisions", () => {
  it("merges actuals and vintages by timestamp", () => {
    const rows = mergeRevisions(R);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ actual: 100, v0: 105 });
    expect(rows[1]).toMatchObject({ actual: 110, v1: 111 });
  });
  it("distinguishes decision vintage from post-cutoff updates", () => {
    expect(vintageStyle(R.vintages[0]).tag).toMatch(/decision/);
    expect(vintageStyle(R.vintages[1]).tag).toMatch(/After cutoff/);
    expect(vintageStyle(R.vintages[1]).dash).toBeDefined();
  });
});
