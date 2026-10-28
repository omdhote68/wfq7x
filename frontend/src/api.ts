import type { Filters } from "./types";

const BASE: string = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

export type Params = Record<string, string | number | undefined | null>;

export function buildUrl(path: string, params: Params = {}): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  });
  const qs = q.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ""}`;
}

export function filterParams(f: Filters): Params {
  return { start: f.start, end: f.end, cutoff_hour: f.cutoffHour, cutoff_minute: f.cutoffMinute };
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError("Cannot reach the analytics API. Check that the backend is running and try again.", 0);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}
