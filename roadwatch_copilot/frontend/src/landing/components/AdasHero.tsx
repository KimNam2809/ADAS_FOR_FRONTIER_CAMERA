import { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import {
  createState,
  draw,
  footprint,
  readPalette,
  invalidateGradients,
  LOOP,
  WORLD_SPAN,
  type HeroState,
  type Palette,
} from "../lib/heroScene";

gsap.registerPlugin(useGSAP);

/** danger: cảnh có mối nguy → chỉ báo đổi sang đỏ. */
const CAPTIONS = [
  { text: "Theo dõi làn đường", danger: false, ego: "XE CON", live: true },
  { text: "Nhận diện và theo dõi", danger: false, ego: "XE CON", live: true },
  { text: "Nguy cơ va chạm phía trước", danger: true, ego: "XE CON", live: true },
  { text: "Xe nhập làn từ bên phải", danger: true, ego: "XE CON", live: true },
  { text: "Người đi bộ vào quỹ đạo", danger: true, ego: "XE CON", live: true },
  { text: "Xe máy trong điểm mù", danger: true, ego: "XE TẢI", live: false },
  { text: "Xe trước giảm tốc · tài xế chưa phản ứng", danger: true, ego: "XE CON", live: true },
  { text: "Mưa mù · vẫn thấy xe phía trước", danger: true, ego: "XE TẢI", live: true },
];

/**
 * Câu cảnh báo phát ra loa. Lấy nguyên văn từ catalog canonical của Alert
 * Governor (backend/roadwatch/alert_copy.py, profile vNext) — banner và TTS dùng chung một
 * chuỗi, nên chữ hiện trên hero cũng phải là chữ hệ thống thật sự đọc.
 */
const VOICE = [
  "Cảnh báo va chạm",
  "Ô tô nhập làn từ bên phải. Hãy chú ý.",
  "Người đi bộ phía trước; giảm tốc độ.",
  "Ô tô phía trước đang giảm tốc. Hãy chú ý.",
];

/**
 * Ba cảnh cuối cần cảm biến hoặc trạng thái mà bản đang chạy chưa có, nên
 * chúng KHÔNG mượn câu của Alert Governor. Chữ ở đây mô tả hành vi mong muốn
 * và luôn đi kèm nhãn cho biết cảnh đó đã chạy được hay chưa.
 */
const FUTURE_NOTE = [
  "Cần cảm biến sau/bên — camera trước không thấy vùng này",
  "Hệ không biết tài xế đang nhìn đâu; nó chỉ biết xe trước đang phanh",
  "Hai nhánh hỏng khác nhau: làn khoá lại, vật thể vẫn chạy",
];

/** Lý do kênh loa đang im lặng — im lặng cũng phải giải thích được. */
const VOICE_STATUS = [
  "Đang theo dõi · chưa có mối nguy",
  "Đã bám ô tô · chưa phát cảnh báo",
  "Đang theo dõi lề phải · chưa cắt quỹ đạo",
  "Ngoài tầm nhìn camera trước · không phát được",
  "Chất lượng làn thấp · đã khoá cảnh báo lệch làn",
  "Đã bám xe trước · đang theo dõi khoảng cách",
  "Nhánh làn đã khoá · nhánh vật thể vẫn bám được",
];

/** Số cột sóng âm. Biên độ suy ra từ worldOffset nên không cần tween riêng. */
const BARS = [0, 1, 2, 3, 4];

/**
 * Bề rộng một ký tự mono, tính theo em: JetBrains Mono có advance 0.6em, cộng
 * letter-spacing 0.14em của nhãn. Dùng để kẹp nhãn trong khung mà không phải
 * đọc offsetWidth mỗi frame (đọc là ép reflow).
 */
const LABEL_CHAR_EM = 0.74;

/**
 * Nhãn khoảng cách tương đối. `z` chỉ phục vụ dàn cảnh, không phải
 * phép đo từ camera; landing vì thế tuyệt đối không hiển thị mét.
 */
function proximityLabel(z: number): string {
  if (z <= 12) return "RẤT GẦN";
  if (z <= 20) return "GẦN";
  if (z <= 34) return "ĐANG TỚI GẦN";
  return "ĐÃ BÁM";
}

/**
 * Dựng timeline 26s, tám cảnh, xe con và xe tải xen kẽ.
 *
 * Ba cảnh cuối (điểm mù, tài xế rời mắt, mưa lớn) mô tả tình huống thật trên
 * đường, nhưng chỉ cảnh mưa là hành vi bản đang chạy làm được. Hai cảnh kia
 * cần cảm biến chưa có, và nhãn trên khung nói rõ điều đó thay vì diễn như
 * thể hệ đã xử lý được.
 */
function buildTimeline(state: HeroState) {
  const tl = gsap.timeline({ repeat: -1, defaults: { ease: "none" } });
  const [lead, cutin, ped, cone, bike, slow] = state.boxes;

  // Thế giới trôi liên tục; WORLD_SPAN là bội số chu kỳ vạch nên lặp liền mạch.
  tl.to(state, { worldOffset: WORLD_SPAN, duration: LOOP }, 0);

  /* ---- lane · 0–3 ---- */
  tl.addLabel("lane", 0);
  tl.set(state, { fade: 1 }, 0);
  tl.set(state.trajectory, { curve: 0, length: 1, tone: 0, alpha: 1 }, 0);
  tl.set(lead, { alpha: 0, box: 0, z: 48, tone: 0, labelAlpha: 0 }, 0);
  tl.set(cutin, { alpha: 0, box: 0, x: 3.5, z: 26, tone: 0, labelAlpha: 0 }, 0);
  tl.set(ped, { alpha: 0, box: 0, x: 6.6, z: 22, tone: 0, labelAlpha: 0 }, 0);
  tl.set(cone, { alpha: 0, box: 0, z: 16, tone: 0, labelAlpha: 0 }, 0);
  tl.set(bike, { alpha: 0, box: 0, x: 3.4, z: 2.2, tone: 0, labelAlpha: 0 }, 0);
  tl.set(slow, { alpha: 0, box: 0, x: 0, z: 44, tone: 0, labelAlpha: 0 }, 0);
  tl.set(state.ego, { kind: 0, swerve: 0 }, 0);
  tl.set(state.veil, { alpha: 0, kind: 0 }, 0);
  tl.set(state.blind, { alpha: 0 }, 0);
  tl.set(state.hud, { riskAlpha: 0 }, 0);
  tl.set(state.voice, { alpha: 0, index: 0, status: 0, tone: 0 }, 0);
  tl.set(state.captions, { alpha: 0 }, 0);
  tl.set(state.captions[0], { alpha: 1 }, 0);

  /* ---- detect · 3–6 · box vẽ dần, nhãn đếm 48m → 32m ---- */
  tl.addLabel("detect", 3);
  tl.to(lead, { alpha: 1, duration: 0.4 }, 3.0);
  tl.to(lead, { box: 1, duration: 0.7 }, 3.15);
  tl.to(lead, { labelAlpha: 1, duration: 0.3 }, 3.5);
  tl.to(lead, { z: 32, duration: 2.6 }, 3.2);
  tl.set(state.voice, { status: 1 }, 3.25);
  // Bám được xe phía trước KHÔNG phải lý do để nói. Kênh giọng nói giữ im lặng
  // suốt `lane` và `detect` — đúng contract của Alert Governor.

  /* ---- fcw · 6–9 · phanh gấp, đỏ, quỹ đạo ngắn lại, risk proxy ---- */
  tl.addLabel("fcw", 6);
  tl.to(lead, { z: 13, duration: 1.6, ease: "power2.in" }, 6.1);
  tl.set(lead, { tone: 1 }, 6.35);
  tl.set(state.trajectory, { tone: 1 }, 6.35);
  tl.to(state.trajectory, { length: 0.42, duration: 0.9, ease: "power2.out" }, 6.35);
  tl.to(state.hud, { riskAlpha: 1, duration: 0.3 }, 6.4);
  // critical: audio nổ ngay sau khi severity lên đỏ
  tl.set(state.voice, { index: 0, tone: 1 }, 6.45);
  tl.to(state.voice, { alpha: 1, duration: 0.18 }, 6.45);
  tl.to(state.voice, { alpha: 0, duration: 0.3 }, 8.45);

  /* ---- cutin · 9–12 · box hiện TRƯỚC khi chạm vạch làn ---- */
  tl.addLabel("cutin", 9);
  tl.to(lead, { alpha: 0, box: 0, labelAlpha: 0, duration: 0.5 }, 9.0);
  tl.to(state.hud, { riskAlpha: 0, duration: 0.4 }, 9.0);
  tl.set(lead, { tone: 0 }, 9.6);
  tl.set(state.trajectory, { tone: 0 }, 9.5);
  tl.to(state.trajectory, { length: 1, duration: 0.8 }, 9.2);
  // khung xong ở 9.65; xe chạm vạch làn (x = 1.75) mãi tới ~10.46
  tl.to(cutin, { alpha: 1, duration: 0.3 }, 9.0);
  tl.to(cutin, { box: 1, duration: 0.5 }, 9.15);
  tl.to(cutin, { labelAlpha: 1, duration: 0.3 }, 9.3);
  tl.to(cutin, { x: 0.4, duration: 1.8, ease: "power1.inOut" }, 9.5);
  tl.to(cutin, { z: 18, duration: 2.6 }, 9.4);
  tl.to(state.trajectory, { curve: -1.7, duration: 1.2, ease: "power2.out" }, 10.0);
  // advisory: nói trước khi xe kia chạm vạch, giọng không dùng tông khẩn cấp
  tl.set(state.voice, { index: 1, tone: 0 }, 9.95);
  tl.to(state.voice, { alpha: 1, duration: 0.18 }, 9.95);
  tl.to(state.voice, { alpha: 0, duration: 0.3 }, 11.5);

  /* ---- vru · 12–16 ----
     Cảnh báo gắn với Ý ĐỊNH, không gắn với sự tồn tại. Người đứng trên lề chỉ
     được bám (khung xanh); chỉ khi bước về phía lòng đường — tức hướng vào
     đầu xe — khung mới chuyển đỏ và trajectory mới né. Cái cone đứng yên trên
     lề thì giữ khung xanh suốt: hệ thống thấy nó, nhưng nó không phải mối nguy. */
  tl.addLabel("vru", 12);
  tl.to(cutin, { alpha: 0, box: 0, labelAlpha: 0, duration: 0.5 }, 11.9);
  // xe tạt đầu đã đi, đường thông — quỹ đạo phải về thẳng trước đã
  tl.to(state.trajectory, { curve: 0, duration: 0.7 }, 11.95);
  tl.set(state.voice, { alpha: 0, status: 2, tone: 0 }, 11.9);

  // cone: vật cản tĩnh trên lề — chỉ theo dõi, và phải có nhãn để người xem
  // đọc được nó là gì thay vì đoán qua một chấm tròn
  tl.to(cone, { alpha: 1, duration: 0.35 }, 12.1);
  tl.to(cone, { box: 1, duration: 0.45 }, 12.25);
  tl.to(cone, { labelAlpha: 1, duration: 0.3 }, 12.4);
  tl.to(cone, { z: 6, duration: 1.6 }, 12.1);

  // người đi bộ: hiện trên lề, mới bám được nên khung xanh
  tl.to(ped, { alpha: 1, duration: 0.35 }, 12.0);
  tl.to(ped, { box: 1, duration: 0.5 }, 12.15);
  tl.to(ped, { labelAlpha: 1, duration: 0.3 }, 12.3);
  tl.to(ped, { z: 10, duration: 1.9 }, 12.0);

  // bước rời lề, hướng vào lòng đường
  tl.to(ped, { x: 2.2, duration: 1.5 }, 12.3);
  // vector chuyển động đã rõ là cắt vào quỹ đạo -> lúc này mới cảnh báo
  tl.set(ped, { tone: 2 }, 12.75);
  tl.to(state.trajectory, { curve: -1.3, duration: 0.7, ease: "power2.out" }, 12.75);
  tl.set(state.voice, { index: 2, tone: 2 }, 12.8);
  tl.to(state.voice, { alpha: 1, duration: 0.18 }, 12.8);

  /* ---- giữ câu VRU đủ lâu, rồi crossfade 0.6s về lane ---- */
  tl.to(state.voice, { alpha: 0, duration: 0.3 }, 14.4);
  tl.to(ped, { alpha: 0, box: 0, labelAlpha: 0, duration: 0.3 }, 14.5);
  tl.to(cone, { alpha: 0, box: 0, labelAlpha: 0, duration: 0.3 }, 14.5);
  tl.to(state.trajectory, { curve: 0, duration: 0.4 }, 14.5);

  /* ---- 6. ĐIỂM MÙ · xe tải (14.8–18.6) --------------------------------------
   * Xe chủ đổi thành xe tải và bắt đầu tạt sang phải. Xe máy nằm ở z âm — tức
   * NGANG VÀ SAU ca-bin — nên camera trước không hề thấy nó. Vùng gạch chéo vẽ
   * đúng phần khuất đó; hộp bao KHÔNG hiện, vì hệ không có gì để bám.
   */
  tl.addLabel("blindspot", 14.8);
  tl.set(state.ego, { kind: 1 }, 14.7);
  tl.set(state.voice, { alpha: 0, status: 3, tone: 1 }, 14.7);
  tl.to(state.blind, { alpha: 1, duration: 0.5 }, 14.9);
  tl.set(bike, { x: 3.4, z: 2.2 }, 14.9);
  tl.to(bike, { alpha: 1, duration: 0.4 }, 14.9);
  tl.to(bike, { z: 7.4, duration: 2.6, ease: "none" }, 15.2);
  // xe tải bắt đầu chuyển làn về phía xe máy — mối nguy nằm ở chỗ không thấy
  tl.to(state.ego, { swerve: 1.5, duration: 1.6, ease: "power1.inOut" }, 16.2);
  tl.to(state.trajectory, { curve: 1.4, duration: 1.6, ease: "power1.inOut" }, 16.2);
  tl.set(state.trajectory, { tone: 1 }, 16.6);
  tl.to(state.hud, { riskAlpha: 1, duration: 0.3 }, 16.6);

  /* ---- 7. TÀI XẾ RỜI MẮT · xe con (18.6–22) ---------------------------------
   * Xe phía trước chậm dần trong khi xe chủ giữ nguyên tốc độ. Không có gì
   * trong khung báo rằng tài xế đang nhìn chỗ khác — đó chính là vấn đề, và là
   * lý do cảnh này cần một camera hướng tài xế mà bản đang chạy không có.
   */
  tl.addLabel("distract", 18.6);
  tl.to(state.blind, { alpha: 0, duration: 0.4 }, 18.3);
  tl.to(bike, { alpha: 0, duration: 0.3 }, 18.3);
  tl.to(state.ego, { swerve: 0, duration: 0.6 }, 18.3);
  tl.to(state.trajectory, { curve: 0, duration: 0.6 }, 18.3);
  tl.set(state.ego, { kind: 0 }, 18.5);
  tl.set(state.trajectory, { tone: 0 }, 18.5);
  tl.to(state.hud, { riskAlpha: 0, duration: 0.3 }, 18.4);
  tl.set(slow, { x: 0, z: 44, tone: 0, box: 0 }, 18.5);
  tl.set(state.voice, { alpha: 0, status: 5, tone: 0 }, 18.5);
  tl.to(slow, { alpha: 1, duration: 0.4 }, 18.6);
  tl.to(slow, { box: 1, duration: 0.35 }, 19.0);
  tl.to(slow, { labelAlpha: 1, duration: 0.3 }, 19.1);
  // khoảng cách đóng lại đều đặn: xe trước phanh, xe chủ chưa phản ứng
  tl.to(slow, { z: 13, duration: 2.4, ease: "power1.in" }, 19.2);
  tl.set(slow, { tone: 2 }, 20.5);
  tl.set(state.trajectory, { tone: 1 }, 20.5);
  tl.to(state.trajectory, { length: 0.5, duration: 0.7, ease: "power2.out" }, 20.5);
  tl.to(state.hud, { riskAlpha: 1, duration: 0.3 }, 20.5);
  // Câu này CÓ THẬT trong alert_copy.py. Hệ không biết tài xế đang nhìn đâu,
  // nhưng cảnh báo hướng trước vẫn nổ — và đó mới là thứ cứu tình huống này.
  tl.set(state.voice, { index: 3, tone: 2 }, 20.55);
  tl.to(state.voice, { alpha: 1, duration: 0.18 }, 20.55);
  tl.to(state.voice, { alpha: 0, duration: 0.3 }, 21.6);

  /* ---- 8. MƯA LỚN · xe tải (22–25.6) ----------------------------------------
   * Màn mưa che phần xa trước tiên. Vạch kẻ ở xa mất theo, chất lượng làn tụt,
   * và cổng `lane_quality_min` khoá cảnh báo lệch làn — hành vi này CÓ THẬT
   * trong risk.py, nên đây là cảnh duy nhất trong ba cảnh mới được gắn nhãn
   * đang chạy.
   */
  tl.addLabel("weather", 22.0);
  tl.to(slow, { alpha: 0, box: 0, labelAlpha: 0, duration: 0.4 }, 21.7);
  tl.to(state.hud, { riskAlpha: 0, duration: 0.3 }, 21.7);
  tl.set(state.ego, { kind: 1 }, 21.9);
  tl.set(state.trajectory, { tone: 0 }, 21.9);
  tl.to(state.trajectory, { length: 1, duration: 0.5 }, 21.9);
  tl.set(state.veil, { kind: 0 }, 21.9);
  tl.set(state.voice, { alpha: 0, status: 6, tone: 1 }, 21.9);
  tl.to(state.veil, { alpha: 1, duration: 1.2 }, 22.0);

  // (a) Nhánh LÀN hỏng trước: quỹ đạo co lại và nhạt đi theo đúng cái mất đi
  //     là tầm nhìn xa. Cổng chất lượng làn khoá cảnh báo lệch làn.
  tl.to(state.trajectory, { length: 0.34, duration: 1.2, ease: "power1.inOut" }, 22.4);
  tl.to(state.trajectory, { alpha: 0.4, duration: 1.0 }, 22.6);

  // (b) Nhánh VẬT THỂ thì KHÔNG hỏng theo. Xe phía trước hiện ra rất mờ trong
  //     màn sương — mờ vì nó bị màn sương phủ lên, đúng như mắt người thấy —
  //     nhưng hộp bao vẽ SAU màn sương nên vẫn sắc nét. Chính khoảng cách giữa
  //     hai thứ đó là lợi ích của hệ trong điều kiện này.
  tl.set(lead, { x: 0, z: 40, tone: 0, box: 0, labelAlpha: 0 }, 23.4);
  tl.to(lead, { alpha: 1, duration: 1.0 }, 23.5);
  tl.to(lead, { z: 15, duration: 4.0, ease: "power1.in" }, 23.6);
  tl.to(lead, { box: 1, duration: 0.4 }, 24.6);
  tl.to(lead, { labelAlpha: 1, duration: 0.3 }, 24.8);
  tl.set(state.voice, { status: 6 }, 24.6);

  // (c) Khi xe đã quá gần: cảnh báo va chạm nổ, dù làn vẫn đang bị khoá.
  tl.set(lead, { tone: 2 }, 27.0);
  tl.set(state.trajectory, { tone: 1 }, 27.0);
  tl.to(state.hud, { riskAlpha: 1, duration: 0.3 }, 27.0);
  tl.set(state.voice, { index: 0, tone: 2 }, 27.05);
  tl.to(state.voice, { alpha: 1, duration: 0.18 }, 27.05);
  tl.to(state.voice, { alpha: 0, duration: 0.3 }, 28.85);

  /* ---- vòng lặp: mờ về rồi dựng lại trạng thái cảnh 1 --------------------- */
  tl.to(state, { fade: 0, duration: 0.35, ease: "power1.in" }, 29.1);
  tl.set(state.veil, { alpha: 0, kind: 0 }, 29.5);
  tl.set(state.ego, { kind: 0, swerve: 0 }, 29.5);
  tl.set(state.blind, { alpha: 0 }, 29.5);
  tl.set(lead, { alpha: 0, box: 0, labelAlpha: 0, z: 48, tone: 0 }, 29.5);
  tl.set(state.hud, { riskAlpha: 0 }, 29.5);
  tl.set(state.voice, { alpha: 0, status: 0, tone: 0 }, 29.5);
  tl.set(state.trajectory, { curve: 0, length: 1, tone: 0, alpha: 1 }, 29.5);
  tl.to(state, { fade: 1, duration: 0.35, ease: "power1.out" }, 29.5);

  /* ---- caption crossfade ở mỗi mốc cảnh ---- */
  const marks = [0, 3, 6, 9, 12, 14.8, 18.6, 22.0];
  for (let i = 1; i < marks.length; i++) {
    tl.to(state.captions[i - 1], { alpha: 0, duration: 0.35 }, marks[i] - 0.2);
    tl.to(state.captions[i], { alpha: 1, duration: 0.35 }, marks[i] + 0.05);
  }
  tl.to(state.captions[7], { alpha: 0, duration: 0.25 }, 29.25);
  tl.to(state.captions[0], { alpha: 1, duration: 0.25 }, 29.55);

  return tl;
}

export default function AdasHero() {
  const rootRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const captionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const labelRefs = useRef<(HTMLDivElement | null)[]>([]);
  const riskRef = useRef<HTMLDivElement>(null);
  const voiceRef = useRef<HTMLDivElement>(null);
  const voiceIdleRef = useRef<HTMLDivElement>(null);
  const voiceStatusRef = useRef<HTMLSpanElement>(null);
  const voiceLineRef = useRef<HTMLDivElement>(null);
  const voiceTextRef = useRef<HTMLSpanElement>(null);
  const barRefs = useRef<(HTMLSpanElement | null)[]>([]);

  useGSAP(
    () => {
      const root = rootRef.current!;
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext("2d", { alpha: false })!;
      const state = createState();
      let palette: Palette = readPalette(root);
      let W = 0;
      let H = 0;
      let labelCharW = 8;

      const resize = () => {
        const rect = root.getBoundingClientRect();
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = Math.max(1, Math.round(rect.width));
        H = Math.max(1, Math.round(rect.height));
        canvas.width = Math.round(W * dpr);
        canvas.height = Math.round(H * dpr);
        canvas.style.width = `${W}px`;
        canvas.style.height = `${H}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        palette = readPalette(root);
        const probe = labelRefs.current[0];
        if (probe) {
          const fs = parseFloat(getComputedStyle(probe).fontSize) || 11;
          labelCharW = fs * LABEL_CHAR_EM;
        }
        invalidateGradients();
      };
      resize();

      const ro = new ResizeObserver(resize);
      ro.observe(root);

      /** Lớp chữ DOM — đọc state, chiếu toạ độ, ghi transform/opacity. */
      const syncOverlay = () => {
        for (let i = 0; i < CAPTIONS.length; i++) {
          const node = captionRefs.current[i];
          if (node) node.style.opacity = String(state.captions[i].alpha * state.fade);
        }
        state.boxes.forEach((actor, i) => {
          const node = labelRefs.current[i];
          if (!node) return;
          const a = actor.labelAlpha * actor.alpha * state.fade;
          node.style.opacity = String(a);
          if (a <= 0.001) return;
          const text = `${actor.label.toUpperCase()} · ${proximityLabel(actor.z)}`;
          if (node.textContent !== text) node.textContent = text;
          const f = footprint(actor, W, H);
          const pad = Math.max(3, f.w * 0.12);
          // Vật thể sát mép phải đẩy nhãn ra ngoài khung và bị cắt mất chữ.
          const limit = Math.max(8, W - text.length * labelCharW - 8);
          const x = Math.min(Math.max(f.x - pad, 8), limit);
          node.style.transform = `translate3d(${Math.round(x)}px, ${Math.round(f.y - pad)}px, 0) translateY(-100%)`;
          node.dataset.tone = String(actor.tone);
        });
        const risk = riskRef.current;
        if (risk) {
          const a = state.hud.riskAlpha * state.fade;
          risk.style.opacity = String(a);
        }
        const voice = voiceRef.current;
        if (voice) {
          const spoken = state.voice.alpha;
          voice.style.opacity = String(state.fade);
          voice.dataset.tone = String(state.voice.tone);
          const idle = voiceIdleRef.current;
          if (idle) idle.style.opacity = String(1 - spoken);
          const status = voiceStatusRef.current;
          if (status) {
            const text = VOICE_STATUS[state.voice.status];
            if (status.textContent !== text) status.textContent = text;
          }
          const line = voiceLineRef.current;
          if (line) line.style.opacity = String(spoken);
          if (spoken > 0.001) {
            const text = VOICE[state.voice.index];
            const slot = voiceTextRef.current;
            if (slot && slot.textContent !== text) slot.textContent = text;
            for (let i = 0; i < barRefs.current.length; i++) {
              const bar = barRefs.current[i];
              if (!bar) continue;
              // worldOffset chạy 0→306 trong 16s; sóng âm chỉ là chỉ báo trực quan.
              const s =
                0.28 + 0.72 * Math.abs(Math.sin(state.worldOffset * 2.2 + i * 1.7));
              bar.style.transform = `scaleY(${s.toFixed(3)})`;
            }
          }
        }
      };

      const mm = gsap.matchMedia();

      mm.add(
        {
          reduced: "(prefers-reduced-motion: reduce)",
          full: "(prefers-reduced-motion: no-preference)",
        },
        (self) => {
          // --- Giảm chuyển động: một khung tĩnh của cảnh 1, không rAF, không loop.
          if (self.conditions!.reduced) {
            const tl = buildTimeline(state);
            tl.pause(0.6); // đứng yên trong `lane`
            draw(ctx, state, W, H, palette);
            syncOverlay();
            const redraw = () => {
              gsap.ticker.wake();
              resize();
              tl.pause(0.6);
              draw(ctx, state, W, H, palette);
              syncOverlay();
              gsap.ticker.sleep();
            };
            ro.disconnect();
            const ro2 = new ResizeObserver(redraw);
            ro2.observe(root);
            // Không còn gì để chạy: ru ticker của GSAP ngủ để rAF thôi quay.
            gsap.ticker.sleep();
            return () => {
              ro2.disconnect();
              tl.kill();
              gsap.ticker.wake();
            };
          }

          // --- Đầy đủ: một timeline + một vòng rAF riêng.
          const tl = buildTimeline(state);
          // Canvas `alpha: false` khởi tạo với nền đen. Vẽ ngay một khung trước
          // rAF đầu tiên để không có flash đen (và để prerender/headless nhận
          // được trạng thái hợp lệ ngay cả khi animation frame bị trì hoãn).
          draw(ctx, state, W, H, palette);
          syncOverlay();
          performance.mark("hero-first-frame");
          if (import.meta.env.DEV) {
            const w = window as unknown as Record<string, unknown>;
            w.__heroTl = tl;
            w.__heroState = state;
          }

          let raf = 0;
          let running = false;
          const frame = () => {
            raf = requestAnimationFrame(frame);
            draw(ctx, state, W, H, palette);
            syncOverlay();
          };
          const start = () => {
            if (running) return;
            running = true;
            tl.play();
            raf = requestAnimationFrame(frame);
          };
          const stop = () => {
            if (!running) return;
            running = false;
            tl.pause();
            cancelAnimationFrame(raf);
          };

          let onScreen = true;
          const evaluate = () => {
            if (onScreen && document.visibilityState === "visible") start();
            else stop();
          };

          const io = new IntersectionObserver(
            ([entry]) => {
              onScreen = entry.isIntersecting;
              evaluate();
            },
            { threshold: 0.01 },
          );
          io.observe(root);
          document.addEventListener("visibilitychange", evaluate);
          evaluate();

          return () => {
            io.disconnect();
            document.removeEventListener("visibilitychange", evaluate);
            cancelAnimationFrame(raf);
            tl.kill();
            if (import.meta.env.DEV) {
              const w = window as unknown as Record<string, unknown>;
              delete w.__heroTl;
              delete w.__heroState;
            }
          };
        },
      );

      return () => {
        ro.disconnect();
        mm.revert();
      };
    },
    { scope: rootRef },
  );

  return (
    <div ref={rootRef} className="absolute inset-0 overflow-hidden">
      <canvas ref={canvasRef} className="block h-full w-full" aria-hidden="true" />

      {/* Lớp chữ DOM đè trên canvas — không có text nào vẽ trong canvas */}
      <div className="pointer-events-none absolute inset-0">
        {/* nhãn detection bám theo khung bao */}
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            ref={(el) => {
              labelRefs.current[i] = el;
            }}
            data-tone="0"
            style={{ opacity: 0 }}
            className="absolute left-0 top-0 whitespace-nowrap pb-1 font-mono text-[clamp(0.625rem,0.58vw,0.85rem)] leading-none tracking-[0.14em] text-signal will-change-transform data-[tone='1']:text-state-alert data-[tone='2']:text-state-alert"
          />
        ))}

        {/* Proxy rủi ro theo ảnh; không tuyên bố TTC/khoảng cách vật lý. */}
        <div
          ref={riskRef}
          style={{ opacity: 0 }}
          className="absolute right-[clamp(1.5rem,3.2vw,5.5rem)] top-1/2 rounded-sm border border-state-alert/40 px-[clamp(0.6rem,0.9vw,1.2rem)] py-1.5 font-mono text-[clamp(0.6875rem,0.62vw,0.9rem)] tracking-[0.14em] text-state-alert"
        >
          NGUY CƠ CAO · ƯỚC TÍNH THEO ẢNH
        </div>

        {/* caption từng cảnh */}
        <div className="absolute bottom-[clamp(7.5rem,20vw,9rem)] left-[clamp(1.5rem,3.2vw,5.5rem)] md:bottom-[clamp(2rem,3vw,4rem)]">
          {CAPTIONS.map((cap, i) => (
            <div
              key={cap.text}
              ref={(el) => {
                captionRefs.current[i] = el;
              }}
              style={{ opacity: i === 0 ? 1 : 0 }}
              className="absolute left-0 top-0 flex items-center gap-3 whitespace-nowrap font-mono text-[clamp(0.6875rem,0.62vw,0.9rem)] tracking-[0.2em] text-text-mid"
            >
              <span
                className={
                  "inline-block size-1.5 rounded-full " +
                  (cap.danger ? "bg-state-alert" : "bg-signal")
                }
              />
              <span className="text-text-low">{cap.ego}</span>
              {cap.text.toUpperCase()}
              {/* Cảnh cần cảm biến chưa có phải tự khai báo ngay tại chỗ —
                  không để người xem tưởng hệ đã làm được việc này. */}
              {!cap.live && (
                <span className="border border-border px-2 py-0.5 text-text-low">
                  KỊCH BẢN MỤC TIÊU
                </span>
              )}
            </div>
          ))}
        </div>

        {/* ---- kênh giọng nói ----------------------------------------------
            Luôn hiện, vì trạng thái IM LẶNG cũng là một tuyên bố về hệ thống:
            Alert Governor chỉ mở loa khi có sự kiện đủ mức, không kêu suốt. */}
        <div
          ref={voiceRef}
          data-tone="0"
          className="absolute bottom-[clamp(1.35rem,3vw,4rem)] left-[clamp(1.5rem,3.2vw,5.5rem)] right-[clamp(1.5rem,3.2vw,5.5rem)] flex flex-col items-start gap-2 text-signal md:left-auto md:max-w-[min(62vw,44rem)] md:items-end data-[tone='1']:text-state-alert data-[tone='2']:text-state-alert"
        >
          <div className="font-mono text-[clamp(0.625rem,0.58vw,0.85rem)] leading-none tracking-[0.2em] text-text-low">
            MÔ PHỎNG KÊNH LOA · PIPER TIẾNG VIỆT · NGOẠI TUYẾN
          </div>

          <div className="relative h-[clamp(2.75rem,7vw,3.5rem)] w-full md:h-[clamp(1.35rem,1.9vw,2.25rem)]">
            {/* im lặng */}
            <div
              ref={voiceIdleRef}
              className="absolute left-0 top-1/2 flex -translate-y-1/2 items-center gap-3 whitespace-nowrap font-mono text-[clamp(0.625rem,0.58vw,0.85rem)] tracking-[0.12em] text-text-low md:left-auto md:right-0"
            >
              <span className="inline-block size-1.5 shrink-0 rounded-full bg-signal/50" />
              <span ref={voiceStatusRef}>{VOICE_STATUS[0]}</span>
            </div>

            {/* đang phát */}
            <div
              ref={voiceLineRef}
              style={{ opacity: 0 }}
              className="absolute left-0 top-1/2 flex max-w-full -translate-y-1/2 items-center gap-3 md:left-auto md:right-0"
            >
              <span className="flex h-[clamp(0.8rem,1.1vw,1.3rem)] items-center gap-[2px]">
                {BARS.map((i) => (
                  <span
                    key={i}
                    ref={(el) => {
                      barRefs.current[i] = el;
                    }}
                    className="block h-full w-[2px] origin-center rounded-full bg-current will-change-transform"
                  />
                ))}
              </span>
              <span className="text-[clamp(0.875rem,1.15vw,1.65rem)] font-light leading-tight">
                “<span ref={voiceTextRef} />”
              </span>
              <span className="hidden shrink-0 font-mono text-[clamp(0.6rem,0.52vw,0.75rem)] tracking-[0.16em] sm:inline">
                ĐANG PHÁT QUA LOA
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
