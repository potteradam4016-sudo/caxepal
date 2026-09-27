import { useCallback, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { ViewState } from '../components/ViewState'
import { useApp } from '../context/AppContext'
import { useApiResource } from '../hooks/useApiResource'
import type { useNoticeOverlay } from '../hooks/useNoticeOverlay'
import { api } from '../services/api'
import { errorMessage } from '../services/http'
import { calendarDays, currentSeoulMonth, shiftMonth } from '../utils/calendar'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']
export function CalendarPage() {
  const overlay = useOutletContext<ReturnType<typeof useNoticeOverlay>>()
  const { favoritesRevision } = useApp()
  const [month, setMonth] = useState(currentSeoulMonth)
  const loader = useCallback((signal: AbortSignal) => {
    void favoritesRevision
    return api.calendar(month, signal)
  }, [month, favoritesRevision])
  const { data, loading, error, retry } = useApiResource(loader)
  const days = useMemo(() => calendarDays(month), [month])
  const title = `${Number(month.slice(0, 4))}년 ${Number(month.slice(5))}월`
  const events = data?.month === month ? data.events : []
  return <div className="page">
    <header className="page-header"><div><span className="eyebrow">MY SCHEDULE</span><h1>내 캘린더</h1><p>찜한 공지의 신청 일정과 실제 행사 일정을 한눈에 봐요.</p></div></header>
    <div className="calendar-layout">
      <section className="calendar-panel" aria-label={`${title} 일정`}>
        <div className="calendar-header">
          <button className="icon-button" aria-label="이전 달" disabled={month === '1900-01'} onClick={() => setMonth((current) => shiftMonth(current, -1))}>←</button>
          <h2>{title}</h2>
          <button className="icon-button" aria-label="다음 달" disabled={month === '2200-12'} onClick={() => setMonth((current) => shiftMonth(current, 1))}>→</button>
        </div>
        {loading ? <ViewState state="loading" /> : error ? <ViewState state="error" message={errorMessage(error)} onRetry={retry} /> : <>
          {!events.length && <p className="muted-copy" role="status">이번 달에 표시할 일정이 없습니다.</p>}
          <div className="calendar-grid calendar-grid--weekdays">{WEEKDAYS.map((day) => <div key={day}>{day}</div>)}</div>
          <div className="calendar-grid calendar-grid--days">{days.map((date, index) => {
            if (!date) return <div className="calendar-day calendar-day--muted" aria-hidden="true" key={`blank-${index}`} />
            return <div className="calendar-day" key={date}><time dateTime={date}>{Number(date.slice(8))}</time>
              {events.filter((event) => event.display_start <= date && date <= event.display_end).map((event) =>
                <button className={`calendar-event calendar-event--${event.kind === 'event' ? 'activity' : 'application'}`} title={`${event.title}: ${event.start_date ?? '시작일 미정'} ~ ${event.end_date ?? '종료일 미정'}`} onClick={() => overlay.openNotice(event.notice_id)} key={event.id}>
                  <b>{event.label}</b><span>{event.title}</span>
                  {event.is_partial && <small>일부 날짜 미정</small>}
                  {event.continues_before_month && date === event.display_start && <small>이전 달부터</small>}
                  {event.continues_after_month && date === event.display_end && <small>다음 달까지</small>}
                </button>)}
            </div>
          })}</div>
        </>}
      </section>
      <aside className="calendar-side">
        <section><h2>일정 구분</h2><div className="legend"><span><i className="legend__swatch legend__swatch--application" />신청 일정</span><span><i className="legend__swatch legend__swatch--activity" />행사 일정</span></div></section>
        <section className="undated-list"><h2>일정 미정</h2>{!loading && !error && (data?.undated.length ?
          data.undated.map((item, index) => <button key={`${item.notice_id}-${index}`} onClick={() => overlay.openNotice(item.notice_id)}><b>{item.title}</b><span>{item.label}</span></button>) :
          <p className="muted-copy">일정 미정 공지가 없습니다.</p>)}</section>
      </aside>
    </div>
  </div>
}
