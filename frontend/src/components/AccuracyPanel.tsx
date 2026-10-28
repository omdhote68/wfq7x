import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { buildUrl, filterParams } from "../api";
import { fmtDay, fmtNum, fmtPct, fmtSigned } from "../format";
import type { Accuracy, Filters, Metrics } from "../types";
import { useFetch } from "../useFetch";
import { Empty, ErrorBox, Loading, Section } from "./States";

export function AccuracyPanel({ filters, metrics }: { filters: Filters; metrics: Metrics | null }) {
  const { data, loading, error, reload } = useFetch<Accuracy>(buildUrl("/api/accuracy", filterParams(filters)));

  if (loading) return <Loading label="Computing accuracy…" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data || data.daily.length === 0) return <Empty>No accuracy data in the selected range.</Empty>;

  const daily = data.daily.map((r) => ({ ...r, label: fmtDay(r.period ?? "") }));
  const weekly = data.weekly.map((r) => ({ ...r, label: `w/c ${fmtDay(r.period ?? "")}` }));
  const dist = data.distribution.map((b) => ({ ...b, label: `${fmtNum(b.bin_start_mw)}` }));
  const hours = data.by_hour.map((r) => ({ ...r, label: `${String(r.hour).padStart(2, "0")}:00` }));

  return (
    <div className="space-y-4">
      <p className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
        <strong>Sign convention:</strong> error = forecast − actual (MW). Above zero = over-forecast (risk of under-buying); below zero = under-forecast (risk of over-buying).
      </p>

      {metrics && (
        <Section title="Over- vs under-forecasting" subtitle="Share of matched half-hours and mean size of each miss">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid="over-under">
            <div className="card"><p className="label">Over-forecast</p><p className="text-xl font-semibold">{fmtPct(metrics.over_pct)}</p><p className="text-xs text-slate-600">mean {fmtSigned(metrics.mean_over_mw)} MW</p></div>
            <div className="card"><p className="label">Under-forecast</p><p className="text-xl font-semibold">{fmtPct(metrics.under_pct)}</p><p className="text-xs text-slate-600">mean {fmtSigned(metrics.mean_under_mw)} MW</p></div>
            <div className="card"><p className="label">90th pct absolute error</p><p className="text-xl font-semibold">{fmtNum(metrics.p90_abs_error_mw)} MW</p><p className="text-xs text-slate-600">9 in 10 intervals miss by less than this</p></div>
          </div>
          {metrics.sample_note && <p className="mt-2 text-sm text-amber-900">{metrics.sample_note}</p>}
        </Section>
      )}

      <Section title="Daily accuracy" subtitle="MAE and bias per delivery day (MW)">
        <div className="h-64"><ResponsiveContainer>
          <LineChart data={daily} margin={{ left: 8, right: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="label" fontSize={12} stroke="#475569" minTickGap={20} />
            <YAxis fontSize={12} stroke="#475569" label={{ value: "MW", angle: -90, position: "insideLeft", fill: "#475569" }} />
            <Tooltip formatter={(v: number) => `${fmtNum(v)} MW`} />
            <Legend />
            <ReferenceLine y={0} stroke="#94a3b8" />
            <Line dataKey="mae_mw" name="MAE (MW)" stroke="#0d9488" dot={false} isAnimationActive={false} />
            <Line dataKey="rmse_mw" name="RMSE (MW)" stroke="#0f172a" dot={false} isAnimationActive={false} />
            <Line dataKey="bias_mw" name="Bias (MW)" stroke="#d97706" dot={false} strokeDasharray="4 3" isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer></div>
      </Section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Error distribution" subtitle="Count of half-hours by error bin (MW, forecast − actual)">
          <div className="h-64"><ResponsiveContainer>
            <BarChart data={dist} margin={{ left: 8, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" fontSize={11} stroke="#475569" minTickGap={16} label={{ value: "bin start (MW)", position: "insideBottom", offset: -2, fill: "#475569", fontSize: 11 }} />
              <YAxis fontSize={12} stroke="#475569" />
              <Tooltip formatter={(v: number) => `${v} intervals`} labelFormatter={(l: string) => `Bin from ${l} MW`} />
              <Bar dataKey="count" name="Intervals" fill="#0d9488" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer></div>
        </Section>
        <Section title="Weekly comparison" subtitle="MAE and bias by week (MW)">
          <div className="h-64"><ResponsiveContainer>
            <BarChart data={weekly} margin={{ left: 8, right: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" fontSize={11} stroke="#475569" />
              <YAxis fontSize={12} stroke="#475569" />
              <Tooltip formatter={(v: number) => `${fmtNum(v)} MW`} />
              <Legend />
              <Bar dataKey="mae_mw" name="MAE (MW)" fill="#0d9488" isAnimationActive={false} />
              <Bar dataKey="bias_mw" name="Bias (MW)" fill="#d97706" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer></div>
        </Section>
      </div>

      <Section title="Accuracy by hour of day (UK time)" subtitle="MAE and bias for each half-hour window grouped by hour (MW)">
        <div className="h-64"><ResponsiveContainer>
          <BarChart data={hours} margin={{ left: 8, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="label" fontSize={11} stroke="#475569" interval={1} />
            <YAxis fontSize={12} stroke="#475569" />
            <Tooltip formatter={(v: number) => `${fmtNum(v)} MW`} />
            <Legend />
            <Bar dataKey="mae_mw" name="MAE (MW)" fill="#0d9488" isAnimationActive={false} />
            <Bar dataKey="bias_mw" name="Bias (MW)" fill="#d97706" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer></div>
      </Section>
    </div>
  );
}
