import { useCallback, useEffect, useState } from 'react'
import { isAbort } from '../services/http'

export function useApiResource<T>(loader: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  const retry = useCallback(() => setRevision((value) => value + 1), [])
  useEffect(() => {
    const controller = new AbortController()
    void Promise.resolve().then(() => {
      if (controller.signal.aborted) return
      setLoading(true); setError(null)
      return loader(controller.signal)
    }).then((value) => { if (!controller.signal.aborted && value !== undefined) setData(value) })
      .catch((failure: unknown) => { if (!controller.signal.aborted && !isAbort(failure)) setError(failure) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [loader, revision])
  return { data, error, loading, retry }
}
