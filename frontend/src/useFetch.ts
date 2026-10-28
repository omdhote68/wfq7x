import { useCallback, useEffect, useState } from "react";
import { ApiError, getJson } from "./api";

export interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Fetches `url` (null = idle). Cancels in-flight requests when the url changes. */
export function useFetch<T>(url: string | null): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(url !== null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (url === null) return;
    const ctl = new AbortController();
    setLoading(true);
    setError(null);
    getJson<T>(url, ctl.signal)
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if ((e as Error).name === "AbortError") return;
        setError(e instanceof ApiError ? e.message : "Unexpected error while loading data.");
        setLoading(false);
      });
    return () => ctl.abort();
  }, [url, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, reload };
}
