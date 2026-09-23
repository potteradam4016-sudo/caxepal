import type { KeyboardEvent, MouseEvent } from 'react'
import type { Notice } from '../types'
import { getScheduleSummary } from '../utils/format'

interface NoticeCardProps {
  notice: Notice
  favorite: boolean
  pending: boolean
  showRecommendation?: boolean
  onOpen: (id: string) => void
  onToggleFavorite: (id: string) => void
}

export function NoticeCard({
  notice,
  favorite,
  pending,
  showRecommendation = false,
  onOpen,
  onToggleFavorite,
}: NoticeCardProps) {
  const openWithKeyboard = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onOpen(notice.id)
    }
  }

  const toggleFavorite = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    onToggleFavorite(notice.id)
  }

  return (
    <article
      className="notice-card"
      role="button"
      tabIndex={0}
      aria-label={`${notice.title} 상세 보기`}
      onClick={() => onOpen(notice.id)}
      onKeyDown={openWithKeyboard}
    >
      <div className="notice-card__head">
        <div className="notice-card__content">
          <span className="notice-source">
            {notice.source}
            {!showRecommendation && <span aria-hidden="true"> · </span>}
            {!showRecommendation && <time dateTime={notice.publishedAt}>{notice.publishedAt}</time>}
          </span>
          <h2>{notice.title}</h2>
          <div className="badges">
            {showRecommendation && notice.recommendationScore !== null && (
              <span className="badge badge--score">{notice.recommendationScore <= 3 ? `조건 일치 ${notice.recommendationScore}/3` : `추천도 ${notice.recommendationScore}%`}</span>
            )}
            {notice.isDeadlineSoon && <span className="badge badge--deadline">마감 임박</span>}
            {!showRecommendation && <span className="badge">{notice.categories[0]}</span>}
          </div>
        </div>
        <button
          className={`favorite-button ${favorite ? 'favorite-button--active' : ''}`}
          type="button"
          aria-label={favorite ? `${notice.title} 찜 해제` : `${notice.title} 찜 추가`}
          aria-pressed={favorite}
          disabled={pending}
          onClick={toggleFavorite}
        >
          <span aria-hidden="true">{favorite ? '♥' : '♡'}</span>
        </button>
      </div>
      <div className="summary-grid">
        <div><b>대상</b><span>{notice.target}</span></div>
        <div><b>활동</b><span>{notice.activity}</span></div>
        <div><b>신청·행사 일정</b><span>{getScheduleSummary(notice.schedule)}</span></div>
      </div>
      {showRecommendation && notice.recommendationReason && (
        <p className="recommendation-reason">{notice.recommendationReason}</p>
      )}
    </article>
  )
}
