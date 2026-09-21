import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { CalendarPage } from './pages/CalendarPage'
import { NewNoticesPage } from './pages/NewNoticesPage'
import { RecommendPage } from './pages/RecommendPage'

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/recommend" replace />} />
        <Route path="recommend" element={<RecommendPage />} />
        <Route path="new" element={<NewNoticesPage />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="*" element={<Navigate to="/recommend" replace />} />
      </Route>
    </Routes>
  )
}
