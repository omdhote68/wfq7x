import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { buildUrl } from "../api";
import { fmtDateTime, fmtNum, fmtSigned } from "../format";
import type { Filters, Meta, Revisions } from "../types";
import { useFetch } from "../useFetch";
import { Empty, ErrorBox, Loading, Section } from "./States";

type Row = Record<string, number | string | null>;

export function mergeRevisions(r: Revisions): Row[] {
  const rows = new Map<string, Row>();
  const get = (t: string): Row => {
    let row = rows.get(t);
    if (!row) rows.set(t, (row = { t }));
    return row;
  };
  r.actual.forEach((a) => (get(a.t).actual = a.actual_mw));
  r.vintages.forEach((v, i) => v.points.forEach((p) => (get(p.t)[`v${i}`] = p.forecast_mw)));
  return [...rows.values()].sort((a, b) => String(a.t).localeCompare(String(b.t)));
}

export function vintageStyle(v: { is_day_ahead_vintage: boolean; after_cutoff: boolean }) {
  if (v.is_day_ahead_vintage) return { stroke: "#0d9488", width: 3, dash: undefined, tag: "Day-ahead decision vintage" };
  if (v.after_cutoff) return { stroke: "#94a3b8", width: 1.25, dash: "5 4", tag: "After cutoff (not usable for the decision)" };
  return { stroke: "#7dd3c8", width: 1.25, dash: undefined, tag: "Earlier vintage" };
}

export function RevisionsPanel({ filters, meta }: { filters: Filters; meta: Meta }) {
  const [day, setDay] = useState<string>(filters.start);
  const url = day >= meta.period_start && day <= meta.period_end
    ? buildUrl("/api/revisions", { delivery_date: day, cutoff_hour: filters.cutoffHour, cutoff_minute: filters.cutoffMinute, max_vintages: 8 })
    : null;
  const { data, loading, error, reload } = useFetch<Revisions>(url);
  const rows = useMemo(() => (data ? mergeRevisions(data) : []), [data]);

  return (
    <Section
      title="Forecast revisions for a delivery day"
      subtitle="How successive WINDFOR publications changed their view of the same day, compared with what was actually generated (MW)."
      right={
        <div>
          <label className="label" htmlFor="rev-day">Delivery date</label>
          <input id="rev-day" type="date" className="input" min={meta.period_start} max={meta.period_end} value={day} onChange={(e) => setDay(e.target.value)} />
        </div>
      }
    >
      {url === null && <Empty>Pick a delivery date between {meta.period_start} and {meta.period_end}.</Empty>}
      {loading && <Loading label="Loading forecast vintages…" />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && !loading && !error && data.vintages.length === 0 && <Empty>No forecast vintages were published for this delivery date.</Empty>}
      {data && !loading && !error && data.vintages.length > 0 && (
        <>
          <p className="mb-2 text-sm text-slate-700">
            Cutoff for this day: <strong>{fmtDateTime(data.cutoff)}</strong> (UK time). Thick teal line = latest vintage published on or before the cutoff;
            dashed grey = published after the cutoff and therefore not available when buying.
          </p>
          <div className="h-80" data-testid="rev-chart"><ResponsiveContainer>
            <LineChart data={rows} margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="t" fontSize={12} stroke="#475569" tickFormatter={(v: string) => fmtDateTime(v).slice(-5)} minTickGap={30} />
              <YAxis fontSize={12} stroke="#475569" label={{ value: "MW", angle: -90, position: "insideLeft", fill: "#475569" }} />
              <Tooltip labelFormatter={(v: string) => `${fmtDateTime(v)} (UK time)`} formatter={(v: number) => `${fmtNum(v)} MW`} />
              <Legend />
              <Line dataKey="actual" name="Actual (MW)" stroke="#0f172a" strokeWidth={2} dot={false} isAnimationActive={false} />
              {data.vintages.map((v, i) => {
                const s = vintageStyle(v);
                return <Line key={v.publish_time} dataKey={`v${i}`} name={`Pub ${fmtDateTime(v.publish_time)}`} stroke={s.stroke} strokeWidth={s.width} strokeDasharray={s.dash} dot={false} isAnimationActive={false} />;
              })}
            </LineChart>
          </ResponsiveContainer></div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm" data-testid="vintage-table">
              <thead className="text-xs uppercase text-slate-600">
                <tr><th className="py-1 pr-3">Published (UK)</th><th className="pr-3">Status</th><th className="pr-3 text-right">MAE (MW)</th><th className="pr-3 text-right">Bias (MW)</th><th className="text-right">Intervals</th></tr>
              </thead>
              <tbody>
                {data.vintages.map((v) => (
                  <tr key={v.publish_time} className={`border-t border-slate-100 ${v.is_day_ahead_vintage ? "bg-teal-50 font-medium" : ""}`}>
                    <td className="py-1 pr-3">{fmtDateTime(v.publish_time)}</td>
                    <td className="pr-3">{vintageStyle(v).tag}</td>
                    <td className="pr-3 text-right">{fmtNum(v.mae_mw)}</td>
                    <td className="pr-3 text-right">{fmtSigned(v.bias_mw)}</td>
                    <td className="text-right">{v.n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-slate-600">Up to 8 vintages are shown (evenly spaced, always including the decision vintage). Error = forecast − actual.</p>
        </>
      )}
    </Section>
  );
}
