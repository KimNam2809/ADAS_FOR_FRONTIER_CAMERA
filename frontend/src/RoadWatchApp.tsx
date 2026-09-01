import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type AlertEvent, type MediaItem, type StartupStatus, type Status, type User } from "./api";
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
  traffic_context: {
    mode: "normal",
    risk_state: "calm",
    density_score: 0,
    confirmed_road_users: 0,
    two_wheeler_count: 0,
    road_occupancy: 0,
    low_motion_ratio: 0,
    audio_policy: "normal",
    policy_mode: "off",
    attention_due: false,
    transition: null,
    fallback: false,
    error: null,
  },
  events: [],
  active_events: [],
  degraded_reasons: [],
  guardrail: "Chỉ hỗ trợ cảnh báo — không tự lái, phanh hoặc đánh lái.",
  audio: { enabled: false, provider: "-", queue_size: 0, output_owner: "none" },
  slm: {
    enabled: false,
    state: "disabled",
    model: "qwen2.5-0.5b",
    provider: "-",
    queue_size: 0,
    max_queue_age_seconds: 30,
    load_ms: null,
    generated: 0,
    failed: 0,
    last_latency_ms: null,
    last_result_status: null,
    last_event_id: null,
    last_failure_reason: null,
    last_quality_score: null,
    last_output_tokens: null,
    last_result_at: null,
    error: null,
  },
  metrics: {
    uptime_seconds: 0,
    captured_frames: 0,
    processed_frames: 0,
    dropped_frames: 0,
    processed_fps: 0,
    display_fps: 0,
    frame_drop_ratio: 0,
    alerts_emitted: 0,
    alerts_suppressed: 0,
    latencies: {},
  },
};

const INITIAL_STARTUP: StartupStatus = {
  deployment_profile: "cloud_demo",
  deferred: true,
  ready: false,
  state: "starting",
  stage: "container",
  message: "Đang đánh thức dịch vụ RoadWatch trên Google Cloud.",
  started_at: Date.now() / 1000,
  ready_at: null,
  elapsed_seconds: 0,
  retry_after_seconds: 2,
  error: null,
};

function LandingLink({ floating = false }: { floating?: boolean }) {
  return <a href="/" className={`landing-link${floating ? " floating" : ""}`} aria-label="Quay lại landing page RoadWatch">
    <span aria-hidden="true">←</span> <span>Landing</span>
  </a>;
}

function useStartupGate() {
  const [status, setStatus] = useState<StartupStatus>(INITIAL_STARTUP);
  const [retryKey, setRetryKey] = useState(0);
  useEffect(() => {
    let stopped = false;
    let timer: number | undefined;
    const startedAt = Date.now();
    const poll = async () => {
      try {
        const next = await api.startup();
        if (stopped) return;
        setStatus(next);
        if (!next.ready && next.state !== "error") {
          timer = window.setTimeout(() => { void poll(); }, Math.max(1000, next.retry_after_seconds * 1000));
        }
      } catch {
        if (stopped) return;
        setStatus((current) => ({
          ...current,
          ready: false,
          state: "starting",
          stage: "container",
          elapsed_seconds: Math.round((Date.now() - startedAt) / 100) / 10,
          message: "Google Cloud đang khởi tạo container và kết nối hệ thống AI.",
          error: null,
        }));
        timer = window.setTimeout(() => { void poll(); }, 2000);
      }
    };
    void poll();
    return () => {
      stopped = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [retryKey]);
  return { status, retry: () => setRetryKey((value) => value + 1) };
}

function StartupGate({ status, retry }: { status: StartupStatus; retry: () => void }) {
  const stages = ["container", "assets", "perception", "tts", "ready"];
  const stageIndex = status.state === "error" ? -1 : stages.indexOf(status.stage);
  return <main className="startup-shell" role="status" aria-live="polite">
    <LandingLink floating />
    <section className={`startup-card ${status.state === "error" ? "error" : ""}`}>
      <div className="brand-lockup startup-brand"><img src="/logo.png" alt="RoadWatch" /><div><strong>RoadWatch</strong><span>ON-DEMAND AI</span></div></div>
      <div className="startup-visual"><i /><i /><i /><span>AI</span></div>
      <span className="startup-kicker">{status.state === "error" ? "KHỞI ĐỘNG CHƯA THÀNH CÔNG" : "ĐANG KHỞI ĐỘNG HỆ THỐNG"}</span>
      <h1>{status.state === "error" ? "RoadWatch cần được thử lại" : "Vui lòng đợi trong ít phút"}</h1>
      <p className="startup-message">{status.message}</p>
      <p className="startup-explainer">Để tiết kiệm tài nguyên, GCP và các model chỉ hoạt động khi có người truy cập. Lần mở đầu tiên thường cần 1–3 phút để tải Object Detection, Traffic Sign, Lane Detection và Piper tiếng Việt. Trang sẽ tự chuyển khi hệ thống sẵn sàng.</p>
      <div className="startup-progress" aria-label="Tiến độ khởi động">
        {stages.slice(0, -1).map((stage, index) => <span key={stage} className={stageIndex > index ? "done" : stageIndex === index ? "active" : ""}><i />{["GCP", "Dữ liệu", "Model AI", "TTS Việt"][index]}</span>)}
      </div>
      <div className="startup-meta"><span><i className="pulse-dot" />{status.state === "error" ? "Cần thử lại" : "Đang tự động kiểm tra"}</span><b>{Math.round(status.elapsed_seconds)} giây</b></div>
      {status.state === "error" && <><button className="primary-button startup-retry" onClick={retry}>Kiểm tra lại trạng thái</button><small className="startup-error">Mã trạng thái: {status.error ?? "STARTUP_INIT_FAILED"}. Nếu thông báo vẫn còn, vui lòng tải lại URL sau ít phút.</small></>}
      <div className="startup-safety">RoadWatch chỉ hỗ trợ cảnh báo — không tự lái, phanh hoặc đánh lái.</div>
    </section>
  </main>;
}

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
      <LandingLink floating />
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
    let stopped = false;
    let timer: number | undefined;
    const poll = async () => {
      let nextStatus: Status | undefined;
      try {
        const next = await api.status(token);
        nextStatus = next;
        if (stopped) return;
        setStatus(next);
        setConnected(true);
      } catch {
        setConnected(false);
      } finally {
        if (!stopped) {
          // Status telemetry is intentionally decoupled from the MJPEG/video
          // stream and inference loop. Poll less while idle and slightly less
          // aggressively on Cloud Run to reduce render/JSON overhead without
          // changing frame processing or alert timing.
          const delay = nextStatus?.running
            ? nextStatus.deployment_profile === "cloud_demo" ? 750 : 500
            : nextStatus ? 1500 : 1000;
          timer = window.setTimeout(() => { void poll(); }, delay);
        }
      }
    };
    void poll();
    return () => { stopped = true; if (timer !== undefined) window.clearTimeout(timer); };
  }, [token]);
  return { status, connected };
}

type BrowserAudioState = {
  enabled: boolean;
  ready: boolean;
  provider: string;
  lastMessage?: string;
  error?: string;
  activate: () => Promise<boolean>;
};

function normalizeAudioMessage(value: string): string {
  const tokens = value.trim().replace(/\s+/g, " ").split(" ").filter(Boolean);
  const result: string[] = [];
  let previous = "";
  for (const token of tokens) {
    const comparable = token.replace(/[^\p{L}\p{N}]+/gu, "").toLocaleLowerCase("vi-VN");
    if (comparable && comparable === previous) continue;
    result.push(token);
    if (comparable) previous = comparable;
  }
  return result.join(" ");
}

function audioMessageKey(event: AlertEvent): string {
  return `${event.event_type}:${normalizeAudioMessage(event.spoken_message ?? event.display_message ?? event.message).toLocaleLowerCase("vi-VN")}`;
}

function useBrowserAudio(token: string, status: Status): BrowserAudioState {
  const [state, setState] = useState<BrowserAudioState>({
    enabled: "AudioContext" in window,
    ready: false,
    provider: "Piper vi_VN · Trúc Ly + Web Audio beep",
    activate: async () => false,
  });
  const audioContext = useRef<AudioContext | null>(null);
  const seenEvents = useRef<Set<string>>(new Set());
  const inFlightEvents = useRef<Set<string>>(new Set());
  const retryAt = useRef<Map<string, number>>(new Map());
  const beepedEvents = useRef<Set<string>>(new Set());
  const session = useRef<string | undefined>(undefined);
  const activeSources = useRef<AudioBufferSourceNode[]>([]);
  const requests = useRef<AbortController[]>([]);
  const activePlayback = useRef<{ key: string; severity: AlertEvent["severity"]; source: AudioBufferSourceNode } | null>(null);
  const recentAudioKeys = useRef<Map<string, number>>(new Map());

  const stopAudio = () => {
    requests.current.forEach((request) => request.abort());
    requests.current = [];
    activeSources.current.forEach((source) => {
      try { source.stop(); } catch { /* source already ended */ }
    });
    activeSources.current = [];
    activePlayback.current = null;
  };

  const activate = useCallback(async (): Promise<boolean> => {
    if (!("AudioContext" in window)) {
      setState((current) => ({ ...current, enabled: false, error: "Trình duyệt không hỗ trợ âm thanh" }));
      return false;
    }
    try {
      const context = audioContext.current ??= new AudioContext();
      if (context.state !== "running") await context.resume();
      if (context.state !== "running") throw new Error("Trình duyệt chưa cho phép phát âm thanh");
      setState((current) => ({ ...current, enabled: true, ready: true, error: undefined }));
      return true;
    } catch (reason) {
      setState((current) => ({
        ...current,
        enabled: true,
        ready: false,
        error: reason instanceof Error ? reason.message : "Trình duyệt chặn âm thanh",
      }));
      return false;
    }
  }, []);

  useEffect(() => {
    // Browser autoplay policy requires a user gesture. Awaiting resume() is
    // important: setting ready before the promise settles can make the audio
    // effect observe a suspended context and never retry for the same event.
    const unlock = () => { void activate(); };
    window.addEventListener("pointerdown", unlock);
    window.addEventListener("keydown", unlock);
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, [activate]);

  useEffect(() => {
    if (session.current === status.session_id) return;
    session.current = status.session_id;
    seenEvents.current.clear();
    inFlightEvents.current.clear();
    retryAt.current.clear();
    beepedEvents.current.clear();
    recentAudioKeys.current.clear();
    stopAudio();
  }, [status.session_id]);

  useEffect(() => {
    // Backend and browser must never play the same event. New backends expose
    // an explicit owner; the fallback keeps compatibility with old Cloud
    // responses where disabled server audio implied browser playback.
    const outputOwner = status.audio.output_owner ?? (status.audio.enabled ? "server" : "browser");
    if (outputOwner !== "browser" || !status.running || status.playback === "paused") {
      stopAudio();
      return;
    }
    const context = audioContext.current;
    if (!state.ready || !context || context.state !== "running") return;
    // Keep one browser request in flight. This preserves governor priority and
    // prevents several WAVs from overlapping when polling publishes a burst.
    if (inFlightEvents.current.size) return;
    const now = Date.now() / 1000;
    const candidates = status.events.filter((event) => {
      const key = `${status.session_id ?? "none"}:${event.event_id ?? event.id ?? event.created_at}`;
      const audioKey = audioMessageKey(event);
      const recentUntil = recentAudioKeys.current.get(audioKey) ?? 0;
      return (
        ["tts", "beep_tts", "context_beep"].includes(event.audio_action) &&
        !seenEvents.current.has(key) &&
        !inFlightEvents.current.has(key) &&
        now * 1000 >= recentUntil &&
        now * 1000 >= (retryAt.current.get(key) ?? 0) &&
        now - event.created_at <= 4.0 &&
        (event.expires_at === undefined || event.expires_at >= now)
      );
    });
    if (!candidates.length) return;
    const event = [...candidates].sort((left, right) => {
      const severity = { critical: 3, warning: 2, advisory: 1, informational: 0 };
      return severity[right.severity] - severity[left.severity] || right.risk_score - left.risk_score;
    })[0];
    const message = event.spoken_message ?? event.display_message ?? event.message;
    const eventId = event.event_id;
    if (!eventId) {
      setState((current) => ({ ...current, error: "Cảnh báo thiếu event ID cho Piper" }));
      return;
    }
    const eventKey = `${status.session_id ?? "none"}:${eventId}`;
    const canonicalAudioKey = audioMessageKey(event);
    const active = activePlayback.current;
    if (active) {
      if (active.key === canonicalAudioKey) {
        seenEvents.current.add(eventKey);
        return;
      }
      if (event.severity !== "critical" || active.severity === "critical") return;
      // A critical event may preempt a lower-severity sentence, but it still
      // owns the only playback channel and never overlaps the old source.
      stopAudio();
    }
    inFlightEvents.current.add(eventKey);

    if (event.audio_action === "context_beep") {
      try {
        const pattern: Array<[number, number]> = [[920, 70], [0, 110], [1100, 70]];
        let cursor = context.currentTime;
        pattern.forEach(([frequency, duration]) => {
          if (frequency > 0) {
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            oscillator.frequency.value = frequency;
            gain.gain.setValueAtTime(0.0001, cursor);
            gain.gain.exponentialRampToValueAtTime(0.20, cursor + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, cursor + duration / 1000);
            oscillator.connect(gain).connect(context.destination);
            oscillator.start(cursor);
            oscillator.stop(cursor + duration / 1000);
          }
          cursor += duration / 1000;
        });
        seenEvents.current.add(eventKey);
        setState((current) => ({
          ...current,
          ready: true,
          lastMessage: event.display_message ?? event.message,
          error: undefined,
        }));
      } catch (reason) {
        setState((current) => ({
          ...current,
          error: reason instanceof Error ? reason.message : "Không phát được beep ngữ cảnh",
        }));
      } finally {
        inFlightEvents.current.delete(eventKey);
      }
      return;
    }

    let speechStartAt = context.currentTime;
    if (event.audio_action === "beep_tts" && !beepedEvents.current.has(eventKey)) {
      try {
        const pattern: Array<[number, number]> = [[1180, 90], [0, 55], [1450, 130]];
        let cursor = context.currentTime;
        pattern.forEach(([frequency, duration]) => {
          if (frequency > 0) {
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            oscillator.frequency.value = frequency;
            gain.gain.setValueAtTime(0.0001, cursor);
            gain.gain.exponentialRampToValueAtTime(0.18, cursor + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, cursor + duration / 1000);
            oscillator.connect(gain).connect(context.destination);
            oscillator.start(cursor);
            oscillator.stop(cursor + duration / 1000);
          }
          cursor += duration / 1000;
        });
        speechStartAt = cursor + 0.08;
        beepedEvents.current.add(eventKey);
      } catch (reason) {
        setState((current) => ({
          ...current,
          error: reason instanceof Error ? reason.message : "Không phát được beep",
        }));
      }
    }

    const controller = new AbortController();
    requests.current.push(controller);
    void api.ttsAudio(token, eventId).then(async (result) => {
      if (controller.signal.aborted || session.current !== status.session_id) return;
      const buffer = await context.decodeAudioData(result.wav.slice(0));
      if (controller.signal.aborted || context.state !== "running") return;
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      activeSources.current.push(source);
      source.onended = () => {
        activeSources.current = activeSources.current.filter((item) => item !== source);
        if (activePlayback.current?.source === source) activePlayback.current = null;
      };
      activePlayback.current = { key: canonicalAudioKey, severity: event.severity, source };
      source.start(Math.max(context.currentTime + 0.01, speechStartAt));
      seenEvents.current.add(eventKey);
      recentAudioKeys.current.set(canonicalAudioKey, Date.now() + 2500);
      retryAt.current.delete(eventKey);
      setState((current) => ({
        ...current,
        ready: true,
         provider: `${result.provider} · ${result.voiceName} · ${result.cache}`,
        lastMessage: message,
        error: undefined,
      }));
    }).catch((reason) => {
      if (controller.signal.aborted) return;
      // A transient 503/cold start must not permanently consume the event.
      // The next status poll can retry while the event is still fresh.
      retryAt.current.set(eventKey, Date.now() + 1000);
      setState((current) => ({
        ...current,
        error: `Piper TTS lỗi: ${reason instanceof Error ? reason.message : "không xác định"}`,
      }));
    }).finally(() => {
      inFlightEvents.current.delete(eventKey);
      requests.current = requests.current.filter((item) => item !== controller);
    });
  }, [activate, state.ready, status.audio.enabled, status.audio.output_owner, status.events, status.playback, status.running, status.session_id, token]);

  useEffect(() => () => stopAudio(), []);

  return { ...state, activate };
}

function ScreenIdentity({ mode, status, user, onViewChange, logout }: {
  mode: "driver" | "engineer";
  status: Status;
  user: User;
  onViewChange: (value: "driver" | "engineer") => void;
  logout: () => void;
}) {
  const canSwitch = user.role === "engineer";
  const outputOwner = status.audio.output_owner ?? (status.audio.enabled ? "server" : "browser");
  const audioAvailable = outputOwner === "browser" || (outputOwner === "server" && status.audio.enabled);
  return <div className={`screen-identity ${mode}-identity`}>
    <div className="screen-heading">
      <div>
        <span className="eyebrow">{mode === "driver" ? "DRIVER HUD" : "ENGINEER CONSOLE"}</span>
        <h1>{mode === "driver" ? "Driver HUD" : "Engineer Console"}</h1>
        <p>{mode === "driver" ? "Trợ lý cảnh báo phía trước · chỉ hỗ trợ tài xế." : "Perception & Safety Evidence · kiểm chứng có audit."}</p>
      </div>
    </div>
    <div className="screen-actions">
      <div className="screen-status" aria-label="Trạng thái màn hình">
        <span className={audioAvailable ? "status-on" : "status-off"}><i />Âm thanh: {audioAvailable ? "Bật" : "Tắt"}</span>
        <span className={status.running ? "status-on" : "status-off"}><i />Camera: {status.running ? "ON" : "STANDBY"}</span>
        <b>{mode === "driver" ? "DEMO HUD" : "MODEL RUNTIME"}</b>
      </div>
      <div className="screen-role-actions">
        {canSwitch && <button className="screen-mode-button" type="button" onClick={() => onViewChange(mode === "driver" ? "engineer" : "driver")}>
          {mode === "driver" ? "Engineer Console" : "Driver HUD"}
        </button>}
        <button className="screen-user" type="button" onClick={logout}>{user.username}<small>Đăng xuất</small></button>
      </div>
    </div>
  </div>;
}

const HUD_ASSET_BY_CLASS: Record<string, string> = {
  bicycle: "/hud/traffic-bicycle.png",
  bike: "/hud/traffic-bicycle.png",
  cyclist: "/hud/traffic-bicycle.png",
  car: "/hud/traffic-car.png",
  automobile: "/hud/traffic-car.png",
  vehicle: "/hud/traffic-car.png",
  bus: "/hud/traffic-truck.png",
  truck: "/hud/traffic-truck.png",
  motorcycle: "/hud/traffic-motorcycle.png",
  motorbike: "/hud/traffic-motorcycle.png",
  person: "/hud/traffic-person.png",
  pedestrian: "/hud/traffic-person.png",
};

function asFiniteNumber(value: unknown): number | undefined {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function hudAssetFor(label: string): string | undefined {
  const normalized = label.toLowerCase().replaceAll("_", " ").trim();
  if (normalized.includes("xe máy")) return HUD_ASSET_BY_CLASS.motorcycle;
  if (normalized.includes("xe đạp")) return HUD_ASSET_BY_CLASS.bicycle;
  if (normalized.includes("người")) return HUD_ASSET_BY_CLASS.person;
  if (normalized.includes("xe tải") || normalized.includes("xe buýt")) return HUD_ASSET_BY_CLASS.truck;
  if (normalized.includes("ô tô") || normalized.includes("phương tiện")) return HUD_ASSET_BY_CLASS.car;
  return HUD_ASSET_BY_CLASS[normalized];
}

function hudXPosition(track: Record<string, unknown>): number {
  const normalized = asFiniteNumber(track.projected_x_norm) ?? asFiniteNumber(track.origin_x_norm);
  if (normalized !== undefined && normalized >= 0 && normalized <= 1) return clamp(normalized * 100, 14, 86);
  const location = String(track.location ?? "").toLowerCase();
  if (location.includes("trái") || location.includes("left")) return 27;
  if (location.includes("phải") || location.includes("right")) return 73;
  return 50;
}

type HudActor = {
  id: string;
  label: string;
  asset: string;
  x: number;
  y: number;
  scale: number;
  risk: number;
  severity: "normal" | "warning" | "critical";
};

function spreadHudActors(actors: HudActor[]): HudActor[] {
  const placed: HudActor[] = [];
  for (const actor of actors) {
    let x = actor.x;
    for (let attempt = 0; attempt < 4; attempt += 1) {
      const overlaps = placed.some((current) => Math.abs(current.x - x) < 10 && Math.abs(current.y - actor.y) < 11);
      if (!overlaps) break;
      const direction = attempt % 2 === 0 ? 1 : -1;
      const distance = 11 + Math.floor(attempt / 2) * 10;
      x = clamp(actor.x + direction * distance, 14, 86);
    }
    placed.push({ ...actor, x });
  }
  return placed;
}

const HudPanel = React.memo(function HudPanel({ status, role }: { status: Status; role: "driver" | "engineer" }) {
  const context = status.traffic_context;
  const active = status.active_events?.find((event) => event.display_scope !== "hud_context");
  const hudOnlyEvents = status.active_events?.filter((event) => event.display_scope === "hud_context" && event.event_type !== "traffic_context_attention").slice(0, 3) ?? [];
  const actors = useMemo<HudActor[]>(() => status.running ? spreadHudActors(status.tracks.map((track, index) => {
    const label = String(track.class_name ?? track.label ?? track.name ?? "Đối tượng").replaceAll("_", " ");
    const asset = hudAssetFor(label);
    if (!asset) return undefined;
    const proximity = clamp(asFiniteNumber(track.proximity_score) ?? 0.32, 0, 1);
    const risk = clamp(asFiniteNumber(track.risk_score) ?? 0, 0, 1);
    return {
      id: String(track.track_id ?? track.id ?? `${label}-${index}`),
      label,
      asset,
      x: hudXPosition(track),
      y: 13 + proximity * 43,
      scale: 0.46 + proximity * 0.48,
      risk,
      severity: risk >= 0.75 ? "critical" : risk >= 0.45 ? "warning" : "normal",
    } satisfies HudActor;
  }).filter((actor): actor is HudActor => Boolean(actor))
    .sort((first, second) => (second.risk - first.risk) || (second.y - first.y))
    .slice(0, 5)) : [], [status.running, status.tracks]);
  const simulatedSpeed = status.running ? Math.min(60, 28 + (Math.floor(status.source_time) % 15)) : 0;
  return <aside className={`hud-panel ${role}`} aria-label="Driver HUD mô phỏng">
    <div className="hud-mode"><i />DEMO · TELEMETRY MÔ PHỎNG</div>
    <div className="hud-speed"><strong>{simulatedSpeed}</strong><span>km/h</span><small>TỐC ĐỘ MÔ PHỎNG</small></div>
    {context.mode === "dense" && <div className="hud-context-card"><strong>GIAO THÔNG ĐÔNG</strong><span>CẢNH BÁO CHỌN LỌC</span></div>}
    {context.mode === "dense" && hudOnlyEvents.length > 0 && <div className="hud-context-events">{hudOnlyEvents.map((event) => <span key={event.event_id ?? event.id}>{event.display_message ?? event.message}</span>)}</div>}
    <div className={`hud-connection ${status.running ? "active" : ""}`}><i />{status.running ? "EDGE OFFLINE" : "SẴN SÀNG"}<small>Chỉ hỗ trợ cảnh báo</small></div>
    <div className="hud-road" aria-label="Mô phỏng vùng quan sát phía trước">
      <div className="hud-lane-line left" /><div className="hud-lane-line right" />
      <img className="hud-ego-vehicle" src="/hud/ego-car.png" alt="Xe RoadWatch mô phỏng" decoding="async" />
      {actors.map((actor) => <div
        className={`hud-track-sprite ${actor.severity}`}
        key={actor.id}
        style={{ left: `${actor.x}%`, top: `${actor.y}%`, transform: `translate(-50%, -50%) scale(${actor.scale})` }}
        title={`${actor.label} · risk ${Math.round(actor.risk * 100)}%`}
      >
        <img src={actor.asset} alt={actor.label} decoding="async" />
        {actor.severity !== "normal" && <span>{actor.label}</span>}
      </div>)}
    </div>
    <div className="hud-summary">
      <span><b>{status.running ? status.tracks.length : 0}</b> đối tượng</span>
      <span><b>{status.running ? Math.round((status.lane?.quality ?? 0) * 100) : 0}%</b> lane quality</span>
    </div>
    <div className={`hud-focus ${active?.severity ?? "idle"}`}><i />{active ? active.event_type : "NO ACTIVE ALERT"}<small>{active ? "Đang ưu tiên cảnh báo" : "RoadWatch đang biết im lặng"}</small></div>
  </aside>;
});

function VideoStage({ token, status, compact = false }: { token: string; status: Status; compact?: boolean }) {
  const [streamFailed, setStreamFailed] = useState(false);
  const topEvent = status.active_events?.find((event) => event.display_scope !== "hud_context");
  const source = status.source_key ?? "";
  const previewUrl = source && !source.match(/^\d+$/)
    ? `/api/media/file?source=${encodeURIComponent(source)}&token=${encodeURIComponent(token)}`
    : "";
  useEffect(() => {
    setStreamFailed(false);
  }, [status.session_id, source]);
  const showPreview = Boolean(previewUrl) && (!status.running || status.frame_id === 0 || streamFailed);
  return <section className={`video-stage ${compact ? "compact" : ""}`} data-aspect-ratio="16:9" aria-label="RoadWatch video viewport">
    {showPreview ? <><video key={`${status.session_id ?? source}-${streamFailed ? "stream-fallback" : "preview"}`} className="source-preview" src={previewUrl} controls muted playsInline autoPlay preload="metadata" /><div className="preview-status">{streamFailed ? "Đang hiển thị video gốc · perception vẫn tiếp tục" : status.running ? `Đang nạp perception · ${status.stage ?? "loading"}` : "Video mẫu sẵn sàng"}</div></> : status.running ? <img key={status.session_id} src={`/api/stream.mjpg?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(status.session_id ?? "")}`} alt="Luồng camera RoadWatch" onError={() => setStreamFailed(true)} /> : <div className="video-placeholder"><div className="road-perspective"><i /><i /></div><strong>Sẵn sàng phân tích</strong><span>Chọn video và bắt đầu phiên RoadWatch</span></div>}
    <div className="camera-badge">CAM 01 · {status.source ?? "NO SOURCE"}</div>
    <div className="offline-badge">● OFFLINE EDGE</div>
    {topEvent && status.running && <div className={`hazard-banner ${topEvent.severity}`}><span>{topEvent.severity === "critical" ? "!" : "i"}</span><div><small>{topEvent.event_type.toUpperCase()}</small><strong>{topEvent.display_message ?? topEvent.message}</strong></div><b>{Math.round(topEvent.risk_score * 100)}</b></div>}
  </section>;
}

function SessionControls({ token, status, onActivateAudio }: { token: string; status: Status; onActivateAudio?: () => Promise<boolean> }) {
  const [media, setMedia] = useState<MediaItem[]>([]);
  const [source, setSource] = useState("test_video10.mp4");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | undefined>();
  const [seekDraft, setSeekDraft] = useState(0);
  const [dragging, setDragging] = useState(false);
  useEffect(() => { api.media(token).then((items) => { setMedia(items); const values = items.map((item) => item.source ?? item.name); if (!values.includes(source) && values.length) setSource(values[0]); }).catch((reason) => setError(String(reason))); }, [token]);
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
  const selectedSession = (status.source_key ?? status.source) === source || status.source === source.split("/").pop();
  async function upload(file: File | undefined) {
    if (!file) return;
    setSelectedFile(file); setUploading(true); setError("");
    try {
      const item = await api.uploadVideo(token, file);
      setMedia((current) => [...current, item]);
      setSource(item.source ?? item.name);
      setSeekDraft(0);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải video");
    } finally { setUploading(false); }
  }
  async function commitSeek() {
    setDragging(false);
    if (status.running && status.seekable) await run(() => api.seek(token, seekDraft));
  }
  return <div className="session-controls">
    <select aria-label="Video demo" value={source} onChange={(event) => setSource(event.target.value)} disabled={status.running}>
      {media.map((item) => <option key={item.source ?? item.name} value={item.source ?? item.name}>{item.name} · {item.condition ?? "mixed"} · {item.size_mb} MB</option>)}
    </select>
    <label className={`upload-control ${uploading ? "uploading" : ""}`} htmlFor="roadwatch-upload"><span className="upload-icon">↑</span><span><strong>{uploading ? "Đang tải lên…" : selectedFile ? selectedFile.name : "Thêm video"}</strong><small>{uploading ? "Đang lưu vào kho replay" : selectedFile ? `${(selectedFile.size / 1048576).toFixed(1)} MB · đã chọn` : "MP4 / MOV / MKV · tối đa 25 MB"}</small></span><input id="roadwatch-upload" aria-label="Tải video tùy chỉnh" type="file" accept="video/*" disabled={status.running || uploading} onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label>
    {!status.running && <button className="primary-button" onClick={() => run(async () => { await onActivateAudio?.(); await api.start(token, source, startAt); })} disabled={busy}>{busy ? "Đang xử lý…" : startAt > 0 ? `Tiếp tục từ ${formatTime(startAt)}` : "Bắt đầu phân tích"}</button>}
    {status.running && <>
      <button className="transport-button" onClick={() => run(async () => { if (status.playback === "paused") { await onActivateAudio?.(); await api.resume(token); } else { await api.pause(token); } })} disabled={busy}>{status.playback === "paused" ? "▶ Tiếp tục" : "Ⅱ Tạm dừng"}</button>
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

function DriverHUD({ token, status, browserAudio, user, onViewChange, logout }: { token: string; status: Status; browserAudio: BrowserAudioState; user: User; onViewChange: (value: "driver" | "engineer") => void; logout: () => void }) {
  const active = status.active_events?.find((event) => event.display_scope !== "hud_context");
  return <main className="page driver-page">
    <div className="screen-layout driver-layout-v2">
      <HudPanel status={status} role="driver" />
      <section className="screen-content driver-content">
        <ScreenIdentity mode="driver" status={status} user={user} onViewChange={onViewChange} logout={logout} />
        <VideoStage token={token} status={status} />
        <SessionControls token={token} status={status} onActivateAudio={browserAudio.activate} />
        <section className="driver-status-row">
          <div className="focus-card"><span>NGUY CƠ HIỆN TẠI</span><strong>{active ? Math.round(active.risk_score * 100) : 0}<small>/100</small></strong><div className="risk-meter"><i style={{ width: `${active ? active.risk_score * 100 : 0}%` }} /></div><p>{active?.display_message ?? active?.message ?? "Không có cảnh báo cần chú ý."}</p></div>
          <div className="audio-card"><span className="audio-icon">)))</span><div><strong>Âm thanh tiếng Việt</strong><small>{browserAudio.enabled ? browserAudio.error ?? `${browserAudio.ready ? "Sẵn sàng" : "Chạm để bật"} · ${browserAudio.provider}` : "Trình duyệt không hỗ trợ âm thanh"}</small></div></div>
        </section>
        <div className="driver-disclaimer"><i>i</i><span>{status.guardrail}</span></div>
        <details className="driver-evidence"><summary>Chi tiết sự kiện cho kỹ sư</summary><EventRibbon events={status.events.slice(0, 4)} /></details>
      </section>
    </div>
  </main>;
}

function EventRibbon({ events }: { events: AlertEvent[] }) {
  return <section className="event-ribbon"><div className="section-title"><span>SỰ KIỆN GẦN NHẤT</span><small>Evidence timeline</small></div><div className="ribbon-list">{events.length ? events.map((event, index) => <article key={`${event.event_id ?? event.id ?? index}-${event.created_at}`} className={event.severity}><i /><div><strong>{event.display_message ?? event.message}</strong><span>{new Date(event.created_at * 1000).toLocaleTimeString("vi-VN")} · risk {Math.round(event.risk_score * 100)} · {event.audio_route ?? event.audio_status ?? event.audio_action}</span></div></article>) : <div className="empty-event">Chưa có sự kiện — RoadWatch đang biết im lặng.</div>}</div></section>;
}

type EventFilter = "all" | AlertEvent["severity"] | "suppressed";

function EventHistory({ token, status }: { token: string; status: Status }) {
  const [filter, setFilter] = useState<EventFilter>("all");
  const [selected, setSelected] = useState<string | undefined>();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const events = useMemo(() => status.events.slice().sort((left, right) => (right.source_time ?? right.created_at) - (left.source_time ?? left.created_at)), [status.events]);
  const filtered = events.filter((event) => {
    if (filter === "all") return true;
    if (filter === "suppressed") return Boolean(event.suppression_reason) || event.lifecycle_status === "suppressed" || event.audio_status === "suppressed";
    return event.severity === filter;
  });
  async function focusEvent(event: AlertEvent) {
    const key = event.event_id ?? String(event.id ?? event.created_at);
    setSelected(key); setMessage("");
    if (!status.running || !status.seekable || event.source_time === undefined) {
      setMessage("Sự kiện đã chọn; cần phiên replay đang chạy để tua đến bằng chứng.");
      return;
    }
    setBusy(true);
    try { await api.seek(token, event.source_time); setMessage(`Đã tua đến ${formatClock(event.source_time)}.`); }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : "Không thể mở bằng chứng."); }
    finally { setBusy(false); }
  }
  const visible = filtered.slice(0, 100);
  return <section className="panel event-history-panel">
    <div className="panel-title"><div><span>EVENT HISTORY</span><strong>Lịch sử sự kiện · session audit</strong></div><b>{events.length}</b></div>
    <div className="event-history-toolbar"><div className="event-filters" role="group" aria-label="Lọc sự kiện">{(["all", "critical", "warning", "suppressed"] as EventFilter[]).map((value) => <button type="button" key={value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{value === "all" ? "Tất cả" : value === "critical" ? "Critical" : value === "warning" ? "Warning" : "Suppressed"}</button>)}</div><button type="button" className="secondary-button" onClick={() => { if (visible[0]) void focusEvent(visible[0]); }} disabled={!visible.length || busy}>Mở bằng chứng</button></div>
    <div className="event-history-table" role="table" aria-label="Lịch sử cảnh báo">
      <div className="event-history-head" role="row"><span>Thời gian</span><span>Sự kiện</span><span>Đối tượng</span><span>Bối cảnh</span><span>Lifecycle / Audio</span></div>
       {visible.length ? visible.map((event, index) => { const key = event.event_id ?? String(event.id ?? `${event.created_at}-${index}`); return <button type="button" role="row" className={`event-history-row ${selected === key ? "selected" : ""}`} key={key} onClick={() => void focusEvent(event)}><span>{formatClock(event.source_time ?? 0)}</span><span><i className={event.severity} />{event.event_type}</span><span>{event.evidence?.object_label ? String(event.evidence.object_label) : event.object_id ? `#${event.object_id}` : "—"}</span><span>{event.location ?? "Phía trước"}</span><code>{event.lifecycle_status ?? "accepted"} · {event.audio_route ?? event.audio_status ?? event.audio_action}{event.suppression_reason ? ` · ${event.suppression_reason}` : ""}{event.slm_status ? ` · SLM:${event.slm_status}` : ""}</code></button>; }) : <div className="empty-event">Không có sự kiện phù hợp với bộ lọc.</div>}
    </div>
    <small className="event-history-note">{message || "Bấm vào một dòng để tua video đến timestamp và kiểm tra evidence."}{events.length > 100 ? ` Hiển thị 100/${events.length} sự kiện gần nhất.` : ""}</small>
  </section>;
}

function formatClock(seconds: number) {
  const safe = Math.max(0, Math.floor(seconds || 0));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const secs = safe % 60;
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}` : `${minutes}:${String(secs).padStart(2, "0")}`;
}

function EngineerConsole({ token, status, browserAudio, user, onViewChange, logout }: { token: string; status: Status; browserAudio: BrowserAudioState; user: User; onViewChange: (value: "driver" | "engineer") => void; logout: () => void }) {
  const [warning, setWarning] = useState(0.56);
  const [critical, setCritical] = useState(0.78);
  const [message, setMessage] = useState("");
  const latencies = status.metrics.latencies;
  const latestSlmEvent = status.events.find((event) => Boolean(event.slm_explanation) || ["pending", "fallback"].includes(event.slm_status ?? ""));
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
    <div className="screen-layout engineer-layout-v2">
      <HudPanel status={status} role="engineer" />
      <section className="screen-content engineer-content">
        <ScreenIdentity mode="engineer" status={status} user={user} onViewChange={onViewChange} logout={logout} />
        <div className="metrics-row"><Metric label="Processed FPS" value={status.metrics.processed_fps} hint="FPS frame đã chạy perception + risk; không phải FPS hiển thị." /><Metric label="Display FPS" value={status.metrics.display_fps ?? 0} hint="FPS frame đã encode cho màn hình; frame skip chỉ dùng để hiển thị, không ra cảnh báo mới." /><Metric label="Sampling skip" value={`${((status.metrics.sampling_skip_ratio ?? status.metrics.frame_drop_ratio) * 100).toFixed(1)}%`} hint="Frame bỏ khỏi inference theo cadence; không đồng nghĩa overload drop." /><Metric label="E2E P50" value={`${latencies.end_to_end?.p50_ms ?? 0} ms`} /><Metric label="E2E P95" value={`${latencies.end_to_end?.p95_ms ?? 0} ms`} /><Metric label="Warmup" value={`${status.metrics.warmup_ms ?? 0} ms`} hint="Thời gian nạp model, tách khỏi E2E inference." /></div>
        <VideoStage token={token} status={status} />
        <SessionControls token={token} status={status} onActivateAudio={browserAudio.activate} />
        <div className="engineer-bottom-grid">
          <EventHistory token={token} status={status} />
          <aside className="engineer-side">
           <section className="panel model-panel"><div className="panel-title"><div><span>MODEL RUNTIME</span><strong>Perception health</strong></div><b className={status.degraded_reasons.length ? "warn" : "ok"}>{status.degraded_reasons.length ? "DEGRADED" : "HEALTHY"}</b></div>{Object.entries(status.models ?? {}).map(([name, model]) => <div className="model-row" key={name}><i className={model.error ? "bad" : model.loaded ? "good" : "idle"} /><div><strong>{name}</strong><span>{model.provider}</span></div><b>{model.loaded ? "Loaded" : model.error ? "Error" : "Standby"}</b></div>)}<div className="model-row"><i className={status.slm?.state === "ready" ? "good" : status.slm?.state === "error" ? "bad" : "idle"} /><div><strong>SLM explanation</strong><span>{status.slm?.model ?? "qwen2.5-0.5b"} · {status.slm?.provider ?? "-"}</span></div><b>{status.slm?.enabled ? status.slm?.state : "Disabled"}</b></div></section>
             <section className="panel context-panel"><div className="panel-title"><div><span>ROADWATCH ALERT CONTEXT V1</span><strong>Selective Audio</strong></div><b className={status.traffic_context.mode === "dense" ? "warn" : "ok"}>{status.traffic_context.mode.toUpperCase()}</b></div><div className="context-grid"><span>Density<strong>{Math.round(status.traffic_context.density_score * 100)}%</strong></span><span>Road users<strong>{status.traffic_context.confirmed_road_users}</strong></span><span>2-wheelers<strong>{status.traffic_context.two_wheeler_count}</strong></span><span>Audio<strong>{status.traffic_context.audio_policy}</strong></span></div><small>{status.traffic_context.error ? `Fallback: ${status.traffic_context.error}` : status.traffic_context.mode === "dense" ? `${Math.round(status.traffic_context.low_motion_ratio * 100)}% đang chuyển động thấp · event an toàn chuyển HUD-only.` : "Policy enforce · cảnh báo nguy hiểm vẫn ưu tiên."}</small></section>
             <section className="panel slm-panel"><div className="panel-title"><div><span>SLM EXPLANATION</span><strong>Giải thích kỹ thuật</strong></div><b className={status.slm?.state === "ready" ? "ok" : status.slm?.state === "error" ? "warn" : ""}>{status.slm?.enabled ? status.slm.state.toUpperCase() : "DISABLED"}</b></div><div className="slm-runtime-grid"><span>Provider<strong>{status.slm?.provider ?? "-"}</strong></span><span>Queue<strong>{status.slm?.queue_size ?? 0}</strong></span><span>Ready<strong>{status.slm?.generated ?? 0}</strong></span><span>Fallback<strong>{status.slm?.failed ?? 0}</strong></span></div>{status.slm?.last_latency_ms ? <small className="slm-runtime-note">Lần gần nhất: {Math.round(status.slm.last_latency_ms)} ms{status.slm.last_quality_score !== null && status.slm.last_quality_score !== undefined ? ` · quality ${Math.round(status.slm.last_quality_score)}%` : ""}</small> : null}{latestSlmEvent?.slm_explanation ? <p className="slm-explanation-text">{latestSlmEvent.slm_explanation}</p> : latestSlmEvent?.slm_status === "pending" ? <p className="slm-muted">Đang tạo giải thích kỹ thuật bất đồng bộ…</p> : latestSlmEvent?.slm_status === "fallback" ? <p className="slm-muted">Fallback deterministic{latestSlmEvent.slm_failure_reason ? ` · ${latestSlmEvent.slm_failure_reason}` : ""}</p> : <p className="slm-muted">SLM chỉ giải thích event đã được chấp nhận; không quyết định cảnh báo.</p>}{status.slm?.last_failure_reason ? <small className="slm-failure-note">Lý do gần nhất: {status.slm.last_failure_reason}</small> : null}</section>
             <section className="panel threshold-panel"><div className="panel-title"><div><span>HITL CONFIG</span><strong>FCW thresholds</strong></div><b>AUDITED</b></div><label><span>Warning <b>{warning.toFixed(2)}</b></span><input aria-label="FCW warning threshold" type="range" min="0.35" max="0.75" step="0.01" value={warning} onChange={(event) => setWarning(Number(event.target.value))} /></label><label><span>Critical <b>{critical.toFixed(2)}</b></span><input aria-label="FCW critical threshold" type="range" min="0.60" max="0.95" step="0.01" value={critical} onChange={(event) => setCritical(Number(event.target.value))} /></label><button className="primary-button" onClick={saveThresholds} disabled={status.running}>Lưu cấu hình</button><small>Dừng phiên trước khi nạp ngưỡng mới. {message}</small></section>
          </aside>
        </div>
      </section>
    </div>
  </main>;
}

export default function RoadWatchApp() {
  const startup = useStartupGate();
  const [token, setToken] = useState(() => localStorage.getItem("roadwatch_token") ?? "");
  const [user, setUser] = useState<User | null>(() => { const value = localStorage.getItem("roadwatch_user"); return value ? JSON.parse(value) as User : null; });
  const [view, setView] = useState<"driver" | "engineer">(() => {
    try {
      const stored = localStorage.getItem("roadwatch_user");
      return stored && (JSON.parse(stored) as User).role === "engineer" ? "engineer" : "driver";
    } catch {
      return "driver";
    }
  });
  const realtime = useRoadWatch(token);
  const status = token ? realtime.status : EMPTY_STATUS;
  const browserAudio = useBrowserAudio(token, status);
  const effectiveView = useMemo(() => user?.role === "driver" ? "driver" : view, [user, view]);
  function loggedIn(nextToken: string, nextUser: User) { localStorage.setItem("roadwatch_token", nextToken); localStorage.setItem("roadwatch_user", JSON.stringify(nextUser)); setToken(nextToken); setUser(nextUser); setView(nextUser.role === "engineer" ? "engineer" : "driver"); }
  function logout() { localStorage.removeItem("roadwatch_token"); localStorage.removeItem("roadwatch_user"); setToken(""); setUser(null); }
  if (!startup.status.ready) return <StartupGate status={startup.status} retry={startup.retry} />;
  if (!token || !user) return <Login onLogin={loggedIn} />;
  return <div className="app-shell">{effectiveView === "engineer" ? <EngineerConsole token={token} status={status} browserAudio={browserAudio} user={user} onViewChange={setView} logout={logout} /> : <DriverHUD token={token} status={status} browserAudio={browserAudio} user={user} onViewChange={setView} logout={logout} />}<footer><span>RoadWatch v0.2 · Evidence lifecycle</span><strong>⚠ Không thay thế việc quan sát và điều khiển của tài xế.</strong></footer></div>;
}
