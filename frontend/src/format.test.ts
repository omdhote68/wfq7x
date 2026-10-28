import { describe, expect, it } from "vitest";
import { errorLabel, fmtGwh, fmtNum, fmtPct, fmtSigned } from "./format";
import { buildUrl } from "./api";

describe("format", () => {
  it("formats numbers and nulls", () => {
    expect(fmtNum(1234.5, 0)).toBe("1,235");
    expect(fmtNum(null)).toBe("—");
    expect(fmtPct(12.345, 1)).toBe("12.3%");
    expect(fmtPct(null)).toBe("—");
  });
  it("signs errors", () => {
    expect(fmtSigned(50)).toBe("+50");
    expect(fmtSigned(-50)).toBe("-50");
    expect(errorLabel(10)).toBe("over-forecast");
    expect(errorLabel(-10)).toBe("under-forecast");
    expect(errorLabel(0)).toBe("");
  });
  it("converts MWh to GWh", () => {
    expect(fmtGwh(2_500_000)).toBe("2,500.0");
  });
});

describe("buildUrl", () => {
  it("skips empty params", () => {
    expect(buildUrl("/api/x", { a: 1, b: "", c: undefined, d: "z" })).toBe("/api/x?a=1&d=z");
  });
});
