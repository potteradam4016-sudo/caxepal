const SESSION_KEY = 'scnu-pick:api:v1:session'
const SESSION_EVENT = 'scnu-pick:session-expired'
export interface Session { token: string; expiresAt: number }

export const session = {
  key: SESSION_KEY,
  read(): Session | null {
    try {
      const value = JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? 'null') as Session | null
      return value && typeof value.token === 'string' && value.token.length > 0 && Number.isFinite(value.expiresAt) ? value : null
    } catch { return null }
  },
  save(value: Session) { sessionStorage.setItem(SESSION_KEY, JSON.stringify(value)) },
  clear() { sessionStorage.removeItem(SESSION_KEY) },
  subscribe(listener: () => void) {
    window.addEventListener(SESSION_EVENT, listener)
    return () => window.removeEventListener(SESSION_EVENT, listener)
  },
}

export class ApiError extends Error {
  status: number
  code: string
  details: { field: string; type: string }[]
  retryAfter: string | null
  constructor(status: number, code: string, message: string, details: { field: string; type: string }[] = [], retryAfter: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.retryAfter = retryAfter
  }
}

export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return '요청을 처리하지 못했습니다. 다시 시도해 주세요.'
  if (error.status === 429) return `요청이 많습니다. ${error.retryAfter && /^\d+$/.test(error.retryAfter) ? `${error.retryAfter}초 후` : '잠시 후'} 다시 시도해 주세요.`
  return error.message
}
export const isAbort = (error: unknown) => error instanceof DOMException && error.name === 'AbortError'
export const isConflict = (error: unknown) => error instanceof ApiError && error.code === 'PROFILE_CONFLICT'

function expire(token: string) {
  if (session.read()?.token !== token) return
  session.clear()
  window.dispatchEvent(new Event(SESSION_EVENT))
}

export async function request<T>(path: string, options: { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean } = {}): Promise<T> {
  const saved = options.auth === false ? null : session.read()
  if (saved && saved.expiresAt * 1000 <= Date.now()) {
    expire(saved.token)
    throw new ApiError(401, 'INVALID_SESSION', '로그인 시간이 만료되었습니다. 다시 로그인해 주세요.')
  }
  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (saved) headers.Authorization = `Bearer ${saved.token}`
  const base = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:3104').replace(/\/+$/, '')
  let response: Response
  try {
    response = await fetch(`${base}/api${path}`, { method: options.method ?? 'GET', headers, signal: options.signal,
      body: options.body === undefined ? undefined : JSON.stringify(options.body) })
  } catch (error) {
    if (isAbort(error)) throw error
    throw new ApiError(0, 'NETWORK_ERROR', '서버에 연결하지 못했습니다. 연결 상태를 확인하고 다시 시도해 주세요.')
  }
  // Ignore responses issued under a session that has since been replaced or cleared.
  if (options.signal?.aborted || (saved && session.read()?.token !== saved.token)) throw new DOMException('Stale request', 'AbortError')
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const info = payload?.error
    if (response.status === 401 && saved && info?.code !== 'INVALID_CREDENTIALS') expire(saved.token)
    throw new ApiError(response.status, info?.code ?? 'HTTP_ERROR', info?.message ?? '서버 오류가 발생했습니다. 다시 시도해 주세요.', info?.details ?? [], response.headers.get('Retry-After'))
  }
  if (response.status === 204) return undefined as T
  const data: T = await response.json()
  if (options.signal?.aborted || (saved && session.read()?.token !== saved.token)) throw new DOMException('Stale request', 'AbortError')
  return data
}
