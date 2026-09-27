import { useCallback } from 'react'
import { useApp } from '../context/AppContext'
import { useApiResource } from '../hooks/useApiResource'
import { api } from '../services/api'
import { ApiError, errorMessage } from '../services/http'
import { Modal } from './Modal'
import { ViewState } from './ViewState'

export function safeLink(value: string | null) {
  if (!value) return undefined
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined } catch { return undefined }
}
export function NoticeDetailModal({ noticeId, onClose }: { noticeId: number; onClose: () => void }) {
  const { favorites, favoritePending, favoritesLoading, favoritesError, toggleFavorite, profileRevision } = useApp()
  const loader = useCallback((signal: AbortSignal) => {
    void profileRevision
    if (!Number.isSafeInteger(noticeId) || noticeId < 1) return Promise.reject(new ApiError(404, 'NOTICE_NOT_FOUND', '공지를 찾을 수 없습니다.'))
    return api.detail(noticeId, signal)
  }, [noticeId, profileRevision])
  const { data: notice, loading, error, retry } = useApiResource(loader)
  return <Modal title={notice?.title ?? '공지 상세'} onClose={onClose} size="wide">
    {loading ? <ViewState state="loading" /> : error ? <ViewState state={error instanceof ApiError && error.status === 404 ? 'empty' : 'error'} message={errorMessage(error)} onRetry={retry} /> : notice &&
      <div className="detail-content">
        <div className="detail-meta"><span className="notice-source">{notice.source}</span><div className="badges">
          {notice.recommendation && <span className="badge badge--score">추천도 {notice.recommendation.score}%</span>}
          <span className="badge">{notice.deadlineLabel}</span>
        </div></div>
        {notice.analysisStatus === 'failed' ? <p className="analysis-notice" role="status">자동 분석에 실패했습니다. 신청 전 원문에서 정보를 확인해 주세요.</p>
          : notice.analysisStatus !== 'reviewed' && <p className="analysis-notice" role="status">자동 추출한 정보입니다. 신청 전 원문에서 확인해 주세요.</p>}
        <div className="notice-summary">{notice.summary.map((line, index) => <p key={index}>{line}</p>)}</div>
        <div className="detail-grid">
          <section><b>대상</b><p>{notice.target ?? '미기재'}</p>
            {notice.recruitmentText && <div className="detail-subfield"><b>모집인원</b><p>{notice.recruitmentText}</p></div>}
          </section>
          <section><b>신청 방법</b><p>{notice.applicationMethod ?? '미기재'}</p></section>
          <section><b>상금</b><p className="detail-prize">{notice.prize.status === 'none' ? '없음' : notice.prize.status === 'not_stated' ? '미기재' : notice.prize.description ?? '있음'}</p></section>
          <section><b>마일리지</b>{notice.mileages.length ? notice.mileages.map((item, index) =>
            <p key={index}>{item.system}: {item.points_text ?? '점수 미기재'} ({item.condition ?? '조건 미기재'})</p>) : <p>미기재</p>}</section>
        </div>
        {notice.recommendation && <section className="detail-reason"><h3>추천 이유</h3>{notice.recommendation.reasons.map((reason, index) => <p key={index}>{reason}</p>)}</section>}
        {!!notice.attachments.length && <section><h3>첨부파일</h3><ul>{notice.attachments.map((item, index) =>
          <li key={index}>{safeLink(item.url) ? <a href={safeLink(item.url)} target="_blank" rel="noreferrer">{item.name}</a> : item.name}</li>)}</ul></section>}
        <div className="modal-actions">
          {safeLink(notice.originalUrl) && <a className="button button--primary" href={safeLink(notice.originalUrl)} target="_blank" rel="noreferrer">원문 보기</a>}
          <button className="button button--favorite" type="button" aria-pressed={favorites.has(notice.id)}
            disabled={favoritesLoading || Boolean(favoritesError) || favoritePending.has(notice.id)} onClick={() => void toggleFavorite(notice.id)}>
            {favorites.has(notice.id) ? '♥ 찜 해제' : '♡ 찜하기'}</button>
        </div>
      </div>}
  </Modal>
}
