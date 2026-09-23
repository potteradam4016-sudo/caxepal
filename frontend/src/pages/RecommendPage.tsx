import { useCallback, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { DevScenarioPanel } from '../components/DevScenarioPanel'
import { NoticeCard } from '../components/NoticeCard'
import { ViewState } from '../components/ViewState'
import { useApp } from '../context/AppContext'
import type { useNoticeOverlay } from '../hooks/useNoticeOverlay'
import { useNotices } from '../hooks/useNotices'
import { mockNoticeService } from '../services/mockNoticeService'
import { NOTICE_CATEGORIES, type AsyncState, type NoticeCategory, type NoticeFilters } from '../types'

const FILTER_CATEGORIES = NOTICE_CATEGORIES.filter((category) => category !== '취업')

export function RecommendPage() {
  const overlay = useOutletContext<ReturnType<typeof useNoticeOverlay>>()
  const { favorites, favoritePending, toggleFavorite, profile, profileRevision } = useApp()
  const [query, setQuery] = useState('')
  const [categories, setCategories] = useState<NoticeCategory[]>([])
  const [deadlineSoon, setDeadlineSoon] = useState(false)
  const [scenario, setScenario] = useState<AsyncState>('success')
  const filters = useMemo<NoticeFilters>(() => ({ query, categories, deadlineSoon }), [query, categories, deadlineSoon])
  const loadRecommendations = useCallback((nextFilters: NoticeFilters) => mockNoticeService.listRecommended(nextFilters, profile ?? undefined), [profile])
  const { notices, loading, error, retry } = useNotices(loadRecommendations, filters, profileRevision)

  const reset = () => {
    setQuery('')
    setCategories([])
    setDeadlineSoon(false)
    setScenario('success')
  }

  const toggleCategory = (category: NoticeCategory) => {
    setCategories((current) => current.includes(category) ? current.filter((item) => item !== category) : [...current, category])
  }

  const displayState = scenario !== 'success' ? scenario : error ? 'error' : loading ? 'loading' : notices.length ? 'success' : 'empty'

  return (
    <div className="page">
      <header className="page-header">
        <div><span className="eyebrow">FOR YOU</span><h1>추천 공지</h1><p>학적·관심 분야·활동 유형을 바탕으로 추천해요.</p></div>
        <button className="button button--secondary" type="button" onClick={overlay.openProfile}>관심사 변경</button>
      </header>
      <div className="toolbar">
        <label className="search-field">
          <span aria-hidden="true">⌕</span>
          <span className="sr-only">추천 공지 검색</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="공지 제목이나 키워드 검색" />
        </label>
      </div>
      <div className="filter-row" aria-label="추천 공지 필터">
        <button className={`chip ${categories.length === 0 && !deadlineSoon ? 'chip--active' : ''}`} type="button" aria-pressed={categories.length === 0 && !deadlineSoon} onClick={() => { setCategories([]); setDeadlineSoon(false) }}>전체</button>
        <button className={`chip ${deadlineSoon ? 'chip--active chip--deadline' : ''}`} type="button" aria-pressed={deadlineSoon} onClick={() => setDeadlineSoon((value) => !value)}>마감 임박</button>
        {FILTER_CATEGORIES.map((category) => <button className={`chip ${categories.includes(category) ? 'chip--active' : ''}`} type="button" aria-pressed={categories.includes(category)} onClick={() => toggleCategory(category)} key={category}>{category}</button>)}
        <button className="filter-reset" type="button" onClick={reset}>초기화</button>
      </div>
      <DevScenarioPanel value={scenario} onChange={setScenario} />
      <div className="result-heading"><b>맞춤 공지</b>{displayState === 'success' && <span>{notices.length}개의 추천</span>}</div>
      {displayState === 'loading' && <ViewState state="loading" />}
      {displayState === 'error' && <ViewState state="error" onRetry={() => { setScenario('success'); retry() }} />}
      {displayState === 'empty' && <ViewState state="empty" onReset={reset} />}
      {displayState === 'success' && (
        <div className="card-list">
          {notices.map((notice) => <NoticeCard notice={notice} favorite={favorites.has(notice.id)} pending={favoritePending.has(notice.id)} showRecommendation onOpen={overlay.openNotice} onToggleFavorite={(id) => void toggleFavorite(id)} key={notice.id} />)}
        </div>
      )}
    </div>
  )
}
