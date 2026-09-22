import type { AcademicProfile, AuthUser, Profile } from '../types'

const USERS_KEY = 'scnu-pick:v3:users'
const SESSION_KEY = 'scnu-pick:v3:session'
const WAIT_MS = 240

const DEMO_USER: AuthUser = {
  username: 'demo',
  onboardingCompleted: true,
  academicDraft: {
    department: '컴퓨터공학과',
    grade: '2학년',
    enrollmentStatus: '재학',
  },
  preferenceDraft: { interests: ['AI', '개발'], activityTypes: ['프로젝트'] },
  profile: {
    department: '컴퓨터공학과',
    grade: '2학년',
    enrollmentStatus: '재학',
    interests: ['AI', '개발'],
    activityTypes: ['프로젝트'],
  },
}

const wait = () => new Promise((resolve) => window.setTimeout(resolve, WAIT_MS))
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function readUsers(): Record<string, AuthUser> {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(USERS_KEY) ?? '{}') as Record<string, AuthUser>
    return { [DEMO_USER.username]: clone(DEMO_USER), ...parsed }
  } catch {
    return { [DEMO_USER.username]: clone(DEMO_USER) }
  }
}

function writeUsers(users: Record<string, AuthUser>) {
  sessionStorage.setItem(USERS_KEY, JSON.stringify(users))
}

function updateUser(username: string, update: (user: AuthUser) => AuthUser): AuthUser {
  const users = readUsers()
  const next = update(users[username])
  users[username] = next
  writeUsers(users)
  return clone(next)
}

export const mockAuthService = {
  getSession(): AuthUser | null {
    const username = sessionStorage.getItem(SESSION_KEY)
    return username ? clone(readUsers()[username] ?? null) : null
  },

  async login(username: string, password: string): Promise<AuthUser> {
    await wait()
    const normalizedUsername = username.trim().toLowerCase()
    const user = readUsers()[normalizedUsername]
    if (!user || password.length < 8) throw new Error('INVALID_CREDENTIALS')
    sessionStorage.setItem(SESSION_KEY, normalizedUsername)
    return clone(user)
  },

  async signup(username: string): Promise<AuthUser> {
    await wait()
    const normalizedUsername = username.trim().toLowerCase()
    const users = readUsers()
    if (users[normalizedUsername]) throw new Error('DUPLICATE_USERNAME')
    const user: AuthUser = {
      username: normalizedUsername,
      onboardingCompleted: false,
      academicDraft: null,
      preferenceDraft: { interests: [], activityTypes: [] },
      profile: null,
    }
    users[normalizedUsername] = user
    writeUsers(users)
    sessionStorage.setItem(SESSION_KEY, normalizedUsername)
    return clone(user)
  },

  async saveAcademic(username: string, academic: AcademicProfile): Promise<AuthUser> {
    await wait()
    return updateUser(username, (user) => ({ ...user, academicDraft: academic }))
  },

  async completeOnboarding(username: string, interests: string[], activityTypes: string[]): Promise<AuthUser> {
    await wait()
    return updateUser(username, (user) => {
      if (!user.academicDraft) throw new Error('ACADEMIC_REQUIRED')
      const profile: Profile = { ...user.academicDraft, interests, activityTypes }
      return {
        ...user,
        onboardingCompleted: true,
        preferenceDraft: { interests, activityTypes },
        profile,
      }
    })
  },

  savePreferenceDraft(username: string, interests: string[], activityTypes: string[]): AuthUser {
    return updateUser(username, (user) => ({ ...user, preferenceDraft: { interests, activityTypes } }))
  },

  async updateProfile(username: string, profile: Profile): Promise<AuthUser> {
    await wait()
    return updateUser(username, (user) => ({
      ...user,
      academicDraft: {
        department: profile.department,
        grade: profile.grade,
        enrollmentStatus: profile.enrollmentStatus,
      },
      preferenceDraft: { interests: profile.interests, activityTypes: profile.activityTypes },
      profile,
    }))
  },

  logout() {
    sessionStorage.removeItem(SESSION_KEY)
  },
}

export const authStorageKeys = { users: USERS_KEY, session: SESSION_KEY }
