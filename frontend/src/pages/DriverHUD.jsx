import { useRef, useEffect, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useWebSocket } from '../hooks/useWebSocket'
import { apiPost } from '../api/client'

const PRIORITY_COLOR = { 1: 'var(--alert-p1)', 2: 'var(--alert-p2)', 3: 'var(--alert-p3)' }
const PRIORITY_LABEL = { 1: '🔴 KHẨN CẤP', 2: '🟠 CẢNH BÁO', 3: '🟡 THÔNG TIN' }

export default function DriverHUD() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const canvasRef  = useRef(null)
  const imgRef     = useRef(new Image())

  const [metrics, setMetrics]   = useState({ fps: 0, latency_ms: 0, cpu: 0, mem: 0 })
  const [alerts, setAlerts]     = useState([])
  const [detections, setDetections] = useState([])
  const [videoPath, setVideoPath]   = useState('demo_videos/test.mp4')
  const [running, setRunning]       = useState(false)
  const [hasAudio, setHasAudio]     = useState(false)
  const alertsRef = useRef([])

  // Draw frame + bounding boxes on canvas
  const drawFrame = useCallback((b64, dets) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const img = imgRef.current

    img.onload = () => {
      canvas.width  = img.naturalWidth
      canvas.height = img.naturalHeight
      ctx.drawImage(img, 0, 0)

      // Draw detections
      dets.forEach(d => {
        const { x1, y1, x2, y2 } = d.bbox
        const color = d.is_priority ? 'hsl(0,90%,58%)' : 'hsl(185,90%,52%)'
        const w = x2 - x1, h = y2 - y1

        ctx.strokeStyle = color
        ctx.lineWidth   = 2.5
        ctx.shadowColor = color
        ctx.shadowBlur  = 8

        // Corner-bracket style box
        const cs = 14  // corner size
        ctx.beginPath()
        ctx.moveTo(x1+cs, y1); ctx.lineTo(x1, y1); ctx.lineTo(x1, y1+cs)
        ctx.moveTo(x2-cs, y1); ctx.lineTo(x2, y1); ctx.lineTo(x2, y1+cs)
        ctx.moveTo(x1, y2-cs); ctx.lineTo(x1, y2); ctx.lineTo(x1+cs, y2)
        ctx.moveTo(x2-cs, y2); ctx.lineTo(x2, y2); ctx.lineTo(x2, y2-cs)
        ctx.stroke()
        ctx.shadowBlur = 0

        // Label
        const label = `${d.class_name} ${(d.confidence*100).toFixed(0)}%`
        ctx.font = 'bold 12px Inter, sans-serif'
        const tw = ctx.measureText(label).width
        ctx.fillStyle = color
        ctx.globalAlpha = 0.85
        ctx.fillRect(x1, y1 - 20, tw + 10, 18)
        ctx.globalAlpha = 1
        ctx.fillStyle = '#fff'
        ctx.fillText(label, x1 + 5, y1 - 6)
      })
    }
    img.src = 'data:image/jpeg;base64,' + b64
  }, [])

  const onMessage = useCallback((data) => {
    if (data.frame_b64) {
      drawFrame(data.frame_b64, data.detections || [])
      setDetections(data.detections || [])
    }
    if (data.metrics) setMetrics(data.metrics)
    if (data.alerts?.length) {
      const now = Date.now()
      const newAlerts = data.alerts.map((a, i) => ({
        ...a, id: now + i, time: new Date().toLocaleTimeString('vi-VN')
      }))
      setHasAudio(true)
      setTimeout(() => setHasAudio(false), 2000)
      alertsRef.current = [...newAlerts, ...alertsRef.current].slice(0, 20)
      setAlerts([...alertsRef.current])
    }
  }, [drawFrame])

  const { connected } = useWebSocket(onMessage)

  const startVideo = async () => {
    try {
      await apiPost('/video/start', { video_path: videoPath, loop: true })
      setRunning(true)
    } catch (e) {
      alert('Lỗi: ' + e.message)
    }
  }
  const stopVideo = async () => {
    await apiPost('/video/stop', {})
    setRunning(false)
  }

  return (
    <div style={styles.root}>
      {/* ── Top bar ─────────────────────────────────────────── */}
      <header style={styles.topbar} className="glass">
        <div style={styles.topLeft}>
          <span style={styles.logo}>🚗 RoadWatch</span>
          <span className="badge badge-ok">{connected ? '● LIVE' : '○ Offline'}</span>
          {hasAudio && <span style={styles.audioIcon} className="pulse">🔊</span>}
        </div>

        <div style={styles.topCenter}>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              style={styles.pathInput}
              value={videoPath}
              onChange={e => setVideoPath(e.target.value)}
              placeholder="Đường dẫn video..."
            />
            {!running
              ? <button id="hud-start" className="btn btn-primary" onClick={startVideo} style={{ padding: '6px 16px', fontSize: 13 }}>▶ Chạy</button>
              : <button id="hud-stop"  className="btn btn-danger"  onClick={stopVideo}  style={{ padding: '6px 16px', fontSize: 13 }}>■ Dừng</button>
            }
          </div>
        </div>

        <div style={styles.topRight}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>👤 {user?.username}</span>
          {user?.role === 'engineer' &&
            <button className="btn btn-ghost" style={{ padding: '5px 12px', fontSize: 12 }}
              onClick={() => navigate('/dashboard')}>Dashboard</button>
          }
          <button className="btn btn-ghost" style={{ padding: '5px 12px', fontSize: 12 }}
            onClick={() => { logout(); navigate('/login') }}>Thoát</button>
        </div>
      </header>

      {/* ── Main area ────────────────────────────────────────── */}
      <main style={styles.main}>
        {/* Video canvas */}
        <div style={styles.videoWrap} className="glass">
          {running
            ? <canvas ref={canvasRef} style={styles.canvas} />
            : <div style={styles.placeholder}>
                <div style={{ fontSize: 48 }}>📹</div>
                <div style={{ color: 'var(--text-secondary)', marginTop: 12 }}>Nhập đường dẫn video và nhấn ▶ Chạy</div>
              </div>
          }

          {/* HUD overlays on video */}
          {running && (
            <>
              {/* FCW indicator */}
              {alerts.some(a => a.alert_type === 'collision' && a.priority === 1) && (
                <div style={styles.fcwBadge} className="pulse blink">
                  ⚠️ FCW
                </div>
              )}
              {/* Detection count badge */}
              <div style={styles.detCount}>
                🎯 {detections.length} vật thể
              </div>
            </>
          )}
        </div>

        {/* Right sidebar */}
        <aside style={styles.sidebar}>
          {/* Metrics */}
          <div style={styles.sideCard} className="glass">
            <div style={styles.sideTitle}>📊 Hiệu Suất</div>
            <div style={styles.metricsGrid}>
              <MetricBox value={metrics.fps} label="FPS" color="var(--color-fps)" unit="" />
              <MetricBox value={metrics.latency_ms} label="Latency" color="var(--color-latency)" unit="ms" />
              <MetricBox value={metrics.cpu} label="CPU" color="var(--color-cpu)" unit="%" />
              <MetricBox value={metrics.mem} label="RAM" color="var(--color-mem)" unit="%" />
            </div>
            <PerformanceBar fps={metrics.fps} latency={metrics.latency_ms} />
          </div>

          {/* Detected objects */}
          <div style={styles.sideCard} className="glass">
            <div style={styles.sideTitle}>🎯 Phát Hiện ({detections.length})</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
              {detections.length === 0
                ? <span className="text-muted" style={{ fontSize: 12 }}>Không có vật thể</span>
                : detections.map((d, i) => (
                  <span key={i}
                    className={d.is_priority ? 'badge badge-p2' : 'badge badge-ok'}>
                    {CLASS_ICON[d.class_name] || '●'} {d.class_name} {(d.confidence*100).toFixed(0)}%
                  </span>
                ))
              }
            </div>
          </div>

          {/* Alerts log */}
          <div style={{ ...styles.sideCard, flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }} className="glass">
            <div style={styles.sideTitle}>🔔 Cảnh Báo ADAS</div>
            <div style={styles.alertList}>
              {alerts.length === 0
                ? <div style={styles.noAlert}>✅ Không có cảnh báo</div>
                : alerts.map(a => (
                  <div key={a.id} style={{ ...styles.alertItem, borderLeftColor: PRIORITY_COLOR[a.priority] }} className="slide-in">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ fontSize: 10, color: PRIORITY_COLOR[a.priority], fontWeight: 600 }}>
                        {PRIORITY_LABEL[a.priority]}
                      </span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{a.time}</span>
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>{a.message}</div>
                  </div>
                ))
              }
            </div>
          </div>

          {/* Guardrail */}
          <div style={styles.guardrail}>
            ⚠️ <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              AI chỉ <strong style={{ color: 'var(--alert-p2)' }}>cảnh báo</strong>. Không tự động lái/phanh.
            </span>
          </div>
        </aside>
      </main>
    </div>
  )
}

function MetricBox({ value, label, color, unit }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 22, fontWeight: 700, color }}>{value}{unit}</div>
      <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
    </div>
  )
}

function PerformanceBar({ fps, latency }) {
  const fpsOk = fps >= 15
  const latOk = latency < 100
  return (
    <div style={{ marginTop: 10, display: 'flex', gap: 6 }}>
      <span className={`badge ${fpsOk ? 'badge-ok' : 'badge-p2'}`}>FPS {fpsOk ? '✓' : '!'}</span>
      <span className={`badge ${latOk ? 'badge-ok' : 'badge-p2'}`}>Lat {latOk ? '✓' : '!'}</span>
    </div>
  )
}

const CLASS_ICON = {
  person: '🚶', car: '🚗', motorcycle: '🏍️', bus: '🚌',
  truck: '🚛', bicycle: '🚲', 'traffic light': '🚦', 'stop sign': '🛑',
}

const styles = {
  root: { height: '100vh', display: 'flex', flexDirection: 'column', gap: 8, padding: 10, background: 'var(--color-bg)', overflow: 'hidden' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', borderRadius: 'var(--radius-md)', flexShrink: 0 },
  topLeft:  { display: 'flex', alignItems: 'center', gap: 10, minWidth: 200 },
  topCenter:{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, justifyContent: 'center' },
  topRight: { display: 'flex', alignItems: 'center', gap: 8, minWidth: 200, justifyContent: 'flex-end' },
  logo: { fontSize: 16, fontWeight: 700, color: 'var(--accent)' },
  audioIcon: { fontSize: 18 },
  pathInput: { background: 'hsla(220,25%,10%,0.8)', border: '1px solid var(--glass-border)', borderRadius: 8, padding: '6px 12px', color: 'var(--text-primary)', fontSize: 12, width: 260, fontFamily: 'inherit' },
  main: { flex: 1, display: 'flex', gap: 8, overflow: 'hidden' },
  videoWrap: { flex: 1, position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 'var(--radius-lg)' },
  canvas: { width: '100%', height: '100%', objectFit: 'contain' },
  placeholder: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.5 },
  sidebar: { width: 300, display: 'flex', flexDirection: 'column', gap: 8, overflow: 'hidden' },
  sideCard: { padding: 14, borderRadius: 'var(--radius-md)' },
  sideTitle: { fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)', marginBottom: 4 },
  metricsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: '8px 0' },
  alertList: { marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', flex: 1, maxHeight: 300 },
  alertItem: { padding: '8px 10px', background: 'hsla(220,30%,10%,0.5)', borderLeft: '3px solid', borderRadius: '0 var(--radius-sm) var(--radius-sm) 0' },
  noAlert: { color: 'var(--color-fps)', fontSize: 13, textAlign: 'center', padding: 16 },
  fcwBadge: { position: 'absolute', top: 12, left: 12, background: 'var(--alert-p1-bg)', border: '1px solid var(--alert-p1)', color: 'var(--alert-p1)', padding: '6px 14px', borderRadius: 8, fontWeight: 700, fontSize: 14 },
  detCount: { position: 'absolute', bottom: 12, left: 12, background: 'hsla(220,30%,8%,0.85)', border: '1px solid var(--glass-border)', color: 'var(--accent)', padding: '4px 12px', borderRadius: 8, fontSize: 13, fontWeight: 600 },
  guardrail: { padding: '8px 12px', background: 'hsla(32,95%,58%,0.06)', border: '1px solid hsla(32,95%,58%,0.15)', borderRadius: 'var(--radius-md)', display: 'flex', gap: 6, alignItems: 'center', fontSize: 11, flexShrink: 0 },
}
