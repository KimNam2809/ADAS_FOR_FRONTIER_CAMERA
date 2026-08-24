import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, type AlertEvent, type MediaItem, type Status, type User } from "./api";
import "./styles.css";

const EMPTY_STATUS: Status = {
  running: false,
  mode: "idle",
  frame_id: 0,
  source_fps: 0,
  source_time: 0,
  duration_seconds: 0,
  seekable: false,
  playback: "stopped",
  session_id: undefined,
  tracks: [],
  signs: [],
  lane: { quality: 0, offset: 0 },
  events: [],
  active_events: [],
  degraded_reasons: [],
  guardrail: "Chỉ hỗ trợ cảnh báo — không tự lái, phanh hoặc đánh lái.",
  audio: { enabled: false, provider: "-", queue_size: 0 },
  metrics: {
    uptime_seconds: 0,
    captured_frames: 0,
    processed_frames: 0,
    dropped_frames: 0,
    processed_fps: 0,
    frame_drop_ratio: 0,
    alerts_emitted: 0,
    alerts_suppressed: 0,
    latencies: {},
  },
};

function Login({ onLogin }: { onLogin: (token: string, user: User) => void }) {
  const [username, setUsername] = useState("driver");
  const [password, setPassword] = useState("driver123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api.login(username, password);
      onLogin(result.token, result.user);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Đăng nhập thất bại");
    } finally {
      setBusy(false);
    }
  }

  function useDemo(role: "driver" | "engineer") {
    setUsername(role);
    setPassword(role === "driver" ? "driver123" : "engineer123");
  }

  return (
    <main className="login-shell">
      <section className="login-brand">
        <div className="brand-lockup hero-brand">
          <img src="/logo.png" alt="RoadWatch" />
          <div><strong>RoadWatch</strong><span>Edge ADAS Copilot</span></div>
        </div>
        <div className="hero-copy">
          <span className="eyebrow">OFFLINE · EVIDENCE-AWARE · VIETNAM</span>
          <h1>Thấy nguy cơ.<br /><em>Nói điều cần thiết.</em></h1>
          <p>Trợ lý cảnh báo camera trước dành cho giao thông hỗn hợp, ưu tiên xe máy và người đi bộ.</p>
        </div>
        <div className="safety-strip"><i /> Chỉ cảnh báo hỗ trợ — tài xế luôn kiểm soát phương tiện.</div>
      </section>
      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="panel-kicker">ROADWATCH LOCAL</div>
          <h2>Chào mừng trở lại</h2>
          <p>Đăng nhập trực tiếp trên edge device. Không cần Internet.</p>
          <label>Tài khoản<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label>
          <label>Mật khẩu<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" /></label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button" disabled={busy}>{busy ? "Đang kết nối…" : "Vào hệ thống"}</button>
          <div className="demo-users"><span>Dùng nhanh:</span><button type="button" onClick={() => useDemo("driver")}>Tài xế</button><button type="button" onClick={() => useDemo("engineer")}>Kỹ sư ADAS</button></div>
        </form>
      </section>
    </main>
  );
}

function useRoadWatch(token: string) {
  const [status, setStatus] = useState<Status>(EMPTY_STATUS);
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (!token) {
      setConnected(false);
      setStatus(EMPTY_STATUS);
      return;
    }
    let ws: WebSocket | undefined;
    let stopped = false;
    let timer: number;
    const connect = () => {
      const protocol = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${protocol}://${location.host}/ws?token=${encodeURIComponent(token)}`);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (event) => setStatus(JSON.parse(event.data) as Status);
      ws.onclose = () => {
        setConnected(false);
        if (!stopped) timer = window.setTimeout(connect, 1400);
      };
    };
    api.status(token).then(setStatus).catch(() => undefined);
    connect();
    return () => { stopped = true; window.clearTimeout(timer); ws?.close(); };
  }, [token]);
  return { status, connected };
}

function Header({ user, status, connected, view, setView, logout }: {
  user: User; status: Status; connected: boolean; view: string; setView: (value: string) => void; logout: () => void;
}) {
  return <header className="app-header">
    <div className="brand-lockup"><img src="/logo.png" alt="" /><div><strong>RoadWatch</strong><span>Copilot</span></div></div>
    <nav>
      <button className={view === "driver" ? "active" : ""} onClick={() => setView("driver")}>Driver HUD</button>
      {user.role === "engineer" && <button className={view === "engineer" ? "active" : ""} onClick={() => setView("engineer")}>Engineer Console</button>}
    </nav>
    <div className="header-meta">
      <span className={`live-state ${connected ? "online" : ""}`}><i />{connected ? "EDGE ONLINE" : "ĐANG KẾT NỐI"}</span>
      <span className="pipeline-state">{status.running ? "ANALYZING" : "STANDBY"}</span>
      <button className="user-chip" onClick={logout}>{user.username}<small>{user.role}</small></button>
    </div>
  </header>;
}

function VideoStage({ token, status, compact = false }: { token: string; status: Status; compact?: boolean }) {
  const topEvent = status.active_events?.[0];
  return <section className={`video-stage ${compact ? "compact" : ""}`}>
    {status.running ? <img key={status.session_id} src={`/api/stream.mjpg?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(status.session_id ?? "")}`} alt="Luồng camera RoadWatch" /> : <div className="video-placeholder"><div className="road-perspective"><i /><i /></div><strong>Sẵn sàng phân tích</strong><span>Chọn video và bắt đầu phiên RoadWatch</span></div>}
    <div className="camera-badge">CAM 01 · {status.source ?? "NO SOURCE"}</div>
    <div className="offline-badge">● OFFLINE EDGE</div>
    {topEvent && status.running && <div className={`hazard-banner ${topEvent.severity}`}><span>{topEvent.severity === "critical" ? "!" : "i"}</span><div><small>{topEvent.event_type.toUpperCase()}</small><strong>{topEvent.display_message ?? topEvent.message}</strong></div><b>{Math.round(topEvent.risk_score * 100)}</b></div>}
  </section>;
}

function SessionControls({ token, status }: { token: string; status: Status }) {
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [source, setSource] = useState("test_video10.mp4");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [seekDraft, setSeekDraft] = useState(0);
  const [dragging, setDragging] = useState(false);
  useEffect(() => { api.media(token).then((items) => { setMedia(items); if (!items.some((item) => item.name === source) && items.length) setSource(items[0].name); }).catch((reason) => setError(String(reason))); }, [token]);
  useEffect(() => { if (!dragging) setSeekDraft(status.source_time ?? 0); }, [status.source_time, dragging]);
  const formatTime = (seconds: number) => {
    const safe = Math.max(0, Math.floor(seconds || 0));
    const hours = Math.floor(safe / 3600);
    const minutes = Math.floor((safe % 3600) / 60);
    const secs = safe % 60;
    return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}` : `${minutes}:${String(secs).padStart(2, "0")}`;
  };
  async function run(action: () => Promise<unknown>) {
    setBusy(true); setError("");
    try { await action(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể đổi trạng thái"); }
    finally { setBusy(false); }
  }
  const startAt = status.source === source && status.source_time < status.duration_seconds ? status.source_time : 0;
  const selectedSession = status.source === source;
  async function commitSeek() {
    setDragging(false);
    if (status.running && status.seekable) await run(() => api.seek(token, seekDraft));
  }
  return <div className="session-controls">
    <select aria-label="Video demo" value={source} onChange={(event) => setSource(event.target.value)} disabled={status.running}>
      {media.map((item) => <option key={item.name} value={item.name}>{item.name} · {item.size_mb} MB</option>)}
    </select>
    {!status.running && <button className="primary-button" onClick={() => run(() => api.start(token, source, startAt))} disabled={busy}>{busy ? "Đang xử lý…" : startAt > 0 ? `Tiếp tục từ ${formatTime(startAt)}` : "Bắt đầu phân tích"}</button>}
    {status.running && <>
      <button className="transport-button" onClick={() => run(() => status.playback === "paused" ? api.resume(token) : api.pause(token))} disabled={busy}>{status.playback === "paused" ? "▶ Tiếp tục" : "Ⅱ Tạm dừng"}</button>
      <button className="transport-button" onClick={() => run(() => api.seek(token, -10, true))} disabled={busy}>↶ 10s</button>
      <button className="transport-button" onClick={() => run(() => api.seek(token, 10, true))} disabled={busy}>10s ↷</button>
      <button className="transport-button" onClick={() => run(async () => { await api.seek(token, 0); if (status.playback === "paused") await api.resume(token); })} disabled={busy}>↺ Phát lại</button>
      <button className="stop-button" onClick={() => run(() => api.stop(token))} disabled={busy}>■ Dừng</button>
    </>}
    {selectedSession && (status.running || status.duration_seconds > 0) && <div className="replay-timeline">
      <span>{formatTime(dragging ? seekDraft : status.source_time)}</span>
      <input aria-label="Vị trí video" type="range" min="0" max={Math.max(status.duration_seconds, 0.1)} step="0.1" value={Math.min(seekDraft, Math.max(status.duration_seconds, 0.1))} disabled={!status.running || !status.seekable || busy} onPointerDown={() => setDragging(true)} onChange={(event) => setSeekDraft(Number(event.target.value))} onPointerUp={() => void commitSeek()} onKeyUp={() => void commitSeek()} />
      <span>{formatTime(status.duration_seconds)}</span>
      <b>{status.playback === "paused" ? "ĐÃ TẠM DỪNG" : status.running ? "ĐANG PHÁT" : "ĐÃ DỪNG"}</b>
    </div>}
    {error && <span className="inline-error">{error}</span>}
  </div>;
}

function Metric({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return <article className="metric-card"><span>{label}{hint && <abbr title={hint}>?</abbr>}</span><strong>{value}</strong></article>;
}

function DriverHUD({ token, status }: { token: string; status: Status }) {
  const e2e = status.metrics.latencies.end_to_end;
  const active = status.active_events?.[0];
  return <main className="page driver-page">
    <section className="driver-intro"><div><span className="eyebrow">DRIVER VIEW</span><h1>Hành trình an toàn hơn</h1><p>{status.guardrail}</p></div><SessionControls token={token} status={status} /></section>
    <div className="driver-layout">
      <VideoStage token={token} status={status} />
      <aside className="driver-rail">
        <div className="focus-card"><span>NGUY CƠ HIỆN TẠI</span><strong>{active ? Math.round(active.risk_score * 100) : 0}<small>/100</small></strong><div className="risk-meter"><i style={{ width: `${active ? active.risk_score * 100 : 0}%` }} /></div><p>{active?.message ?? "Không có cảnh báo cần chú ý."}</p></div>
        <div className="quick-grid"><Metric label="Đối tượng" value={status.tracks.length} /><Metric label="Lane quality" value={`${Math.round((status.lane?.quality ?? 0) * 100)}%`} hint="Độ tin cậy hình học làn; LDW bị khóa khi chỉ số thấp." /><Metric label="FPS xử lý" value={status.metrics.processed_fps} /><Metric label="P95 latency" value={`${e2e?.p95_ms ?? 0} ms`} hint="Độ trễ end-to-end ở phân vị 95%." /></div>
        <div className="audio-card"><span className="audio-icon">)))</span><div><strong>Vietnamese Audio</strong><small>{status.audio.enabled ? `Sẵn sàng · ${status.audio.provider}` : "Đang tắt"}</small></div></div>
      </aside>
    </div>
    <EventRibbon events={status.events.slice(0, 4)} />
  </main>;
}

function EventRibbon({ events }: { events: AlertEvent[] }) {
  return <section className="event-ribbon"><div className="section-title"><span>SỰ KIỆN GẦN NHẤT</span><small>Evidence timeline</small></div><div className="ribbon-list">{events.length ? events.map((event, index) => <article key={`${event.event_id ?? event.id ?? index}-${event.created_at}`} className={event.severity}><i /><div><strong>{event.message}</strong><span>{new Date(event.created_at * 1000).toLocaleTimeString("vi-VN")} · risk {Math.round(event.risk_score * 100)} · {event.audio_status ?? event.audio_action}</span></div></article>) : <div className="empty-event">Chưa có sự kiện — RoadWatch đang biết im lặng.</div>}</div></section>;
}

function EngineerConsole({ token, status }: { token: string; status: Status }) {
  const [warning, setWarning] = useState(0.56);
  const [critical, setCritical] = useState(0.78);
  const [message, setMessage] = useState("");
  const latencies = status.metrics.latencies;
  useEffect(() => {
    api.config(token).then((config) => {
      const risk = config.risk as { fcw_warning?: number; fcw_critical?: number } | undefined;
      if (risk?.fcw_warning) setWarning(risk.fcw_warning);
      if (risk?.fcw_critical) setCritical(risk.fcw_critical);
    }).catch(() => undefined);
  }, [token]);
  async function saveThresholds() {
    setMessage("");
    try { await api.patchConfig(token, { risk: { fcw_warning: warning, fcw_critical: critical } }); setMessage("Đã lưu cấu hình và tạo audit log."); }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : "Không thể lưu"); }
  }
  return <main className="page engineer-page">
    <section className="engineer-head"><div><span className="eyebrow">ENGINEER CONSOLE</span><h1>Perception & Safety Evidence</h1><p>Quan sát pipeline, kiểm chứng cảnh báo và hiệu chỉnh ngưỡng có audit.</p></div><SessionControls token={token} status={status} /></section>
    <div className="metrics-row"><Metric label="Processed FPS" value={status.metrics.processed_fps} /><Metric label="Sampling skip" value={`${((status.metrics.sampling_skip_ratio ?? status.metrics.frame_drop_ratio) * 100).toFixed(1)}%`} hint="Frame bỏ theo cadence cấu hình; không đồng nghĩa overload drop." /><Metric label="E2E P50" value={`${latencies.end_to_end?.p50_ms ?? 0} ms`} /><Metric label="E2E P95" value={`${latencies.end_to_end?.p95_ms ?? 0} ms`} /><Metric label="Stale audio" value={`${((status.metrics.audio_stale_event_rate ?? 0) * 100).toFixed(1)}%`} hint="Tỷ lệ audio hết hạn/bị thay thế trước khi phát; mục tiêu 0%." /></div>
    <div className="engineer-grid">
      <VideoStage token={token} status={status} compact />
      <section className="panel model-panel"><div className="panel-title"><div><span>MODEL RUNTIME</span><strong>Perception health</strong></div><b className={status.degraded_reasons.length ? "warn" : "ok"}>{status.degraded_reasons.length ? "DEGRADED" : "HEALTHY"}</b></div>{Object.entries(status.models ?? {}).map(([name, model]) => <div className="model-row" key={name}><i className={model.error ? "bad" : model.loaded ? "good" : "idle"} /><div><strong>{name}</strong><span>{model.provider}</span></div><b>{model.loaded ? "Loaded" : model.error ? "Error" : "Standby"}</b></div>)}</section>
      <section className="panel threshold-panel"><div className="panel-title"><div><span>HITL CONFIG</span><strong>FCW thresholds</strong></div><b>AUDITED</b></div><label><span>Warning <b>{warning.toFixed(2)}</b></span><input type="range" min="0.35" max="0.75" step="0.01" value={warning} onChange={(event) => setWarning(Number(event.target.value))} /></label><label><span>Critical <b>{critical.toFixed(2)}</b></span><input type="range" min="0.60" max="0.95" step="0.01" value={critical} onChange={(event) => setCritical(Number(event.target.value))} /></label><button className="primary-button" onClick={saveThresholds} disabled={status.running}>Lưu cấu hình</button><small>Dừng phiên trước khi nạp ngưỡng mới. {message}</small></section>
      <section className="panel evidence-panel"><div className="panel-title"><div><span>DECISION TRACE</span><strong>Evidence packets</strong></div><b>{status.events.length}</b></div><div className="evidence-table"><div className="table-head"><span>Event</span><span>Risk</span><span>Confidence</span><span>Lifecycle / Audio</span></div>{status.events.slice(0, 7).map((event, index) => <div className="table-row" key={`${event.event_id ?? event.id ?? index}-${event.created_at}`}><span><i className={event.severity} />{event.event_type}<small>#{event.object_id ?? "lane"} · t={event.source_time?.toFixed(1) ?? "-"}s</small></span><b>{event.risk_score.toFixed(2)}</b><b>{event.confidence.toFixed(2)}</b><code>{event.lifecycle_status ?? "accepted"}/{event.audio_status ?? event.audio_action}</code></div>)}</div></section>
    </div>
  </main>;
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("roadwatch_token") ?? "");
  const [user, setUser] = useState<User | null>(() => { const value = localStorage.getItem("roadwatch_user"); return value ? JSON.parse(value) as User : null; });
  const [view, setView] = useState("driver");
  const realtime = useRoadWatch(token);
  const status = token ? realtime.status : EMPTY_STATUS;
  const effectiveView = useMemo(() => user?.role === "driver" ? "driver" : view, [user, view]);
  function loggedIn(nextToken: string, nextUser: User) { localStorage.setItem("roadwatch_token", nextToken); localStorage.setItem("roadwatch_user", JSON.stringify(nextUser)); setToken(nextToken); setUser(nextUser); setView(nextUser.role === "engineer" ? "engineer" : "driver"); }
  function logout() { localStorage.removeItem("roadwatch_token"); localStorage.removeItem("roadwatch_user"); setToken(""); setUser(null); }
  if (!token || !user) return <Login onLogin={loggedIn} />;
  return <div className="app-shell"><Header user={user} status={status} connected={realtime.connected} view={effectiveView} setView={setView} logout={logout} />{effectiveView === "engineer" ? <EngineerConsole token={token} status={status} /> : <DriverHUD token={token} status={status} />}<footer><span>RoadWatch v0.2 · Evidence lifecycle</span><strong>⚠ Không thay thế việc quan sát và điều khiển của tài xế.</strong></footer></div>;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
if ("serviceWorker" in navigator && import.meta.env.PROD) navigator.serviceWorker.register("/sw.js").catch(() => undefined);
