export type Role = "driver" | "engineer";

export type User = { username: string; role: Role };

export type LoginResult = { token: string; user: User };

export type StartupStatus = {
  deployment_profile: "cloud_demo" | "edge_local";
  deferred: boolean;
  ready: boolean;
  state: "starting" | "ready" | "error";
  stage: "container" | "assets" | "perception" | "tts" | "ready" | "error";
  message: string;
  started_at: number;
  ready_at?: number | null;
  elapsed_seconds: number;
  retry_after_seconds: number;
  error?: string | null;
};

export type MediaItem = {
  name: string;
  source?: string;
  relative_source?: string;
  source_kind?: "library" | "upload";
  condition?: string;
  size_mb: number;
  duration_seconds?: number;
  cached_result?: boolean;
};

export type AlertEvent = {
  id?: number;
  event_id?: string;
  frame_id?: number;
  source_time?: number;
  created_at: number;
  expires_at?: number;
  event_type: string;
  severity: "critical" | "warning" | "advisory" | "informational";
  message: string;
  display_message?: string;
  spoken_message?: string;
  confidence: number;
  risk_score: number;
  object_id?: number;
  location?: string;
  audio_action: string;
  display_scope?: "hazard_banner" | "hud_context";
  audio_route?: "normal" | "tts" | "beep_tts" | "context_beep" | "hud_only" | "suppressed";
  context_mode?: "normal" | "dense";
  audio_status?: string;
  audio_claim_id?: string;
  audio_play_count?: number;
  canonical_audio_key?: string;
  lifecycle_status?: string;
  suppression_reason?: string;
  slm_explanation?: string | null;
  slm_status?: "pending" | "ready" | "fallback" | "disabled" | "error" | string;
  slm_latency_ms?: number | null;
  slm_failure_reason?: string | null;
  evidence: Record<string, unknown>;
};

export type Status = {
  running: boolean;
  mode: string;
  stage?: string;
  deployment_profile?: "cloud_demo" | "edge_local";
  status_transport?: string;
  cloud_fast_preview?: boolean;
  cloud_full_perception?: boolean;
  source?: string;
  source_key?: string;
  frame_id: number;
  source_fps: number;
  source_time: number;
  duration_seconds: number;
  seekable: boolean;
  playback: "loading" | "playing" | "paused" | "stopped";
  session_id?: string;
  tracks: Array<Record<string, unknown>>;
  signs: Array<Record<string, unknown>>;
  lane: { quality: number; offset: number };
  events: AlertEvent[];
  active_events?: AlertEvent[];
  traffic_context: {
    mode: "normal" | "dense";
    risk_state: "calm" | "threat";
    density_score: number;
    confirmed_road_users: number;
    two_wheeler_count: number;
    road_occupancy: number;
    low_motion_ratio: number;
    audio_policy: "normal" | "dense_selective";
    policy_mode?: "off" | "shadow" | "enforce";
    attention_due?: boolean;
    transition?: string | null;
    fallback?: boolean;
    error?: string | null;
  };
  degraded_reasons: string[];
  error?: string;
  guardrail: string;
  models?: Record<string, { loaded: boolean; provider: string; error?: string }>;
  audio: {
    enabled: boolean;
    provider: string;
    queue_size: number;
    output_owner?: "server" | "browser" | "none";
    server_playback?: boolean;
    browser_playback?: boolean;
    playback_mode?: "single_owner" | "legacy";
    voice_model?: string;
    voice_model_sha256?: string | null;
    voice_config_sha256?: string | null;
    cache_namespace?: string;
    completed?: number;
    dropped_stale?: number;
    error?: string;
  };
  tts?: {
    available: boolean;
    provider: string;
    voice_name?: string;
    voice_model?: string;
    voice_model_sha256?: string | null;
    voice_config_sha256?: string | null;
    sample_rate?: number;
    num_speakers?: number;
    cache_namespace?: string;
    mode: "dedicated_cloud_service" | "local";
    language: string;
    requests: number;
    failed: number;
    last_latency_ms: number;
    error?: string;
  };
  slm: {
    enabled: boolean;
    state: "disabled" | "standby" | "warming" | "ready" | "error" | "closed" | string;
    model: string;
    provider: string;
    queue_size: number;
    max_queue_age_seconds?: number;
    load_ms?: number | null;
    generated: number;
    failed: number;
    last_latency_ms?: number | null;
    last_result_status?: string | null;
    last_event_id?: string | null;
    last_failure_reason?: string | null;
    last_quality_score?: number | null;
    last_output_tokens?: number | null;
    last_result_at?: number | null;
    error?: string | null;
  };
  optional_perception?: {
    sign_age_seconds?: number;
    lane_age_seconds?: number;
    submitted?: number;
    replaced?: number;
  };
  metrics: {
    uptime_seconds: number;
    warmup_ms?: number;
    captured_frames: number;
    processed_frames: number;
    dropped_frames: number;
    scheduled_skipped_frames?: number;
    overload_dropped_frames?: number;
    processed_fps: number;
    display_fps?: number;
    display_frames?: number;
    display_dropped_frames?: number;
    frame_drop_ratio: number;
    sampling_skip_ratio?: number;
    overload_drop_ratio?: number;
    alerts_emitted: number;
    alerts_suppressed: number;
    audio_completed?: number;
    audio_dropped_stale?: number;
    audio_stale_event_rate?: number;
    events_by_type?: Record<string, number>;
    suppression_reasons?: Record<string, number>;
    latencies: Record<string, { mean_ms: number; p50_ms: number; p95_ms: number; samples: number }>;
  };
};

async function request<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Không thể kết nối edge service" }));
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  startup: () => request<StartupStatus>("/api/startup"),
  login: (username: string, password: string) =>
    request<LoginResult>("/api/auth/login", undefined, {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  status: (token: string) => request<Status>("/api/status", token),
  media: (token: string) => request<MediaItem[]>("/api/media", token),
  library: (token: string) => request<{ schema_version: string; items: MediaItem[] }>("/api/library", token),
  uploadVideo: async (token: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    const response = await fetch("/api/uploads", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "Không thể tải video" }));
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    return response.json() as Promise<MediaItem & { run_id: string; sha256: string }>;
  },
  start: (token: string, source: string, startSeconds = 0, durationSeconds?: number) =>
    request<{ ok: boolean; run_id?: string; session_id?: string }>("/api/session/start", token, {
      method: "POST",
      body: JSON.stringify({ source, start_seconds: startSeconds, duration_seconds: durationSeconds }),
    }),
  stop: (token: string) => request<{ ok: boolean }>("/api/session/stop", token, { method: "POST" }),
  pause: (token: string) => request<{ ok: boolean }>("/api/session/pause", token, { method: "POST" }),
  resume: (token: string) => request<{ ok: boolean }>("/api/session/resume", token, { method: "POST" }),
  seek: (token: string, seconds: number, relative = false) =>
    request<{ ok: boolean; target_seconds: number }>("/api/session/seek", token, {
      method: "POST",
      body: JSON.stringify({ seconds, relative }),
    }),
  ttsAudio: async (token: string, eventId: string) => {
    const response = await fetch(`/api/tts/events/${encodeURIComponent(eventId)}.wav`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "Piper tiếng Việt chưa sẵn sàng" }));
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    return {
      wav: await response.arrayBuffer(),
      provider: response.headers.get("X-RoadWatch-TTS-Provider") ?? "piper/vi_VN-vais1000-medium",
      voiceName: (response.headers.get("X-RoadWatch-TTS-Voice") ?? "Truc-Ly") === "Truc-Ly"
        ? "Trúc Ly"
        : (response.headers.get("X-RoadWatch-TTS-Voice") ?? "Trúc Ly"),
      cache: response.headers.get("X-RoadWatch-TTS-Cache") ?? "unknown",
      synthesisMs: Number(response.headers.get("X-RoadWatch-TTS-Ms") ?? "0"),
      modelSha256: response.headers.get("X-RoadWatch-TTS-Model") ?? "unknown",
    };
  },
  config: (token: string) => request<Record<string, unknown>>("/api/config", token),
  patchConfig: (token: string, patch: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/config", token, {
      method: "PATCH",
      body: JSON.stringify({ patch }),
    }),
};
