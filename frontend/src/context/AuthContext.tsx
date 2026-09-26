import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, profileBody, toUser } from '../services/api'
import { errorMessage, isAbort, session } from '../services/http'
import type { AcademicProfile, AuthUser, Profile } from '../types'
type Preferences = Pick<Profile, 'interests' | 'activityTypes'>
const draftKey = (id: string) => `scnu-pick:api:v1:preferences:${id}`
function restoreDraft(user: AuthUser): AuthUser {
  if (user.onboardingCompleted) return user
  try {
    const draft = JSON.parse(sessionStorage.getItem(draftKey(user.id)) ?? 'null') as Preferences | null
    if (draft && Array.isArray(draft.interests) && Array.isArray(draft.activityTypes) &&
      [...draft.interests, ...draft.activityTypes].every((id) => typeof id === 'string')) return { ...user, preferenceDraft: draft }
  } catch { /* Invalid drafts do not replace the server profile. */ }
  return user
}
interface AuthContextValue {
  user: AuthUser | null
  login: (username: string, password: string) => Promise<AuthUser>
  signup: (username: string, password: string) => Promise<void>
  saveAcademic: (academic: AcademicProfile) => Promise<void>
  savePreferenceDraft: (interests: string[], activityTypes: string[]) => void
  completeOnboarding: (interests: string[], activityTypes: string[]) => Promise<void>
  updateProfile: (profile: Profile) => Promise<Profile>
  reloadProfile: () => Promise<AuthUser>
  logout: () => Promise<void>
}
const AuthContext = createContext<AuthContextValue | null>(null)
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>(() => session.read() ? 'loading' : 'ready')
  const [failure, setFailure] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => session.subscribe(() => { setUser(null); setStatus('ready') }), [])
  useEffect(() => {
    const controller = new AbortController()
    if (!session.read()) return
    void Promise.all([api.me(controller.signal), api.profile(controller.signal)])
      .then(([account, profile]) => { if (!controller.signal.aborted) { setUser(restoreDraft(toUser(account, profile))); setStatus('ready') } })
      .catch((error: unknown) => {
        if (isAbort(error) || controller.signal.aborted) return
        if (!session.read()) { setUser(null); setStatus('ready'); return }
        setFailure(errorMessage(error)); setStatus('error')
      })
    return () => controller.abort()
  }, [revision])
  const login = useCallback(async (username: string, password: string) => {
    const response = await api.login(username.trim().toLowerCase(), password)
    session.save({ token: response.access_token, expiresAt: response.expires_at })
    try {
      const profile = await api.profile()
      const next = restoreDraft(toUser(response.user, profile))
      setUser(next); setStatus('ready')
      return next
    } catch (error) {
      if (session.read()) { setFailure(errorMessage(error)); setStatus('error') }
      throw error
    }
  }, [])
  const signup = useCallback(async (username: string, password: string) => {
    await api.register(username.trim().toLowerCase(), password)
  }, [])
  const reloadProfile = useCallback(async () => {
    const [account, profile] = await Promise.all([api.me(), api.profile()])
    const next = toUser(account, profile)
    setUser(next)
    return next
  }, [])
  const updateProfile = useCallback(async (profile: Profile) => {
    if (!user) throw new Error('AUTH_REQUIRED')
    const saved = await api.saveProfile(profileBody(profile))
    const next = toUser({ id: user.id, username: user.username, is_admin: false, onboarding_complete: saved.onboarding_complete }, saved)
    setUser(next)
    return next.profile!
  }, [user])
  const saveAcademic = useCallback(async (academic: AcademicProfile) => {
    if (!user) throw new Error('AUTH_REQUIRED')
    const draft = user.preferenceDraft
    await updateProfile({ ...academic, interests: [], activityTypes: [], version: user.profileVersion })
    setUser((current) => current ? { ...current, preferenceDraft: draft } : current)
  }, [updateProfile, user])
  const savePreferenceDraft = useCallback((interests: string[], activityTypes: string[]) => {
    if (!user) return
    const draft = { interests, activityTypes }
    sessionStorage.setItem(draftKey(user.id), JSON.stringify(draft))
    setUser((current) => current ? { ...current, preferenceDraft: draft } : current)
  }, [user])
  const completeOnboarding = useCallback(async (interests: string[], activityTypes: string[]) => {
    if (!user?.academicDraft) throw new Error('ACADEMIC_REQUIRED')
    await updateProfile({ ...user.academicDraft, interests, activityTypes, version: user.profileVersion })
    sessionStorage.removeItem(draftKey(user.id))
  }, [updateProfile, user])
  const logout = useCallback(async () => {
    const token = session.read()?.token
    try { await api.logout() } finally {
      if (user) sessionStorage.removeItem(draftKey(user.id))
      if (!session.read() || session.read()?.token === token) {
        session.clear()
        setUser(null); setStatus('ready')
      }
    }
  }, [user])
  const value = useMemo(() => ({ user, login, signup, saveAcademic, savePreferenceDraft, completeOnboarding, updateProfile, reloadProfile, logout }),
    [user, login, signup, saveAcademic, savePreferenceDraft, completeOnboarding, updateProfile, reloadProfile, logout])
  return <AuthContext.Provider value={value}>
    {status === 'ready' ? children : <main className="session-state">
      {status === 'loading' ? <p role="status">로그인 정보를 확인하고 있습니다.</p> : <div role="alert"><p>{failure}</p>
        <button className="button button--primary" onClick={() => { setStatus('loading'); setRevision((value) => value + 1) }}>다시 시도</button>
        <button className="button button--secondary" onClick={() => { session.clear(); setUser(null); setStatus('ready') }}>로그인으로 이동</button>
      </div>}
    </main>}
  </AuthContext.Provider>
}
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
