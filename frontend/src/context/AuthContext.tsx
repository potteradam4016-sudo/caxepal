import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { mockAuthService } from '../services/mockAuthService'
import type { AcademicProfile, AuthUser, Profile } from '../types'

interface AuthContextValue {
  user: AuthUser | null
  login: (username: string, password: string) => Promise<AuthUser>
  signup: (username: string) => Promise<AuthUser>
  saveAcademic: (academic: AcademicProfile) => Promise<AuthUser>
  savePreferenceDraft: (interests: string[], activityTypes: string[]) => void
  completeOnboarding: (interests: string[], activityTypes: string[]) => Promise<AuthUser>
  updateProfile: (profile: Profile) => Promise<Profile>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => mockAuthService.getSession())

  const login = useCallback(async (username: string, password: string) => {
    const next = await mockAuthService.login(username, password)
    setUser(next)
    return next
  }, [])

  const signup = useCallback(async (username: string) => {
    const next = await mockAuthService.signup(username)
    setUser(next)
    return next
  }, [])

  const saveAcademic = useCallback(async (academic: AcademicProfile) => {
    if (!user) throw new Error('AUTH_REQUIRED')
    const next = await mockAuthService.saveAcademic(user.username, academic)
    setUser(next)
    return next
  }, [user])

  const savePreferenceDraft = useCallback((interests: string[], activityTypes: string[]) => {
    if (!user) return
    setUser(mockAuthService.savePreferenceDraft(user.username, interests, activityTypes))
  }, [user])

  const completeOnboarding = useCallback(async (interests: string[], activityTypes: string[]) => {
    if (!user) throw new Error('AUTH_REQUIRED')
    const next = await mockAuthService.completeOnboarding(user.username, interests, activityTypes)
    setUser(next)
    return next
  }, [user])

  const updateProfile = useCallback(async (profile: Profile) => {
    if (!user) throw new Error('AUTH_REQUIRED')
    const next = await mockAuthService.updateProfile(user.username, profile)
    setUser(next)
    return next.profile!
  }, [user])

  const logout = useCallback(() => {
    mockAuthService.logout()
    setUser(null)
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    login,
    signup,
    saveAcademic,
    savePreferenceDraft,
    completeOnboarding,
    updateProfile,
    logout,
  }), [completeOnboarding, login, logout, saveAcademic, savePreferenceDraft, signup, updateProfile, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
