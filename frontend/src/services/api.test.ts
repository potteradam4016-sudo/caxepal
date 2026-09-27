import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'
import { ApiError, errorMessage, request, session } from './http'
import { failure, json, mockBackend, notice } from '../test/mockBackend'
import { calendarDays, currentSeoulMonth, shiftMonth } from '../utils/calendar'

beforeEach(() => { mockBackend().authenticate() })
describe('HTTP contract', () => {
  it('handles bodyless success and includes the bearer token', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetcher)
    await expect(api.favorite(42, true)).resolves.toBeUndefined()
    expect(fetcher).toHaveBeenCalledWith('http://localhost:3104/api/bookmarks/42', expect.objectContaining({
      method: 'POST', headers: { Authorization: 'Bearer token-alice' },
    }))
  })
  it('retains field errors and exposes retry-after on rate limits', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ error: { code: 'VALIDATION_ERROR', message: '입력 오류', details: [{ field: 'body.username', type: 'pattern' }] } }, 422)))
    await expect(request('/profile')).rejects.toMatchObject({ status: 422, details: [{ field: 'body.username', type: 'pattern' }] })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ error: { code: 'RATE_LIMIT', message: '잠시 후' } }, 429, { 'Retry-After': '30' })))
    try { await request('/profile') } catch (error) { expect(errorMessage(error)).toContain('30초 후') }
  })
  it('distinguishes network failure and does not destroy a valid session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
    await expect(request('/profile')).rejects.toMatchObject({ status: 0, code: 'NETWORK_ERROR' })
    expect(session.read()).not.toBeNull()
  })
  it('invalidates expired sessions and does not send expired tokens', async () => {
    session.save({ token: 'expired', expiresAt: 1 })
    const fetcher = vi.fn()
    vi.stubGlobal('fetch', fetcher)
    await expect(request('/profile')).rejects.toMatchObject({ status: 401 })
    expect(fetcher).not.toHaveBeenCalled()
    expect(session.read()).toBeNull()
  })
  it('discards old responses without clearing the replacement session', async () => {
    let resolve!: (response: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((done) => { resolve = done })))
    const response = request('/profile')
    session.save({ token: 'replacement', expiresAt: Date.now() / 1000 + 600 })
    resolve(failure(401, 'INVALID_SESSION'))
    await expect(response).rejects.toMatchObject({ name: 'AbortError' })
    expect(session.read()?.token).toBe('replacement')
  })
  it('ignores aborted responses even if the transport completes', async () => {
    let resolve!: (response: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((done) => { resolve = done })))
    const controller = new AbortController()
    const response = request('/profile', { signal: controller.signal })
    controller.abort(); resolve(json({}))
    await expect(response).rejects.toMatchObject({ name: 'AbortError' })
  })
  it('loads every bookmark page instead of truncating at 100', async () => {
    const fetcher = vi.fn(async (url: string) => {
      const page = Number(new URL(url).searchParams.get('page'))
      return json({ items: page === 1 ? Array.from({ length: 100 }, (_, index) => notice(index + 1)) : [notice(101)],
        page, page_size: 100, total: 101 })
    })
    vi.stubGlobal('fetch', fetcher)
    expect(await api.favorites()).toHaveLength(101)
    expect(fetcher).toHaveBeenCalledTimes(2)
  })
  it('normalizes non-JSON server errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('offline', { status: 502 })))
    await expect(request('/profile')).rejects.toBeInstanceOf(ApiError)
  })
})
describe('calendar dates', () => {
  it('uses Seoul current month and preserves leap years and year boundaries', () => {
    vi.useFakeTimers()
    try {
      vi.setSystemTime(new Date('2026-12-31T16:00:00Z'))
      expect(currentSeoulMonth()).toBe('2027-01')
      expect(shiftMonth('2026-12', 1)).toBe('2027-01')
      expect(shiftMonth('2027-01', -1)).toBe('2026-12')
      expect(calendarDays('2028-02').filter(Boolean)).toHaveLength(29)
    } finally { vi.useRealTimers() }
  })
})
