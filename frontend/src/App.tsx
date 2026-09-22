import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { useAuth } from './context/AuthContext'
import { CalendarPage } from './pages/CalendarPage'
import { NewNoticesPage } from './pages/NewNoticesPage'
import { AcademicPage, CompletePage, PreferencesPage } from './pages/OnboardingPages'
import { RecommendPage } from './pages/RecommendPage'
import { LoginPage, SignupPage } from './pages/AuthPages'

function ProtectedRoute() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (!user.onboardingCompleted) return <Navigate to={user.academicDraft ? '/preferences' : '/academic'} replace />
  return <Outlet />
}

export function App() {
  return (
    <Routes>
      <Route path="login" element={<LoginPage />} />
      <Route path="signup" element={<SignupPage />} />
      <Route path="academic" element={<AcademicPage />} />
      <Route path="preferences" element={<PreferencesPage />} />
      <Route path="complete" element={<CompletePage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/recommend" replace />} />
          <Route path="recommend" element={<RecommendPage />} />
          <Route path="new" element={<NewNoticesPage />} />
          <Route path="calendar" element={<CalendarPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/recommend" replace />} />
    </Routes>
  )
}
