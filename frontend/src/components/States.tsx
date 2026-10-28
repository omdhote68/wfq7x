import type { ReactNode } from "react";

export function Loading({ label = "Loading data…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex h-48 items-center justify-center gap-3 text-sm text-slate-600">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
      {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <p className="font-semibold">Something went wrong</p>
      <p className="mt-1">{message}</p>
      <p className="mt-1 text-red-700">
        Check the date range is inside the analysis period, then retry. If it persists, confirm the backend is running.
      </p>
      {onRetry && (
        <button className="btn mt-3" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-40 items-center justify-center rounded-lg border border-dashed border-slate-300 text-sm text-slate-600">
      {children}
    </div>
  );
}

export function Section({ title, subtitle, children, right }: { title: string; subtitle?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="card">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}
