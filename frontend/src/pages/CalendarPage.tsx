import { useCallback, useEffect, useMemo, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { ViewState } from '../components/ViewState'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import type { useNoticeOverlay } from '../hooks/useNoticeOverlay'
import { mockNoticeService } from '../services/mockNoticeService'
import type { CalendarEvent, FavoriteSchedules } from '../types'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

export function CalendarPage() {
  const overlay = useOutletContext<ReturnType<typeof useNoticeOverlay>>()
  const { favorites } = useApp()
  const { user } = useAuth()
  const [cursor, setCursor] = useState(() => new Date(2026, 8, 1))
  const [data, setData] = useState<FavoriteSchedules>({ events: [], undated: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    let active = true
    void Promise.resolve()
      .then(() => {
        if (active) {
          setLoading(true)
          setError(false)
        }
        return mockNoticeService.getFavoriteSchedules(user?.username)
      })
      .then((result) => { if (active) setData(result) })
      .catch(() => { if (active) setError(true) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [favorites, revision, user?.username])

  const changeMonth = useCallback((amount: number) => {
    setCursor((current) => new Date(current.getFullYear(), current.getMonth() + amount, 1))
  }, [])

  const days = useMemo(() => buildMonth(cursor), [cursor])
  const eventMap = useMemo(() => data.events.reduce<Record<string, CalendarEvent[]>>((map, event) => {
    ;(map[event.date] ??= []).push(event)
    return map
  }, {}), [data.events])
  const hasAnySchedule = data.events.length > 0 || data.undated.length > 0

  return (
    <div className="page">
      <header className="page-header"><div><span className="eyebrow">MY SCHEDULE</span><h1>내 캘린더</h1><p>찜한 공지의 신청 일정과 실제 행사 일정을 한눈에 봐요.</p></div></header>
      {loading && <ViewState state="loading" />}
      {error && !loading && <ViewState state="error" onRetry={() => setRevision((value) => value + 1)} />}
      {!loading && !error && !hasAnySchedule && <ViewState state="empty" message="찜한 공지가 없거나 표시할 일정이 없습니다." />}
      {!loading && !error && hasAnySchedule && (
        <div className="calendar-layout">
          <section className="calendar-panel" aria-label={`${cursor.getFullYear()}년 ${cursor.getMonth() + 1}월 일정`}>
            <div className="calendar-header">
              <button className="icon-button" type="button" onClick={() => changeMonth(-1)} aria-label="이전 달">←</button>
              <h2>{cursor.getFullYear()}년 {cursor.getMonth() + 1}월</h2>
              <button className="icon-button" type="button" onClick={() => changeMonth(1)} aria-label="다음 달">→</button>
            </div>
            <div className="calendar-grid calendar-grid--weekdays">{WEEKDAYS.map((day) => <div key={day}>{day}</div>)}</div>
            <div className="calendar-grid calendar-grid--days">
              {days.map((day, index) => {
                if (!day) return <div className="calendar-day calendar-day--muted" aria-hidden="true" key={`blank-${index}`} />
                const isoDate = `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                return <div className="calendar-day" key={isoDate}><time dateTime={isoDate}>{day}</time>{eventMap[isoDate]?.map((event) => <button className={`calendar-event calendar-event--${event.type}`} type="button" title={event.title} onClick={() => overlay.openNotice(event.noticeId)} key={event.id}><b>{event.label}</b><span>{event.title}</span></button>)}</div>
              })}
            </div>
          </section>
          <aside className="calendar-side">
            <section><h2>일정 구분</h2><div className="legend"><span><i className="legend__swatch legend__swatch--application" />신청 일정</span><span><i className="legend__swatch legend__swatch--activity" />행사 일정</span></div></section>
            <section className="undated-list"><h2>일정 미정</h2><p>날짜가 명시되지 않은 찜 공지예요.</p>{data.undated.length ? data.undated.map((notice) => <button type="button" onClick={() => overlay.openNotice(notice.id)} key={notice.id}><b>{notice.title}</b><span>상세 보기 →</span></button>) : <span className="muted-copy">일정 미정 공지가 없습니다.</span>}</section>
          </aside>
        </div>
      )}
    </div>
  )
}

function buildMonth(date: Date): Array<number | null> {
  const blanks = Array<number | null>(new Date(date.getFullYear(), date.getMonth(), 1).getDay()).fill(null)
  const count = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
  return [...blanks, ...Array.from({ length: count }, (_, index) => index + 1)]
}
