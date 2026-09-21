import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { mockNoticeService } from '../services/mockNoticeService'
import type { Notice } from '../types'
import { formatLongDate } from '../utils/format'
import { Modal } from './Modal'
import { ViewState } from './ViewState'

export function NoticeDetailModal({ noticeId, onClose }: { noticeId: string; onClose: () => void }) {
  const { favorites, favoritePending, toggleFavorite } = useApp()
  const [notice, setNotice] = useState<Notice | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void Promise.resolve()
      .then(() => {
        if (active) {
          setLoading(true)
          setFailed(false)
        }
        return mockNoticeService.getNotice(noticeId)
      })
      .then((result) => {
        if (active) setNotice(result)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [noticeId])

  return (
    <Modal title={notice?.title ?? '공지 상세'} onClose={onClose} size="wide">
      {loading && <ViewState state="loading" />}
      {failed && <ViewState state="error" />}
      {!loading && !failed && !notice && <ViewState state="empty" message="요청한 공지를 찾을 수 없습니다." />}
      {!loading && notice && (
        <div className="detail-content">
          <div className="detail-meta">
            <span className="notice-source">{notice.source}</span>
            <div className="badges">
              {notice.recommendationScore !== null && <span className="badge badge--score">추천도 {notice.recommendationScore}%</span>}
              {notice.isDeadlineSoon && <span className="badge badge--deadline">마감 임박</span>}
            </div>
          </div>
          <div className="detail-grid">
            <section><b>대상</b><p>{notice.target}</p></section>
            <section><b>활동</b><p>{notice.activity}</p></section>
            <section><b>신청 일정</b><p>{formatLongDate(notice.schedule.applicationStart)} ~ {formatLongDate(notice.schedule.applicationEnd)}</p></section>
            <section><b>행사 일정</b><p>{formatLongDate(notice.schedule.eventStart)} ~ {formatLongDate(notice.schedule.eventEnd)}</p></section>
            <section><b>상금</b><p>{benefitLabel(notice)}</p></section>
            <section><b>마일리지</b><p>{mileageLabel(notice)}</p></section>
          </div>
          {notice.recommendationReason && (
            <section className="detail-reason"><b>추천 이유</b><p>{notice.recommendationReason}</p></section>
          )}
          <p className="detail-note">원문에 없는 혜택·금액·날짜는 추정하지 않습니다.</p>
          <div className="modal-actions">
            {notice.originalUrl ? (
              <a className="button button--primary" href={notice.originalUrl} target="_blank" rel="noreferrer">원문 보기</a>
            ) : (
              <button className="button button--primary" type="button" disabled title="목 데이터에는 원문 URL이 없습니다">원문 링크 준비 중</button>
            )}
            <button
              className={`button button--favorite ${favorites.has(notice.id) ? 'button--favorite-active' : ''}`}
              type="button"
              aria-pressed={favorites.has(notice.id)}
              disabled={favoritePending.has(notice.id)}
              onClick={() => void toggleFavorite(notice.id)}
            >
              {favorites.has(notice.id) ? '♥ 찜 해제' : '♡ 찜하기'}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

function benefitLabel(notice: Notice) {
  if (notice.benefit.prize.state === 'present') return notice.benefit.prize.detail ?? '있음 · 세부 내용은 원문 확인'
  if (notice.benefit.prize.state === 'absent') return '없음'
  return '미기재'
}

function mileageLabel(notice: Notice) {
  if (!notice.benefit.mileage.length) return '미기재'
  return notice.benefit.mileage
    .map((item) => `${item.system}: ${item.points === null ? '점수 미기재' : `${item.points}점`} (${item.condition ?? '조건 미기재'})`)
    .join(' · ')
}
