import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useNoticeOverlay } from '../hooks/useNoticeOverlay'
import { NoticeDetailModal } from './NoticeDetailModal'
import { ProfileModal } from './ProfileModal'

const navItems = [
  { to: '/recommend', label: '추천 공지', icon: '✦' },
  { to: '/new', label: '신규 공지', icon: '◷' },
  { to: '/calendar', label: '내 캘린더', icon: '▦' },
]

export function AppShell() {
  const overlay = useNoticeOverlay()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
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
          <button className="sidebar__logout" type="button" onClick={handleLogout}>로그아웃</button>
        </div>
      </aside>
      <main className="main-content"><Outlet context={overlay} /></main>
      {overlay.noticeId && <NoticeDetailModal noticeId={overlay.noticeId} onClose={overlay.closeNotice} />}
      {overlay.isProfileOpen && <ProfileModal onClose={overlay.closeProfile} />}
    </div>
  )
}
