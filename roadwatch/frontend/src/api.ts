export type Role = "driver" | "engineer";

export type User = { username: string; role: Role };

export type LoginResult = { token: string; user: User };

export type MediaItem = { name: string; size_mb: number };

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
  audio_status?: string;
  lifecycle_status?: string;
  suppression_reason?: string;
  evidence: Record<string, unknown>;
};

export type Status = {
  running: boolean;
  mode: string;
  source?: string;
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
  degraded_reasons: string[];
  error?: string;
  guardrail: string;
  models?: Record<string, { loaded: boolean; provider: string; error?: string }>;
  audio: { enabled: boolean; provider: string; queue_size: number; completed?: number; dropped_stale?: number; error?: string };
  metrics: {
    uptime_seconds: number;
    captured_frames: number;
    processed_frames: number;
    dropped_frames: number;
    scheduled_skipped_frames?: number;
    overload_dropped_frames?: number;
    processed_fps: number;
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
  login: (username: string, password: string) =>
    request<LoginResult>("/api/auth/login", undefined, {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  status: (token: string) => request<Status>("/api/status", token),
  media: (token: string) => request<MediaItem[]>("/api/media", token),
  start: (token: string, source: string, startSeconds = 0, durationSeconds?: number) =>
    request<{ ok: boolean }>("/api/session/start", token, {
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
  config: (token: string) => request<Record<string, unknown>>("/api/config", token),
  patchConfig: (token: string, patch: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/config", token, {
      method: "PATCH",
      body: JSON.stringify({ patch }),
    }),
};
