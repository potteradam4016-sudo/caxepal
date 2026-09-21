interface ViewStateProps {
  state: 'loading' | 'empty' | 'error'
  message?: string
  onRetry?: () => void
  onReset?: () => void
}

export function ViewState({ state, message, onRetry, onReset }: ViewStateProps) {
  if (state === 'loading') {
    return (
      <div className="skeleton-list" aria-label="공지 목록을 불러오는 중입니다" aria-busy="true">
        {[0, 1, 2].map((item) => <div className="skeleton-card" key={item} />)}
      </div>
    )
  }

  const isError = state === 'error'
  return (
    <div className="state-panel" role={isError ? 'alert' : 'status'}>
      <span className="state-panel__icon" aria-hidden="true">{isError ? '!' : '⌕'}</span>
      <h2>{isError ? '공지를 불러오지 못했습니다' : '조건에 맞는 공지가 없습니다'}</h2>
      <p>{message ?? (isError ? '잠시 후 다시 시도해 주세요.' : '검색어나 필터를 바꿔보세요.')}</p>
      {isError && onRetry && <button className="button button--primary" onClick={onRetry}>다시 시도</button>}
      {!isError && onReset && <button className="button button--secondary" onClick={onReset}>필터 초기화</button>}
    </div>
  )
}
