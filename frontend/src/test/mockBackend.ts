import { vi } from 'vitest'
import type { CalendarDto, InterestDto, NoticeCardDto, ProfileDto, ProfileInputDto, UserDto } from '../services/contracts'
import { session } from '../services/http'

export const interests: InterestDto[] = [
  { id: 'ai_sw', name: 'AI·SW', type: 'field' }, { id: 'arts', name: '문화·예술', type: 'field' },
  { id: 'hackathon', name: '해커톤', type: 'activity' }, { id: 'volunteer', name: '봉사활동', type: 'activity' },
]
export const password = 'test-password-123'
export function notice(id = 1): NoticeCardDto {
  return { id, title: `시험 공지 ${id}`, source_code: 'SCNU_SW', source_name: 'SW중심대학사업단', posted_date: '2026-09-20',
    original_url: 'https://www.scnu.ac.kr/', category: id % 2 ? 'education' : 'contest', summary_lines: ['대상: 재학생', '활동: 교육', '일정: 원문 확인'],
    deadline_date: null, deadline_at: null, d_day: null, deadline_label: '마감 미정', is_closed: false,
    is_bookmarked: false, needs_review: false, recommendation: { score: 2, grade: 'low', reasons: ['학적 조건 일치'], breakdown: [], policy_version: '1' } }
}
function makeProfile(id: string, completed: boolean): ProfileDto {
  return { user_id: id, department: completed ? '컴퓨터공학과' : null, grade: completed ? 2 : null, academic_status: completed ? 'enrolled' : null,
    interests: completed ? [interests[0], interests[2]] : [], onboarding_complete: completed, version: completed ? 1 : 0, updated_at: 1 }
}
export const json = (body: unknown, status = 200, headers?: HeadersInit) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })
export const failure = (status: number, code: string, message = code) => json({ error: { code, message, details: [], request_id: 'test' } }, status)

export function mockBackend() {
  const users = new Map<string, { account: UserDto; profile: ProfileDto; favorites: Set<number> }>()
  const addUser = (name: string, completed = true) => {
    const account = { id: name, username: name, is_admin: false, onboarding_complete: completed }
    const value = { account, profile: makeProfile(name, completed), favorites: new Set<number>() }
    users.set(name, value)
    return value
  }
  addUser('alice'); addUser('bob')
  const notices = Array.from({ length: 23 }, (_, index) => notice(index + 1))
  const calendars = new Map<string, CalendarDto>()
  const errors = new Map<string, Response>()
  const fetcher = vi.fn(async (input: string | URL | Request, init?: RequestInit): Promise<Response> => {
    const url = new URL(String(input))
    const path = url.pathname.replace('/api', '')
    const method = init?.method ?? 'GET'
    const key = `${method} ${path}`
    const custom = errors.get(key)
    if (custom) return custom.clone()
    const name = new Headers(init?.headers).get('Authorization')?.replace('Bearer token-', '')
    const user = name ? users.get(name) : undefined
    const body = init?.body ? JSON.parse(String(init.body)) : {}
    if (path === '/auth/register') {
      if (users.has(body.username)) return failure(409, 'USERNAME_TAKEN', '이미 사용 중인 아이디입니다.')
      addUser(body.username, false)
      return json({ message: '가입 완료' }, 201)
    }
    if (path === '/auth/login') {
      const found = users.get(body.username)
      if (!found || body.password !== password) return failure(401, 'INVALID_CREDENTIALS', '아이디 또는 비밀번호가 올바르지 않습니다.')
      return json({ access_token: `token-${body.username}`, token_type: 'bearer', expires_at: Date.now() / 1000 + 3600, user: found.account })
    }
    if (path === '/interests') return json(interests)
    if (path === '/sources') return json([{ code: 'SCNU_SW', name: 'SW중심대학사업단', list_url: '', enabled: true, last_success_at: null }])
    if (!user) return failure(401, 'INVALID_SESSION')
    if (path === '/auth/me') return json(user.account)
    if (path === '/auth/logout') return new Response(null, { status: 204 })
    if (path === '/profile') {
      if (method === 'PUT') {
        const next = body as ProfileInputDto
        if (next.expected_version !== user.profile.version) return failure(409, 'PROFILE_CONFLICT', '정보가 이미 변경되었습니다. 새로 조회해주세요.')
        const selected = interests.filter((item) => next.interest_ids.includes(item.id))
        const complete = selected.some((item) => item.type === 'field') && selected.some((item) => item.type === 'activity')
        user.profile = { user_id: user.account.id, department: next.department, grade: next.grade, academic_status: next.academic_status,
          interests: selected, onboarding_complete: complete, version: user.profile.version + 1, updated_at: 2 }
        user.account.onboarding_complete = complete
      }
      return json(user.profile)
    }
    if (path.startsWith('/bookmarks/')) {
      const id = Number(path.split('/').pop())
      if (method === 'POST') user.favorites.add(id); else user.favorites.delete(id)
      return new Response(null, { status: 204 })
    }
    if (path === '/calendar') {
      const month = url.searchParams.get('month')!
      return json(calendars.get(month) ?? { month, timezone: 'Asia/Seoul', end_inclusive: true, events: [], undated: [] })
    }
    if (/^\/notices\/\d+$/.test(path)) {
      const item = notices.find((value) => value.id === Number(path.split('/').pop()))
      if (!item) return failure(404, 'NOTICE_NOT_FOUND', '공지를 찾을 수 없습니다.')
      return json({ ...item, is_bookmarked: user.favorites.has(item.id), body_text: '시험 본문', attachments: [{ name: '자료', url: null }],
        content_hash: '', image_only: false, fetched_at: 1, analysis: { provider: 'rules', status: 'reviewed', warnings: [], analyzed_at: 1, data: {
          target_text: null, application_method: null, schedules: [], prize: { status: 'not_stated', description: null, evidence: null },
          mileages: [{ system: '마일리지', points_text: '최대 10~20점', condition: null, evidence: '시험' }] } } })
    }
    const categories = url.searchParams.getAll('category')
    const query = url.searchParams.get('q') ?? ''
    const all = notices.filter((item) => (path !== '/bookmarks' || user.favorites.has(item.id)) &&
      (!categories.length || categories.includes(item.category)) && item.title.includes(query))
    const page = Number(url.searchParams.get('page') ?? 1)
    const size = Number(url.searchParams.get('page_size') ?? 20)
    return json({ items: all.slice((page - 1) * size, page * size).map((item) => ({ ...item, is_bookmarked: user.favorites.has(item.id) })),
      total: all.length, page, page_size: size, profile_version: user.profile.version })
  })
  vi.stubGlobal('fetch', fetcher)
  return { users, notices, calendars, errors, fetcher, addUser,
    authenticate(name = 'alice') { session.save({ token: `token-${name}`, expiresAt: Date.now() / 1000 + 3600 }) } }
}
