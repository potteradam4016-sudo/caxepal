import { useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { NoticeCard } from '../components/NoticeCard'
import { ViewState } from '../components/ViewState'
import { useApp } from '../context/AppContext'
import type { useNoticeOverlay } from '../hooks/useNoticeOverlay'
import { useNotices } from '../hooks/useNotices'
import { mockNoticeService } from '../services/mockNoticeService'
import { NOTICE_CATEGORIES, NOTICE_SOURCES, type NoticeCategory, type NoticeFilters, type NoticeSource } from '../types'

export function NewNoticesPage() {
  const overlay = useOutletContext<ReturnType<typeof useNoticeOverlay>>()
  const { favorites, favoritePending, toggleFavorite } = useApp()
  const [query, setQuery] = useState('')
  const [source, setSource] = useState<NoticeSource | 'all'>('all')
  const [categories, setCategories] = useState<NoticeCategory[]>([])
  const [deadlineSoon, setDeadlineSoon] = useState(false)
  const filters = useMemo<NoticeFilters>(() => ({ query, source, categories, deadlineSoon }), [query, source, categories, deadlineSoon])
  const { notices, loading, error, retry } = useNotices(mockNoticeService.listNew, filters)

  const reset = () => { setQuery(''); setSource('all'); setCategories([]); setDeadlineSoon(false) }
  const toggleCategory = (category: NoticeCategory) => setCategories((current) => current.includes(category) ? current.filter((item) => item !== category) : [...current, category])

  return (
    <div className="page">
      <header className="page-header"><div><span className="eyebrow">RECENTLY ADDED</span><h1>신규 공지</h1><p>원문 등록일 기준 최신 공지를 확인하세요.</p></div></header>
      <div className="toolbar toolbar--split">
        <label className="search-field"><span aria-hidden="true">⌕</span><span className="sr-only">신규 공지 검색</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="신규 공지 검색" /></label>
        <label className="select-field"><span className="sr-only">출처 선택</span><select value={source} onChange={(event) => setSource(event.target.value as NoticeSource | 'all')}><option value="all">전체 출처</option>{NOTICE_SOURCES.map((item) => <option key={item}>{item}</option>)}</select></label>
      </div>
      <div className="filter-row" aria-label="신규 공지 필터">
        <span className="sort-label">최신순</span>
        <button className={`chip ${deadlineSoon ? 'chip--active chip--deadline' : ''}`} type="button" aria-pressed={deadlineSoon} onClick={() => setDeadlineSoon((value) => !value)}>마감 임박</button>
        {NOTICE_CATEGORIES.slice(0, 3).map((category) => <button className={`chip ${categories.includes(category) ? 'chip--active' : ''}`} type="button" aria-pressed={categories.includes(category)} onClick={() => toggleCategory(category)} key={category}>{category}</button>)}
        <button className="filter-reset" type="button" onClick={reset}>초기화</button>
      </div>
      <div className="result-heading"><b>전체 공지</b>{!loading && !error && <span>{notices.length}개</span>}</div>
      {loading && <ViewState state="loading" />}
      {error && !loading && <ViewState state="error" onRetry={retry} />}
      {!loading && !error && notices.length === 0 && <ViewState state="empty" onReset={reset} />}
      {!loading && !error && notices.length > 0 && <div className="card-list">{notices.map((notice) => <NoticeCard notice={notice} favorite={favorites.has(notice.id)} pending={favoritePending.has(notice.id)} onOpen={overlay.openNotice} onToggleFavorite={(id) => void toggleFavorite(id)} key={notice.id} />)}</div>}
    </div>
  )
}
