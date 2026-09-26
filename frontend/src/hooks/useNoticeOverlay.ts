import { useSearchParams } from 'react-router-dom'

export function useNoticeOverlay() {
  const [searchParams, setSearchParams] = useSearchParams()

  const openNotice = (noticeId: number) => {
    const next = new URLSearchParams(searchParams)
    next.set('notice', String(noticeId))
    setSearchParams(next)
  }

  const closeNotice = () => {
    const next = new URLSearchParams(searchParams)
    next.delete('notice')
    setSearchParams(next, { replace: true })
  }

  const openProfile = () => {
    const next = new URLSearchParams(searchParams)
    next.set('profile', 'edit')
    setSearchParams(next)
  }

  const closeProfile = () => {
    const next = new URLSearchParams(searchParams)
    next.delete('profile')
    setSearchParams(next, { replace: true })
  }

  return {
    noticeId: searchParams.has('notice') ? Number(searchParams.get('notice')) : null,
    isProfileOpen: searchParams.get('profile') === 'edit',
    openNotice,
    closeNotice,
    openProfile,
    closeProfile,
  }
}
