import { useEffect, useRef } from "react";

/**
 * Mô phỏng khung nhìn perception của RoadWatch.
 *
 * QUAN TRỌNG: đây là mô phỏng giao diện + logic ưu tiên cảnh báo, KHÔNG phải
 * suy luận model thời gian thực. Kịch bản được viết cứng để minh hoạ đúng thứ
 * tự quyết định: detection → temporal evidence → risk → Alert Governor.
 *
 * Muốn hiển thị pipeline thật, truyền `streamUrl="/api/stream.mjpg"`; khi đó
 * component render MJPEG của backend thay cho canvas mô phỏng.
 */

export type Scenario = "day" | "night" | "rain";
export type AudioRoute = "beep_tts" | "tts" | "hud" | "none";
export type Severity = "critical" | "warning" | "advisory";

export type Outcome = "spoken" | "hud" | "suppressed" | "idle";

export interface TrackRow {
  key: string;
  kind: string;
  track: number;
  conf: number;
  hits: number;
  inEgo: boolean;
}

export interface SceneState {
  time: number;
  counts: Record<string, number>;
  tracks: TrackRow[];
  laneQuality: number;
  laneLocked: boolean;
  drivable: number;
  density: number;
  dense: boolean;
  alert: null | { id: string; severity: Severity; route: AudioRoute; vi: string; en: string; track: string };
  /** Ứng viên event đang được Risk Engine cân nhắc ở thời điểm này. */
  candidate: null | { id: string; track: string; severity: Severity };
  /** Kết quả của 5 cổng deterministic, theo đúng thứ tự Alert Governor kiểm tra. */
  gates: { id: GateId; pass: boolean; detail: string }[];
  outcome: Outcome;
  /** Khoá lý do bị chặn — tra trong content.ts để lấy câu VI/EN. */
  reason: string | null;
  /** Sổ ghi của cả vòng lặp 18 giây: đã cân nhắc / chỉ HUD / đã nói. */
  ledger: { considered: number; hud: number; spoken: number; suppressed: number };
}

export type GateId = "temporal" | "corridor" | "lane" | "risk" | "budget";

export const GATE_ORDER: GateId[] = ["temporal", "corridor", "lane", "risk", "budget"];

/** Sổ ghi cố định của kịch bản 18 giây. */
export const LEDGER = { considered: 5, hud: 1, spoken: 2, suppressed: 2 };

interface TraceWindow {
  at: [number, number];
  candidate: null | { id: string; track: string; severity: Severity };
  gates: Record<GateId, [boolean, string]>;
  outcome: Outcome;
  reason: string | null;
}

const OK: [boolean, string] = [true, "pass"];

/**
 * Chuỗi quyết định của vòng lặp. Bốn cửa sổ im lặng đều có lý do khác nhau —
 * đó chính là điều một trang "chỉ khoe detection" không thể cho xem.
 */
const TRACE: TraceWindow[] = [
  {
    at: [0, 2.6],
    candidate: null,
    gates: { temporal: OK, corridor: OK, lane: OK, risk: [true, "0.18"], budget: OK },
    outcome: "idle",
    reason: null,
  },
  {
    at: [2.6, 5.0],
    candidate: { id: "cut_in", track: "motorcycle #12", severity: "warning" },
    gates: {
      temporal: [false, "2/3 frame"],
      corridor: OK,
      lane: [true, "0.78"],
      risk: [true, "0.61"],
      budget: OK,
    },
    outcome: "suppressed",
    reason: "temporal",
  },
  {
    at: [5.0, 7.3],
    candidate: { id: "cut_in", track: "motorcycle #12", severity: "warning" },
    gates: {
      temporal: [true, "6/3 frame"],
      corridor: OK,
      lane: [true, "0.78"],
      risk: [true, "0.74"],
      budget: OK,
    },
    outcome: "spoken",
    reason: null,
  },
  {
    at: [7.3, 7.7],
    candidate: null,
    gates: { temporal: OK, corridor: OK, lane: OK, risk: [true, "0.22"], budget: OK },
    outcome: "idle",
    reason: null,
  },
  {
    at: [7.7, 9.1],
    candidate: { id: "speed_sign", track: "sign #5", severity: "advisory" },
    gates: {
      temporal: [true, "3/3 lần"],
      corridor: OK,
      lane: [true, "0.78"],
      risk: [true, "0.96"],
      budget: [false, "dense · advisory"],
    },
    outcome: "hud",
    reason: "dense",
  },
  {
    at: [9.1, 11.2],
    candidate: { id: "fcw", track: "car #7", severity: "warning" },
    gates: {
      temporal: [true, "9/3 frame"],
      corridor: OK,
      lane: [true, "0.78"],
      risk: [false, "0.41 < 0.55"],
      budget: OK,
    },
    outcome: "suppressed",
    reason: "risk",
  },
  {
    at: [11.2, 14.4],
    candidate: { id: "fcw", track: "car #7", severity: "critical" },
    gates: {
      temporal: [true, "14/3 frame"],
      corridor: OK,
      lane: [true, "0.78"],
      risk: [true, "0.83 ≥ 0.72"],
      budget: OK,
    },
    outcome: "spoken",
    reason: null,
  },
  {
    at: [14.4, 16.4],
    candidate: { id: "fcw", track: "car #7", severity: "warning" },
    gates: {
      temporal: OK,
      corridor: OK,
      lane: [true, "0.78"],
      risk: [true, "0.69"],
      budget: [false, "cooldown 12 s"],
    },
    outcome: "suppressed",
    reason: "cooldown",
  },
  {
    at: [16.4, 18],
    candidate: null,
    gates: { temporal: OK, corridor: OK, lane: OK, risk: [true, "0.15"], budget: OK },
    outcome: "idle",
    reason: null,
  },
];

export const TRACE_MARKS = TRACE
  .filter((w) => w.outcome !== "idle")
  .map((w) => ({ at: w.at, outcome: w.outcome, id: w.candidate?.id ?? "" }));

const LOOP = 18;

interface Actor {
  id: string;
  kind: "car" | "truck" | "motorcycle" | "pedestrian" | "sign";
  track: number;
  from: number;
  to: number;
  lx: (u: number) => number;
  depth: (u: number) => number;
  conf: number;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const ease = (t: number) => t * t * (3 - 2 * t);

const ACTORS: Actor[] = [
  {
    id: "car",
    kind: "car",
    track: 7,
    from: 0,
    to: LOOP,
    lx: () => 0.06,
    // Giữ khoảng cách → phanh gấp từ giây 9,5 → tách ra lại trước khi lặp.
    depth: (t) =>
      t < 9.5
        ? lerp(0.55, 0.34, t / 9.5)
        : t < 14.5
          ? lerp(0.34, 0.14, ease((t - 9.5) / 5))
          : lerp(0.14, 0.55, ease((t - 14.5) / 3.5)),
    conf: 0.91,
  },
  {
    id: "truck",
    kind: "truck",
    track: 3,
    from: 0,
    to: LOOP,
    lx: () => -0.72,
    depth: (t) => 0.58 + 0.09 * Math.cos((t / LOOP) * Math.PI * 2),
    conf: 0.84,
  },
  {
    id: "moto",
    kind: "motorcycle",
    track: 12,
    from: 2.6,
    to: 12.4,
    lx: (u) => lerp(1.02, 0.22, ease(u)),
    depth: (u) => lerp(0.55, 0.26, ease(u)),
    conf: 0.78,
  },
  {
    id: "ped",
    kind: "pedestrian",
    track: 21,
    from: 0.8,
    to: 8.6,
    lx: (u) => lerp(-1.0, -0.66, ease(u)),
    depth: (u) => lerp(0.44, 0.34, u),
    conf: 0.72,
  },
  {
    id: "sign",
    kind: "sign",
    track: 5,
    from: 1.4,
    to: 9.2,
    lx: (u) => lerp(0.86, 1.3, ease(u)),
    depth: (u) => lerp(0.55, 0.2, ease(u)),
    conf: 0.96,
  },
];

const TIMELINE: { at: [number, number]; id: string; severity: Severity; route: AudioRoute; vi: string; en: string; track: string }[] = [
  {
    at: [5.0, 7.3],
    id: "cut_in",
    severity: "warning",
    route: "tts",
    vi: "Xe máy phía trước bên phải, giảm tốc.",
    en: "Motorcycle ahead on the right, slow down.",
    track: "motorcycle #12",
  },
  {
    at: [7.7, 9.1],
    id: "speed_sign",
    severity: "advisory",
    route: "hud",
    vi: "Giới hạn tốc độ 40 km/h.",
    en: "Speed limit 40.",
    track: "sign #5",
  },
  {
    at: [11.2, 14.4],
    id: "fcw",
    severity: "critical",
    route: "beep_tts",
    vi: "Xe phía trước phanh gấp, giảm tốc.",
    en: "Vehicle ahead braking hard, slow down.",
    track: "car #7",
  },
];

const PALETTE: Record<Scenario, {
  skyTop: string; skyBottom: string; road: string; roadEdge: string; haze: string;
  lane: string; drivable: string; fog: number; laneQuality: number; grain: number;
}> = {
  day: {
    skyTop: "#7FA9DA", skyBottom: "#CBDCEC", road: "#3A3F49", roadEdge: "#525863",
    haze: "rgba(203,220,236,0.85)", lane: "#A78BFA", drivable: "rgba(56,189,248,0.16)",
    fog: 0.05, laneQuality: 0.78, grain: 0.02,
  },
  night: {
    skyTop: "#050A16", skyBottom: "#111C33", road: "#15181F", roadEdge: "#242A35",
    haze: "rgba(17,28,51,0.9)", lane: "#8B5CF6", drivable: "rgba(56,189,248,0.10)",
    fog: 0.16, laneQuality: 0.41, grain: 0.06,
  },
  rain: {
    skyTop: "#33414F", skyBottom: "#5C6B78", road: "#2A2E36", roadEdge: "#3B424C",
    haze: "rgba(92,107,120,0.92)", lane: "#7C3AED", drivable: "rgba(56,189,248,0.11)",
    fog: 0.22, laneQuality: 0.29, grain: 0.09,
  },
};

const CLASS_COLOR: Record<string, string> = {
  car: "#38BDF8",
  truck: "#A78BFA",
  motorcycle: "#F59E0B",
  pedestrian: "#22C55E",
  sign: "#E2E8F0",
};

function roundRect(c: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  const rr = Math.min(r, w / 2, h / 2);
  c.beginPath();
  c.moveTo(x + rr, y);
  c.arcTo(x + w, y, x + w, y + h, rr);
  c.arcTo(x + w, y + h, x, y + h, rr);
  c.arcTo(x, y + h, x, y, rr);
  c.arcTo(x, y, x + w, y, rr);
  c.closePath();
}

export default function DashcamScene({
  scenario,
  playing,
  onState,
  streamUrl,
  compact = false,
  startAt = 0,
  seek,
}: {
  scenario: Scenario;
  playing: boolean;
  onState?: (s: SceneState) => void;
  streamUrl?: string;
  compact?: boolean;
  startAt?: number;
  /** Khi đổi giá trị, đồng hồ nhảy tới thời điểm này (giây trong vòng lặp). */
  seek?: number | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const clockRef = useRef(startAt);
  const lastRef = useRef<number | null>(null);
  const emitRef = useRef(0);
  const stateCb = useRef(onState);
  stateCb.current = onState;

  useEffect(() => {
    if (typeof seek === "number") clockRef.current = ((seek % LOOP) + LOOP) % LOOP;
  }, [seek]);

  useEffect(() => {
    if (streamUrl) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) clockRef.current = startAt || 6.2;

    let raf = 0;
    let w = 0;
    let h = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = Math.max(320, rect.width);
      h = Math.max(180, rect.height);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(resize) : null;
    ro?.observe(canvas);

    const draw = (now: number) => {
      raf = requestAnimationFrame(draw);
      const last = lastRef.current ?? now;
      lastRef.current = now;
      if (playing && !reduced) clockRef.current = (clockRef.current + Math.min(0.05, (now - last) / 1000)) % LOOP;
      const t = clockRef.current;
      const p = PALETTE[scenario];
      const horizon = h * (compact ? 0.44 : 0.46);

      /* --- nền trời và mặt đường ------------------------------------ */
      const sky = ctx.createLinearGradient(0, 0, 0, horizon);
      sky.addColorStop(0, p.skyTop);
      sky.addColorStop(1, p.skyBottom);
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, w, horizon);

      // dải công trình/cây mờ sát đường chân trời — cho chiều sâu, không phải vật thể được nhận diện
      ctx.save();
      ctx.globalAlpha = scenario === "night" ? 0.55 : 0.3;
      ctx.fillStyle = scenario === "night" ? "#020509" : "#5C7796";
      for (let i = 0; i < 26; i++) {
        const seed = (i * 41.37) % 1;
        const bw2 = w * (0.02 + seed * 0.05);
        const bx = (i / 26) * w - bw2 * 0.5;
        const bhh = (h - horizon) * (0.03 + ((i * 17.7) % 10) / 10 * 0.13);
        ctx.fillRect(bx, horizon - bhh, bw2, bhh);
      }
      ctx.restore();

      ctx.fillStyle = p.roadEdge;
      ctx.fillRect(0, horizon, w, h - horizon);

      const roadAt = (y: number) => {
        const f = (y - horizon) / (h - horizon);
        return lerp(w * 0.014, w * 0.9, f);
      };
      ctx.beginPath();
      ctx.moveTo(w * 0.5 - roadAt(horizon), horizon);
      ctx.lineTo(w * 0.5 + roadAt(horizon), horizon);
      ctx.lineTo(w * 0.5 + roadAt(h), h);
      ctx.lineTo(w * 0.5 - roadAt(h), h);
      ctx.closePath();
      ctx.fillStyle = p.road;
      ctx.fill();

      /* --- drivable area overlay ------------------------------------ */
      ctx.save();
      ctx.clip();
      ctx.fillStyle = p.drivable;
      ctx.fillRect(0, horizon, w, h - horizon);
      ctx.strokeStyle = "rgba(56,189,248,0.13)";
      ctx.lineWidth = 1;
      for (let y = horizon + 6; y < h; y += 7) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
      ctx.restore();

      /* --- vạch tim đường chuyển động ------------------------------- */
      const scroll = (t * 0.9) % 1;
      ctx.fillStyle = "rgba(255,255,255,0.55)";
      for (let i = 0; i < 9; i++) {
        const f0 = clamp(((i + scroll) / 9) ** 2.4, 0, 1);
        const f1 = clamp(((i + 0.42 + scroll) / 9) ** 2.4, 0, 1);
        const y0 = horizon + (h - horizon) * f0;
        const y1 = horizon + (h - horizon) * f1;
        const half0 = Math.max(0.6, roadAt(y0) * 0.012);
        const half1 = Math.max(0.9, roadAt(y1) * 0.012);
        ctx.beginPath();
        ctx.moveTo(w * 0.5 - half0, y0);
        ctx.lineTo(w * 0.5 + half0, y0);
        ctx.lineTo(w * 0.5 + half1, y1);
        ctx.lineTo(w * 0.5 - half1, y1);
        ctx.closePath();
        ctx.fill();
      }

      /* --- biên ego-lane -------------------------------------------- */
      const laneQuality = p.laneQuality;
      const laneLocked = laneQuality < 0.5;
      ctx.save();
      ctx.lineWidth = compact ? 2 : 2.6;
      ctx.setLineDash(laneLocked ? [7, 7] : []);
      ctx.strokeStyle = p.lane;
      ctx.shadowColor = p.lane;
      ctx.shadowBlur = laneLocked ? 4 : 14;
      ctx.globalAlpha = laneLocked ? 0.45 : 0.95;
      for (const side of [-1, 1]) {
        ctx.beginPath();
        for (let s = 0; s <= 1; s += 0.05) {
          const y = horizon + (h - horizon) * (s * s * 0.98 + 0.02);
          const x = w * 0.5 + side * roadAt(y) * 0.33;
          if (s === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.restore();

      /* --- diễn viên trong cảnh ------------------------------------- */
      const counts: Record<string, number> = {};
      const rows: TrackRow[] = [];
      const boxes: { x: number; y: number; bw: number; bh: number; kind: string; label: string; conf: number }[] = [];

      for (const a of ACTORS) {
        if (t < a.from || t > a.to) continue;
        const u = clamp((t - a.from) / (a.to - a.from), 0, 1);
        const d = a.depth(a.id === "car" || a.id === "truck" ? t : u);
        const f = clamp((1 - d) ** 1.55, 0.012, 1);
        const y = horizon + (h - horizon) * f;
        const x = w * 0.5 + a.lx(u) * roadAt(y) * 0.52;
        const unit = (h - horizon) * f;

        counts[a.kind] = (counts[a.kind] ?? 0) + 1;
        if (a.kind !== "sign") {
          rows.push({
            key: a.id,
            kind: a.kind,
            track: a.track,
            conf: a.conf,
            hits: Math.min(99, Math.round((t - a.from) * 6)),
            inEgo: Math.abs(a.lx(u)) < 0.55,
          });
        }

        ctx.save();
        if (a.kind === "sign") {
          const r = Math.max(5, unit * 0.2);
          ctx.fillStyle = "#64748B";
          ctx.fillRect(x - r * 0.09, y - r * 0.2, r * 0.18, r * 1.9);
          ctx.beginPath();
          ctx.arc(x, y - r * 0.6, r, 0, Math.PI * 2);
          ctx.fillStyle = "#F8FAFC";
          ctx.fill();
          ctx.lineWidth = Math.max(1.4, r * 0.2);
          ctx.strokeStyle = "#DC2626";
          ctx.stroke();
          if (r > 9) {
            ctx.fillStyle = "#0F172A";
            ctx.font = `700 ${Math.round(r * 1.05)}px ui-monospace, monospace`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("40", x, y - r * 0.55);
          }
          boxes.push({ x: x - r * 1.25, y: y - r * 1.9, bw: r * 2.5, bh: r * 2.5, kind: a.kind, label: `speed_sign #${a.track}`, conf: a.conf });
        } else if (a.kind === "pedestrian") {
          const ph = unit * 0.42;
          const pw = ph * 0.3;
          ctx.fillStyle = scenario === "night" ? "#1E293B" : "#334155";
          roundRect(ctx, x - pw / 2, y - ph, pw, ph * 0.72, pw * 0.4);
          ctx.fill();
          ctx.beginPath();
          ctx.arc(x, y - ph - pw * 0.32, pw * 0.42, 0, Math.PI * 2);
          ctx.fill();
          boxes.push({ x: x - pw * 0.95, y: y - ph - pw * 0.85, bw: pw * 1.9, bh: ph + pw * 0.9, kind: a.kind, label: `person #${a.track}`, conf: a.conf });
        } else if (a.kind === "motorcycle") {
          const bh = unit * 0.34;
          const bw = bh * 0.72;
          ctx.fillStyle = "#0F172A";
          roundRect(ctx, x - bw / 2, y - bh, bw, bh, bw * 0.22);
          ctx.fill();
          ctx.fillStyle = scenario === "night" ? "#475569" : "#64748B";
          ctx.beginPath();
          ctx.arc(x, y - bh - bw * 0.22, bw * 0.3, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "#FBBF24";
          ctx.fillRect(x - bw * 0.16, y - bh * 0.22, bw * 0.32, bh * 0.1);
          boxes.push({ x: x - bw * 0.85, y: y - bh - bw * 0.62, bw: bw * 1.7, bh: bh + bw * 0.7, kind: a.kind, label: `motorcycle #${a.track}`, conf: a.conf });
        } else {
          const isTruck = a.kind === "truck";
          const bh = unit * (isTruck ? 0.6 : 0.42);
          const bw = bh * (isTruck ? 1.05 : 1.42);
          ctx.fillStyle = isTruck ? "#475569" : "#1E293B";
          roundRect(ctx, x - bw / 2, y - bh, bw, bh, bw * 0.09);
          ctx.fill();
          ctx.fillStyle = scenario === "night" ? "#0B1220" : "#94A3B8";
          roundRect(ctx, x - bw * 0.38, y - bh * 0.86, bw * 0.76, bh * 0.34, bw * 0.05);
          ctx.fill();
          const braking = a.id === "car" && t > 9.8 && t < 14.6;
          ctx.fillStyle = braking ? "#EF4444" : "#7F1D1D";
          if (braking) { ctx.shadowColor = "#EF4444"; ctx.shadowBlur = bw * 0.35; }
          ctx.fillRect(x - bw * 0.44, y - bh * 0.28, bw * 0.16, bh * 0.11);
          ctx.fillRect(x + bw * 0.28, y - bh * 0.28, bw * 0.16, bh * 0.11);
          boxes.push({ x: x - bw * 0.6, y: y - bh * 1.12, bw: bw * 1.2, bh: bh * 1.16, kind: a.kind, label: `${a.kind} #${a.track}`, conf: a.conf });
        }
        ctx.restore();
      }

      /* --- thời tiết ------------------------------------------------- */
      if (p.fog > 0) {
        const fog = ctx.createLinearGradient(0, horizon - h * 0.1, 0, h);
        fog.addColorStop(0, p.haze);
        fog.addColorStop(0.55, `rgba(0,0,0,0)`);
        ctx.globalAlpha = p.fog * 3.2;
        ctx.fillStyle = fog;
        ctx.fillRect(0, horizon - h * 0.1, w, h - horizon + h * 0.1);
        ctx.globalAlpha = 1;
      }
      if (scenario === "rain") {
        ctx.strokeStyle = "rgba(226,232,240,0.30)";
        ctx.lineWidth = 1;
        for (let i = 0; i < 90; i++) {
          const seed = (i * 97.13) % 1;
          const rx = ((seed + t * (0.14 + seed * 0.1)) % 1) * w;
          const ry = ((seed * 3.7 + t * (0.85 + seed * 0.5)) % 1) * h;
          ctx.beginPath();
          ctx.moveTo(rx, ry);
          ctx.lineTo(rx - 2.5, ry + 13);
          ctx.stroke();
        }
      }

      /* --- bounding box overlay -------------------------------------- */
      for (const b of boxes) {
        if (b.bw < 7) continue;
        const color = CLASS_COLOR[b.kind] ?? "#38BDF8";
        const seg = Math.min(b.bw, b.bh) * 0.3;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.6;
        ctx.globalAlpha = 0.95;
        const corners: [number, number, number, number][] = [
          [b.x, b.y + seg, b.x, b.y], [b.x, b.y, b.x + seg, b.y],
          [b.x + b.bw - seg, b.y, b.x + b.bw, b.y], [b.x + b.bw, b.y, b.x + b.bw, b.y + seg],
          [b.x + b.bw, b.y + b.bh - seg, b.x + b.bw, b.y + b.bh], [b.x + b.bw, b.y + b.bh, b.x + b.bw - seg, b.y + b.bh],
          [b.x + seg, b.y + b.bh, b.x, b.y + b.bh], [b.x, b.y + b.bh, b.x, b.y + b.bh - seg],
        ];
        ctx.beginPath();
        for (const [x0, y0, x1, y1] of corners) { ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); }
        ctx.stroke();
        ctx.globalAlpha = 0.1;
        ctx.fillStyle = color;
        ctx.fillRect(b.x, b.y, b.bw, b.bh);
        ctx.globalAlpha = 1;

        if (b.bw > 46 && !compact) {
          const text = `${b.label}  ${b.conf.toFixed(2)}`;
          ctx.font = "600 10px ui-monospace, SFMono-Regular, monospace";
          const tw = ctx.measureText(text).width + 10;
          ctx.fillStyle = color;
          roundRect(ctx, b.x, Math.max(2, b.y - 15), tw, 13, 3);
          ctx.fill();
          ctx.fillStyle = "#04070F";
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          ctx.fillText(text, b.x + 5, Math.max(2, b.y - 15) + 7);
        }
      }

      /* --- nhiễu cảm biến -------------------------------------------- */
      if (p.grain > 0.03) {
        ctx.globalAlpha = p.grain;
        ctx.fillStyle = "#94A3B8";
        for (let i = 0; i < 220; i++) {
          const gx = ((i * 73.31 + t * 61) % w);
          const gy = ((i * 131.7 + t * 37) % h);
          ctx.fillRect(gx, gy, 1, 1);
        }
        ctx.globalAlpha = 1;
      }

      /* --- HUD chip trong khung -------------------------------------- */
      const active = TIMELINE.find((a) => t >= a.at[0] && t <= a.at[1]) ?? null;
      const road = (counts.car ?? 0) + (counts.truck ?? 0) + (counts.motorcycle ?? 0) + (counts.pedestrian ?? 0);
      const density = clamp(road / 8, 0, 1);

      if (!compact) {
        ctx.font = "600 10px ui-monospace, SFMono-Regular, monospace";
        const chip = (label: string, cx: number, tone: string) => {
          const tw = ctx.measureText(label).width + 16;
          ctx.fillStyle = "rgba(4,7,15,0.66)";
          roundRect(ctx, cx, 10, tw, 20, 5);
          ctx.fill();
          ctx.fillStyle = tone;
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          ctx.fillText(label, cx + 8, 21);
          return tw + 6;
        };
        let cx = 12;
        cx += chip("11.3 FPS", cx, "#7DD3FC");
        cx += chip("P95 149.9 ms", cx, "#C4B5FD");
        chip(laneLocked ? "LDW LOCKED" : "LANE OK", cx, laneLocked ? "#FBBF24" : "#4ADE80");
      }

      /* --- banner cảnh báo ------------------------------------------- */
      if (active && !compact) {
        const tone = active.severity === "critical" ? "#DC2626" : active.severity === "warning" ? "#F59E0B" : "#2563EB";
        const bh2 = 40;
        const by = h - bh2 - 12;
        ctx.fillStyle = "rgba(4,7,15,0.82)";
        roundRect(ctx, 12, by, w - 24, bh2, 8);
        ctx.fill();
        ctx.fillStyle = tone;
        roundRect(ctx, 12, by, 4, bh2, 2);
        ctx.fill();
        const pulse = 0.55 + 0.45 * Math.sin(t * 7);
        ctx.globalAlpha = active.severity === "critical" ? pulse : 1;
        ctx.beginPath();
        ctx.arc(34, by + bh2 / 2, 5, 0, Math.PI * 2);
        ctx.fillStyle = tone;
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.fillStyle = tone;
        ctx.font = "700 9px ui-monospace, SFMono-Regular, monospace";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(active.severity.toUpperCase(), 48, by + 13);
        ctx.fillStyle = "#F8FAFC";
        ctx.font = "600 13px system-ui, sans-serif";
        ctx.fillText(active.vi, 48, by + 28);
      }

      /* --- phát state ra ngoài --------------------------------------- */
      if (now - emitRef.current > 130 && stateCb.current) {
        emitRef.current = now;
        const win = TRACE.find((x) => t >= x.at[0] && t < x.at[1]) ?? TRACE[0];
        // Lane kém (đêm/mưa) khoá cổng lane và làm đổi kết quả — đúng luật thật.
        const laneGate: [boolean, string] = laneLocked
          ? [false, `quality ${laneQuality.toFixed(2)} < 0.50`]
          : [true, `quality ${laneQuality.toFixed(2)}`];
        const gates = GATE_ORDER.map((id) => {
          const [pass, detail] = id === "lane" ? laneGate : win.gates[id];
          return { id, pass, detail };
        });
        stateCb.current({
          time: t,
          counts,
          tracks: rows,
          laneQuality,
          laneLocked,
          drivable: scenario === "day" ? 0.87 : scenario === "night" ? 0.64 : 0.58,
          density,
          dense: road >= 4,
          alert: active,
          candidate: win.candidate,
          gates,
          outcome: win.outcome,
          reason: win.reason,
          ledger: LEDGER,
        });
      }
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro?.disconnect();
      lastRef.current = null;
    };
  }, [scenario, playing, streamUrl, compact, startAt]);

  if (streamUrl) {
    return <img className="rw-scene-canvas" src={streamUrl} alt="RoadWatch perception stream" />;
  }
  return <canvas ref={canvasRef} className="rw-scene-canvas" role="img" aria-label="RoadWatch perception view simulation" />;
}
