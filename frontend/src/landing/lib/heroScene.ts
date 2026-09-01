/**
 * Hero scene — state, chiếu từ trên xuống, và draw().
 *
 * Camera nhìn thẳng từ trên xuống (bird's-eye), chiếu trực giao: không có
 * chân trời, không hội tụ. Xe chủ đứng yên ở giữa dưới khung, thế giới trôi
 * xuống phía người xem.
 *
 * Trục ngang và trục sâu dùng hai tỉ lệ khác nhau (nén khoảng cách) — đúng
 * quy ước của màn hình ADAS trên xe: bề ngang giữ đúng tỉ lệ để đọc vị trí
 * trong làn, còn chiều sâu nén lại để nhét được ~50m vào khung.
 *
 * draw() CHỈ đọc state và vẽ. Không sửa state, không đụng GSAP.
 * Không vẽ text trong canvas — mọi chữ do lớp DOM ở AdasHero đảm nhiệm.
 */

export const LOOP = 30; // giây; tám cảnh, mỗi cảnh đủ lâu để đọc hết câu
const LANE_W = 3.5; // bề rộng làn (mét)
const VIEW_DEPTH = 50; // mét nhìn thấy phía trước
/**
 * Hằng số nén chiều sâu. Ánh xạ z → màn hình theo log: đạo hàm bằng 1 tại
 * z = 0 nên vùng quanh xe chủ giữ đúng tỉ lệ thật (xe dài gấp ~2.4 lần bề
 * ngang), càng xa càng nén để nhét đủ VIEW_DEPTH vào khung.
 */
const DEPTH_K = 12;
const SHOULDER = 2.6; // lề đường mỗi bên (mét)
/**
 * Hướng đèn dùng chung cho cả cảnh: chếch trên-trái. Mọi highlight, mặt khuất
 * và bóng đổ đều suy ra từ đây — chính sự nhất quán này tạo cảm giác khối,
 * chứ không phải bản thân từng gradient.
 */
const LIGHT = { shadowX: 0.30, shadowY: 0.075, blur: 0.75 };

const DASH_PERIOD = 9; // chu kỳ vạch đứt (mét)
const DASH_LEN = 3;
// 68 × DASH_PERIOD và 12 × BUILD_SPAN → vạch kẻ lẫn dãy nhà đều khớp khi lặp.
// Phải là bội của lcm(9, 51) = 153. Với LOOP = 30 s, tốc độ biểu kiến
// ≈ 20.4 m/s (~73 km/h).
export const WORLD_SPAN = 612;

/** Chu kỳ lặp của dãy nhà. WORLD_SPAN / 6 nên khớp đúng một vòng cuộn. */
const BUILD_SPAN = 51;

/**
 * Hình khối ven đường. Mỗi biến thể là một dấu chân khác nhau; chính sự đa
 * dạng của dấu chân — chứ không phải thêm màu — tạo cảm giác một bối cảnh
 * dựng hình, giống các khối hình học trong hero của Mobileye.
 */
type Shape = "box" | "step" | "cyl" | "arc" | "wedge" | "ridge" | "plate";

type Block = {
  x: number;
  z: number;
  w: number;
  d: number;
  tone: 0 | 1 | 2;
  shape: Shape;
  /** hệ số chiều cao: quyết định độ nhấc của mặt mái và độ đổ của bóng */
  hh: number;
  /** hướng quay của các biến thể bất đối xứng (arc, wedge) */
  flip: boolean;
};

/**
 * Dãy nhà hai bên đường, sinh một lần lúc nạp module bằng LCG có hạt cố định
 * — bố cục phải giống hệt nhau giữa các frame và giữa các lần tải trang.
 */
const BLOCKS: Block[] = (() => {
  let seed = 20260830;
  const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
  const pick = <T,>(xs: readonly T[]) => xs[Math.floor(rnd() * xs.length)];

  // Khung nhìn chỉ thấy khoảng ±11.5m ngang, mà đường + lề đã chiếm ~5.2m mỗi
  // bên. Vậy dải thực sự nhìn thấy chỉ rộng chừng 6m — mọi hình muốn đọc ra
  // được phải nằm gọn trong dải đó, nên hàng sát đường mới là nơi đặt biến
  // thể, còn hàng lùi chỉ còn là gợi ý đường chân trời.
  const NEAR: readonly Shape[] = [
    "box", "step", "cyl", "arc", "wedge", "ridge", "box", "step", "plate", "cyl",
  ];
  const FAR: readonly Shape[] = ["box", "step", "box", "ridge"];

  const out: Block[] = [];
  for (const side of [-1, 1] as const) {
    let z = rnd() * 5;
    while (z < BUILD_SPAN - 5) {
      const shape = pick(NEAR);
      const compact = shape === "cyl" || shape === "arc" || shape === "wedge";
      const deep = compact ? 3 + rnd() * 2.6 : 3.2 + rnd() * 3.2;
      // hình gọn cần hộp bao gần vuông, nếu không sẽ kéo dài thành vệt
      const front = compact ? deep * (0.8 + rnd() * 0.5) : 2.4 + rnd() * 3.4;
      const inset = 5.6 + rnd() * 1.5;
      out.push({
        x: side * (inset + deep / 2),
        z: z + front / 2,
        w: deep,
        d: front,
        tone: pick([0, 1, 2] as const),
        shape,
        hh: shape === "plate" ? 0.12 + rnd() * 0.12
          : shape === "ridge" ? 0.45 + rnd() * 0.3
          : 0.5 + rnd() * 1.4,
        flip: side < 0,
      });
      // dãy lùi phía sau: chỉ ló một phần ở mép khung, tạo lớp chiều sâu
      if (rnd() > 0.45) {
        out.push({
          x: side * (inset + deep + 1.4 + 4),
          z: z + front / 2 + (rnd() - 0.5) * 3,
          w: 8,
          d: 3 + rnd() * 5,
          tone: pick([0, 1] as const),
          shape: pick(FAR),
          hh: 1.1 + rnd() * 0.9,
          flip: side < 0,
        });
      }
      // phần lớn khối đứng sát nhau; thi thoảng chừa một khoảng trống
      z += front + (rnd() > 0.7 ? 2.2 + rnd() * 3.5 : 0.5 + rnd() * 1.2);
    }
  }
  return out;
})();

export type Tone = 0 | 1 | 2; // 0 = xanh (đã bám) · 1, 2 = đỏ (nguy hiểm)

export type Actor = {
  id: string;
  kind: "car" | "ped" | "cone" | "bike";
  x: number; // mét, lệch ngang so với tâm làn chủ
  z: number; // đơn vị không gian nội bộ; UI không hiển thị như phép đo mét
  w: number; // bề ngang (mét)
  len: number; // chiều dài theo hướng đi (mét)
  alpha: number;
  box: number; // 0..1 tiến độ vẽ khung
  tone: Tone;
  label: string;
  labelAlpha: number;
};

/**
 * Cảnh báo bằng giọng nói. Text nằm ở lớp DOM (AdasHero); ở đây chỉ giữ chỉ số
 * câu đang phát, mức hiện/ẩn và tone màu. Biên độ sóng âm suy ra từ
 * `worldOffset` — đã là một giá trị GSAP tween liên tục, nên không cần thêm
 * tween lặp vô hạn làm hỏng độ dài 14s của timeline.
 */
export type Voice = { alpha: number; index: number; status: number; tone: Tone };

export type HeroState = {
  worldOffset: number;
  fade: number;
  trajectory: { curve: number; length: number; tone: Tone; alpha: number };
  /** Xe chủ. `kind` đổi giữa các cảnh: kịch bản xe con và xe tải xen kẽ. */
  ego: { x: number; kind: 0 | 1; swerve: number };
  /** Màn mưa/sương/loá phủ lên toàn cảnh; 0 = trời quang. */
  /** kind 0 = mưa (có vệt), 1 = sương mù (chỉ màn đục). */
  veil: { alpha: number; kind: 0 | 1 };
  /** Vùng camera trước không nhìn tới — vẽ gạch chéo hai bên xe chủ. */
  blind: { alpha: number };
  boxes: Actor[];
  hud: { riskAlpha: number };
  voice: Voice;
  captions: Array<{ alpha: number }>;
};

export function createState(): HeroState {
  return {
    worldOffset: 0,
    fade: 1,
    trajectory: { curve: 0, length: 1, tone: 0, alpha: 1 },
    ego: { x: 0, kind: 0, swerve: 0 },
    veil: { alpha: 0, kind: 0 },
    blind: { alpha: 0 },
    boxes: [
      { id: "lead", kind: "car", x: 0, z: 48, w: 1.9, len: 4.5, alpha: 0, box: 0, tone: 0, label: "ô tô phía trước", labelAlpha: 0 },
      { id: "cutin", kind: "car", x: 3.5, z: 26, w: 1.9, len: 4.5, alpha: 0, box: 0, tone: 0, label: "ô tô bên phải", labelAlpha: 0 },
      { id: "ped", kind: "ped", x: 6.6, z: 22, w: 0.62, len: 0.72, alpha: 0, box: 0, tone: 0, label: "người đi bộ", labelAlpha: 0 },
      { id: "cone", kind: "cone", x: 6.2, z: 16, w: 0.68, len: 0.92, alpha: 0, box: 0, tone: 0, label: "cọc tiêu · lề phải", labelAlpha: 0 },
      // z âm = phía sau xe chủ. Đây là chỗ camera trước không thấy.
      { id: "bike", kind: "bike", x: 3.4, z: 2.2, w: 0.8, len: 1.9, alpha: 0, box: 0, tone: 0, label: "xe máy bên phải", labelAlpha: 0 },
      { id: "slow", kind: "car", x: 0, z: 44, w: 1.9, len: 4.5, alpha: 0, box: 0, tone: 0, label: "ô tô phía trước", labelAlpha: 0 },
    ],
    hud: { riskAlpha: 0 },
    voice: { alpha: 0, index: 0, status: 0, tone: 0 },
    captions: Array.from({ length: 8 }, (_, index) => ({ alpha: index === 0 ? 1 : 0 })),
  };
}

/* ------------------------------------------------------------ hình học --- */

export type View = {
  cx: number; // tâm đường trên màn
  baseY: number; // đuôi xe chủ
  lat: number; // px trên mét (trục ngang, và trục sâu ở cự ly gần)
  roadW: number; // bề rộng phần xe chạy (px)
  pavedW: number; // kể cả lề đường (px)
};

export function makeView(W: number, H: number): View {
  const baseY = H * 0.88;
  // Chọn lat sao cho đúng VIEW_DEPTH mét lấp kín từ xe chủ tới mép trên.
  const span = DEPTH_K * Math.log(1 + VIEW_DEPTH / DEPTH_K);
  // Trần thứ hai giữ cho khung luôn hiện được >= 23m bề ngang: đường và lề đã
  // chiếm 15.7m, phần còn lại là chỗ cho nhà hai bên. Thiếu trần này thì ở
  // khung hẹp nhà bị đẩy hết ra ngoài mép.
  const lat = Math.min(baseY / span, W / 23);
  return {
    cx: W / 2,
    baseY,
    lat,
    roadW: lat * LANE_W * 3,
    pavedW: lat * (LANE_W * 3 + SHOULDER * 2),
  };
}

/**
 * Khoảng cách thế giới (m) → số pixel tính từ xe chủ lên phía trên.
 * Phía sau xe chủ (z < 0) dùng tuyến tính; hai nhánh khớp cả giá trị lẫn đạo
 * hàm tại z = 0 nên không có nếp gãy.
 */
export function depthPx(z: number, v: View): number {
  if (z < 0) return v.lat * z;
  return v.lat * DEPTH_K * Math.log(1 + z / DEPTH_K);
}

/** Hộp bao vật thể trong toạ độ màn hình — dùng chung cho khung HUD và nhãn DOM. */
/**
 * Hộp bao vật thể trong toạ độ màn hình.
 *
 * Chiếu trực giao nên KÍCH THƯỚC vật thể không đổi theo cự ly — chỉ VỊ TRÍ
 * mới đi qua phép nén depthPx(). Nếu lấy chiều dài bằng hiệu depthPx ở hai
 * đầu thì xe càng xa càng ngắn lại, thành ra có phối cảnh giả ở một hình
 * đáng lẽ không có phối cảnh.
 */
export function footprint(a: Actor, W: number, H: number) {
  const v = makeView(W, H);
  const halfW = (a.w / 2) * v.lat;
  const len = a.len * v.lat;
  const rearY = v.baseY - depthPx(a.z, v);
  return { x: v.cx + a.x * v.lat - halfW, y: rearY - len, w: halfW * 2, h: len };
}

/* ---------------------------------------------------------------- màu ---- */

export type Palette = Record<string, [number, number, number]>;

const TOKENS = [
  "--signal", "--state-alert",
  "--object-marker",
  "--surface-0", "--surface-1", "--surface-2",
  "--surface-3", "--surface-4", "--surface-5", "--road",
  "--car-body", "--car-roof", "--car-edge", "--car-glass",
  "--car-shade", "--car-spec", "--shadow-cast",
  "--text-hi", "--text-mid", "--text-low",
];

/**
 * Canvas 2D trên một số runtime vẫn từ chối trực tiếp `oklch()`, dù CSS của
 * trang hỗ trợ. Chuyển OKLCH sang sRGB tại đây để hero không rơi về màu đen.
 */
function parseOklch(value: string): [number, number, number] | null {
  const match = value.match(/^oklch\(\s*([\d.]+)%?\s+([\d.]+)\s+([\d.]+)/i);
  if (!match) return null;
  let l = Number(match[1]);
  if (value.slice(0, value.indexOf(")") + 1).includes("%")) l /= 100;
  const c = Number(match[2]);
  const h = Number(match[3]) * Math.PI / 180;
  const a = c * Math.cos(h);
  const b = c * Math.sin(h);

  const lRoot = l + 0.3963377774 * a + 0.2158037573 * b;
  const mRoot = l - 0.1055613458 * a - 0.0638541728 * b;
  const sRoot = l - 0.0894841775 * a - 1.291485548 * b;
  const ll = lRoot ** 3;
  const mm = mRoot ** 3;
  const ss = sRoot ** 3;
  const linear = [
    4.0767416621 * ll - 3.3077115913 * mm + 0.2309699292 * ss,
    -1.2684380046 * ll + 2.6097574011 * mm - 0.3413193965 * ss,
    -0.0041960863 * ll - 0.7034186147 * mm + 1.707614701 * ss,
  ];
  const channel = (component: number) => {
    const srgb = component <= 0.0031308
      ? 12.92 * component
      : 1.055 * component ** (1 / 2.4) - 0.055;
    return Math.round(Math.max(0, Math.min(1, srgb)) * 255);
  };
  return linear.map(channel) as [number, number, number];
}

/** Đọc token màu từ CSS variable rồi quy về RGB để pha alpha tuỳ ý. */
export function readPalette(el: Element): Palette {
  const cs = getComputedStyle(el);
  const probe = document.createElement("canvas");
  probe.width = probe.height = 1;
  const pctx = probe.getContext("2d", { willReadFrequently: true })!;
  const out: Palette = {};
  for (const token of TOKENS) {
    const value = cs.getPropertyValue(token).trim();
    const converted = parseOklch(value);
    if (converted) {
      out[token] = converted;
      continue;
    }
    pctx.clearRect(0, 0, 1, 1);
    pctx.fillStyle = "#000";
    pctx.fillStyle = value;
    pctx.fillRect(0, 0, 1, 1);
    const [r, g, b] = pctx.getImageData(0, 0, 1, 1).data;
    out[token] = [r, g, b];
  }
  return out;
}

const rgba = (c: [number, number, number], a: number) =>
  `rgba(${c[0]},${c[1]},${c[2]},${a})`;

function toneColor(p: Palette, tone: Tone): [number, number, number] {
  return tone === 0 ? p["--signal"] : p["--state-alert"];
}

/* ------------------------------------------------------------ gradient --- */

type GradCache = {
  w: number; h: number;
  road: CanvasGradient; // mờ dần về phía xa (mép trên)
  shoulder: CanvasGradient;
  dash: CanvasGradient;
  blockA: CanvasGradient;
  blockB: CanvasGradient;
  blockC: CanvasGradient;
  blockEdge: CanvasGradient; // nét viền mái, mờ dần theo chiều sâu
  blockWall: CanvasGradient; // chân khối nhà, tối hơn mặt mái
  sheen: CanvasGradient;     // ánh sáng chéo trên mặt đường
  cloud: CanvasGradient;     // vệt mây mềm ở mép khung
  haze: CanvasGradient; // sương mờ mép trên
  tail: CanvasGradient; // tan vào màu trang ở mép dưới
  shadow: CanvasGradient; // radial đơn vị, transform cho từng xe
};
let gradCache: GradCache | null = null;

export function invalidateGradients(): void {
  gradCache = null;
}

function ensureGradients(
  ctx: CanvasRenderingContext2D,
  W: number,
  H: number,
  p: Palette,
): GradCache {
  if (gradCache && gradCache.w === W && gradCache.h === H) return gradCache;
  const v = makeView(W, H);

  const road = ctx.createLinearGradient(0, v.baseY, 0, 0);
  road.addColorStop(0, rgba(p["--road"], 1));
  road.addColorStop(0.62, rgba(p["--road"], 0.85));
  road.addColorStop(1, rgba(p["--road"], 0));

  const shoulder = ctx.createLinearGradient(0, v.baseY, 0, 0);
  shoulder.addColorStop(0, rgba(p["--surface-2"], 1));
  shoulder.addColorStop(0.62, rgba(p["--surface-2"], 0.8));
  shoulder.addColorStop(1, rgba(p["--surface-2"], 0));

  const dash = ctx.createLinearGradient(0, v.baseY, 0, 0);
  dash.addColorStop(0, rgba(p["--surface-0"], 1));
  dash.addColorStop(0.6, rgba(p["--surface-0"], 0.9));
  dash.addColorStop(1, rgba(p["--surface-0"], 0));

  const blockA = ctx.createLinearGradient(0, v.baseY, 0, 0);
  blockA.addColorStop(0, rgba(p["--surface-2"], 0.62));
  blockA.addColorStop(0.6, rgba(p["--surface-2"], 0.46));
  blockA.addColorStop(1, rgba(p["--surface-2"], 0));

  const blockB = ctx.createLinearGradient(0, v.baseY, 0, 0);
  blockB.addColorStop(0, rgba(p["--surface-3"], 0.44));
  blockB.addColorStop(0.6, rgba(p["--surface-3"], 0.32));
  blockB.addColorStop(1, rgba(p["--surface-3"], 0));

  const blockC = ctx.createLinearGradient(0, v.baseY, 0, 0);
  blockC.addColorStop(0, rgba(p["--surface-1"], 0.95));
  blockC.addColorStop(0.6, rgba(p["--surface-1"], 0.7));
  blockC.addColorStop(1, rgba(p["--surface-1"], 0));

  const blockEdge = ctx.createLinearGradient(0, v.baseY, 0, 0);
  blockEdge.addColorStop(0, rgba(p["--surface-4"], 0.34));
  blockEdge.addColorStop(0.55, rgba(p["--surface-4"], 0.18));
  blockEdge.addColorStop(1, rgba(p["--surface-4"], 0));

  const blockWall = ctx.createLinearGradient(0, v.baseY, 0, 0);
  blockWall.addColorStop(0, rgba(p["--surface-3"], 0.88));
  blockWall.addColorStop(0.6, rgba(p["--surface-3"], 0.62));
  blockWall.addColorStop(1, rgba(p["--surface-3"], 0));

  // ánh sáng chéo: mặt đường sáng hơn phía đèn, tối dần sang phải
  const sheen = ctx.createLinearGradient(v.cx - v.pavedW / 2, 0, v.cx + v.pavedW / 2, 0);
  sheen.addColorStop(0, rgba(p["--car-spec"], 0.5));
  sheen.addColorStop(0.45, rgba(p["--car-spec"], 0.12));
  sheen.addColorStop(1, rgba(p["--shadow-cast"], 0.1));

  const cloud = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
  cloud.addColorStop(0, rgba(p["--surface-0"], 0.9));
  cloud.addColorStop(0.55, rgba(p["--surface-0"], 0.42));
  cloud.addColorStop(1, rgba(p["--surface-0"], 0));

  const haze = ctx.createLinearGradient(0, 0, 0, H * 0.22);
  haze.addColorStop(0, rgba(p["--surface-0"], 0.9));
  haze.addColorStop(1, rgba(p["--surface-0"], 0));

  const tail = ctx.createLinearGradient(0, H * 0.93, 0, H);
  tail.addColorStop(0, rgba(p["--surface-0"], 0));
  tail.addColorStop(1, rgba(p["--surface-0"], 1));

  const shadow = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
  shadow.addColorStop(0, rgba(p["--surface-3"], 0.5));
  shadow.addColorStop(1, rgba(p["--surface-3"], 0));

  gradCache = { w: W, h: H, road, shoulder, dash, blockA, blockB, blockC, blockEdge, blockWall, sheen, cloud, haze, tail, shadow };
  return gradCache;
}

/* ----------------------------------------------------------------- vẽ ---- */

export function draw(
  ctx: CanvasRenderingContext2D,
  state: HeroState,
  W: number,
  H: number,
  p: Palette,
): void {
  const v = makeView(W, H);
  const g = ensureGradients(ctx, W, H, p);
  const halfRoad = v.roadW / 2;

  // Nền tô đục và KHÔNG chịu state.fade, nếu không crossfade sẽ mờ về màu
  // nền canvas thay vì về màu trang.
  ctx.fillStyle = rgba(p["--surface-0"], 1);
  ctx.fillRect(0, 0, W, H);

  ctx.save();
  ctx.globalAlpha = state.fade;

  /* --- 1. Nhà dân hai bên, cuộn cùng thế giới ----------------------------- */
  drawBlocks(ctx, state, v, g, p);

  /* --- 2. Lề đường rồi mặt đường: dải dọc, mờ dần về phía xa -------------- */
  ctx.fillStyle = g.shoulder;
  ctx.fillRect(v.cx - v.pavedW / 2, 0, v.pavedW, H);
  ctx.fillStyle = g.road;
  ctx.fillRect(v.cx - halfRoad, 0, v.roadW, H);

  // ánh sáng chéo: phần xe chạy hứng sáng phía đèn
  ctx.fillStyle = g.sheen;
  ctx.fillRect(v.cx - v.pavedW / 2, 0, v.pavedW, H);

  /* --- 3. Vạch làn đứt, cuộn xuống theo worldOffset ----------------------- */
  const phase = state.worldOffset % DASH_PERIOD;
  const dashW = Math.max(1.5, 0.16 * v.lat);
  ctx.fillStyle = g.dash;
  ctx.beginPath();
  for (const lx of [-LANE_W / 2, LANE_W / 2]) {
    const px = v.cx + lx * v.lat - dashW / 2;
    for (let i = 0; i < 16; i++) {
      const z0 = i * DASH_PERIOD - phase;
      const yTop = v.baseY - depthPx(z0 + DASH_LEN, v);
      const yBot = v.baseY - depthPx(z0, v);
      if (yTop > H || yBot < -20) continue;
      ctx.rect(px, yTop, dashW, yBot - yTop);
    }
  }
  ctx.fill();

  // mép đường
  ctx.fillStyle = rgba(p["--surface-3"], 0.85);
  const edgeW = Math.max(1.5, 0.1 * v.lat);
  ctx.fillRect(v.cx - halfRoad, 0, edgeW, H);
  ctx.fillRect(v.cx + halfRoad - edgeW, 0, edgeW, H);

  /* --- 4. Trajectory: dải từ xe chủ chạy lên ------------------------------ */
  drawTrajectory(ctx, state, v, p);

  /* --- 5. Vật thể xung quanh (xa vẽ trước) -------------------------------- */
  const sorted = [...state.boxes].sort((a, b) => b.z - a.z);
  for (const actor of sorted) {
    if (actor.alpha <= 0.001) continue;
    drawActor(ctx, actor, W, H, v, p, g);
  }

  /* --- 6. Xe chủ ---------------------------------------------------------- */
  const egoX = v.cx + (state.ego.x + state.ego.swerve) * v.lat;
  if (state.ego.kind === 1) {
    drawTruckTop(ctx, egoX, v.baseY, (2.5 / 2) * v.lat, 9.5 * v.lat, p, g);
  } else {
    drawCarTop(ctx, egoX, v.baseY, (1.9 / 2) * v.lat, 4.6 * v.lat, p, "dark", g);
  }

  /* --- 6b. Vùng camera trước không nhìn tới ------------------------------- */
  if (state.blind.alpha > 0.001) drawBlindZone(ctx, state, v, p);

  /* --- 6c. Màn mưa/sương/loá ---------------------------------------------- */
  if (state.veil.alpha > 0.001) drawVeil(ctx, state, W, H, v, p);

  /* --- 7. HUD: khung bao (chữ nằm ở lớp DOM) ------------------------------ */
  for (const actor of sorted) {
    if (actor.box <= 0.001) continue;
    drawBox(ctx, actor, W, H, p);
  }

  // sương mờ ở mép trên — giới hạn tầm nhìn
  ctx.fillStyle = g.haze;
  ctx.fillRect(0, 0, W, H * 0.22);

  // vệt mây mềm ở hai mép trên — mô-típ mượn từ ảnh render, làm dịu góc khung
  for (const [mx, my, mr] of [
    [W * 0.06, H * 0.1, W * 0.3],
    [W * 0.97, H * 0.2, W * 0.26],
  ]) {
    ctx.save();
    ctx.translate(mx, my);
    ctx.scale(mr, mr * 0.72);
    ctx.fillStyle = g.cloud;
    ctx.beginPath();
    ctx.arc(0, 0, 1, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // tan vào màu trang ở mép dưới, tránh cạnh cắt cứng ở ranh giới section
  ctx.fillStyle = g.tail;
  ctx.fillRect(0, H * 0.93, W, H * 0.07);

  ctx.restore();
}

/**
 * Hai lượt tô, mỗi tông một path — giữ số lần đổi fillStyle ở mức 2 mỗi frame
 * thay vì một lần cho mỗi khối.
 */
/**
 * Nối dấu chân của một khối vào path hiện tại. Mọi biến thể đều tham số hoá
 * theo hộp bao, nhờ vậy lượt vẽ mặt mái chỉ cần gọi lại đúng hàm này với hộp
 * đã thu nhỏ và dịch về phía đèn — không cần toán hình riêng cho từng dáng.
 */
function addShape(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  shape: Shape,
  flip: boolean,
) {
  if (w <= 0 || h <= 0) return;
  switch (shape) {
    case "cyl":
      ctx.moveTo(x + w, y + h / 2);
      ctx.ellipse(x + w / 2, y + h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
      break;

    case "wedge": {
      // nêm: một cạnh vát, đọc ra như mặt dốc
      const x0 = flip ? x : x + w;
      const x1 = flip ? x + w : x;
      ctx.moveTo(x0, y);
      ctx.lineTo(x1, y + h * 0.5);
      ctx.lineTo(x0, y + h);
      ctx.closePath();
      break;
    }

    case "arc": {
      // dải cung phần tư, bề dày bằng 40% cạnh ngắn
      const r = Math.min(w, h);
      const t = r * 0.4;
      const cx = flip ? x : x + w;
      const cy = y + h;
      const a0 = flip ? -Math.PI / 2 : Math.PI;
      const a1 = flip ? 0 : -Math.PI / 2;
      ctx.moveTo(cx + Math.cos(a0) * r, cy + Math.sin(a0) * r);
      ctx.arc(cx, cy, r, a0, a1);
      ctx.lineTo(cx + Math.cos(a1) * (r - t), cy + Math.sin(a1) * (r - t));
      ctx.arc(cx, cy, r - t, a1, a0, true);
      ctx.closePath();
      break;
    }

    case "ridge": {
      // tấm gân sóng: các thanh mảnh song song trong hộp bao
      const n = Math.max(3, Math.round(h / Math.max(2, h / 6)));
      const step = h / n;
      for (let i = 0; i < n; i++) ctx.rect(x, y + i * step, w, step * 0.55);
      break;
    }

    case "step": {
      // khối bậc thang: ba tầng thụt dần về một góc
      ctx.rect(x, y, w, h);
      ctx.rect(x + w * 0.18, y + h * 0.1, w * 0.7, h * 0.8);
      ctx.rect(x + w * 0.4, y + h * 0.22, w * 0.5, h * 0.56);
      break;
    }

    default:
      ctx.rect(x, y, w, h);
  }
}

type BlockRect = {
  x: number;
  y: number;
  w: number;
  h: number;
  tone: 0 | 1 | 2;
  shape: Shape;
  hh: number;
  flip: boolean;
};

/** Ba bậc chiều cao — đủ để bóng đổ khác nhau mà chỉ tốn ba lượt fill. */
const TIERS = [0.35, 0.9, 1.7];

function drawBlocks(
  ctx: CanvasRenderingContext2D,
  state: HeroState,
  v: View,
  g: GradCache,
  p: Palette,
) {
  const phase = state.worldOffset % BUILD_SPAN;
  // Thu hình một lần rồi vẽ hai lượt: chân khối tối, mặt mái sáng và nhấc về
  // phía đèn. Dải tối lộ ra ở cạnh khuất chính là vách khối.
  const rects: BlockRect[] = [];
  for (const b of BLOCKS) {
    for (let r = 0; r < 3; r++) {
      const zc = b.z + r * BUILD_SPAN - phase;
      const zNear = zc - b.d / 2;
      const zFar = zc + b.d / 2;
      if (zFar < -14 || zNear > VIEW_DEPTH + 10) continue;
      const yTop = v.baseY - depthPx(zFar, v);
      const yBot = v.baseY - depthPx(zNear, v);
      rects.push({
        x: v.cx + (b.x - b.w / 2) * v.lat,
        y: yTop,
        w: b.w * v.lat,
        h: yBot - yTop,
        tone: b.tone,
        shape: b.shape,
        hh: b.hh,
        flip: b.flip,
      });
    }
  }

  // lượt 1 — chân khối, chia theo bậc chiều cao để bóng đổ khác nhau
  ctx.save();
  ctx.fillStyle = g.blockWall;
  for (const tier of TIERS) {
    ctx.shadowColor = rgba(p["--shadow-cast"], 0.1 + tier * 0.05);
    ctx.shadowBlur = v.lat * 0.3 * tier;
    ctx.shadowOffsetX = v.lat * 0.2 * tier;
    ctx.shadowOffsetY = v.lat * 0.13 * tier;
    ctx.beginPath();
    let any = false;
    for (const r of rects) {
      if (tierOf(r.hh) !== tier) continue;
      addShape(ctx, r.x, r.y, r.w, r.h, r.shape, r.flip);
      any = true;
    }
    if (any) ctx.fill();
  }
  ctx.restore();

  // lượt 2 — mặt mái, thu vào và nhấc theo chiều cao riêng của từng khối.
  // Nét viền mảnh là thứ tách được hai khối cùng tông chồng lên nhau; thiếu
  // nó thì cả cụm nhoè thành một mảng xám.
  ctx.lineWidth = Math.max(1, v.lat * 0.035);
  ctx.strokeStyle = g.blockEdge;
  for (const tone of [0, 1, 2] as const) {
    ctx.fillStyle = tone === 0 ? g.blockA : tone === 1 ? g.blockB : g.blockC;
    ctx.beginPath();
    for (const r of rects) {
      if (r.tone !== tone) continue;
      const ins = Math.min(r.w, r.h) * 0.055;
      addShape(
        ctx,
        r.x + ins - v.lat * 0.34 * r.hh,
        r.y + ins - v.lat * 0.2 * r.hh,
        r.w - ins * 2,
        r.h - ins * 2,
        r.shape,
        r.flip,
      );
    }
    ctx.fill();
    ctx.stroke();
  }
}

function tierOf(hh: number): number {
  return hh < 0.6 ? TIERS[0] : hh < 1.2 ? TIERS[1] : TIERS[2];
}

function drawActor(
  ctx: CanvasRenderingContext2D,
  a: Actor,
  W: number,
  H: number,
  v: View,
  p: Palette,
  g: GradCache,
) {
  const f = footprint(a, W, H);
  ctx.save();
  ctx.globalAlpha *= a.alpha;

  if (a.kind === "car") {
    drawCarTop(ctx, f.x + f.w / 2, f.y + f.h, f.w / 2, f.h, p, "light", g);
  } else if (a.kind === "bike") {
    // Xe máy nhìn từ trên: thân hẹp, người ngồi rộng hơn xe — đúng tỉ lệ mà
    // một hộp bao nhìn thấy, và là hình dạng chiếm phần lớn giao thông VN.
    const cx = f.x + f.w / 2;
    const w = f.w;
    ctx.fillStyle = rgba(p["--surface-4"], 0.92);
    roundRect(ctx, cx - w * 0.3, f.y, w * 0.6, f.h, w * 0.28);
    ctx.fill();
    ctx.fillStyle = rgba(p["--surface-5"], 1);
    ctx.beginPath();
    ctx.ellipse(cx, f.y + f.h * 0.42, w * 0.62, f.h * 0.2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx, f.y + f.h * 0.3, w * 0.3, 0, Math.PI * 2);
    ctx.fill();
  } else if (a.kind === "ped") {
    // Nhìn từ trên: vai là ellipse, đầu là hình tròn ở giữa.
    const cx = f.x + f.w / 2;
    const cy = f.y + f.h / 2;
    const r = Math.max(2, (a.w / 2) * v.lat);
    ctx.fillStyle = rgba(p["--surface-4"], 0.9);
    ctx.beginPath();
    ctx.ellipse(cx, cy, r * 1.15, r * 0.72, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = rgba(p["--surface-5"], 1);
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.6, 0, Math.PI * 2);
    ctx.fill();
  } else {
    // Cọc tiêu được vẽ thành silhouette tam giác có vạch trắng thay vì
    // một chấm tròn. Màu cam mô tả bản thân vật thể; khung xanh/đỏ
    // mới là trạng thái theo dõi/nguy hiểm của RoadWatch.
    const cx = f.x + f.w / 2;
    const cy = f.y + f.h / 2;
    ctx.fillStyle = rgba(p["--object-marker"], 0.96);
    ctx.beginPath();
    ctx.moveTo(cx, f.y);
    ctx.lineTo(f.x + f.w, f.y + f.h * 0.84);
    ctx.lineTo(f.x + f.w * 0.82, f.y + f.h);
    ctx.lineTo(f.x + f.w * 0.18, f.y + f.h);
    ctx.lineTo(f.x, f.y + f.h * 0.84);
    ctx.closePath();
    ctx.fill();
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx, f.y);
    ctx.lineTo(f.x + f.w, f.y + f.h * 0.84);
    ctx.lineTo(f.x + f.w * 0.82, f.y + f.h);
    ctx.lineTo(f.x + f.w * 0.18, f.y + f.h);
    ctx.lineTo(f.x, f.y + f.h * 0.84);
    ctx.closePath();
    ctx.clip();
    ctx.fillStyle = rgba(p["--surface-0"], 0.92);
    ctx.fillRect(f.x, cy - f.h * 0.09, f.w, Math.max(2, f.h * 0.18));
    ctx.restore();
    ctx.strokeStyle = rgba(p["--surface-5"], 0.45);
    ctx.lineWidth = 1;
    ctx.strokeRect(f.x + f.w * 0.08, f.y + f.h * 0.88, f.w * 0.84, Math.max(2, f.h * 0.12));
  }
  ctx.restore();
}

/**
 * Xe tải nhìn từ trên xuống, cùng thủ pháp 2.5D với xe con nhưng chia hai khối:
 * ca-bin ngắn phía trước và thùng dài phía sau, chừa một khe hở giữa hai khối.
 * Chính cái khe đó là thứ đọc ra "xe tải" chứ không phải một hộp dài.
 */
function drawTruckTop(
  ctx: CanvasRenderingContext2D,
  cx: number,
  rearY: number,
  halfW: number,
  len: number,
  p: Palette,
  g: GradCache,
) {
  const cabLen = len * 0.28;
  const gap = len * 0.04;
  const boxLen = len - cabLen - gap;
  const frontY = rearY - len;

  // bóng tiếp đất: một khối, ôm cả ca-bin lẫn thùng
  ctx.save();
  ctx.globalAlpha *= 0.5;
  ctx.translate(cx, rearY - len / 2);
  ctx.scale(halfW * 1.5, len * 0.52);
  ctx.fillStyle = g.shadow;
  ctx.beginPath();
  ctx.arc(0, 0, 1, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  const slab = (y: number, h: number, w: number, roofStop: number) => {
    // mặt sàn + bóng đổ theo hướng đèn chung
    ctx.save();
    ctx.shadowColor = rgba(p["--shadow-cast"], 0.3);
    ctx.shadowBlur = Math.max(6, w * LIGHT.blur);
    ctx.shadowOffsetX = w * LIGHT.shadowX;
    ctx.shadowOffsetY = h * LIGHT.shadowY * 0.5;
    const wall = ctx.createLinearGradient(cx - w, 0, cx + w, 0);
    wall.addColorStop(0, rgba(p["--car-shade"], 1));
    wall.addColorStop(1, rgba(p["--car-edge"], 1));
    ctx.fillStyle = wall;
    roundRect(ctx, cx - w, y, w * 2, h, Math.min(w * 0.22, h * 0.12));
    ctx.fill();
    ctx.restore();

    // mặt nóc: thu vào và nhấc về phía đèn -> lộ vách hông ở cạnh khuất
    const ins = w * 0.07;
    const dx = -w * 0.12;
    const dy = -h * 0.02;
    const deck = ctx.createLinearGradient(cx - w, 0, cx + w, 0);
    deck.addColorStop(0, rgba(p["--car-spec"], 1));
    deck.addColorStop(roofStop, rgba(p["--car-body"], 1));
    deck.addColorStop(1, rgba(p["--car-shade"], 1));
    ctx.fillStyle = deck;
    roundRect(ctx, cx - w + ins + dx, y + ins + dy, (w - ins) * 2, h - ins * 2,
      Math.min(w * 0.18, h * 0.1));
    ctx.fill();
    return { dx, dy, ins };
  };

  const box = slab(frontY + cabLen + gap, boxLen, halfW, 0.55);
  // gân ngang trên nóc thùng: thùng hàng phẳng trơn trông như một viên gạch
  ctx.save();
  ctx.strokeStyle = rgba(p["--car-edge"], 0.5);
  ctx.lineWidth = Math.max(1, halfW * 0.05);
  const ribs = 5;
  for (let i = 1; i < ribs; i++) {
    const y = frontY + cabLen + gap + (boxLen * i) / ribs + box.dy;
    ctx.beginPath();
    ctx.moveTo(cx - halfW * 0.8 + box.dx, y);
    ctx.lineTo(cx + halfW * 0.8 + box.dx, y);
    ctx.stroke();
  }
  ctx.restore();

  const cab = slab(frontY, cabLen, halfW * 0.96, 0.5);
  // kính lái của ca-bin
  ctx.fillStyle = rgba(p["--car-glass"], 0.92);
  roundRect(ctx, cx - halfW * 0.66 + cab.dx, frontY + cabLen * 0.22 + cab.dy,
    halfW * 1.32, cabLen * 0.34, halfW * 0.1);
  ctx.fill();

  // đèn hậu ở đuôi thùng
  ctx.fillStyle = rgba(p["--state-alert"], 0.9);
  for (const sx of [-1, 1]) {
    roundRect(ctx, cx + sx * halfW * 0.72 - halfW * 0.16 + box.dx,
      rearY - len * 0.028 + box.dy, halfW * 0.32, len * 0.016, halfW * 0.06);
    ctx.fill();
  }
}

/**
 * Vùng camera trước KHÔNG nhìn tới: hai dải gạch chéo hai bên và phía sau xe
 * chủ. Đây là điểm mù thật của một hệ chỉ có một camera hướng trước, nên nó
 * được vẽ ra thay vì giấu đi.
 */
function drawBlindZone(
  ctx: CanvasRenderingContext2D,
  state: HeroState,
  v: View,
  p: Palette,
) {
  const cx = v.cx + (state.ego.x + state.ego.swerve) * v.lat;
  const halfW = (state.ego.kind === 1 ? 2.5 : 1.9) * 0.5 * v.lat;
  const len = (state.ego.kind === 1 ? 9.5 : 4.6) * v.lat;
  const top = v.baseY - len * 0.85;
  const bottom = v.baseY + len * 1.1;

  ctx.save();
  ctx.globalAlpha *= state.blind.alpha;
  ctx.beginPath();
  ctx.rect(cx - halfW * 4.6, top, halfW * 3.4, bottom - top);
  ctx.rect(cx + halfW * 1.2, top, halfW * 3.4, bottom - top);
  ctx.clip();
  ctx.fillStyle = rgba(p["--state-alert"], 0.06);
  ctx.fillRect(cx - halfW * 5, top, halfW * 10, bottom - top);
  ctx.strokeStyle = rgba(p["--state-alert"], 0.34);
  ctx.lineWidth = Math.max(1, v.lat * 0.05);
  const step = v.lat * 0.7;
  // Nét chéo 45° đi lên bên phải, nên phải bắt đầu lùi thêm đúng chiều cao dải
  // thì dải bên TRÁI mới có gạch. Thiếu bước lùi này, bên trái chỉ còn mảng tô.
  const span = bottom - top;
  for (let x = cx - halfW * 6 - span; x < cx + halfW * 6; x += step) {
    ctx.beginPath();
    ctx.moveTo(x, bottom);
    ctx.lineTo(x + (bottom - top), top);
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * Màn mưa / sương / loá nắng. Không phải hiệu ứng trang trí: nó che đúng phần
 * xa của khung — nơi vạch kẻ và xe ở xa biến mất trước tiên — nên người xem
 * thấy được vì sao nhánh làn tụt chất lượng chứ không chỉ được thông báo.
 */
function drawVeil(
  ctx: CanvasRenderingContext2D,
  state: HeroState,
  W: number,
  H: number,
  v: View,
  p: Palette,
) {
  ctx.save();
  ctx.globalAlpha *= state.veil.alpha;
  const horizon = v.baseY - depthPx(VIEW_DEPTH, v);

  // đục nhất ở xa, loãng dần về phía mũi xe — đúng thứ tự mà tầm nhìn mất đi
  const haze = ctx.createLinearGradient(0, horizon, 0, v.baseY);
  haze.addColorStop(0, rgba(p["--surface-2"], 0.92));
  haze.addColorStop(0.55, rgba(p["--surface-2"], 0.5));
  haze.addColorStop(1, rgba(p["--surface-2"], 0.12));
  ctx.fillStyle = haze;
  ctx.fillRect(0, 0, W, v.baseY);

  if (state.veil.kind === 0) {
    // vệt mưa: nghiêng theo chiều xe chạy, thưa dần về xa
    ctx.strokeStyle = rgba(p["--surface-3"], 0.3);
    ctx.lineWidth = Math.max(1, v.lat * 0.035);
    // Vị trí sinh từ hạt cố định nhưng ĐƯỢC DỜI theo worldOffset: mưa đứng yên
    // đọc ra thành vết xước trên ống kính, không phải mưa.
    const band = H - horizon;
    const fall = (state.worldOffset * 90) % band;
    const n = 90;
    for (let i = 0; i < n; i++) {
      const seed = (i * 9301 + 49297) % 233280;
      const rx = (seed / 233280) * W;
      const base = (((seed * 7) % 233280) / 233280) * band;
      const ry = horizon + ((base + fall) % band);
      const l = v.lat * 0.5 + (ry - horizon) * 0.06;
      ctx.beginPath();
      ctx.moveTo(rx, ry);
      ctx.lineTo(rx - l * 0.28, ry + l);
      ctx.stroke();
    }
  }
  ctx.restore();
}

/**
 * Xe nhìn từ trên xuống. Đầu xe hướng lên. Dựng theo lớp dọc thân:
 * bóng → thân → nắp ca-pô → kính lái → nóc → kính sau → đèn hậu → gương.
 */
function drawCarTop(
  ctx: CanvasRenderingContext2D,
  cx: number,
  rearY: number,
  halfW: number,
  len: number,
  p: Palette,
  skin: "light" | "dark",
  g: GradCache,
) {
  const bodyC = p["--car-body"];
  const shadeC = p["--car-shade"];
  const roofC = p["--car-roof"];
  const glassC = p["--car-glass"];
  const edgeC = p["--car-edge"];
  const specC = p["--car-spec"];
  const edgeW = skin === "dark" ? 1.6 : 1.2;
  const frontY = rearY - len;
  const at = (t: number) => frontY + len * t; // t: 0 = đầu xe, 1 = đuôi
  let deckX = 0;
  let deckY = 0;
  const rad = Math.min(halfW * 0.42, len * 0.16);
  const simple = halfW < 7 || len < 16;

  /* 1. Bóng tiếp đất: tối, chặt, không lệch. Đây là thứ khiến xe ĐỨNG TRÊN
        mặt đường thay vì dán lên nó. */
  ctx.save();
  ctx.translate(cx, frontY + len / 2);
  ctx.scale(halfW * 1.35, len * 0.56);
  ctx.fillStyle = g.shadow;
  ctx.beginPath();
  ctx.arc(0, 0, 1, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  /* 2. Mặt sàn: chiếm trọn dấu chân xe, tô tối. Mặt nóc ở bước sau sẽ thu nhỏ
        và dịch về phía đèn, để lộ dải tối này ở cạnh khuất — đó chính là VÁCH
        HÔNG. Nhìn từ trên xuống, bề dày chỉ đọc được nhờ dải vách này. */
  ctx.save();
  ctx.shadowColor = rgba(p["--shadow-cast"], 0.42);
  ctx.shadowBlur = Math.max(5, halfW * LIGHT.blur);
  ctx.shadowOffsetX = halfW * LIGHT.shadowX;
  ctx.shadowOffsetY = len * LIGHT.shadowY;
  const wall = ctx.createLinearGradient(cx - halfW, frontY, cx + halfW, rearY);
  wall.addColorStop(0, rgba(shadeC, 1));
  wall.addColorStop(1, rgba(edgeC, 1));
  ctx.fillStyle = wall;
  roundRect(ctx, cx - halfW, frontY, halfW * 2, len, rad);
  ctx.fill();
  ctx.restore();

  // mặt nóc: thu vào và nhấc về phía đèn (trên-trái)
  const liftX = halfW * 0.1;
  const liftY = len * 0.028;
  const ins = halfW * 0.05;
  const ux = cx - halfW + ins - liftX;
  const uy = frontY + ins * 0.7 - liftY;
  const uw = halfW * 2 - ins * 2;
  const uh = len - ins * 1.4;

  deckX = -liftX;
  deckY = -liftY;
  const body = ctx.createLinearGradient(ux, uy, ux + uw, uy + uh);
  body.addColorStop(0, rgba(specC, 1));
  body.addColorStop(0.32, rgba(bodyC, 1));
  body.addColorStop(0.74, rgba(bodyC, 1));
  body.addColorStop(1, rgba(shadeC, 1));
  ctx.fillStyle = body;
  roundRect(ctx, ux, uy, uw, uh, rad * 0.92);
  ctx.fill();

  /* 3. Vát cạnh mặt nóc: nét sáng phía đèn, tối dần sang cạnh khuất. */
  const bevel = ctx.createLinearGradient(ux, uy, ux + uw, uy + uh);
  bevel.addColorStop(0, rgba(specC, 0.95));
  bevel.addColorStop(0.45, rgba(edgeC, 0.45));
  bevel.addColorStop(1, rgba(edgeC, 0.9));
  ctx.strokeStyle = bevel;
  ctx.lineWidth = edgeW;
  roundRect(ctx, ux, uy, uw, uh, rad * 0.92);
  ctx.stroke();

  if (simple) {
    ctx.fillStyle = rgba(p["--state-alert"], 0.9);
    ctx.fillRect(cx - halfW * 0.8, at(0.9), Math.max(1.2, halfW * 0.55), Math.max(1.2, len * 0.07));
    ctx.fillRect(cx + halfW * 0.25, at(0.9), Math.max(1.2, halfW * 0.55), Math.max(1.2, len * 0.07));
    return;
  }

  /* 4. Vệt specular chạy dọc mép hướng đèn, cắt gọn trong thân. */
  ctx.save();
  roundRect(ctx, ux, uy, uw, uh, rad * 0.92);
  ctx.clip();
  const spec = ctx.createLinearGradient(ux, 0, ux + uw * 0.42, 0);
  spec.addColorStop(0, rgba(specC, 0));
  spec.addColorStop(0.45, rgba(specC, 0.62));
  spec.addColorStop(1, rgba(specC, 0));
  ctx.fillStyle = spec;
  ctx.fillRect(ux, uy + uh * 0.05, uw * 0.45, uh * 0.9);
  ctx.restore();

  // gương chiếu hậu
  ctx.fillStyle = rgba(bodyC, 1);
  const mW = halfW * 0.2;
  const mH = len * 0.05;
  ctx.fillRect(cx - halfW - mW * 0.75 + deckX, at(0.3) + deckY, mW, mH);
  ctx.fillRect(cx + halfW - mW * 0.25 + deckX, at(0.3) + deckY, mW, mH);

  /* 5. Nóc: hơi thấp hơn vai xe nên nhận ít sáng hơn ở mép khuất. */
  const roof = ctx.createLinearGradient(cx - halfW * 0.8, 0, cx + halfW * 0.8, 0);
  roof.addColorStop(0, rgba(roofC, 1));
  roof.addColorStop(1, rgba(shadeC, 1));
  ctx.fillStyle = roof;
  roundRect(ctx, cx - halfW * 0.8 + deckX, at(0.3) + deckY, halfW * 1.6, len * 0.34, Math.min(halfW * 0.24, len * 0.08));
  ctx.fill();

  /* 6. Kính: nền tối có chuyển sắc, cộng một vệt phản chiếu trời chéo. */
  const drawGlass = (x: number, y: number, w: number, h: number, r: number) => {
    const gl = ctx.createLinearGradient(x, y, x + w, y + h);
    gl.addColorStop(0, rgba(glassC, 0.99));
    gl.addColorStop(0.55, rgba(glassC, 0.9));
    gl.addColorStop(1, rgba(glassC, 0.99));
    ctx.fillStyle = gl;
    roundRect(ctx, x, y, w, h, r);
    ctx.fill();
    ctx.save();
    roundRect(ctx, x, y, w, h, r);
    ctx.clip();
    const ref = ctx.createLinearGradient(x, y, x + w * 0.8, y + h);
    ref.addColorStop(0, rgba(specC, 0.32));
    ref.addColorStop(0.42, rgba(specC, 0.05));
    ref.addColorStop(1, rgba(specC, 0));
    ctx.fillStyle = ref;
    ctx.fillRect(x, y, w, h);
    ctx.restore();
  };
  drawGlass(cx - halfW * 0.76 + deckX, at(0.19) + deckY, halfW * 1.52, len * 0.13, len * 0.04);
  drawGlass(cx - halfW * 0.74 + deckX, at(0.66) + deckY, halfW * 1.48, len * 0.12, len * 0.04);

  // đèn hậu ở mép đuôi
  const lampW = halfW * 0.5;
  const lampH = Math.max(1.5, len * 0.05);
  for (const lx of [cx - halfW * 0.86 + deckX, cx + halfW * 0.36 + deckX]) {
    ctx.fillStyle = rgba(p["--state-alert"], 0.2);
    roundRect(ctx, lx - lampW * 0.14, at(0.88) + deckY - lampH * 0.6, lampW * 1.28, lampH * 2.4, lampH * 0.7);
    ctx.fill();
    ctx.fillStyle = rgba(p["--state-alert"], 0.95);
    roundRect(ctx, lx, at(0.9) + deckY, lampW, lampH, lampH * 0.45);
    ctx.fill();
  }
}

/** Khung bao kiểu ngoặc góc, vẽ dần theo actor.box (0..1). */
function drawBox(
  ctx: CanvasRenderingContext2D,
  a: Actor,
  W: number,
  H: number,
  p: Palette,
) {
  const f = footprint(a, W, H);
  const pad = Math.max(3, f.w * 0.12);
  const x0 = f.x - pad;
  const y0 = f.y - pad;
  const bw = f.w + pad * 2;
  const bh = f.h + pad * 2;
  const c = toneColor(p, a.tone);
  const arm = Math.min(bw, bh) * 0.34 * a.box;

  ctx.save();
  ctx.globalAlpha *= a.alpha;
  ctx.strokeStyle = rgba(c, 0.95);
  ctx.lineWidth = 1.6;
  ctx.lineCap = "square";
  ctx.beginPath();
  ctx.moveTo(x0, y0 + arm); ctx.lineTo(x0, y0); ctx.lineTo(x0 + arm, y0);
  ctx.moveTo(x0 + bw - arm, y0); ctx.lineTo(x0 + bw, y0); ctx.lineTo(x0 + bw, y0 + arm);
  ctx.moveTo(x0 + bw, y0 + bh - arm); ctx.lineTo(x0 + bw, y0 + bh); ctx.lineTo(x0 + bw - arm, y0 + bh);
  ctx.moveTo(x0 + arm, y0 + bh); ctx.lineTo(x0, y0 + bh); ctx.lineTo(x0, y0 + bh - arm);
  ctx.stroke();

  ctx.globalAlpha *= 0.1 * a.box;
  ctx.fillStyle = rgba(c, 1);
  ctx.fillRect(x0, y0, bw, bh);
  ctx.restore();
}

function drawTrajectory(
  ctx: CanvasRenderingContext2D,
  state: HeroState,
  v: View,
  p: Palette,
) {
  const t = state.trajectory;
  if (t.alpha <= 0.001 || t.length <= 0.001) return;
  const zMax = 46 * t.length;
  const c = toneColor(p, t.tone);
  const STEPS = 24;

  const left: [number, number][] = [];
  const right: [number, number][] = [];
  for (let i = 0; i <= STEPS; i++) {
    const u = i / STEPS;
    const z = u * zMax;
    const cx = state.ego.x + t.curve * u * u; // uốn dần, gốc luôn thẳng
    const halfWidth = 0.95 * (1 - u * 0.3);
    const y = v.baseY - depthPx(z, v);
    left.push([v.cx + (cx - halfWidth) * v.lat, y]);
    right.push([v.cx + (cx + halfWidth) * v.lat, y]);
  }

  const grad = ctx.createLinearGradient(0, v.baseY, 0, v.baseY - depthPx(zMax, v));
  grad.addColorStop(0, rgba(c, 0.5));
  grad.addColorStop(0.55, rgba(c, 0.26));
  grad.addColorStop(1, rgba(c, 0));

  ctx.save();
  ctx.globalAlpha *= t.alpha;
  ctx.beginPath();
  ctx.moveTo(left[0][0], left[0][1]);
  for (const q of left) ctx.lineTo(q[0], q[1]);
  for (let i = right.length - 1; i >= 0; i--) ctx.lineTo(right[i][0], right[i][1]);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  const edge = ctx.createLinearGradient(0, v.baseY, 0, v.baseY - depthPx(zMax, v));
  edge.addColorStop(0, rgba(c, 0.9));
  edge.addColorStop(1, rgba(c, 0));
  ctx.strokeStyle = edge;
  ctx.lineWidth = 1.5;
  ctx.lineJoin = "round";
  for (const side of [left, right]) {
    ctx.beginPath();
    ctx.moveTo(side[0][0], side[0][1]);
    for (const q of side) ctx.lineTo(q[0], q[1]);
    ctx.stroke();
  }
  ctx.restore();
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  const rr = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}
