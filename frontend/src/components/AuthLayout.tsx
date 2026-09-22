import type { ReactNode } from 'react'

export function AuthLayout({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <main className="auth-layout">
      <section className="auth-story" aria-label="SCNU PICK 소개">
        <div className="auth-brand">
          <span className="auth-brand__mark"><img src="/icons/SCNU_PICK_icon.png?v=20260922-2" alt="" /></span>
          <span>SCNU PICK<small>교내 공지 추천 서비스</small></span>
        </div>
        <div className="auth-story__copy">
          <span className="auth-story__eyebrow">NOTICE, PICKED FOR YOU</span>
          <h1>놓치기 쉬운 교내 공지를<br />내게 맞게 골라보세요.</h1>
          <p>학적과 관심 분야를 바탕으로 필요한 공지를 모아보고, 찜한 일정은 캘린더에서 관리할 수 있어요.</p>
        </div>
        <p className="auth-story__foot">Sunchon National University</p>
      </section>
      <section className="auth-content">
        <div className={`auth-panel ${wide ? 'auth-panel--wide' : ''}`}>{children}</div>
      </section>
    </main>
  )
}

export function StepIndicator({ current }: { current: 1 | 2 | 3 }) {
  const steps = ['학적 정보', '관심사 선택', '등록 완료']
  return (
    <ol className="step-indicator" aria-label="최초 등록 진행 단계">
      {steps.map((label, index) => {
        const number = index + 1
        const state = number < current ? 'done' : number === current ? 'current' : 'upcoming'
        return <li className={`step-indicator__item step-indicator__item--${state}`} aria-current={state === 'current' ? 'step' : undefined} key={label}><span>{number < current ? '✓' : number}</span><b>{label}</b></li>
      })}
    </ol>
  )
}
