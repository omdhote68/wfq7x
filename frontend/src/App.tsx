import { useMemo, useState } from "react";
import { AccuracyPanel } from "./components/AccuracyPanel";
import { DataExplorer } from "./components/DataExplorer";
import { KpiCards } from "./components/KpiCards";
import { Methodology } from "./components/Methodology";
import { RevisionsPanel } from "./components/RevisionsPanel";
import { ErrorBox, Loading } from "./components/States";
import { TimeSeriesChart } from "./components/TimeSeriesChart";
import { buildUrl, filterParams } from "./api";
import type { Filters, Meta, Metrics } from "./types";
import { useFetch } from "./useFetch";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "accuracy", label: "Forecast accuracy" },
  { id: "revisions", label: "Revisions" },
  { id: "explorer", label: "Data explorer" },
  { id: "method", label: "Methodology" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function App() {
  const meta = useFetch<Meta>(buildUrl("/api/meta"));
  const [tab, setTab] = useState<Tab>("overview");
  const [menu, setMenu] = useState(false);
  const [draft, setDraft] = useState<Filters | null>(null);
  const [applied, setApplied] = useState<Filters | null>(null);

  const m = meta.data;
  const filters = useMemo<Filters | null>(() => {
    if (applied) return applied;
    if (!m) return null;
    return { start: m.period_start, end: m.period_end, cutoffHour: m.cutoff_hour, cutoffMinute: m.cutoff_minute };
  }, [applied, m]);
  const form = draft ?? filters;

  const metrics = useFetch<Metrics>(filters ? buildUrl("/api/metrics", filterParams(filters)) : null);
  const invalid = !!form && (form.start > form.end || (m ? form.start < m.period_start || form.end > m.period_end : false));

  return (
    <div className="min-h-screen">
      <header className="bg-slate-900 text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div>
            <p className="text-lg font-semibold tracking-tight">Wind Forecast Desk</p>
            <p className="text-xs text-slate-300">Day-ahead procurement analytics · GB national wind</p>
          </div>
          <button className="btn md:hidden" aria-expanded={menu} aria-controls="nav" onClick={() => setMenu(!menu)}>Menu</button>
        </div>
        <nav id="nav" aria-label="Sections" className={`mx-auto max-w-7xl px-4 pb-2 ${menu ? "block" : "hidden"} md:block`}>
          <ul className="flex flex-col gap-1 md:flex-row">
            {TABS.map((t) => (
              <li key={t.id}>
                <button
                  aria-current={tab === t.id ? "page" : undefined}
                  className={`w-full rounded-md px-3 py-1.5 text-left text-sm ${tab === t.id ? "bg-teal-600 text-white" : "text-slate-200 hover:bg-slate-800"}`}
                  onClick={() => { setTab(t.id); setMenu(false); }}
                >{t.label}</button>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      {m?.data_source === "sample" && (
        <div role="alert" className="bg-amber-100 px-4 py-2 text-center text-sm font-medium text-amber-950" data-testid="sample-banner">
          SYNTHETIC DEMO DATA — not Elexon data. Figures below are for UI development only and must not be used for decisions.
        </div>
      )}

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-6">
        {meta.loading && <Loading label="Connecting to analytics API…" />}
        {meta.error && <ErrorBox message={meta.error} onRetry={meta.reload} />}

        {m && form && filters && (
          <>
            {tab !== "method" && (
              <form className="card flex flex-wrap items-end gap-3" aria-label="Filters"
                onSubmit={(e) => { e.preventDefault(); if (!invalid) { setApplied(form); setDraft(null); } }}>
                <div><label className="label" htmlFor="f-start">Delivery from</label>
                  <input id="f-start" type="date" className="input" min={m.period_start} max={m.period_end} value={form.start} onChange={(e) => setDraft({ ...form, start: e.target.value })} /></div>
                <div><label className="label" htmlFor="f-end">Delivery to</label>
                  <input id="f-end" type="date" className="input" min={m.period_start} max={m.period_end} value={form.end} onChange={(e) => setDraft({ ...form, end: e.target.value })} /></div>
                <div><label className="label" htmlFor="f-cut">Cutoff (D−1, {m.cutoff_tz})</label>
                  <input id="f-cut" type="time" className="input" value={`${String(form.cutoffHour).padStart(2, "0")}:${String(form.cutoffMinute).padStart(2, "0")}`}
                    onChange={(e) => { const [h, mi] = e.target.value.split(":").map(Number); if (!Number.isNaN(h) && !Number.isNaN(mi)) setDraft({ ...form, cutoffHour: h, cutoffMinute: mi }); }} /></div>
                <button className="btn btn-active" type="submit" disabled={invalid}>Apply</button>
                <button className="btn" type="button" onClick={() => { setApplied(null); setDraft(null); }}>Reset</button>
                {invalid && <p role="alert" className="w-full text-sm text-red-700">Start must be on or before end, and both within {m.period_start} to {m.period_end}.</p>}
                <p className="w-full text-xs text-slate-600">{m.cutoff_rule}</p>
              </form>
            )}

            {tab === "overview" && (
              <>
                {metrics.loading && <Loading label="Calculating metrics…" />}
                {metrics.error && <ErrorBox message={metrics.error} onRetry={metrics.reload} />}
                {metrics.data && !metrics.loading && <KpiCards metrics={metrics.data} />}
                <TimeSeriesChart filters={filters} />
              </>
            )}
            {tab === "accuracy" && <AccuracyPanel filters={filters} metrics={metrics.data} />}
            {tab === "revisions" && <RevisionsPanel filters={filters} meta={m} />}
            {tab === "explorer" && <DataExplorer filters={filters} />}
            {tab === "method" && <Methodology meta={m} />}
          </>
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-slate-600">
        {m?.attribution ?? "Contains BMRS data © Elexon Limited."} Developed with AI assistance. Not investment or trading advice.
      </footer>
    </div>
  );
}
