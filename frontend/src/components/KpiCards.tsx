import { fmtGwh, fmtNum, fmtPct, fmtSigned } from "../format";
import type { Metrics } from "../types";

interface Kpi {
  id: string;
  label: string;
  value: string;
  unit: string;
  help: string;
}

export function buildKpis(m: Metrics): Kpi[] {
  return [
    { id: "actual", label: "Actual wind energy", value: fmtGwh(m.actual_energy_mwh), unit: "GWh",
      help: "Sum of half-hourly average MW × 0.5 h. Counts every interval with an actual reading." },
    { id: "forecast", label: "Day-ahead forecast energy", value: fmtGwh(m.forecast_energy_mwh), unit: "GWh",
      help: "Same calculation on the forecast selected at the cutoff. Counts every interval with an eligible forecast." },
    { id: "mae", label: "MAE", value: fmtNum(m.mae_mw, 0), unit: "MW",
      help: "Mean absolute error: average size of the miss, ignoring direction." },
    { id: "rmse", label: "RMSE", value: fmtNum(m.rmse_mw, 0), unit: "MW",
      help: "Root mean squared error: like MAE but penalises large misses more." },
    { id: "mape", label: "MAPE", value: fmtPct(m.mape_pct, 1), unit: "",
      help: `Mean absolute % error. Intervals with actual < ${fmtNum(m.mape_min_actual_mw)} MW are excluded (${fmtNum(m.mape_excluded)} excluded) to avoid dividing by ~0.` },
    { id: "bias", label: "Forecast bias", value: fmtSigned(m.bias_mw, 0), unit: "MW",
      help: "Mean of (forecast − actual). Positive = over-forecast on average, so you would under-buy; negative = under-forecast." },
    { id: "coverage", label: "Matched coverage", value: fmtPct(m.coverage_pct, 1), unit: "",
      help: `${fmtNum(m.intervals_matched)} of ${fmtNum(m.intervals_expected)} half-hours have both an actual and an eligible forecast.` },
  ];
}

export function KpiCards({ metrics }: { metrics: Metrics }) {
  return (
    <div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7" data-testid="kpi-grid">
        {buildKpis(metrics).map((k) => (
          <div key={k.id} className="card" data-testid={`kpi-${k.id}`}>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-600">{k.label}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">
              {k.value}
              {k.unit && <span className="ml-1 text-sm font-normal text-slate-600">{k.unit}</span>}
            </p>
            <p className="mt-2 text-xs leading-snug text-slate-600">{k.help}</p>
          </div>
        ))}
      </div>
      {metrics.sample_note && (
        <p role="note" className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {metrics.sample_note}
        </p>
      )}
      <p className="mt-2 text-xs text-slate-600">
        Error = forecast − actual (MW). Positive = over-forecast, negative = under-forecast. Decision cutoff: {metrics.cutoff_used}.
      </p>
    </div>
  );
}
