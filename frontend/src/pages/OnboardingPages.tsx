import { useRef, useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { AuthLayout, StepIndicator } from '../components/AuthLayout'
import { useAuth } from '../context/AuthContext'
import type { AcademicProfile, Profile } from '../types'

const INTERESTS = ['AI', '개발', '창업', '취업', '장학']
const ACTIVITY_TYPES = ['프로젝트', '특강', '공모전', '멘토링']

function OnboardingHeading({ title, description }: { title: string; description: string }) {
  return <header className="onboarding-heading"><h2 tabIndex={-1}>{title}</h2><p>{description}</p></header>
}

export function AcademicPage() {
  const { user, saveAcademic } = useAuth()
  const navigate = useNavigate()
  const [draft, setDraft] = useState<Partial<AcademicProfile>>(user?.academicDraft ?? {})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState(false)
  if (!user) return <Navigate to="/login" replace />
  if (user.onboardingCompleted) return <Navigate to="/recommend" replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const department = draft.department?.trim() ?? ''
    const nextErrors: Record<string, string> = {}
    if (department.length < 1 || department.length > 60) nextErrors.department = '학과를 1~60자로 입력해 주세요.'
    if (!draft.grade) nextErrors.grade = '학년을 선택해 주세요.'
    if (!draft.enrollmentStatus) nextErrors.enrollmentStatus = '학적 상태를 선택해 주세요.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return
    setPending(true)
    try {
      await saveAcademic({ department, grade: draft.grade!, enrollmentStatus: draft.enrollmentStatus! })
      navigate('/preferences')
    } finally {
      setPending(false)
    }
  }

  return <AuthLayout wide><StepIndicator current={1} /><OnboardingHeading title="학적 정보를 알려주세요" description="추천할 공지의 대상 조건을 확인하는 데 사용해요." /><form className="onboarding-form" aria-busy={pending} onSubmit={submit}>
    <label className="auth-field" htmlFor="department"><span>학과</span><input id="department" value={draft.department ?? ''} disabled={pending} maxLength={60} placeholder="예: 컴퓨터공학과" aria-invalid={Boolean(errors.department)} onChange={(event) => setDraft({ ...draft, department: event.target.value })} />{errors.department && <small className="field-error" role="alert">{errors.department}</small>}</label>
    <div className="form-grid">
      <label className="auth-field" htmlFor="grade"><span>학년</span><select id="grade" value={draft.grade ?? ''} disabled={pending} aria-invalid={Boolean(errors.grade)} onChange={(event) => setDraft({ ...draft, grade: event.target.value as Profile['grade'] })}><option value="">선택해 주세요</option>{['1학년', '2학년', '3학년', '4학년', '5학년 이상'].map((grade) => <option key={grade}>{grade}</option>)}</select>{errors.grade && <small className="field-error" role="alert">{errors.grade}</small>}</label>
      <label className="auth-field" htmlFor="enrollment"><span>학적 상태</span><select id="enrollment" value={draft.enrollmentStatus ?? ''} disabled={pending} aria-invalid={Boolean(errors.enrollmentStatus)} onChange={(event) => setDraft({ ...draft, enrollmentStatus: event.target.value as Profile['enrollmentStatus'] })}><option value="">선택해 주세요</option>{['재학', '휴학', '기타'].map((status) => <option key={status}>{status}</option>)}</select>{errors.enrollmentStatus && <small className="field-error" role="alert">{errors.enrollmentStatus}</small>}</label>
    </div>
    <div className="onboarding-actions"><button className="auth-submit" type="submit" disabled={pending}>{pending ? '저장 중…' : '다음'}</button></div>
  </form></AuthLayout>
}

export function PreferencesPage() {
  const { user, savePreferenceDraft, completeOnboarding } = useAuth()
  const navigate = useNavigate()
  const [interests, setInterests] = useState(user?.preferenceDraft.interests ?? [])
  const [activities, setActivities] = useState(user?.preferenceDraft.activityTypes ?? [])
  const [errors, setErrors] = useState({ interests: '', activities: '' })
  const [pending, setPending] = useState(false)
  const firstInterest = useRef<HTMLButtonElement>(null)
  const firstActivity = useRef<HTMLButtonElement>(null)
  const [enteredAsCompleted] = useState(() => user?.onboardingCompleted ?? false)
  if (!user) return <Navigate to="/login" replace />
  if (enteredAsCompleted) return <Navigate to="/recommend" replace />
  if (!user.academicDraft) return <Navigate to="/academic" replace />

  const toggle = (list: string[], value: string, setter: (next: string[]) => void, other: string[], interestGroup: boolean) => {
    const next = list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
    setter(next)
    savePreferenceDraft(interestGroup ? next : other, interestGroup ? other : next)
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const nextErrors = {
      interests: interests.length ? '' : '관심 분야를 1개 이상 선택해 주세요.',
      activities: activities.length ? '' : '활동 유형을 1개 이상 선택해 주세요.',
    }
    setErrors(nextErrors)
    if (nextErrors.interests) { firstInterest.current?.focus(); return }
    if (nextErrors.activities) { firstActivity.current?.focus(); return }
    setPending(true)
    try {
      await completeOnboarding(interests, activities)
      navigate('/complete', { replace: true })
    } finally {
      setPending(false)
    }
  }

  return <AuthLayout wide><StepIndicator current={2} /><OnboardingHeading title="관심 분야를 선택해 주세요" description="여러 개 선택할 수 있으며, 언제든 내 정보에서 바꿀 수 있어요." /><form className="preference-form" aria-busy={pending} onSubmit={submit}>
    <fieldset className="choice-section"><legend>관심 분야 <span>{interests.length}개 선택</span></legend><p>어떤 주제의 공지를 보고 싶나요?</p><div className="choice-grid">{INTERESTS.map((item, index) => <button ref={index === 0 ? firstInterest : undefined} className={`choice-button ${interests.includes(item) ? 'choice-button--active' : ''}`} type="button" disabled={pending} aria-pressed={interests.includes(item)} key={item} onClick={() => toggle(interests, item, setInterests, activities, true)}><b>{item}</b><span>{interests.includes(item) ? '선택됨' : '선택'}</span></button>)}</div>{errors.interests && <small className="field-error" role="alert">{errors.interests}</small>}</fieldset>
    <fieldset className="choice-section"><legend>활동 유형 <span>{activities.length}개 선택</span></legend><p>참여하고 싶은 활동을 골라주세요.</p><div className="choice-grid">{ACTIVITY_TYPES.map((item, index) => <button ref={index === 0 ? firstActivity : undefined} className={`choice-button ${activities.includes(item) ? 'choice-button--active' : ''}`} type="button" disabled={pending} aria-pressed={activities.includes(item)} key={item} onClick={() => toggle(activities, item, setActivities, interests, false)}><b>{item}</b><span>{activities.includes(item) ? '선택됨' : '선택'}</span></button>)}</div>{errors.activities && <small className="field-error" role="alert">{errors.activities}</small>}</fieldset>
    <div className="onboarding-actions onboarding-actions--split"><button className="auth-secondary" type="button" disabled={pending} onClick={() => navigate('/academic')}>이전</button><button className="auth-submit" type="submit" disabled={pending}>{pending ? '저장 중…' : '선택 완료'}</button></div>
  </form></AuthLayout>
}

export function CompletePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  if (!user) return <Navigate to="/login" replace />
  if (!user.onboardingCompleted || !user.profile) return <Navigate to={user.academicDraft ? '/preferences' : '/academic'} replace />
  return <AuthLayout wide><StepIndicator current={3} /><div className="complete-icon" aria-hidden="true">✓</div><OnboardingHeading title="맞춤 설정을 완료했어요" description="선택한 정보를 바탕으로 지금부터 공지를 추천해 드릴게요." /><dl className="profile-summary"><div><dt>학적 정보</dt><dd>{user.profile.department} · {user.profile.grade} · {user.profile.enrollmentStatus}</dd></div><div><dt>관심 분야</dt><dd>{user.profile.interests.join(', ')}</dd></div><div><dt>활동 유형</dt><dd>{user.profile.activityTypes.join(', ')}</dd></div></dl><button className="auth-submit" type="button" onClick={() => navigate('/recommend', { replace: true })}>추천 공지 보러 가기</button></AuthLayout>
}
