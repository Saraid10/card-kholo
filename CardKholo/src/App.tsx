import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Calendar from './pages/Calendar'
import Check from './pages/Check'
import ControlRoom from './pages/ControlRoom'
import Directions from './pages/Directions'
import FirstHour from './pages/FirstHour'
import HostPreview from './pages/host/HostPreview'
import HostSetup from './pages/host/HostSetup'
import HostSpeak from './pages/host/HostSpeak'
import Invite from './pages/Invite'
import Landing from './pages/Landing'
import LinkFamily from './pages/LinkFamily'
import NotFound from './pages/NotFound'
import Result from './pages/Result'
import Welcome from './pages/Welcome'
import { api } from './api'
import { onSlowStart } from './api/http'
import { UserProvider, useUser } from './state/user'

function ScrollTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

/** Shown while the sleeping Render backend wakes up (first slow call only). */
function WakingBanner() {
  const { t } = useUser()
  const [slow, setSlow] = useState(false)
  useEffect(() => onSlowStart(setSlow), [])
  useEffect(() => { api.health().catch(() => {}) }, []) // start waking the server on first load
  if (!slow) return null
  return (
    <div role="status" className="fixed inset-x-0 top-0 z-50 bg-gold px-4 py-2 text-center text-[0.95rem] font-medium text-ink shadow">
      {t('waking')}
    </div>
  )
}

export default function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <ScrollTop />
        <WakingBanner />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/start" element={<Welcome />} />
          <Route path="/link" element={<LinkFamily />} />
          <Route path="/check" element={<Check />} />
          <Route path="/scan" element={<Navigate to="/check" replace />} />
          <Route path="/result/:scanId" element={<Result />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/functions/:scanId" element={<Navigate to="/calendar" replace />} />
          <Route path="/directions/:index" element={<Directions />} />
          <Route path="/first-hour/:scanId" element={<FirstHour />} />
          <Route path="/host" element={<HostSetup />} />
          <Route path="/host/speak" element={<HostSpeak />} />
          <Route path="/host/preview" element={<HostPreview />} />
          <Route path="/i/:inviteId" element={<Invite />} />
          <Route path="/status" element={<ControlRoom />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </UserProvider>
  )
}
