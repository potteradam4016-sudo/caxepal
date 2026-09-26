import type { AuthUser, Notice, NoticeDetail, NoticeFilters, NoticePage, Profile } from '../types'
import type { CalendarDto, InterestDto, LoginDto, NoticeCardDto, NoticeDetailDto, NoticePageDto, ProfileDto, ProfileInputDto, SourceDto, UserDto } from './contracts'
import { request } from './http'
export function toUser(user: UserDto, profile: ProfileDto): AuthUser {
  const academic = profile.department && profile.grade && profile.academic_status
    ? { department: profile.department, grade: profile.grade, enrollmentStatus: profile.academic_status } : null
  const preferences = {
    interests: profile.interests.filter((item) => item.type === 'field').map((item) => item.id),
    activityTypes: profile.interests.filter((item) => item.type === 'activity').map((item) => item.id),
  }
  return { id: user.id, username: user.username, onboardingCompleted: profile.onboarding_complete,
    profileVersion: profile.version, academicDraft: academic, preferenceDraft: preferences,
    profile: academic ? { ...academic, ...preferences, version: profile.version } : null }
}
export function toNotice(item: NoticeCardDto): Notice {
  return { id: item.id, title: item.title, source: item.source_name, sourceCode: item.source_code,
    publishedAt: item.posted_date, category: item.category, summary: item.summary_lines,
    deadlineLabel: item.deadline_label, isClosed: item.is_closed,
    isDeadlineSoon: !item.is_closed && item.d_day !== null && item.d_day >= 0 && item.d_day <= 7,
    isBookmarked: item.is_bookmarked, needsReview: item.needs_review,
    recommendation: item.recommendation, originalUrl: item.original_url }
}
export const api = {
  register: (username: string, password: string) => request<{ message: string }>('/auth/register', { method: 'POST', body: { username, password }, auth: false }),
  login: (username: string, password: string) => request<LoginDto>('/auth/login', { method: 'POST', body: { username, password }, auth: false }),
  me: (signal?: AbortSignal) => request<UserDto>('/auth/me', { signal }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  profile: (signal?: AbortSignal) => request<ProfileDto>('/profile', { signal }),
  saveProfile: (body: ProfileInputDto) => request<ProfileDto>('/profile', { method: 'PUT', body }),
  interests: (signal?: AbortSignal) => request<InterestDto[]>('/interests', { signal }),
  sources: (signal?: AbortSignal) => request<SourceDto[]>('/sources', { signal }),
  async list(kind: 'recommended' | 'new', filters: NoticeFilters, page: number, signal?: AbortSignal): Promise<NoticePage> {
    const query = new URLSearchParams({ page: String(page), page_size: '20' })
    if (filters.query.trim()) query.set('q', filters.query.trim())
    for (const category of filters.categories) query.append('category', category)
    if (filters.source && filters.source !== 'all') query.set('source', filters.source)
    if (filters.deadlineSoon) query.set('closing_days', '7')
    const data = await request<NoticePageDto>(`/notices/${kind}?${query}`, { signal })
    return { items: data.items.map(toNotice), total: data.total, page: data.page, pageSize: data.page_size, profileVersion: data.profile_version ?? null }
  },
  async detail(id: number, signal?: AbortSignal): Promise<NoticeDetail> {
    const dto = await request<NoticeDetailDto>(`/notices/${id}`, { signal })
    const data = dto.analysis.data
    return { ...toNotice(dto), body: dto.body_text, target: data.target_text, applicationMethod: data.application_method,
      schedules: data.schedules, prize: data.prize, mileages: data.mileages, attachments: dto.attachments }
  },
  async favorites(signal?: AbortSignal): Promise<number[]> {
    const ids = new Set<number>()
    for (let page = 1; ; page++) {
      const data = await request<NoticePageDto>(`/bookmarks?page=${page}&page_size=100`, { signal })
      data.items.forEach((item) => ids.add(item.id))
      if (data.items.length === 0 || data.page * data.page_size >= data.total) return [...ids]
    }
  },
  favorite: (id: number, added: boolean) => request<void>(`/bookmarks/${id}`, { method: added ? 'POST' : 'DELETE' }),
  calendar: (month: string, signal?: AbortSignal) => request<CalendarDto>(`/calendar?month=${month}`, { signal }),
}
export function profileBody(profile: Profile): ProfileInputDto {
  return { department: profile.department.trim(), grade: profile.grade, academic_status: profile.enrollmentStatus,
    interest_ids: [...profile.interests, ...profile.activityTypes], expected_version: profile.version }
}
