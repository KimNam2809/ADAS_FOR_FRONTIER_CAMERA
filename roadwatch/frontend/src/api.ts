export type Role = "driver" | "engineer";

export type User = { username: string; role: Role };

export type LoginResult = { token: string; user: User };

export type MediaItem = { name: string; size_mb: number };

export type AlertEvent = {
  id?: number;
  created_at: number;
  event_type: string;
  severity: "critical" | "warning" | "advisory" | "informational";
  message: string;
  confidence: number;
  risk_score: number;
  object_id?: number;
  location?: string;
  audio_action: string;
  evidence: Record<string, unknown>;
};

export type Status = {
  running: boolean;
  mode: string;
  source?: string;
  frame_id: number;
  source_fps: number;
  tracks: Array<Record<string, unknown>>;
  signs: Array<Record<string, unknown>>;
  lane: { quality: number; offset: number };
  events: AlertEvent[];
  degraded_reasons: string[];
  error?: string;
  guardrail: string;
  models?: Record<string, { loaded: boolean; provider: string; error?: string }>;
  audio: { enabled: boolean; provider: string; queue_size: number; error?: string };
  metrics: {
    uptime_seconds: number;
    captured_frames: number;
    processed_frames: number;
    dropped_frames: number;
    processed_fps: number;
    frame_drop_ratio: number;
    alerts_emitted: number;
    alerts_suppressed: number;
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
  start: (token: string, source: string) =>
    request<{ ok: boolean }>("/api/session/start", token, {
      method: "POST",
      body: JSON.stringify({ source }),
    }),
  stop: (token: string) => request<{ ok: boolean }>("/api/session/stop", token, { method: "POST" }),
  config: (token: string) => request<Record<string, unknown>>("/api/config", token),
  patchConfig: (token: string, patch: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/config", token, {
      method: "PATCH",
      body: JSON.stringify({ patch }),
    }),
};

