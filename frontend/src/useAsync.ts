import { useEffect, useState } from 'react'

export interface AsyncState<T> {
  data: T | undefined
  error: Error | undefined
  loading: boolean
}

// Minimal fetch-on-change hook. The `cancelled` flag drops responses from
// superseded requests so fast typing or quick navigation can't show stale data.
// With enabled=false the hook stays in loading and doesn't call fn.
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[], enabled = true): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: undefined, error: undefined, loading: true })

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: undefined }))
    fn().then(
      (data) => !cancelled && setState({ data, error: undefined, loading: false }),
      (error: Error) => !cancelled && setState({ data: undefined, error, loading: false }),
    )
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled])

  return state
}
