import type { Meta } from "../types";
import { Section } from "./States";

export function Methodology({ meta }: { meta: Meta }) {
  return (
    <div className="space-y-4">
      <Section title="Methodology & data quality">
        <div className="space-y-3 text-sm leading-relaxed text-slate-800">
          <p><strong>Actuals:</strong> Elexon BMRS FUELHH, rows with fuelType = WIND, field <code>generation</code> (MW, average power over the half-hour starting at <code>startTime</code>).</p>
          <p><strong>Forecasts:</strong> Elexon BMRS WINDFOR. <code>startTime</code> is the delivery time; <code>publishTime</code> is when the forecast was created. The returned data is hourly, so each hourly value is reused for the following half-hour slot to align with half-hour actuals. This is a carry-forward assumption, not an Elexon half-hour forecast.</p>
          <p><strong>Day-ahead vintage selection:</strong> {meta.cutoff_rule} Forecasts published after the cutoff are never used, so there is no look-ahead bias. If no forecast was published by the cutoff, the interval is reported as missing rather than back-filled.</p>
          <p><strong>Cutoff is an assumption.</strong> It is configurable here and is not presented as a verified market gate-closure rule. Change it in the filter bar to see how sensitive results are.</p>
          <p><strong>Error convention:</strong> {meta.error_convention}.</p>
          <p><strong>Energy vs power:</strong> generation values are MW. Energy (MWh) = MW × 0.5 h per half-hour. Sums of MW are never labelled MWh.</p>
          <p><strong>MAPE:</strong> computed only where actual ≥ {meta.mape_min_actual_mw} MW; smaller actuals (including zero) are excluded and counted on the KPI card.</p>
          <p><strong>Data quality:</strong> non-WIND rows, null values, unparseable timestamps and duplicate (startTime, publishTime) pairs are dropped. The matched table is built on the full half-hourly calendar (DST-aware, UK local days), so gaps show as missing rather than disappearing. Hourly forecast values carried into the second half-hour are identified in the data note above.</p>
          <p><strong>Statistical caution:</strong> with fewer than 100 matched intervals the app flags metrics as indicative only. Even with more, half-hours are strongly autocorrelated, so treat the sample as fewer independent observations than the count suggests.</p>
        </div>
      </Section>
      <Section title="Data source">
        <p className="text-sm text-slate-800">{meta.attribution}</p>
        <p className="mt-2 text-sm text-slate-700">Current data: <strong>{meta.data_source}</strong>. {meta.data_note}</p>
      </Section>
    </div>
  );
}
