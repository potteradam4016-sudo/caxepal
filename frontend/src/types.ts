import type { AcademicStatus, Category, NoticeDetailDto, RecommendationDto, ScheduleDto, SourceCode } from './services/contracts'
export const CATEGORY_LABELS: Record<Category, string> = {
  contest: '공모전·대회', education: '교육·특강', scholarship: '장학·지원', career: '취업',
  startup: '창업', overseas: '해외', volunteer: '봉사', other: '기타',
}
export const NOTICE_CATEGORIES = Object.keys(CATEGORY_LABELS) as Category[]
export const STATUS_LABELS: Record<AcademicStatus, string> = { enrolled: '재학', on_leave: '휴학', graduating: '졸업예정', graduated: '졸업' }
export type NoticeCategory = Category
export type NoticeSource = SourceCode
export interface AcademicProfile { department: string; grade: number; enrollmentStatus: AcademicStatus }
export interface Profile extends AcademicProfile { interests: string[]; activityTypes: string[]; version: number }
export interface AuthUser {
  id: string; username: string; onboardingCompleted: boolean; profileVersion: number
  academicDraft: AcademicProfile | null
  preferenceDraft: Pick<Profile, 'interests' | 'activityTypes'>
  profile: Profile | null
}
export interface Notice {
  id: number; title: string; source: string; sourceCode: SourceCode; publishedAt: string
  category: Category; summary: string[]; deadlineLabel: string; isClosed: boolean; isDeadlineSoon: boolean
  isBookmarked: boolean; needsReview: boolean; recommendation: RecommendationDto | null; originalUrl: string
}
export interface NoticeDetail extends Notice {
  body: string; target: string | null; applicationMethod: string | null; schedules: ScheduleDto[]
  prize: NoticeDetailDto['analysis']['data']['prize']
  mileages: NoticeDetailDto['analysis']['data']['mileages']
  attachments: NoticeDetailDto['attachments']
}
export interface NoticeFilters { query: string; categories: Category[]; source?: SourceCode | 'all'; deadlineSoon?: boolean }
export interface NoticePage { items: Notice[]; total: number; page: number; pageSize: number; profileVersion: number | null }
