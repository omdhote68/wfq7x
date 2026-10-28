import { useState } from "react";
import { Brush, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { filterParams, buildUrl } from "../api";
import { errorLabel, fmtDateTime, fmtDay, fmtNum, fmtSigned } from "../format";
import type { Filters, Granularity, TimeSeries, TSPoint } from "../types";
import { useFetch } from "../useFetch";
import { Empty, ErrorBox, Loading, Section } from "./States";

const MODES: { id: Granularity; label: string }[] = [
  { id: "half_hour", label: "Half-hourly" },
  { id: "day", label: "Daily mean" },
  { id: "week", label: "Weekly mean" },
];

export function ChartTooltip({ active, payload, granularity }: { active?: boolean; payload?: { payload: TSPoint }[]; granularity: Granularity }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3 text-xs shadow-md" data-testid="chart-tooltip">
      <p className="font-semibold">{granularity === "half_hour" ? fmtDateTime(p.t) : fmtDay(p.t)} (UK time)</p>
      <p>Actual: {fmtNum(p.actual_mw)} MW</p>
      <p>Forecast: {fmtNum(p.forecast_mw)} MW</p>
      <p>
        Error: {fmtSigned(p.error_mw)} MW {errorLabel(p.error_mw) && `(${errorLabel(p.error_mw)})`}
      </p>
      {p.publish_time && <p>Forecast published: {fmtDateTime(p.publish_time)}</p>}
      {granularity !== "half_hour" && <p>Intervals averaged: {p.n}</p>}
    </div>
  );
}

export function TimeSeriesChart({ filters }: { filters: Filters }) {
  const [g, setG] = useState<Granularity>("half_hour");
  const url = buildUrl("/api/timeseries", { ...filterParams(filters), granularity: g });
  const { data, loading, error, reload } = useFetch<TimeSeries>(url);
  const hasData = !!data && data.points.some((p) => p.actual_mw !== null || p.forecast_mw !== null);

  return (
    <Section
      title="Actual vs day-ahead forecast wind generation"
      subtitle="MW (half-hourly average power). Forecast = latest vintage published before the decision cutoff."
      right={
        <div className="flex gap-1" role="group" aria-label="Aggregation">
          {MODES.map((m) => (
            <button key={m.id} className={`btn ${g === m.id ? "btn-active" : ""}`} aria-pressed={g === m.id} onClick={() => setG(m.id)}>
              {m.label}
            </button>
          ))}
        </div>
      }
    >
      {loading && <Loading label="Loading time series…" />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {!loading && !error && data && !hasData && <Empty>No data in the selected range.</Empty>}
      {!loading && !error && hasData && data && (
        <div className="h-80 w-full" data-testid="ts-chart">
          <ResponsiveContainer>
            <LineChart data={data.points} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="t" tickFormatter={(v: string) => (g === "half_hour" ? fmtDay(v) : fmtDay(v))} minTickGap={40} stroke="#475569" fontSize={12} />
              <YAxis stroke="#475569" fontSize={12} tickFormatter={(v: number) => fmtNum(v)} label={{ value: "MW", angle: -90, position: "insideLeft", fill: "#475569" }} />
              <Tooltip content={<ChartTooltip granularity={g} />} />
              <Legend />
              <Line type="monotone" dataKey="actual_mw" name="Actual (FUELHH, MW)" stroke="#0f172a" dot={false} strokeWidth={1.5} connectNulls={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="forecast_mw" name="Day-ahead forecast (WINDFOR, MW)" stroke="#0d9488" dot={false} strokeWidth={1.5} connectNulls={false} isAnimationActive={false} />
              {data.points.length > 60 && <Brush dataKey="t" height={24} stroke="#0d9488" tickFormatter={(v: string) => fmtDay(v)} />}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Section>
  );
}
