export const NOTICE_SOURCES = [
  '순천대학교 대표 공지',
  'SW중심대학사업단',
  'AI인재양성부트캠프사업단',
] as const

export const NOTICE_CATEGORIES = ['장학/지원', '대외활동', '교육/특강', '프로젝트', '취업'] as const

export type NoticeSource = (typeof NOTICE_SOURCES)[number]
export type NoticeCategory = (typeof NOTICE_CATEGORIES)[number]
export type BenefitState = 'present' | 'absent' | 'unspecified'
export type AsyncState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

export interface NoticeSchedule {
  applicationStart: string | null
  applicationEnd: string | null
  eventStart: string | null
  eventEnd: string | null
}

export interface Benefit {
  prize: { state: BenefitState; detail?: string }
  mileage: Array<{ system: string; points: number | null; condition: string | null }>
  other: string[]
}

export interface Notice {
  id: string
  title: string
  source: NoticeSource
  publishedAt: string
  target: string
  activity: string
  categories: NoticeCategory[]
  keywords: string[]
  schedule: NoticeSchedule
  benefit: Benefit
  recommendationScore: number | null
  recommendationReason: string | null
  isDeadlineSoon: boolean
  isRecommended: boolean
  originalUrl: string | null
}

export interface Profile {
  department: string
  grade: '1학년' | '2학년' | '3학년' | '4학년'
  enrollmentStatus: '재학' | '휴학' | '기타'
  interests: string[]
  activityTypes: string[]
}

export interface NoticeFilters {
  query: string
  categories: NoticeCategory[]
  source?: NoticeSource | 'all'
  deadlineSoon?: boolean
}

export type CalendarEventType = 'application' | 'activity'
export type CalendarEventKind = 'start' | 'end'

export interface CalendarEvent {
  id: string
  noticeId: string
  title: string
  date: string
  type: CalendarEventType
  kind: CalendarEventKind
  label: string
}

export interface FavoriteSchedules {
  events: CalendarEvent[]
  undated: Notice[]
}
