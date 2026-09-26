import type { InterestDto } from '../services/contracts'
import { useId } from 'react'
import { STATUS_LABELS, type AcademicProfile, type Profile } from '../types'

export function academicError(draft: Partial<AcademicProfile>): string | null {
  const department = draft.department?.trim() ?? ''
  if (department.length < 2 || department.length > 80 || [...department].some((char) => char.charCodeAt(0) < 32)) return '학과를 2~80자로 입력해 주세요.'
  if (!draft.grade || draft.grade < 1 || draft.grade > 6) return '학년을 선택해 주세요.'
  if (!draft.enrollmentStatus) return '학적 상태를 선택해 주세요.'
  return null
}
export function AcademicFields({ value, onChange, disabled }: {
  value: Partial<AcademicProfile>; onChange: (next: Partial<AcademicProfile>) => void; disabled: boolean
}) {
  const id = useId()
  return <fieldset className="profile-fields" disabled={disabled}>
    <div className="auth-field"><label htmlFor={id + '-department'}>학과</label><input id={id + '-department'} value={value.department ?? ''} maxLength={80} onChange={(event) => onChange({ ...value, department: event.target.value })} /></div>
    <div className="form-grid">
      <div className="auth-field"><label htmlFor={id + '-grade'}>학년</label><select id={id + '-grade'} value={value.grade ?? ''} onChange={(event) => onChange({ ...value, grade: Number(event.target.value) })}>
        <option value="">선택해 주세요</option>{[1, 2, 3, 4, 5, 6].map((grade) => <option value={grade} key={grade}>{grade}학년</option>)}
      </select></div>
      <div className="auth-field"><label htmlFor={id + '-status'}>학적 상태</label><select id={id + '-status'} value={value.enrollmentStatus ?? ''} onChange={(event) => onChange({ ...value, enrollmentStatus: event.target.value as AcademicProfile['enrollmentStatus'] })}>
        <option value="">선택해 주세요</option>{Object.entries(STATUS_LABELS).map(([id, label]) => <option value={id} key={id}>{label}</option>)}
      </select></div>
    </div>
  </fieldset>
}
export function PreferenceFields({ value, options, onChange, disabled }: {
  value: Pick<Profile, 'interests' | 'activityTypes'>; options: InterestDto[]
  onChange: (value: Pick<Profile, 'interests' | 'activityTypes'>) => void; disabled: boolean
}) {
  return <>{(['field', 'activity'] as const).map((type) => {
    const key = type === 'field' ? 'interests' : 'activityTypes'
    return <fieldset className="choice-section" disabled={disabled} key={type}><legend>{type === 'field' ? '관심 분야' : '활동 유형'} <span>{value[key].length}개 선택</span></legend>
      <div className="choice-grid">{options.filter((item) => item.type === type).map((item) =>
        <button className={`choice-button ${value[key].includes(item.id) ? 'choice-button--active' : ''}`} type="button" aria-pressed={value[key].includes(item.id)} key={item.id}
          onClick={() => onChange({ ...value, [key]: value[key].includes(item.id) ? value[key].filter((id) => id !== item.id) : [...value[key], item.id] })}>
          <b>{item.name}</b><span>{value[key].includes(item.id) ? '선택됨' : '선택'}</span>
        </button>)}</div>
    </fieldset>
  })}</>
}
export function preferenceError(value: Pick<Profile, 'interests' | 'activityTypes'>, options: InterestDto[]): string | null {
  if (!value.interests.length) return '관심 분야를 1개 이상 선택해 주세요.'
  if (!value.activityTypes.length) return '활동 유형을 1개 이상 선택해 주세요.'
  if (value.interests.some((id) => !options.some((item) => item.id === id && item.type === 'field')) ||
      value.activityTypes.some((id) => !options.some((item) => item.id === id && item.type === 'activity'))) return '관심사 선택지를 다시 확인해 주세요.'
  return null
}
