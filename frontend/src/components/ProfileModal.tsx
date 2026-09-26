import { useState, type FormEvent } from 'react'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { useApiResource } from '../hooks/useApiResource'
import { api } from '../services/api'
import { errorMessage, isConflict } from '../services/http'
import type { Profile } from '../types'
import { AcademicFields, academicError, PreferenceFields, preferenceError } from './ProfileFields'
import { Modal } from './Modal'
import { ViewState } from './ViewState'

export function ProfileModal({ onClose }: { onClose: () => void }) {
  const { profile } = useApp()
  return <Modal title="학적·관심사 수정" onClose={onClose}>
    {profile ? <ProfileForm initialProfile={profile} onClose={onClose} /> : <p role="status">저장된 정보를 불러오는 중입니다.</p>}
  </Modal>
}
function ProfileForm({ initialProfile, onClose }: { initialProfile: Profile; onClose: () => void }) {
  const { saveProfile } = useApp()
  const { reloadProfile } = useAuth()
  const options = useApiResource(api.interests)
  const [draft, setDraft] = useState(initialProfile)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  const [saving, setSaving] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const invalid = academicError(draft) ?? preferenceError(draft, options.data ?? [])
    if (invalid) { setError(invalid); return }
    setSaving(true); setError('')
    try { await saveProfile(draft); onClose() }
    catch (failure) { setError(errorMessage(failure)); setConflict(isConflict(failure)) }
    finally { setSaving(false) }
  }
  const reload = async () => {
    setSaving(true)
    try {
      const latest = await reloadProfile()
      if (latest.profile) setDraft(latest.profile)
      setError(''); setConflict(false)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setSaving(false) }
  }
  if (options.loading) return <ViewState state="loading" />
  if (options.error) return <ViewState state="error" message={errorMessage(options.error)} onRetry={options.retry} />
  return <form onSubmit={submit} aria-busy={saving}>
    <AcademicFields value={draft} onChange={(academic) => setDraft({ ...draft, ...academic })} disabled={saving} />
    <PreferenceFields value={draft} options={options.data ?? []} onChange={(next) => setDraft({ ...draft, ...next })} disabled={saving} />
    {error && <p className="form-alert" role="alert">{error}</p>}
    {conflict && <button className="button button--secondary" type="button" disabled={saving} onClick={() => void reload()}>최신 정보 다시 불러오기</button>}
    <div className="modal-actions"><button className="button button--secondary" type="button" onClick={onClose}>취소</button>
      <button className="button button--primary" disabled={saving || conflict}>{saving ? '저장 중…' : '저장'}</button></div>
  </form>
}
