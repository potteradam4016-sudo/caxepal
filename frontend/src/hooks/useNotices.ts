import { useCallback, useEffect, useState } from 'react'
import type { Notice, NoticeFilters } from '../types'

export function useNotices(loader: (filters: NoticeFilters) => Promise<Notice[]>, filters: NoticeFilters, revision = 0) {
  const [notices, setNotices] = useState<Notice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [requestVersion, setRequestVersion] = useState(0)

  const retry = useCallback(() => setRequestVersion((value) => value + 1), [])

  useEffect(() => {
    let active = true
    void Promise.resolve()
      .then(() => {
        if (active) {
          setLoading(true)
          setError(false)
        }
        return loader(filters)
      })
      .then((result) => { if (active) setNotices(result) })
      .catch(() => { if (active) setError(true) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [loader, filters, revision, requestVersion])

  return { notices, loading, error, retry }
}
