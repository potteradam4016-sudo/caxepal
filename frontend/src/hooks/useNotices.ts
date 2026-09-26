import { useCallback } from 'react'
import { api } from '../services/api'
import { ApiError } from '../services/http'
import { useAuth } from '../context/AuthContext'
import { useApiResource } from './useApiResource'
import type { NoticeFilters } from '../types'

export function useNotices(kind: 'recommended' | 'new', filters: NoticeFilters, page: number) {
  const { user, reloadProfile } = useAuth()
  const version = user?.profileVersion ?? 0
  const loader = useCallback(async (signal: AbortSignal) => {
    // Include the profile version in the request lifecycle so edits invalidate recommendation results.
    void version
    try { return await api.list(kind, filters, page, signal) }
    catch (error) {
      if (error instanceof ApiError && error.code === 'PROFILE_INCOMPLETE') await reloadProfile()
      throw error
    }
  }, [kind, filters, page, version, reloadProfile])
  return useApiResource(loader)
}
