import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { App } from './App'
import { AppProviders } from './context/AppProviders'
import './styles.css'

// Keep the 2560x1440 composition intact at other viewport sizes.
const root = document.getElementById('root')!
const Router = import.meta.env.VITE_STATIC_HOSTING === 'true' ? HashRouter : BrowserRouter
function scaleLayout() {
  const scale = window.innerWidth <= 680 ? 1 : Math.min(window.innerWidth / 2560, window.innerHeight / 1440)
  root.style.zoom = String(1.1 * scale)
}
scaleLayout()
window.addEventListener('resize', scaleLayout)

createRoot(root).render(
  <StrictMode>
    <Router>
      <AppProviders><App /></AppProviders>
    </Router>
  </StrictMode>,
)
