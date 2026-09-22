import { describe, expect, it } from 'vitest'
import { mockNoticeService, storageKeys } from './mockNoticeService'

describe('mockNoticeService', () => {
  it('filters recommendations by query and multiple categories', async () => {
    const result = await mockNoticeService.listRecommended({
      query: '개발',
      categories: ['프로젝트', '교육/특강'],
      deadlineSoon: false,
    })

    expect(result.map((notice) => notice.id)).toEqual(['ai-project', 'opensource-lecture'])
  })

  it('sorts new notices by published date descending', async () => {
    const result = await mockNoticeService.listNew({ query: '', categories: [], source: 'all' })
    expect(result[0].id).toBe('extracurricular-guide')
    expect(result.at(-1)?.id).toBe('career-mentoring')
  })

  it('persists favorites and derives calendar events', async () => {
    await mockNoticeService.toggleFavorite('career-mentoring', true)
    const schedules = await mockNoticeService.getFavoriteSchedules()

    expect(JSON.parse(localStorage.getItem(storageKeys.favorites()) ?? '[]')).toContain('career-mentoring')
    expect(schedules.undated.map((notice) => notice.id)).toContain('career-mentoring')
    expect(schedules.events.some((event) => event.noticeId === 'ai-project' && event.label === '신청 마감')).toBe(true)
  })

  it('falls back safely when persisted profile is invalid', async () => {
    localStorage.setItem(storageKeys.profile(), '{broken json')
    await expect(mockNoticeService.getProfile()).resolves.toMatchObject({ department: '컴퓨터공학과' })
  })

  it('keeps favorites separated by username', async () => {
    await mockNoticeService.toggleFavorite('career-mentoring', true, 'userone')
    expect(mockNoticeService.getFavoriteIds('userone')).toContain('career-mentoring')
    expect(mockNoticeService.getFavoriteIds('usertwo')).not.toContain('career-mentoring')
  })
})
