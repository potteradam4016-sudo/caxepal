import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { mockNoticeService } from '../services/mockNoticeService'
import type { Profile } from '../types'

interface AppContextValue {
  favorites: Set<string>
  favoritePending: Set<string>
  profile: Profile | null
  profileRevision: number
  toggleFavorite: (id: string) => Promise<void>
  saveProfile: (profile: Profile) => Promise<void>
  showToast: (message: string, tone?: 'default' | 'error') => void
}

const AppContext = createContext<AppContextValue | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [favorites, setFavorites] = useState(() => new Set(mockNoticeService.getFavoriteIds()))
  const [favoritePending, setFavoritePending] = useState(new Set<string>())
  const [profile, setProfile] = useState<Profile | null>(null)
  const [profileRevision, setProfileRevision] = useState(0)
  const [toast, setToast] = useState<{ message: string; tone: 'default' | 'error' } | null>(null)

  useEffect(() => {
    void mockNoticeService.getProfile().then(setProfile)
  }, [])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(null), 2400)
    return () => window.clearTimeout(timer)
  }, [toast])

  const showToast = useCallback((message: string, tone: 'default' | 'error' = 'default') => {
    setToast({ message, tone })
  }, [])

  const toggleFavorite = useCallback(
    async (id: string) => {
      if (favoritePending.has(id)) return
      const wasFavorite = favorites.has(id)
      setFavoritePending((current) => new Set(current).add(id))
      setFavorites((current) => {
        const next = new Set(current)
        if (wasFavorite) next.delete(id)
        else next.add(id)
        return next
      })

      try {
        const saved = await mockNoticeService.toggleFavorite(id, !wasFavorite)
        setFavorites(new Set(saved))
        showToast(wasFavorite ? '찜을 해제했어요.' : '찜에 추가했어요. 캘린더에 일정이 연결됩니다.')
      } catch {
        setFavorites((current) => {
          const rollback = new Set(current)
          if (wasFavorite) rollback.add(id)
          else rollback.delete(id)
          return rollback
        })
        showToast('찜 상태를 저장하지 못했습니다. 다시 시도해 주세요.', 'error')
      } finally {
        setFavoritePending((current) => {
          const next = new Set(current)
          next.delete(id)
          return next
        })
      }
    },
    [favoritePending, favorites, showToast],
  )

  const saveProfile = useCallback(
    async (nextProfile: Profile) => {
      const saved = await mockNoticeService.updateProfile(nextProfile)
      setProfile(saved)
      setProfileRevision((value) => value + 1)
      showToast('저장했어요. 추천 결과를 새 정보 기준으로 갱신했습니다.')
    },
    [showToast],
  )

  const value = useMemo(
    () => ({ favorites, favoritePending, profile, profileRevision, toggleFavorite, saveProfile, showToast }),
    [favorites, favoritePending, profile, profileRevision, toggleFavorite, saveProfile, showToast],
  )

  return (
    <AppContext.Provider value={value}>
      {children}
      <div className={`toast ${toast ? 'toast--visible' : ''} ${toast?.tone === 'error' ? 'toast--error' : ''}`} role="status" aria-live="polite">
        {toast?.message}
      </div>
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) throw new Error('useApp must be used within AppProvider')
  return context
}
