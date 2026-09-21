import { DEFAULT_PROFILE, MOCK_NOTICES } from '../data/mockData'
import type { CalendarEvent, FavoriteSchedules, Notice, NoticeFilters, Profile } from '../types'

const PROFILE_KEY = 'scnu-pick:v1:profile'
const FAVORITES_KEY = 'scnu-pick:v1:favorites'
const DEFAULT_FAVORITES = ['ai-project', 'opensource-lecture']
const WAIT_MS = 180

const wait = () => new Promise((resolve) => window.setTimeout(resolve, WAIT_MS))

function readJson<T>(key: string, fallback: T, validate: (value: unknown) => value is T): T {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    const parsed: unknown = JSON.parse(raw)
    return validate(parsed) ? parsed : fallback
  } catch {
    return fallback
  }
}

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string')

const isProfile = (value: unknown): value is Profile => {
  if (!value || typeof value !== 'object') return false
  const profile = value as Partial<Profile>
  return (
    typeof profile.department === 'string' &&
    ['1학년', '2학년', '3학년', '4학년'].includes(profile.grade ?? '') &&
    ['재학', '휴학', '기타'].includes(profile.enrollmentStatus ?? '') &&
    isStringArray(profile.interests) &&
    isStringArray(profile.activityTypes)
  )
}

function matchesFilters(notice: Notice, filters: NoticeFilters) {
  const normalizedQuery = filters.query.trim().toLocaleLowerCase('ko-KR')
  const searchable = [notice.title, notice.source, notice.target, notice.activity, ...notice.keywords]
    .join(' ')
    .toLocaleLowerCase('ko-KR')
  const matchesQuery = !normalizedQuery || searchable.includes(normalizedQuery)
  const matchesCategories =
    filters.categories.length === 0 || filters.categories.some((category) => notice.categories.includes(category))
  const matchesSource = !filters.source || filters.source === 'all' || notice.source === filters.source
  const matchesDeadline = !filters.deadlineSoon || notice.isDeadlineSoon
  return matchesQuery && matchesCategories && matchesSource && matchesDeadline
}

function dateEvents(notice: Notice): CalendarEvent[] {
  const fields: Array<{
    date: string | null
    type: CalendarEvent['type']
    kind: CalendarEvent['kind']
    label: string
  }> = [
    { date: notice.schedule.applicationStart, type: 'application', kind: 'start', label: '신청 시작' },
    { date: notice.schedule.applicationEnd, type: 'application', kind: 'end', label: '신청 마감' },
    { date: notice.schedule.eventStart, type: 'activity', kind: 'start', label: '행사 시작' },
    { date: notice.schedule.eventEnd, type: 'activity', kind: 'end', label: '행사 종료' },
  ]
  return fields.flatMap((field) =>
    field.date
      ? [{ id: `${notice.id}-${field.type}-${field.kind}`, noticeId: notice.id, title: notice.title, ...field, date: field.date }]
      : [],
  )
}

export const mockNoticeService = {
  async listRecommended(filters: NoticeFilters): Promise<Notice[]> {
    await wait()
    return MOCK_NOTICES.filter((notice) => notice.isRecommended && matchesFilters(notice, filters)).sort(
      (a, b) => (b.recommendationScore ?? 0) - (a.recommendationScore ?? 0),
    )
  },

  async listNew(filters: NoticeFilters): Promise<Notice[]> {
    await wait()
    return MOCK_NOTICES.filter((notice) => matchesFilters(notice, filters)).sort((a, b) =>
      b.publishedAt.localeCompare(a.publishedAt),
    )
  },

  async getNotice(id: string): Promise<Notice | null> {
    await wait()
    return MOCK_NOTICES.find((notice) => notice.id === id) ?? null
  },

  getFavoriteIds(): string[] {
    return readJson(FAVORITES_KEY, DEFAULT_FAVORITES, isStringArray).filter((id) =>
      MOCK_NOTICES.some((notice) => notice.id === id),
    )
  },

  async toggleFavorite(id: string, nextValue: boolean): Promise<string[]> {
    await wait()
    const current = this.getFavoriteIds()
    const next = nextValue ? [...new Set([...current, id])] : current.filter((favoriteId) => favoriteId !== id)
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(next))
    return next
  },

  async getFavoriteSchedules(): Promise<FavoriteSchedules> {
    await wait()
    const favoriteIds = this.getFavoriteIds()
    const favorites = MOCK_NOTICES.filter((notice) => favoriteIds.includes(notice.id))
    return {
      events: favorites.flatMap(dateEvents).sort((a, b) => a.date.localeCompare(b.date)),
      undated: favorites.filter((notice) => Object.values(notice.schedule).every((date) => date === null)),
    }
  },

  async getProfile(): Promise<Profile> {
    await wait()
    return readJson(PROFILE_KEY, DEFAULT_PROFILE, isProfile)
  },

  async updateProfile(profile: Profile): Promise<Profile> {
    await wait()
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile))
    return profile
  },
}

export const storageKeys = { profile: PROFILE_KEY, favorites: FAVORITES_KEY }
