import type { AsyncState } from '../types'

export function DevScenarioPanel({ value, onChange }: { value: AsyncState; onChange: (state: AsyncState) => void }) {
  if (!import.meta.env.DEV) return null
  return (
    <details className="dev-panel">
      <summary>개발용 상태 시나리오</summary>
      <div className="dev-panel__actions">
        {(['success', 'loading', 'empty', 'error'] as AsyncState[]).map((state) => (
          <button
            className={`button button--small ${value === state ? 'button--primary' : 'button--secondary'}`}
            type="button"
            key={state}
            onClick={() => onChange(state)}
          >
            {{ success: '정상', loading: '로딩', empty: '빈 상태', error: '오류', idle: '대기' }[state]}
          </button>
        ))}
      </div>
    </details>
  )
}
