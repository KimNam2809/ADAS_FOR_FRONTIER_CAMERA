import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Login from './pages/Login'
import DriverHUD from './pages/DriverHUD'
import EngineerDashboard from './pages/EngineerDashboard'

function RequireAuth({ children, role }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role) return <Navigate to={user.role === 'engineer' ? '/dashboard' : '/hud'} replace />
  return children
}

export default function App() {
  const { user } = useAuth()
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={user ? <Navigate to={user.role === 'engineer' ? '/dashboard' : '/hud'} /> : <Login />} />
        <Route path="/hud" element={<RequireAuth><DriverHUD /></RequireAuth>} />
        <Route path="/dashboard" element={<RequireAuth role="engineer"><EngineerDashboard /></RequireAuth>} />
        <Route path="*" element={<Navigate to={user ? (user.role === 'engineer' ? '/dashboard' : '/hud') : '/login'} />} />
      </Routes>
    </BrowserRouter>
  )
}
