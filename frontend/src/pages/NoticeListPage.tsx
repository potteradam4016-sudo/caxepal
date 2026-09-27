import { useEffect, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { NoticeCard } from '../components/NoticeCard'
import { ViewState } from '../components/ViewState'
import { useApp } from '../context/AppContext'
import { useApiResource } from '../hooks/useApiResource'
import type { useNoticeOverlay } from '../hooks/useNoticeOverlay'
import { useNotices } from '../hooks/useNotices'
import { api } from '../services/api'
import { errorMessage } from '../services/http'
import { CATEGORY_LABELS, NOTICE_CATEGORIES, type NoticeCategory, type NoticeFilters, type NoticeSource } from '../types'

export function NoticeListPage({ kind }: { kind: 'recommended' | 'new' }) {
  const overlay = useOutletContext<ReturnType<typeof useNoticeOverlay>>()
  const { favorites, favoritePending, favoritesLoading, favoritesError, toggleFavorite } = useApp()
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<NoticeFilters>({ query: '', categories: [], source: 'all', deadlineSoon: false })
  const [page, setPage] = useState(1)
  const sources = useApiResource(api.sources)
  useEffect(() => {
    if (query.trim() === filters.query) return
    const timer = window.setTimeout(() => { setFilters((current) => ({ ...current, query: query.trim() })); setPage(1) }, 300)
    return () => window.clearTimeout(timer)
  }, [query, filters.query])
  const stableFilters = useMemo(() => filters, [filters])
  const { data, loading, error, retry } = useNotices(kind, stableFilters, page)
  const recommended = kind === 'recommended'
  const update = (next: Partial<NoticeFilters>) => { setFilters((current) => ({ ...current, ...next })); setPage(1) }
  const reset = () => { setQuery(''); update({ query: '', categories: [], source: 'all', deadlineSoon: false }) }
  const toggle = (category: NoticeCategory) => update({ categories: filters.categories.includes(category) ? filters.categories.filter((item) => item !== category) : [...filters.categories, category] })
  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / 20))
  return <div className="page">
    <header className="page-header"><div><span className="eyebrow">{recommended ? 'FOR YOU' : 'RECENTLY ADDED'}</span>
      <h1>{recommended ? '추천 공지' : '신규 공지'}</h1><p>{recommended ? '학적·관심 분야·활동 유형을 바탕으로 추천해요.' : '원문 등록일 기준 최신 공지를 확인하세요.'}</p></div>
      {recommended && <button className="button button--secondary" onClick={overlay.openProfile}>관심사 변경</button>}
    </header>
    <div className="toolbar toolbar--split">
      <label className="search-field"><span className="sr-only">{recommended ? '추천 공지 검색' : '신규 공지 검색'}</span>
        <input value={query} maxLength={100} onChange={(event) => setQuery(event.target.value)} placeholder="공지 검색" /></label>
      <label className="select-field"><span className="sr-only">출처 선택</span><select disabled={sources.loading || Boolean(sources.error)} value={filters.source} onChange={(event) => update({ source: event.target.value as NoticeSource | 'all' })}>
        <option value="all">전체 출처</option>{sources.data?.map((source) => <option value={source.code} key={source.code}>{source.name}</option>)}
      </select></label>
    </div>
    {Boolean(sources.error) && <div className="form-alert" role="alert">{errorMessage(sources.error)} <button onClick={sources.retry}>출처 다시 불러오기</button></div>}
    <div className="filter-row" aria-label={recommended ? '추천 공지 필터' : '신규 공지 필터'}>
      <button className={`chip ${!filters.categories.length && !filters.deadlineSoon ? 'chip--active' : ''}`} aria-pressed={!filters.categories.length && !filters.deadlineSoon} onClick={() => update({ categories: [], deadlineSoon: false })}>전체</button>
      <button className={`chip ${filters.deadlineSoon ? 'chip--active chip--deadline' : ''}`} aria-pressed={filters.deadlineSoon} onClick={() => update({ deadlineSoon: !filters.deadlineSoon })}>마감 임박</button>
      {NOTICE_CATEGORIES.map((category) => <button className={`chip ${filters.categories.includes(category) ? 'chip--active' : ''}`} aria-pressed={filters.categories.includes(category)} onClick={() => toggle(category)} key={category}>{CATEGORY_LABELS[category]}</button>)}
      <button className="filter-reset" onClick={reset}>초기화</button>
    </div>
    <div className="result-heading"><b>{recommended ? '맞춤 공지' : '전체 공지'}</b>{!loading && !error && <span>{data?.total ?? 0}개</span>}</div>
    {loading ? <ViewState state="loading" /> : error ? <ViewState state="error" message={errorMessage(error)} onRetry={retry} /> :
      data?.items.length ? <div className="card-list">{data.items.map((notice) =>
        <NoticeCard notice={notice} favorite={favoritesLoading ? notice.isBookmarked : favorites.has(notice.id)}
          pending={favoritesLoading || Boolean(favoritesError) || favoritePending.has(notice.id)} showRecommendation={recommended}
          onOpen={overlay.openNotice} onToggleFavorite={(id) => void toggleFavorite(id)} key={notice.id} />)}</div> :
        <ViewState state="empty" onReset={reset} />}
    <nav className="pagination" aria-label="공지 페이지">
      <button className="icon-button" aria-label="이전 페이지" disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)}>←</button>
      <span>{page} / {totalPages}</span>
      <button className="icon-button" aria-label="다음 페이지" disabled={loading || Boolean(error) || page >= totalPages} onClick={() => setPage((value) => value + 1)}>→</button>
    </nav>
  </div>
}
