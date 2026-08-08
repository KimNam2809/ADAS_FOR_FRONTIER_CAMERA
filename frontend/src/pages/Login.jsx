import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const ROLES = [
  { id: 'driver',   label: '🚗 Tài Xế',        desc: 'HUD lái xe thời gian thực' },
  { id: 'engineer', label: '🔧 Kỹ Sư ADAS',    desc: 'Dashboard giám sát & cấu hình' },
]

export default function Login() {
  const { login } = useAuth()
  const navigate   = useNavigate()
  const [form, setForm]     = useState({ username: '', password: '' })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(form.username, form.password)
      navigate(user.role === 'engineer' ? '/dashboard' : '/hud')
    } catch (err) {
      setError(err.message || 'Đăng nhập thất bại')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      {/* Background decoration */}
      <div style={styles.bgGrad1} />
      <div style={styles.bgGrad2} />

      <div style={styles.card} className="glass fade-in">
        {/* Logo */}
        <div style={styles.logo}>
          <div style={styles.logoIcon}>🚗</div>
          <div>
            <div style={styles.logoTitle}>RoadWatch Copilot</div>
            <div style={styles.logoSub} className="text-muted">ADAS Edge Intelligence · v1.0</div>
          </div>
        </div>

        <div style={styles.divider} />

        {/* Credentials */}
        <form onSubmit={handleSubmit} style={styles.form}>
          <div className="form-group">
            <label className="form-label">Tên đăng nhập</label>
            <input
              id="login-username"
              className="form-input"
              placeholder="driver  hoặc  engineer"
              value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Mật khẩu</label>
            <input
              id="login-password"
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div style={styles.errorBox}>⚠️ {error}</div>
          )}

          <button id="login-submit" className="btn btn-primary w-full" type="submit" disabled={loading}>
            {loading ? <><span className="spinner" /> Đang xác thực...</> : 'Đăng Nhập'}
          </button>
        </form>

        {/* Demo accounts hint */}
        <div style={styles.hint}>
          <div style={styles.hintTitle} className="text-muted">Demo accounts</div>
          {ROLES.map(r => (
            <button
              key={r.id}
              style={styles.roleBtn}
              className="btn btn-ghost"
              onClick={() => setForm({
                username: r.id,
                password: r.id === 'driver' ? 'driver123' : 'eng456',
              })}
            >
              <span>{r.label}</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.desc}</span>
            </button>
          ))}
        </div>

        {/* Warning banner */}
        <div style={styles.guardrail}>
          <span style={{ color: 'var(--alert-p2)' }}>⚠️</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
            Hệ thống chỉ cung cấp cảnh báo hỗ trợ lái xe. <strong style={{ color: 'var(--alert-p1)' }}>KHÔNG</strong> tự động lái / phanh / đánh lái.
          </span>
        </div>
      </div>
    </div>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    position: 'relative',
    overflow: 'hidden',
  },
  bgGrad1: {
    position: 'fixed', top: '-20%', right: '-10%',
    width: 600, height: 600,
    borderRadius: '50%',
    background: 'radial-gradient(circle, hsla(185,90%,52%,0.08) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  bgGrad2: {
    position: 'fixed', bottom: '-20%', left: '-10%',
    width: 500, height: 500,
    borderRadius: '50%',
    background: 'radial-gradient(circle, hsla(270,75%,65%,0.06) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  card: {
    width: '100%', maxWidth: 440,
    padding: 36,
    display: 'flex', flexDirection: 'column', gap: 20,
    position: 'relative', zIndex: 1,
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 14,
  },
  logoIcon: {
    width: 52, height: 52,
    background: 'linear-gradient(135deg, hsl(185,90%,20%), hsl(185,90%,38%))',
    borderRadius: 14,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 26,
    boxShadow: '0 0 24px var(--accent-glow)',
    flexShrink: 0,
  },
  logoTitle: {
    fontSize: 20, fontWeight: 700, color: 'var(--text-primary)',
  },
  logoSub: { fontSize: 12 },
  divider: { height: 1, background: 'var(--glass-border)' },
  form: { display: 'flex', flexDirection: 'column', gap: 16 },
  errorBox: {
    padding: '10px 14px',
    background: 'var(--alert-p1-bg)',
    border: '1px solid hsla(0,90%,58%,0.3)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--alert-p1)',
    fontSize: 13,
  },
  hint: { display: 'flex', flexDirection: 'column', gap: 8 },
  hintTitle: { fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' },
  roleBtn: {
    display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
    gap: 2, padding: '10px 14px',
  },
  guardrail: {
    display: 'flex', gap: 8, alignItems: 'flex-start',
    padding: '10px 14px',
    background: 'hsla(32,95%,58%,0.06)',
    border: '1px solid hsla(32,95%,58%,0.15)',
    borderRadius: 'var(--radius-md)',
  },
}
