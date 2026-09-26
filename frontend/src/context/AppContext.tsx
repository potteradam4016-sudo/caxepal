import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api } from '../services/api'
import { errorMessage, isAbort } from '../services/http'
import type { Profile } from '../types'
import { useAuth } from './AuthContext'

interface AppContextValue {
  favorites: Set<number>; favoritePending: Set<number>; favoritesLoading: boolean; favoritesError: string
  retryFavorites: () => void; favoritesRevision: number
  profile: Profile | null; profileRevision: number
  toggleFavorite: (id: number) => Promise<void>
  saveProfile: (profile: Profile) => Promise<void>
  showToast: (message: string, tone?: 'default' | 'error') => void
}
const AppContext = createContext<AppContextValue | null>(null)
export function AppProvider({ children }: { children: ReactNode }) {
  const { user, updateProfile } = useAuth()
  const [favorites, setFavorites] = useState(new Set<number>())
  const [favoritePending, setFavoritePending] = useState(new Set<number>())
  const pending = useRef(new Set<number>())
  const alive = useRef(true)
  const [favoritesLoading, setFavoritesLoading] = useState(Boolean(user))
  const [favoritesError, setFavoritesError] = useState('')
  const [reload, setReload] = useState(0)
  const [favoritesRevision, setFavoritesRevision] = useState(0)
  const [toast, setToast] = useState<{ message: string; tone: 'default' | 'error' } | null>(null)
  const userId = user?.id
  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])
  useEffect(() => {
    if (!userId) return
    const controller = new AbortController()
    void Promise.resolve().then(() => {
      if (controller.signal.aborted) return
      setFavoritesLoading(true); setFavoritesError('')
      return api.favorites(controller.signal)
    }).then((ids) => { if (!controller.signal.aborted && ids) setFavorites(new Set(ids)) })
      .catch((error: unknown) => { if (!controller.signal.aborted && !isAbort(error)) setFavoritesError(errorMessage(error)) })
      .finally(() => { if (!controller.signal.aborted) setFavoritesLoading(false) })
    return () => controller.abort()
  }, [userId, reload])
  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(null), 3000)
    return () => window.clearTimeout(timer)
  }, [toast])
  const retryFavorites = useCallback(() => setReload((value) => value + 1), [])
  const showToast = useCallback((message: string, tone: 'default' | 'error' = 'default') => setToast({ message, tone }), [])
  const toggleFavorite = useCallback(async (id: number) => {
    if (pending.current.has(id) || favoritesLoading || favoritesError) return
    const wasFavorite = favorites.has(id)
    pending.current.add(id)
    setFavoritePending(new Set(pending.current))
    setFavorites((current) => { const next = new Set(current); if (wasFavorite) next.delete(id); else next.add(id); return next })
    try {
      await api.favorite(id, !wasFavorite)
      if (!alive.current) return
      setFavoritesRevision((value) => value + 1)
      showToast(wasFavorite ? '찜을 해제했어요.' : '찜에 추가했어요.')
    } catch (error) {
      if (!alive.current || isAbort(error)) return
      setFavorites((current) => { const next = new Set(current); if (wasFavorite) next.add(id); else next.delete(id); return next })
      showToast(errorMessage(error), 'error')
    } finally {
      pending.current.delete(id)
      if (alive.current) setFavoritePending(new Set(pending.current))
    }
  }, [favorites, favoritesError, favoritesLoading, showToast])
  const saveProfile = useCallback(async (profile: Profile) => {
    await updateProfile(profile)
    if (alive.current) showToast('저장했어요. 추천 결과를 새 정보 기준으로 갱신했습니다.')
  }, [updateProfile, showToast])
  const profile = user?.profile ?? null
  const profileRevision = user?.profileVersion ?? 0
  const value = useMemo(() => ({ favorites, favoritePending, favoritesLoading, favoritesError, retryFavorites, favoritesRevision,
    profile, profileRevision, toggleFavorite, saveProfile, showToast }),
    [favorites, favoritePending, favoritesLoading, favoritesError, retryFavorites, favoritesRevision, profile, profileRevision, toggleFavorite, saveProfile, showToast])
  return <AppContext.Provider value={value}>
    {children}
    <div className={`toast ${toast ? 'toast--visible' : ''} ${toast?.tone === 'error' ? 'toast--error' : ''}`} role="status" aria-live="polite">{toast?.message}</div>
  </AppContext.Provider>
}
export function useApp() {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used within AppProvider')
  return context
}
