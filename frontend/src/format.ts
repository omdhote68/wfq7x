const TZ = "Europe/London";

export function fmtNum(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtSigned(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v > 0 ? "+" : ""}${fmtNum(v, digits)}`;
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  return v === null || v === undefined ? "—" : `${fmtNum(v, digits)}%`;
}

/** MWh -> GWh text for headline cards (1 GWh = 1,000 MWh). */
export function fmtGwh(mwh: number | null | undefined): string {
  return mwh === null || mwh === undefined ? "—" : fmtNum(mwh / 1000, 1);
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-GB", {
    timeZone: TZ, day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

export function fmtDay(iso: string): string {
  const d = new Date(iso.length <= 10 ? `${iso}T12:00:00Z` : iso);
  return d.toLocaleDateString("en-GB", { timeZone: TZ, day: "2-digit", month: "short" });
}

export function errorLabel(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return "";
  return v > 0 ? "over-forecast" : "under-forecast";
}
