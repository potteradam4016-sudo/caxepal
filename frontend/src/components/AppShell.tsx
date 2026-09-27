import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useNoticeOverlay } from '../hooks/useNoticeOverlay'
import { NoticeDetailModal } from './NoticeDetailModal'
import { ProfileModal } from './ProfileModal'
import { useState } from 'react'
import { useApp } from '../context/AppContext'

const navItems = [
  { to: '/recommend', label: '추천 공지', icon: '✦' },
  { to: '/new', label: '신규 공지', icon: '◷' },
  { to: '/calendar', label: '내 캘린더', icon: '▦' },
]

export function AppShell() {
  const overlay = useNoticeOverlay()
  const { user, logout } = useAuth()
  const { favoritesError, retryFavorites } = useApp()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const handleLogout = async () => {
    if (loggingOut) return
    setLoggingOut(true)
    try { await logout() } catch { /* Local session is cleared even if the server is offline. */ }
    finally { navigate('/login', { replace: true }) }
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">
            <img src="/icons/SCNU_PICK_icon.png?v=20260922-2" alt="" />
          </span>
          <div>SCNU PICK<small>교내 공지 추천 서비스</small></div>
        </div>
        <nav className="nav" aria-label="주요 메뉴">
          {navItems.map((item) => (
            <NavLink className={({ isActive }) => `nav__link ${isActive ? 'nav__link--active' : ''}`} to={item.to} key={item.to}>
              <span aria-hidden="true">{item.icon}</span>{item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__profile">
          <p><b>{user?.profile?.department ?? '내 추천 정보'}</b><span>{user?.username}</span></p>
          <button className="sidebar__profile-button" type="button" onClick={overlay.openProfile}>내 정보 수정</button>
          <button className="sidebar__logout" type="button" disabled={loggingOut} onClick={() => void handleLogout()}>로그아웃</button>
        </div>
      </aside>
      <main className="main-content">
        {favoritesError && <div className="form-alert" role="alert">{favoritesError} <button onClick={retryFavorites}>찜 다시 불러오기</button></div>}
        <Outlet context={overlay} />
      </main>
      {overlay.noticeId && <NoticeDetailModal noticeId={overlay.noticeId} onClose={overlay.closeNotice} />}
      {overlay.isProfileOpen && <ProfileModal onClose={overlay.closeProfile} />}
    </div>
  )
}
