import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { AuthLayout, StepIndicator } from '../components/AuthLayout'
import { AcademicFields, academicError, PreferenceFields, preferenceError } from '../components/ProfileFields'
import { ViewState } from '../components/ViewState'
import { useAuth } from '../context/AuthContext'
import { useApiResource } from '../hooks/useApiResource'
import { api } from '../services/api'
import { errorMessage, isConflict } from '../services/http'
import { STATUS_LABELS, type AcademicProfile } from '../types'

function Heading({ title }: { title: string }) { return <header className="onboarding-heading"><h2 tabIndex={-1}>{title}</h2></header> }
export function AcademicPage() {
  const { user, saveAcademic, reloadProfile } = useAuth()
  const navigate = useNavigate()
  const [draft, setDraft] = useState<Partial<AcademicProfile>>(user?.academicDraft ?? {})
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  const [pending, setPending] = useState(false)
  if (!user) return <Navigate to="/login" replace />
  if (user.onboardingCompleted) return <Navigate to="/recommend" replace />
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const invalid = academicError(draft)
    if (invalid) { setError(invalid); return }
    setPending(true); setError('')
    try { await saveAcademic(draft as AcademicProfile); navigate('/preferences') }
    catch (failure) { setError(errorMessage(failure)); setConflict(isConflict(failure)) }
    finally { setPending(false) }
  }
  const reload = async () => {
    setPending(true)
    try { const latest = await reloadProfile(); setDraft(latest.academicDraft ?? {}); setConflict(false); setError('') }
    catch (failure) { setError(errorMessage(failure)) }
    finally { setPending(false) }
  }
  return <AuthLayout wide><StepIndicator current={1} /><Heading title="학적 정보를 알려주세요" />
    <form className="onboarding-form" onSubmit={submit} aria-busy={pending}>
      <AcademicFields value={draft} onChange={setDraft} disabled={pending} />
      {error && <p className="form-alert" role="alert">{error}</p>}
      {conflict && <button type="button" className="auth-secondary" disabled={pending} onClick={() => void reload()}>최신 정보 다시 불러오기</button>}
      <div className="onboarding-actions"><button className="auth-submit" disabled={pending || conflict}>{pending ? '저장 중…' : '다음'}</button></div>
    </form>
  </AuthLayout>
}
export function PreferencesPage() {
  const { user, savePreferenceDraft, completeOnboarding, reloadProfile } = useAuth()
  const navigate = useNavigate()
  const options = useApiResource(api.interests)
  const [draft, setDraft] = useState(user?.preferenceDraft ?? { interests: [], activityTypes: [] })
  const [enteredAsCompleted] = useState(user?.onboardingCompleted ?? false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  if (!user) return <Navigate to="/login" replace />
  if (enteredAsCompleted) return <Navigate to="/recommend" replace />
  if (!user.academicDraft) return <Navigate to="/academic" replace />
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const invalid = preferenceError(draft, options.data ?? [])
    if (invalid) { setError(invalid); return }
    setPending(true); setError('')
    try { await completeOnboarding(draft.interests, draft.activityTypes); navigate('/complete', { replace: true }) }
    catch (failure) { setError(errorMessage(failure)); setConflict(isConflict(failure)) }
    finally { setPending(false) }
  }
  const reload = async () => {
    setPending(true)
    try {
      const latest = await reloadProfile()
      setDraft(latest.preferenceDraft)
      savePreferenceDraft(latest.preferenceDraft.interests, latest.preferenceDraft.activityTypes)
      setConflict(false); setError('')
      if (latest.onboardingCompleted) navigate('/recommend', { replace: true })
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setPending(false) }
  }
  return <AuthLayout wide><StepIndicator current={2} /><Heading title="관심 분야를 선택해 주세요" />
    {options.loading ? <ViewState state="loading" /> : options.error ? <ViewState state="error" message={errorMessage(options.error)} onRetry={options.retry} /> :
      <form className="preference-form" onSubmit={submit} aria-busy={pending}>
        <PreferenceFields value={draft} options={options.data ?? []} disabled={pending}
          onChange={(next) => { setDraft(next); savePreferenceDraft(next.interests, next.activityTypes) }} />
        {error && <p className="form-alert" role="alert">{error}</p>}
        {conflict && <button className="auth-secondary" type="button" disabled={pending} onClick={() => void reload()}>최신 정보 다시 불러오기</button>}
        <div className="onboarding-actions onboarding-actions--split">
          <button className="auth-secondary" type="button" disabled={pending} onClick={() => navigate('/academic')}>이전</button>
          <button className="auth-submit" disabled={pending || conflict}>{pending ? '저장 중…' : '선택 완료'}</button>
        </div>
      </form>}
  </AuthLayout>
}
export function CompletePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const options = useApiResource(api.interests)
  if (!user) return <Navigate to="/login" replace />
  if (!user.onboardingCompleted || !user.profile) return <Navigate to={user.academicDraft ? '/preferences' : '/academic'} replace />
  const labels = (ids: string[]) => ids.map((id) => options.data?.find((item) => item.id === id)?.name ?? id).join(', ')
  return <AuthLayout wide><StepIndicator current={3} /><Heading title="맞춤 설정을 완료했어요" />
    {Boolean(options.error) && <ViewState state="error" message={errorMessage(options.error)} onRetry={options.retry} />}
    <dl className="profile-summary">
      <div><dt>학적 정보</dt><dd>{user.profile.department} · {user.profile.grade}학년 · {STATUS_LABELS[user.profile.enrollmentStatus]}</dd></div>
      <div><dt>관심 분야</dt><dd>{options.loading ? '불러오는 중…' : labels(user.profile.interests)}</dd></div>
      <div><dt>활동 유형</dt><dd>{options.loading ? '불러오는 중…' : labels(user.profile.activityTypes)}</dd></div>
    </dl><button className="auth-submit" onClick={() => navigate('/recommend', { replace: true })}>추천 공지 보러 가기</button>
  </AuthLayout>
}
