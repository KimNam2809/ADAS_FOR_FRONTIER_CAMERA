import { useState, useCallback, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useWebSocket } from '../hooks/useWebSocket'
import { apiGet, apiPut, apiPost } from '../api/client'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'

const TABS = [
  { id: 'live',    label: '📹 Live' },
  { id: 'metrics', label: '📊 Metrics' },
  { id: 'config',  label: '⚙️ Config' },
  { id: 'log',     label: '📋 Log' },
]

export default function EngineerDashboard() {
  const { user, logout }   = useAuth()
  const navigate           = useNavigate()
  const [tab, setTab]      = useState('live')
  const [metrics, setMetrics] = useState({ fps: 0, latency_ms: 0, cpu: 0, mem: 0, detections: 0 })
  const [history, setHistory] = useState([])
  const [detLog, setDetLog]   = useState([])
  const [alerts, setAlerts]   = useState([])
  const [frame, setFrame]     = useState(null)
  const [detections, setDetections] = useState([])
  const [running, setRunning]   = useState(false)
  const [videoPath, setVideoPath] = useState('demo_videos/test.mp4')
  const canvasRef = useRef(null)
  const imgRef    = useRef(new Image())

  // Draw frame to canvas
  const drawFrame = useCallback((b64, dets) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const img = imgRef.current
    img.onload = () => {
      canvas.width  = img.naturalWidth
      canvas.height = img.naturalHeight
      ctx.drawImage(img, 0, 0)
      dets.forEach(d => {
        const { x1, y1, x2, y2 } = d.bbox
        const color = d.is_priority ? '#f87171' : '#22d3ee'
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        ctx.strokeRect(x1, y1, x2-x1, y2-y1)
        ctx.font = 'bold 11px Inter, sans-serif'
        ctx.fillStyle = color
        ctx.fillRect(x1, y1-16, ctx.measureText(d.class_name).width + 8, 14)
        ctx.fillStyle = '#000'
        ctx.fillText(d.class_name, x1+4, y1-5)
      })
    }
    img.src = 'data:image/jpeg;base64,' + b64
  }, [])

  const onMessage = useCallback((data) => {
    if (data.metrics) {
      const m = data.metrics
      setMetrics(m)
      const ts = new Date().toLocaleTimeString('vi-VN')
      setHistory(h => [...h.slice(-60), { time: ts, fps: m.fps, latency: m.latency_ms, cpu: m.cpu, mem: m.mem }])
    }
    if (data.detections) {
      setDetections(data.detections)
      if (data.detections.length > 0) {
        const ts = new Date().toLocaleTimeString('vi-VN')
        setDetLog(l => [{
          time: ts, frameId: data.frame_id,
          count: data.detections.length,
          classes: data.detections.map(d => d.class_name).join(', '),
          fps: data.metrics?.fps, lat: data.metrics?.latency_ms,
        }, ...l].slice(0, 200))
      }
    }
    if (data.alerts?.length) setAlerts(a => [...data.alerts.map((x, i) => ({ ...x, id: Date.now()+i, time: new Date().toLocaleTimeString('vi-VN') })), ...a].slice(0, 50))
    if (data.frame_b64) drawFrame(data.frame_b64, data.detections || [])
  }, [drawFrame])

  const { connected } = useWebSocket(onMessage)

  const startVideo = async () => { await apiPost('/video/start', { video_path: videoPath, loop: true }); setRunning(true) }
  const stopVideo  = async () => { await apiPost('/video/stop', {}); setRunning(false) }

  return (
    <div style={styles.root}>
      {/* ── Sidebar ────────────────────────────────────────── */}
      <nav style={styles.nav} className="glass">
        <div style={styles.navLogo}>
          <div style={{ fontSize: 22 }}>🚗</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--accent)' }}>RoadWatch</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Engineer</div>
          </div>
        </div>

        <div style={styles.navTabs}>
          {TABS.map(t => (
            <button key={t.id} id={`tab-${t.id}`}
              style={{ ...styles.navItem, ...(tab === t.id ? styles.navItemActive : {}) }}
              onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        <div style={styles.navBottom}>
          <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
            <span className={`badge ${connected ? 'badge-ok' : 'badge-p1'}`}>
              {connected ? '● Connected' : '○ Offline'}
            </span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>👤 {user?.username}</div>
          <button className="btn btn-ghost" style={{ width: '100%', fontSize: 12, padding: '8px' }}
            onClick={() => navigate('/hud')}>Driver HUD</button>
          <button className="btn btn-ghost" style={{ width: '100%', fontSize: 12, padding: '8px', marginTop: 4 }}
            onClick={() => { logout(); navigate('/login') }}>Đăng Xuất</button>
        </div>
      </nav>

      {/* ── Main content ──────────────────────────────────── */}
      <main style={styles.main}>
        {/* Top bar */}
        <header style={styles.header} className="glass">
          <div>
            <h1 style={styles.pageTitle}>{TABS.find(t => t.id === tab)?.label}</h1>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>RoadWatch Copilot – ADAS Engineer Console</div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <MetricChip label="FPS" value={metrics.fps} unit="" color="var(--color-fps)" />
            <MetricChip label="Latency" value={metrics.latency_ms} unit="ms" color="var(--color-latency)" />
            <MetricChip label="CPU" value={metrics.cpu} unit="%" color="var(--color-cpu)" />
            <MetricChip label="RAM" value={metrics.mem} unit="%" color="var(--color-mem)" />
          </div>
        </header>

        {/* Tab Content */}
        <div style={styles.content}>
          {tab === 'live'    && <LiveTab canvasRef={canvasRef} detections={detections} alerts={alerts} running={running} videoPath={videoPath} setVideoPath={setVideoPath} startVideo={startVideo} stopVideo={stopVideo} />}
          {tab === 'metrics' && <MetricsTab history={history} />}
          {tab === 'config'  && <ConfigTab />}
          {tab === 'log'     && <LogTab rows={detLog} />}
        </div>
      </main>
    </div>
  )
}

// ── Metric Chip ──────────────────────────────────────────────────────────────
function MetricChip({ label, value, unit, color }) {
  return (
    <div style={{ textAlign: 'center', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 10, padding: '6px 14px' }}>
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 18, fontWeight: 700, color }}>{value}{unit}</div>
      <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)' }}>{label}</div>
    </div>
  )
}

// ── Live Tab ─────────────────────────────────────────────────────────────────
function LiveTab({ canvasRef, detections, alerts, running, videoPath, setVideoPath, startVideo, stopVideo }) {
  return (
    <div style={{ display: 'flex', gap: 12, height: '100%' }}>
      {/* Video */}
      <div className="glass" style={{ flex: 1, borderRadius: 'var(--radius-lg)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
        {!running && (
          <div style={{ display: 'flex', gap: 8, padding: 16 }}>
            <input value={videoPath} onChange={e => setVideoPath(e.target.value)} style={{ background: 'hsla(220,25%,10%,0.8)', border: '1px solid var(--glass-border)', borderRadius: 8, padding: '8px 12px', color: 'var(--text-primary)', fontSize: 13, width: 300 }} placeholder="Đường dẫn video..." />
            <button id="eng-start" className="btn btn-primary" onClick={startVideo}>▶ Phân Tích</button>
          </div>
        )}
        {running && <button id="eng-stop" className="btn btn-danger" style={{ margin: 12 }} onClick={stopVideo}>■ Dừng</button>}
        <canvas ref={canvasRef} style={{ maxWidth: '100%', maxHeight: 'calc(100% - 60px)', objectFit: 'contain' }} />
      </div>

      {/* Detection table + alerts */}
      <div style={{ width: 280, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div className="glass" style={{ padding: 14, borderRadius: 'var(--radius-md)', flex: 1 }}>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>🎯 Detections ({detections.length})</div>
          <div style={{ overflowY: 'auto', maxHeight: 200 }}>
            <table className="data-table" style={{ width: '100%' }}>
              <thead><tr><th>Class</th><th>Conf</th><th>Priority</th></tr></thead>
              <tbody>
                {detections.map((d, i) => (
                  <tr key={i}>
                    <td>{d.class_name}</td>
                    <td style={{ color: 'var(--accent)' }}>{(d.confidence*100).toFixed(0)}%</td>
                    <td>{d.is_priority ? <span className="badge badge-p2">⚠</span> : <span className="badge badge-ok">✓</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="glass" style={{ padding: 14, borderRadius: 'var(--radius-md)', flex: 1, overflowY: 'auto' }}>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>🔔 Alerts</div>
          {alerts.slice(0, 8).map(a => (
            <div key={a.id} style={{ padding: '6px 8px', marginBottom: 4, background: 'hsla(220,30%,10%,0.5)', borderLeft: `2px solid ${a.priority === 1 ? 'var(--alert-p1)' : a.priority === 2 ? 'var(--alert-p2)' : 'var(--alert-p3)'}`, borderRadius: '0 4px 4px 0', fontSize: 12 }}>
              <div style={{ color: 'var(--text-muted)', fontSize: 10 }}>{a.time}</div>
              <div>{a.message}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Metrics Tab ───────────────────────────────────────────────────────────────
function MetricsTab({ history }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <ChartCard title="FPS & Latency (ms)" data={history}
        lines={[{ key: 'fps', color: 'var(--color-fps)', name: 'FPS' }, { key: 'latency', color: 'var(--color-latency)', name: 'Latency ms' }]} />
      <ChartCard title="CPU % & RAM %" data={history}
        lines={[{ key: 'cpu', color: 'var(--color-cpu)', name: 'CPU %' }, { key: 'mem', color: 'var(--color-mem)', name: 'RAM %' }]} />
    </div>
  )
}

function ChartCard({ title, data, lines }) {
  return (
    <div className="glass" style={{ padding: 20, borderRadius: 'var(--radius-lg)' }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 16 }}>{title}</div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsla(220,30%,25%,0.3)" />
          <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: 'hsl(222,22%,9%)', border: '1px solid var(--glass-border)', borderRadius: 8, fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {lines.map(l => <Line key={l.key} type="monotone" dataKey={l.key} stroke={l.color} dot={false} name={l.name} strokeWidth={2} />)}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Config Tab (HITL) ─────────────────────────────────────────────────────────
function ConfigTab() {
  const [cfg, setCfg] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)

  useEffect(() => {
    apiGet('/config/detector').then(setCfg).catch(console.error)
  }, [])

  const save = async () => {
    setSaving(true)
    try { await apiPut('/config/detector', cfg); setSaved(true); setTimeout(() => setSaved(false), 2000) }
    catch(e) { alert('Lỗi: ' + e.message) }
    finally { setSaving(false) }
  }
  const reset = async () => {
    await apiPost('/config/reset', {})
    apiGet('/config/detector').then(setCfg)
  }

  if (!cfg) return <div style={{ padding: 40, textAlign: 'center' }}><div className="spinner" /></div>

  return (
    <div className="glass" style={{ padding: 28, borderRadius: 'var(--radius-lg)', maxWidth: 700 }}>
      <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 20, color: 'var(--accent)' }}>
        ⚙️ HITL – Cấu Hình Ngưỡng Phát Hiện
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <SliderRow label="Ngưỡng Confidence" min={0.1} max={0.95} step={0.05}
          value={cfg.conf_threshold}
          onChange={v => setCfg(c => ({ ...c, conf_threshold: v }))} />
        <SliderRow label="Ngưỡng IoU (NMS)" min={0.1} max={0.9} step={0.05}
          value={cfg.iou_threshold}
          onChange={v => setCfg(c => ({ ...c, iou_threshold: v }))} />
        <SliderRow label="TTC Cảnh Báo (giây)" min={0.5} max={10} step={0.5}
          value={cfg.ttc_warn_seconds}
          onChange={v => setCfg(c => ({ ...c, ttc_warn_seconds: v }))} />
        <SliderRow label="TTC Khẩn Cấp (giây)" min={0.3} max={5} step={0.1}
          value={cfg.ttc_critical_seconds}
          onChange={v => setCfg(c => ({ ...c, ttc_critical_seconds: v }))} />
        <SliderRow label="Cooldown P1 (giây)" min={0.5} max={10} step={0.5}
          value={cfg.alert_cooldown_p1}
          onChange={v => setCfg(c => ({ ...c, alert_cooldown_p1: v }))} />
        <SliderRow label="Cooldown P2 (giây)" min={1} max={15} step={0.5}
          value={cfg.alert_cooldown_p2}
          onChange={v => setCfg(c => ({ ...c, alert_cooldown_p2: v }))} />
      </div>

      <div style={{ marginTop: 24 }}>
        <div className="form-label" style={{ marginBottom: 8 }}>Input Size</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {[320, 480, 640].map(s => (
            <button key={s}
              className={`btn ${cfg.input_size === s ? 'btn-primary' : 'btn-ghost'}`}
              style={{ padding: '8px 20px' }}
              onClick={() => setCfg(c => ({ ...c, input_size: s }))}>
              {s}×{s}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 24, display: 'flex', gap: 10 }}>
        <button id="cfg-save" className="btn btn-primary" onClick={save} disabled={saving}>
          {saving ? 'Đang lưu...' : saved ? '✓ Đã lưu!' : '💾 Lưu Cấu Hình'}
        </button>
        <button className="btn btn-ghost" onClick={reset}>↺ Reset mặc định</button>
      </div>
    </div>
  )
}

function SliderRow({ label, min, max, step, value, onChange }) {
  return (
    <div className="form-group">
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <label className="form-label">{label}</label>
        <span style={{ fontSize: 13, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent)' }}>{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))} />
    </div>
  )
}

// ── Log Tab ───────────────────────────────────────────────────────────────────
function LogTab({ rows }) {
  return (
    <div className="glass" style={{ padding: 16, borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
        📋 Detection Log ({rows.length} records)
      </div>
      <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 260px)' }}>
        <table className="data-table">
          <thead>
            <tr><th>Time</th><th>Frame</th><th>Count</th><th>Classes</th><th>FPS</th><th>Latency</th></tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.time}</td>
                <td>{r.frameId}</td>
                <td style={{ color: 'var(--accent)' }}>{r.count}</td>
                <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.classes}</td>
                <td style={{ color: 'var(--color-fps)' }}>{r.fps}</td>
                <td style={{ color: 'var(--color-latency)' }}>{r.lat}ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const styles = {
  root: { height: '100vh', display: 'flex', overflow: 'hidden', background: 'var(--color-bg)' },
  nav: { width: 200, padding: 16, display: 'flex', flexDirection: 'column', borderRadius: 0, margin: 8, borderRadius: 'var(--radius-lg)', flexShrink: 0 },
  navLogo: { display: 'flex', gap: 10, alignItems: 'center', marginBottom: 24 },
  navTabs: { display: 'flex', flexDirection: 'column', gap: 4, flex: 1 },
  navItem: { padding: '10px 14px', borderRadius: 'var(--radius-md)', textAlign: 'left', fontSize: 13, fontWeight: 500, color: 'var(--text-muted)', background: 'transparent', border: 'none', cursor: 'pointer', transition: 'all 0.15s' },
  navItemActive: { background: 'var(--glass-bg)', color: 'var(--accent)', border: '1px solid var(--glass-border)' },
  navBottom: { marginTop: 'auto' },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '8px 8px 8px 0' },
  header: { padding: '12px 20px', borderRadius: 'var(--radius-lg)', marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 },
  pageTitle: { fontSize: 18, fontWeight: 700 },
  content: { flex: 1, overflowY: 'auto', paddingBottom: 8 },
}
