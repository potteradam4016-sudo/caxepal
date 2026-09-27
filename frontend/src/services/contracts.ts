export type AcademicStatus = 'enrolled' | 'on_leave' | 'graduating' | 'graduated'
export type SourceCode = 'SCNU_MAIN' | 'SCNU_SW' | 'SCNU_AI'
export type Category = 'contest' | 'education' | 'scholarship' | 'career' | 'startup' | 'overseas' | 'volunteer' | 'other'
export interface InterestDto { id: string; name: string; type: 'field' | 'activity' }
export interface SourceDto { code: SourceCode; name: string; list_url: string; enabled: boolean; last_success_at: number | null }
export interface UserDto { id: string; username: string; is_admin: boolean; onboarding_complete: boolean }
export interface LoginDto { access_token: string; token_type: 'bearer'; expires_at: number; user: UserDto }
export interface ProfileDto {
  user_id: string; department: string | null; grade: number | null; academic_status: AcademicStatus | null
  interests: InterestDto[]; onboarding_complete: boolean; version: number; updated_at: number
}
export interface ProfileInputDto {
  department: string; grade: number; academic_status: AcademicStatus; interest_ids: string[]; expected_version: number
}
export interface RecommendationDto {
  score: number; grade: string; reasons: string[]
  breakdown: { criterion: string; score: number; max_score: number; reason: string | null }[]
  policy_version: string
}
export interface NoticeCardDto {
  id: number; title: string; source_code: SourceCode; source_name: string; posted_date: string; original_url: string
  category: Category; summary_lines: string[]; deadline_date: string | null; deadline_at: number | null
  d_day: number | null; deadline_label: string; is_closed: boolean; is_bookmarked: boolean
  needs_review: boolean; recommendation: RecommendationDto | null
}
export interface NoticePageDto { items: NoticeCardDto[]; total: number; page: number; page_size: number; profile_version?: number | null }
export interface ScheduleDto {
  kind: 'application' | 'event'; label: string; start_date: string | null; end_date: string | null
  start_time: string | null; end_time: string | null; evidence: string
}
export interface NoticeDetailDto extends NoticeCardDto {
  body_text: string; attachments: { name: string; url: string | null }[]; content_hash: string; image_only: boolean; fetched_at: number
  analysis: { provider: string; status: string; warnings: string[]; analyzed_at: number; data: {
    target_text: string | null; summary_lines: string[]; schedules: ScheduleDto[]; application_method: string | null
    prize: { status: 'present' | 'none' | 'not_stated'; description: string | null; evidence: string | null }
    mileages: { system: string; points_text: string | null; condition: string | null; evidence: string }[]
  } }
}
export interface CalendarDto {
  month: string; timezone: 'Asia/Seoul'; end_inclusive: boolean
  events: { id: string; notice_id: number; title: string; kind: 'application' | 'event'; label: string
    start_date: string | null; end_date: string | null; start_time: string | null; end_time: string | null
    display_start: string; display_end: string; is_partial: boolean; continues_before_month: boolean; continues_after_month: boolean }[]
  undated: { notice_id: number; title: string; label: string }[]
}
