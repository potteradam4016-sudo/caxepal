import type { KeyboardEvent, MouseEvent } from 'react'
import { CATEGORY_LABELS, type Notice } from '../types'

export function NoticeCard({ notice, favorite, pending, showRecommendation = false, onOpen, onToggleFavorite }: {
  notice: Notice; favorite: boolean; pending: boolean; showRecommendation?: boolean
  onOpen: (id: number) => void; onToggleFavorite: (id: number) => void
}) {
  const openWithKeyboard = (event: KeyboardEvent<HTMLElement>) => {
    if (event.target !== event.currentTarget) return
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onOpen(notice.id) }
  }
  const toggle = (event: MouseEvent<HTMLButtonElement>) => { event.stopPropagation(); onToggleFavorite(notice.id) }
  return <article className="notice-card" role="button" tabIndex={0} aria-label={`${notice.title} 상세 보기`} onClick={() => onOpen(notice.id)} onKeyDown={openWithKeyboard}>
    <div className="notice-card__head"><div className="notice-card__content">
      <span className="notice-source">{notice.source} · <time dateTime={notice.publishedAt}>{notice.publishedAt}</time></span>
      <h2>{notice.title}</h2><div className="badges">
        {showRecommendation && notice.recommendation && <span className="badge badge--score">추천도 {notice.recommendation.score}%</span>}
        <span className="badge">{CATEGORY_LABELS[notice.category]}</span>
        <span className={`badge ${notice.isDeadlineSoon ? 'badge--deadline' : ''}`}>{notice.deadlineLabel}</span>
      </div></div>
      <button className={`favorite-button ${favorite ? 'favorite-button--active' : ''}`} type="button" aria-label={`${notice.title} 찜 ${favorite ? '해제' : '추가'}`} aria-pressed={favorite} disabled={pending} onClick={toggle}>
        <span aria-hidden="true">{favorite ? '♥' : '♡'}</span>
      </button>
    </div>
    <div className="notice-summary">{notice.summary.map((line, index) => <p key={index}>{line}</p>)}</div>
    {showRecommendation && notice.recommendation?.reasons.map((reason, index) => <p className="recommendation-reason" key={index}>{reason}</p>)}
  </article>
}
