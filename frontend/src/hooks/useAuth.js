import { useState, useCallback } from 'react'
import { apiPost } from '../api/client'

export function useAuth() {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('adas_user')
      return raw ? JSON.parse(raw) : null
    } catch { return null }
  })

  const login = useCallback(async (username, password) => {
    const data = await apiPost('/auth/login', { username, password })
    localStorage.setItem('token', data.access_token)
    const u = { username: data.username, role: data.role }
    localStorage.setItem('adas_user', JSON.stringify(u))
    setUser(u)
    return u
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('adas_user')
    setUser(null)
  }, [])

  return { user, login, logout }
}
