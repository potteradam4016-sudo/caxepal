import { useState, type FormEvent } from 'react'
import { useApp } from '../context/AppContext'
import type { Profile } from '../types'
import { Modal } from './Modal'

const INTERESTS = ['AI', '개발', '창업', '취업', '장학']
const ACTIVITY_TYPES = ['프로젝트', '특강', '공모전', '멘토링']

export function ProfileModal({ onClose }: { onClose: () => void }) {
  const { profile } = useApp()

  if (!profile) {
    return <Modal title="학적·관심사 수정" onClose={onClose}><p className="loading-copy">저장된 정보를 불러오는 중입니다…</p></Modal>
  }

  return <ProfileForm initialProfile={profile} onClose={onClose} />
}

function ProfileForm({ initialProfile, onClose }: { initialProfile: Profile; onClose: () => void }) {
  const { saveProfile, showToast } = useApp()
  const [draft, setDraft] = useState<Profile>(initialProfile)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const toggleListValue = (key: 'interests' | 'activityTypes', value: string) => {
    setDraft((current) => {
      const list = current[key]
      return { ...current, [key]: list.includes(value) ? list.filter((item) => item !== value) : [...list, value] }
    })
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const department = draft.department.trim()
    const nextErrors: Record<string, string> = {}
    if (department.length < 1 || department.length > 60) nextErrors.department = '학과를 1~60자로 입력해 주세요.'
    if (!draft.interests.length) nextErrors.interests = '관심 분야를 1개 이상 선택해 주세요.'
    if (!draft.activityTypes.length) nextErrors.activityTypes = '활동 유형을 1개 이상 선택해 주세요.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return
    setSaving(true)
    try {
      await saveProfile({ ...draft, department })
      onClose()
    } catch {
      showToast('저장하지 못했습니다. 입력한 값은 그대로 유지됩니다.', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="학적·관심사 수정" onClose={onClose}>
      <form onSubmit={submit}>
        <label className="field">
          <span>학과</span>
          <input value={draft.department} maxLength={60} aria-invalid={Boolean(errors.department)} onChange={(event) => setDraft({ ...draft, department: event.target.value })} />
          {errors.department && <small className="field-error" role="alert">{errors.department}</small>}
        </label>
        <label className="field">
          <span>학년</span>
          <select value={draft.grade} onChange={(event) => setDraft({ ...draft, grade: event.target.value as Profile['grade'] })}>
            {['1학년', '2학년', '3학년', '4학년', '5학년 이상'].map((grade) => <option key={grade}>{grade}</option>)}
          </select>
        </label>
        <label className="field">
          <span>학적 상태</span>
          <select value={draft.enrollmentStatus} onChange={(event) => setDraft({ ...draft, enrollmentStatus: event.target.value as Profile['enrollmentStatus'] })}>
            {['재학', '휴학', '기타'].map((status) => <option key={status}>{status}</option>)}
          </select>
        </label>
        <fieldset className="field fieldset">
          <legend>관심 분야</legend>
          <div className="chip-group">
            {INTERESTS.map((interest) => (
              <button className={`chip ${draft.interests.includes(interest) ? 'chip--active' : ''}`} type="button" aria-pressed={draft.interests.includes(interest)} key={interest} onClick={() => toggleListValue('interests', interest)}>{interest}</button>
            ))}
          </div>
          {errors.interests && <small className="field-error" role="alert">{errors.interests}</small>}
        </fieldset>
        <fieldset className="field fieldset">
          <legend>활동 유형</legend>
          <div className="chip-group">
            {ACTIVITY_TYPES.map((type) => (
              <button className={`chip ${draft.activityTypes.includes(type) ? 'chip--active' : ''}`} type="button" aria-pressed={draft.activityTypes.includes(type)} key={type} onClick={() => toggleListValue('activityTypes', type)}>{type}</button>
            ))}
          </div>
          {errors.activityTypes && <small className="field-error" role="alert">{errors.activityTypes}</small>}
        </fieldset>
        <div className="modal-actions">
          <button className="button button--secondary" type="button" onClick={onClose}>취소</button>
          <button className="button button--primary" type="submit" disabled={saving}>{saving ? '저장 중…' : '저장'}</button>
        </div>
      </form>
    </Modal>
  )
}
