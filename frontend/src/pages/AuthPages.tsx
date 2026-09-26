import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../components/AuthLayout'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../services/http'

const USERNAME_PATTERN = /^[a-z][a-z0-9_]{2,31}$/
const USERNAME_ERROR = '아이디는 영문 소문자로 시작하는 소문자·숫자·밑줄 3~32자로 입력해 주세요.'

function PasswordInput({ id, label, value, onChange, error, disabled, autoComplete = 'current-password' }: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  error?: string
  disabled?: boolean
  autoComplete?: string
}) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <span className="password-input">
        <input id={id} type={visible ? 'text' : 'password'} value={value} disabled={disabled} autoComplete={autoComplete} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} onChange={(event) => onChange(event.target.value)} />
        <button type="button" onClick={() => setVisible((current) => !current)} aria-label={`${label} ${visible ? '숨기기' : '보기'}`}>{visible ? '숨기기' : '보기'}</button>
      </span>
      {error && <small className="field-error" id={`${id}-error`} role="alert">{error}</small>}
    </div>
  )
}

function AuthHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className="auth-heading"><span>{eyebrow}</span><h2 tabIndex={-1}>{title}</h2><p>{description}</p></header>
}

function nextPath(user: { onboardingCompleted: boolean; academicDraft: unknown }) {
  if (user.onboardingCompleted) return '/recommend'
  return user.academicDraft ? '/preferences' : '/academic'
}

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState(false)
  if (user) return <Navigate to={nextPath(user)} replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const nextErrors: Record<string, string> = {}
    if (!USERNAME_PATTERN.test(username.trim())) nextErrors.username = USERNAME_ERROR
    if (password.length < 1 || password.length > 128) nextErrors.password = '비밀번호를 1~128자로 입력해 주세요.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return
    setPending(true)
    try {
      const nextUser = await login(username, password)
      navigate(nextPath(nextUser), { replace: true })
    } catch (error) {
      setErrors({ form: errorMessage(error) })
    } finally {
      setPending(false)
    }
  }

  return <AuthLayout><AuthHeading eyebrow="WELCOME BACK" title="로그인" description="내게 맞는 교내 공지를 이어서 확인해 보세요." /><form className="auth-form" aria-busy={pending} onSubmit={submit}>
    {location.state?.registered && <p role="status">가입이 완료되었습니다. 아이디와 비밀번호로 로그인해 주세요.</p>}
    {errors.form && <div className="form-alert" role="alert">{errors.form}</div>}
    <div className="auth-field"><label htmlFor="login-username">아이디</label><input id="login-username" autoComplete="username" value={username} disabled={pending} aria-invalid={Boolean(errors.username)} aria-describedby={errors.username ? 'login-username-error' : undefined} onChange={(event) => setUsername(event.target.value.toLowerCase())} />{errors.username && <small className="field-error" id="login-username-error" role="alert">{errors.username}</small>}</div>
    <PasswordInput id="login-password" label="비밀번호" value={password} disabled={pending} error={errors.password} onChange={setPassword} />
    <button className="auth-submit" type="submit" disabled={pending}>{pending ? '처리 중…' : '로그인'}</button>
  </form><p className="auth-switch">아직 계정이 없나요? <Link to="/signup">회원가입</Link></p></AuthLayout>
}

export function SignupPage() {
  const { user, signup, login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState(false)
  if (user) return <Navigate to={nextPath(user)} replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const nextErrors: Record<string, string> = {}
    if (!USERNAME_PATTERN.test(username.trim())) nextErrors.username = USERNAME_ERROR
    if (password.length < 12 || password.length > 128) nextErrors.password = '비밀번호는 12~128자로 입력해 주세요.'
    if (password !== confirm) nextErrors.confirm = '비밀번호가 일치하지 않습니다.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return
    setPending(true)
    try {
      await signup(username, password)
      try {
        await login(username, password)
        navigate('/academic', { replace: true })
      } catch {
        navigate('/login', { replace: true, state: { registered: true } })
      }
    } catch (error) {
      setErrors({ form: errorMessage(error) })
    } finally {
      setPending(false)
    }
  }

  return <AuthLayout><AuthHeading eyebrow="CREATE ACCOUNT" title="회원가입" description="아이디를 만들고 나에게 필요한 공지를 설정해 보세요." /><form className="auth-form" aria-busy={pending} onSubmit={submit}>
    {errors.form && <div className="form-alert" role="alert">{errors.form}</div>}
    <div className="auth-field"><label htmlFor="signup-username">아이디</label><input id="signup-username" autoComplete="username" value={username} disabled={pending} maxLength={32} aria-invalid={Boolean(errors.username)} aria-describedby={errors.username ? 'signup-username-error' : undefined} onChange={(event) => setUsername(event.target.value.toLowerCase())} />{errors.username && <small className="field-error" id="signup-username-error" role="alert">{errors.username}</small>}</div>
    <PasswordInput id="signup-password" label="비밀번호" value={password} disabled={pending} error={errors.password} autoComplete="new-password" onChange={setPassword} />
    <PasswordInput id="signup-confirm" label="비밀번호 확인" value={confirm} disabled={pending} error={errors.confirm} autoComplete="new-password" onChange={setConfirm} />
    <p className="auth-note">아이디는 영문자로 시작하는 소문자·숫자·밑줄 3~32자, 비밀번호는 12~128자로 입력해 주세요.</p>
    <button className="auth-submit" type="submit" disabled={pending}>{pending ? '처리 중…' : '가입하고 시작하기'}</button>
  </form><p className="auth-switch">이미 계정이 있나요? <Link to="/login">로그인</Link></p></AuthLayout>
}
