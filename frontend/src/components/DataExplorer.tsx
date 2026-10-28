import { useEffect, useState } from "react";
import { buildUrl, filterParams } from "../api";
import { fmtDateTime, fmtNum, fmtPct, fmtSigned } from "../format";
import type { Filters, MatchedPage, Quality } from "../types";
import { useFetch } from "../useFetch";
import { Empty, ErrorBox, Loading, Section } from "./States";

const QUALITY_LABEL: Record<Quality, string> = {
  ok: "Matched",
  missing_actual: "No actual",
  missing_forecast: "No eligible forecast",
  missing_both: "No data",
};

export function DataExplorer({ filters }: { filters: Filters }) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(48);
  const [quality, setQuality] = useState("");
  const [direction, setDirection] = useState("");
  const [search, setSearch] = useState("");
  const [minAbs, setMinAbs] = useState("");
  const [sort, setSort] = useState("asc");

  useEffect(() => setPage(1), [filters, pageSize, quality, direction, search, minAbs, sort]);

  const common = { ...filterParams(filters), quality, direction, search, min_abs_error: minAbs, };
  const url = buildUrl("/api/matched", { ...common, page, page_size: pageSize, sort });
  const csv = buildUrl("/api/matched/export.csv", common);
  const { data, loading, error, reload } = useFetch<MatchedPage>(url);
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <Section
      title="Data explorer"
      subtitle="Half-hourly matched observations. Error = forecast − actual (MW). % error shown only where actual ≥ the MAPE threshold."
      right={<a className="btn" href={csv} download>Export filtered CSV</a>}
    >
      <div className="mb-3 grid grid-cols-2 gap-3 md:grid-cols-5">
        <div><label className="label" htmlFor="ex-q">Data quality</label>
          <select id="ex-q" className="input w-full" value={quality} onChange={(e) => setQuality(e.target.value)}>
            <option value="">All</option>
            {(Object.keys(QUALITY_LABEL) as Quality[]).map((q) => <option key={q} value={q}>{QUALITY_LABEL[q]}</option>)}
          </select></div>
        <div><label className="label" htmlFor="ex-d">Error direction</label>
          <select id="ex-d" className="input w-full" value={direction} onChange={(e) => setDirection(e.target.value)}>
            <option value="">All</option><option value="over">Over-forecast</option><option value="under">Under-forecast</option>
          </select></div>
        <div><label className="label" htmlFor="ex-m">Min |error| (MW)</label>
          <input id="ex-m" type="number" min={0} className="input w-full" value={minAbs} onChange={(e) => setMinAbs(e.target.value)} /></div>
        <div><label className="label" htmlFor="ex-s">Search date/time</label>
          <input id="ex-s" placeholder="e.g. 2026-01-14 or 18:30" className="input w-full" value={search} onChange={(e) => setSearch(e.target.value)} maxLength={32} /></div>
        <div><label className="label" htmlFor="ex-o">Order</label>
          <select id="ex-o" className="input w-full" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="asc">Oldest first</option><option value="desc">Newest first</option>
          </select></div>
      </div>

      {loading && <Loading label="Loading rows…" />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {!loading && !error && data && data.items.length === 0 && <Empty>No rows match these filters.</Empty>}
      {!loading && !error && data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm" data-testid="explorer-table">
              <thead className="text-xs uppercase text-slate-600">
                <tr>
                  <th className="py-1 pr-3">Delivery (UK)</th><th className="pr-3 text-right">Actual (MW)</th><th className="pr-3 text-right">Forecast (MW)</th>
                  <th className="pr-3">Forecast published (UK)</th><th className="pr-3 text-right">Error (MW)</th><th className="pr-3 text-right">|Error| (MW)</th>
                  <th className="pr-3 text-right">% error</th><th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.start_time} className="border-t border-slate-100">
                    <td className="py-1 pr-3 whitespace-nowrap">{fmtDateTime(r.start_time)}</td>
                    <td className="pr-3 text-right">{fmtNum(r.actual_mw)}</td>
                    <td className="pr-3 text-right">{fmtNum(r.forecast_mw)}</td>
                    <td className="pr-3 whitespace-nowrap">{fmtDateTime(r.publish_time)}</td>
                    <td className={`pr-3 text-right ${r.error_mw !== null && r.error_mw > 0 ? "text-amber-700" : "text-sky-700"}`}>{fmtSigned(r.error_mw)}</td>
                    <td className="pr-3 text-right">{fmtNum(r.abs_error_mw)}</td>
                    <td className="pr-3 text-right">{r.pct_error === null ? "n/a" : fmtPct(r.pct_error)}</td>
                    <td><span className={`rounded px-1.5 py-0.5 text-xs ${r.quality === "ok" ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"}`}>{QUALITY_LABEL[r.quality]}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
            <span>{fmtNum(data.total)} rows · page {page} of {pages}</span>
            <div className="flex items-center gap-2">
              <label className="sr-only" htmlFor="ex-ps">Rows per page</label>
              <select id="ex-ps" className="input" value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
                {[24, 48, 100, 250].map((n) => <option key={n} value={n}>{n} / page</option>)}
              </select>
              <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <button className="btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          </div>
        </>
      )}
    </Section>
  );
}
