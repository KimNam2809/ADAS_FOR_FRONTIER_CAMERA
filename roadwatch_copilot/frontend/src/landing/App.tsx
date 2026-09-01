import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import AdasHero from "./components/AdasHero";
import FullscreenToggle from "./components/FullscreenToggle";
import VoiceList from "./components/VoiceList";
import { ActiveStack, ArchitectureDiagram, GateChart, GateLedger, LatencyChart, MediaBand } from "./components/Figures";

gsap.registerPlugin(useGSAP);

const REPO = "https://github.com/AI20K-Build-Phase-Cohort-3/P-162";
const CONFIGURED_DEMO_URL = import.meta.env.VITE_DEMO_URL?.trim();
const DEMO_URL = CONFIGURED_DEMO_URL || "/app/";
const HAS_TECHNICAL_DEMO = true;

const NAV_ITEMS = [
  ["Kiến trúc", "#architecture"],
  ["Nhận thức", "#perception"],
  ["Mô hình 3D", "#model3d"],
  ["Bằng chứng", "#evidence"],
];

/**
 * Catalog vNext — banner và loa cùng dùng canonical message. `slug` trỏ tới
 * file trong public/voice, do tools/gen_voice.py sinh bằng chính Piper của
 * web_demo; `seconds` là độ dài thật của file đó.
 */
const ALERTS = [
  { slug: "fcw", event: "Va chạm phía trước · nguy cấp", line: "Cảnh báo va chạm", channel: "BÍP KHẨN + GIỌNG NÓI", mode: "voice" as const, danger: true, seconds: 0.78 },
  { slug: "vru", event: "Người đi bộ cắt vào quỹ đạo", line: "Người đi bộ phía trước; giảm tốc độ.", channel: "GIỌNG NÓI", mode: "voice" as const, danger: true, seconds: 1.56 },
  { slug: "cutin", event: "Xe nhập làn từ bên phải", line: "Ô tô nhập làn từ bên phải. Hãy chú ý.", channel: "GIỌNG NÓI", mode: "voice" as const, danger: false, seconds: 1.87 },
  { slug: "cross", event: "Cắt ngang trước mũi xe", line: "Xe máy cắt ngang từ bên trái.", channel: "GIỌNG NÓI", mode: "voice" as const, danger: false, seconds: 1.46 },
  { slug: "brake", event: "Xe trước giảm tốc nhanh", line: "Ô tô phía trước đang giảm tốc. Hãy chú ý.", channel: "GIỌNG NÓI", mode: "voice" as const, danger: false, seconds: 1.96 },
  { slug: "ldw", event: "Lệch làn đã xác nhận", line: "Cảnh báo lệch làn bên trái.", channel: "GIỌNG NÓI", mode: "voice" as const, danger: false, seconds: 1.4 },
  { slug: "speed", event: "Biển giới hạn tốc độ đã gắn làn", line: "Giới hạn 80 ki-lô-mét/giờ phía trước.", channel: "GIỌNG NÓI", mode: "voice" as const, danger: false, seconds: 2.05 },
  { slug: null, event: "Biển cấm đi vào chưa rõ hướng", line: "Biển cấm đi vào; kiểm tra hướng.", channel: "HUD · CHỜ XÁC NHẬN HƯỚNG", mode: "conditional" as const, danger: false, seconds: 0 },
  { slug: null, event: "Nhiều biển tốc độ, chưa gắn được làn", line: "Nhiều biển giới hạn tốc độ; xem làn mình.", channel: "HUD · KHÔNG ĐỌC SỐ", mode: "hud" as const, danger: false, seconds: 0 },
];

/**
 * Hai khung hình cùng chỉ số, chạy qua hai bộ model khác nhau. Số vật thể lấy
 * trực tiếp từ đầu ra: index.json của tools/render_webdemo_frames.py và
 * tv3_layer1.jsonl của tools/render_layer1v2_frames.py.
 */
const COMPARE = [
  {
    time: "13:26:11",
    note: "khung 1545 — đoạn có giá long môn và cụm biển báo bên phải",
    panes: [
      {
        src: "/landing/evidence/tv3-shipping-a.jpg",
        alt: "Khung dashcam với ba hộp bao xe và vạch kẻ đứt quãng do bộ model đang chạy sinh ra",
        label: "ĐANG CHẠY",
        stack: "yolo11n · YOLOP",
        found: "3 vật thể · 0 biển báo",
        shipping: true,
      },
      {
        src: "/landing/evidence/tv3-research-a.jpg",
        alt: "Cùng khung hình, dòng nghiên cứu bắt được nhiều xe, người đi bộ và hai biển báo",
        label: "NGHIÊN CỨU",
        stack: "yolo26s · YOLOPv2",
        found: "18 vật thể · 2 biển báo",
        shipping: false,
      },
    ],
  },
  {
    time: "13:26:24",
    note: "khung 1920 — đường thoáng, hai xe cùng làn",
    panes: [
      {
        src: "/landing/evidence/tv3-shipping-b.jpg",
        alt: "Khung dashcam đường thoáng với bốn hộp bao xe",
        label: "ĐANG CHẠY",
        stack: "yolo11n · YOLOP",
        found: "4 vật thể",
        shipping: true,
      },
      {
        src: "/landing/evidence/tv3-research-b.jpg",
        alt: "Cùng khung hình, dòng nghiên cứu bắt thêm xe ở xa và người đi xe máy bên phải",
        label: "NGHIÊN CỨU",
        stack: "yolo26s · YOLOPv2",
        found: "13 vật thể",
        shipping: false,
      },
    ],
  },
];

/** RW-05 qua bốn lần siết ngưỡng, 21/08/2026. Nguồn: web_demo/evaluation/. */
/**
 * Giá phải trả của dòng nghiên cứu, lấy từ README và report của
 * training/layer1_pipeline_v2. Độ phủ làn là số của chính pipeline đó đo trên
 * test_video3 — lý do thật khiến nó chưa thay được bản đang chạy, và nó không
 * có lợi cho dòng nghiên cứu.
 */
/**
 * Hai ảnh đêm chạy qua layer1_pipeline_v2. Số lấy từ jsonl và report của chính
 * lần chạy đó — xem tools/render_layer1v2_frames.py.
 */
const NIGHT = [
  {
    src: "/landing/evidence/night-marked.jpg",
    alt: "Đường đêm có vạch kẻ rõ: sáu hộp bao phương tiện, dải vạch kẻ đỏ bám hai bên làn",
    label: "ĐƯỜNG CÓ VẠCH",
    objects: "6 vật thể",
    lane: "làn 65% — nhưng 60% là giữ tạm",
    laneOk: true,
  },
  {
    src: "/landing/evidence/night-vn.jpg",
    alt: "Giao thông hỗn hợp ban đêm ở Việt Nam: mười ba hộp bao gồm ô tô, xe máy và người đi bộ, không có vạch kẻ nào",
    label: "HỖN HỢP · VIỆT NAM",
    objects: "13 vật thể · 4 người · 3 xe máy",
    lane: "làn 0%",
    laneOk: false,
  },
];

const RESEARCH_COST = [
  {
    label: "ĐỘ PHỦ LÀN",
    value: "38.9% so với 69.9%",
    note: "đo trên chính test_video3",
  },
  {
    label: "NGÂN SÁCH ORIN",
    value: "chỉ lọt ở ≤ 480px, ≤ 10 Hz",
    note: "ngoại suy, chưa đo trên Orin thật",
  },
];

const RW05 = [
  { time: "15:36", recall: 0.9444, fp: 15.4639, dir: 0.5882, dup: 0.2212 },
  { time: "16:11", recall: 0.4444, fp: 1.5464, dir: 1.0, dup: 0.0367 },
  { time: "16:28", recall: 0.4444, fp: 0.0, dir: 1.0, dup: 0.0326 },
  { time: "17:07", recall: 0.4444, fp: 0.0, dir: 1.0, dup: 0.0345 },
];

/** Điều hướng trong chân trang — cùng nguồn với thanh nav, thêm mục an toàn. */
const FOOTER_NAV = [
  ["Kiến trúc", "#architecture"],
  ["Nhận thức", "#perception"],
  ["Mô hình 3D", "#model3d"],
  ["Bằng chứng", "#evidence"],
  ["Cảnh báo giọng nói", "#voice"],
];

const STATUS = [
  {
    label: "MỨC SẴN SÀNG",
    value: "R0 · TECHNICAL PoC",
    body: "Demo nghiên cứu có bằng chứng; chưa được chứng nhận cho xe thật.",
  },
  {
    label: "LÕI CẢNH BÁO",
    value: "OFFLINE · EDGE-FIRST",
    body: "Perception, rule engine và Piper không cần cloud trong đường cảnh báo.",
  },
  {
    label: "BASELINE ĐANG DÙNG",
    value: "YOLO11n · YOLOP",
    body: "Biển báo Phase 2 và Piper Việt; model mới chỉ thay khi vượt safety gate.",
  },
  {
    label: "RANH GIỚI",
    value: "WARNING-ONLY",
    body: "Không gửi lệnh phanh, ga, vô lăng hay ghi dữ liệu lên ECU.",
  },
];

/** Lề ngang và nhịp dọc co theo bề rộng màn, để trang lấp đầy mọi kích thước. */
const PAD = "px-[clamp(1.5rem,3.2vw,5.5rem)]";
const MICRO = "text-[clamp(0.6875rem,0.62vw,0.9rem)]";
const H2 = "text-[clamp(1.75rem,3.3vw,4.5rem)] font-bold leading-[1.02] tracking-[-0.025em]";
const BODY = "text-[clamp(1rem,1.22vw,1.85rem)] font-light leading-relaxed text-text-mid";
const SECTION = "py-[clamp(3.5rem,5.5vw,9rem)]";

export default function App() {
  const rootRef = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(
        {
          reduced: "(prefers-reduced-motion: reduce)",
          full: "(prefers-reduced-motion: no-preference)",
        },
        (self) => {
          const targets = gsap.utils.toArray<HTMLElement>("[data-reveal]");
          // Giảm chuyển động: hiện thẳng, không nạp cả ScrollTrigger.
          if (self.conditions!.reduced) {
            gsap.set(targets, { opacity: 1, y: 0 });
            return;
          }
          gsap.registerPlugin(ScrollTrigger);
          // opacity + transform: không chạm layout nên không sinh CLS.
          gsap.set(targets, { opacity: 0, y: 26 });
          ScrollTrigger.batch(targets, {
            start: "top 86%",
            once: true,
            onEnter: (batch) =>
              gsap.to(batch, {
                opacity: 1,
                y: 0,
                duration: 0.7,
                ease: "power2.out",
                stagger: 0.1,
                overwrite: true,
              }),
          });
        },
      );
      return () => mm.revert();
    },
    { scope: rootRef },
  );

  return (
    <main ref={rootRef} className="min-h-screen bg-background text-foreground">
      {/* ==================== HERO ==================== */}
      <section
        id="hero"
        className="relative flex h-screen w-full flex-col overflow-hidden"
      >
        <AdasHero />

        <header className={`relative z-20 flex items-center justify-between gap-8 pr-[clamp(5rem,7vw,8rem)] ${PAD} pt-[clamp(1.5rem,2.4vw,3rem)]`}>
          <a
            href="#hero"
            aria-label="RoadWatch Copilot — về đầu trang"
            className="flex shrink-0 items-center gap-[clamp(0.55rem,0.8vw,0.9rem)] text-[clamp(1.05rem,1.3vw,1.85rem)] tracking-[-0.02em] text-foreground no-underline"
          >
            <img
              src="/logo.png"
              alt=""
              width="1254"
              height="1254"
              className="size-[clamp(2.75rem,4vw,4rem)] shrink-0 object-contain"
            />
            <span className="whitespace-nowrap">
              <strong className="font-bold">RoadWatch</strong>
              <span className="font-light text-text-mid"> Copilot</span>
            </span>
          </a>

          <nav aria-label="Điều hướng chính" className="hidden items-center gap-[clamp(1rem,1.6vw,2.25rem)] lg:flex">
            {NAV_ITEMS.map(([label, href]) => (
              <a
                key={href}
                href={href}
                className={`font-mono ${MICRO} tracking-[0.12em] text-text-mid no-underline transition-colors hover:text-signal`}
              >
                {label.toUpperCase()}
              </a>
            ))}
            <a
              href={DEMO_URL}
              className={`border border-signal px-4 py-2 font-mono ${MICRO} tracking-[0.12em] text-signal no-underline transition-colors hover:bg-signal hover:text-background`}
            >
              {HAS_TECHNICAL_DEMO ? "MỞ DEMO" : "XEM BẰNG CHỨNG"}
            </a>
          </nav>
        </header>

        <div className={`pointer-events-none relative z-10 mt-[clamp(3.5rem,10vh,8rem)] ${PAD}`}>
          <div className="max-w-[min(34rem,82vw)]">
            <div className={`font-mono ${MICRO} tracking-[0.18em] text-text-low`}>
              EDGE AI · CẢNH BÁO TIẾNG VIỆT · WARNING-ONLY
            </div>
            <h1 className="mt-4 text-[clamp(2.55rem,5.2vw,6.5rem)] font-light leading-[0.9] tracking-[-0.035em]">
              Nhìn đường.
              <br />
              <span className="font-bold text-signal">Nói đúng lúc.</span>
            </h1>
            <p className="mt-5 max-w-[36ch] text-[clamp(0.95rem,1.12vw,1.4rem)] font-light leading-relaxed text-text-mid">
              Trợ lý cảnh báo cho camera trước, hiểu giao thông hỗn hợp
              Việt Nam và phát câu nói ngay trên xe mà không cần mạng.
            </p>
            <div className="pointer-events-auto mt-7 flex flex-wrap items-center gap-4">
              <a
                href="#architecture"
                className={`border border-signal bg-signal px-5 py-3 font-mono ${MICRO} tracking-[0.12em] text-background no-underline transition-opacity hover:opacity-85`}
              >
                KHÁM PHÁ HỆ THỐNG
              </a>
              <a
                href={DEMO_URL}
                className={`border border-border bg-background/70 px-5 py-3 font-mono ${MICRO} tracking-[0.12em] text-foreground no-underline transition-colors hover:border-signal hover:text-signal`}
              >
                {HAS_TECHNICAL_DEMO ? "MỞ DEMO KỸ THUẬT →" : "XEM BẰNG CHỨNG →"}
              </a>
            </div>
          </div>
        </div>

        <FullscreenToggle />
      </section>

      {/* ==================== TUYÊN NGÔN ==================== */}
      <section
        id="statement"
        className={`${PAD} pb-[clamp(3rem,5vw,7rem)] pt-[clamp(3.5rem,6vw,9rem)]`}
      >
        <h2 className="max-w-[19ch] font-light leading-[0.92] tracking-[-0.03em] text-[clamp(2.5rem,7.4vw,8rem)]">
          Từ camera tới <span className="font-bold text-signal">bằng chứng</span>
          <br />
          và <span className="font-bold text-signal">một câu nói</span>
        </h2>
        <p className="mt-[clamp(1.25rem,1.8vw,2.5rem)] max-w-[36ch] text-[clamp(1.125rem,1.45vw,2.125rem)] font-light leading-snug text-text-mid">
          Nhận thức thời gian thực cho xe chạy đường Việt Nam — làn, phương
          tiện, người đi bộ, biển báo — rồi cảnh báo bằng một câu tiếng Việt
          ngắn, phát ngay trên xe, không cần mạng.
        </p>
      </section>

      {/* ==================== TRẠNG THÁI SẢN PHẨM ==================== */}
      <section aria-label="Trạng thái sản phẩm" className={`border-t border-border ${PAD}`}>
        <div className="grid md:grid-cols-2 xl:grid-cols-4">
          {STATUS.map((item, index) => (
            <div
              key={item.label}
              data-reveal
              className={`py-[clamp(1.5rem,2.4vw,3rem)] md:px-6 ${index > 0 ? "border-t border-border md:border-l md:border-t-0" : ""}`}
            >
              <div className={`font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
                {item.label}
              </div>
              <div className="mt-3 font-mono text-[clamp(1rem,1.2vw,1.45rem)] text-signal">
                {item.value}
              </div>
              <p className={`mt-3 ${MICRO} leading-relaxed text-text-mid`}>{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ==================== DẢI: ĐẦU VÀO ==================== */}
      <MediaBand
        src="/landing/evidence/camera-mount.jpg"
        alt="Camera hành trình gắn sau kính lái, nhìn từ trong khoang xe"
        bg="var(--band-night)"
        position="72% 60%"
      >
        <div data-reveal className={`font-mono ${MICRO} tracking-[0.18em] text-on-dark-mid`}>
          ĐẦU VÀO
        </div>
        <h2 data-reveal className={`mt-3 max-w-[15ch] ${H2} text-on-dark`}>
          Một camera, không thêm cảm biến
        </h2>
        <p data-reveal className="mt-6 max-w-[40ch] text-[clamp(1rem,1.22vw,1.85rem)] font-light leading-relaxed text-on-dark-mid">
          Toàn bộ nhận thức dựng từ một luồng hình 30 khung mỗi giây. Không
          radar, không lidar, không cần sửa gì trên xe.
        </p>
      </MediaBand>

      {/* ==================== KIẾN TRÚC ==================== */}
      <section id="architecture" className={`border-t border-border ${PAD} ${SECTION}`}>
        <div data-reveal className={`font-mono ${MICRO} tracking-[0.18em] text-text-low`}>
          KIẾN TRÚC
        </div>
        <h2 data-reveal className={`mt-3 max-w-[18ch] ${H2}`}>
          Bốn tầng, một chiều dữ liệu
        </h2>
        <p data-reveal className={`mt-5 max-w-[46ch] ${BODY}`}>
          Đường ra quyết định khẩn cấp nằm trọn ở Tầng 3 và không đi qua mô hình
          ngôn ngữ. Tầng 4 chạy nền, chỉ chỉnh ngưỡng và nói.
        </p>
        <div data-reveal className="mt-[clamp(2.5rem,4vw,5rem)] overflow-x-auto">
          <div className="min-w-[680px]">
            <ArchitectureDiagram />
          </div>
        </div>
      </section>

      {/* ==================== NHẬN THỨC ==================== */}
      <section id="perception" className={`border-t border-border ${PAD} ${SECTION}`}>
        <div data-reveal className={`font-mono ${MICRO} tracking-[0.18em] text-text-low`}>
          TẦNG 1 · NHẬN THỨC
        </div>
        <h2 data-reveal className={`mt-3 max-w-[20ch] ${H2}`}>
          Bốn mô hình rời, một vòng lặp
        </h2>

        <figure data-reveal className="m-0 mt-[clamp(2.5rem,4vw,5rem)]">
          <img
            src="/landing/evidence/tv3-shipping-wide.jpg"
            alt="Nút giao đông xe: bộ model đang chạy bắt được mười phương tiện, một người đi xe máy và một biển cấm đi vào"
            className="-mx-[clamp(1.5rem,3.2vw,5.5rem)] w-[calc(100%+2*clamp(1.5rem,3.2vw,5.5rem))] max-w-none"
            loading="lazy"
            width={2000}
            height={1125}
          />
          <figcaption className={`mt-3 font-mono ${MICRO} leading-relaxed text-text-low`}>
            test_video3.mp4 · 13:28:04 · bộ model đang chạy — 10 vật thể, 1 biển
            cấm đi vào. Vạch kẻ đứt quãng: giới hạn thật ở nút giao rộng.
          </figcaption>
        </figure>

        <div data-reveal className={`mt-[clamp(3rem,5vw,6rem)] font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
          CÙNG MỘT KHUNG HÌNH · test_video3.mp4
        </div>
        <h3 data-reveal className="mt-3 max-w-[26ch] text-[clamp(1.25rem,1.9vw,2.5rem)] font-bold leading-tight tracking-[-0.02em]">
          Bản đang chạy so với dòng nghiên cứu
        </h3>
        <p data-reveal className={`mt-4 max-w-[52ch] ${BODY}`}>
          Cùng một giây, hai bộ model. Xanh là vật thể đã bám, đỏ là vạch kẻ.
        </p>

        {COMPARE.map((c) => (
          <div
            key={c.time}
            data-reveal
            className="mt-[clamp(1.5rem,2.4vw,2.5rem)] overflow-hidden rounded-lg bg-surface-2 p-[clamp(0.75rem,1.1vw,1.5rem)]"
          >
            <div className="grid gap-[clamp(0.75rem,1.1vw,1.5rem)] md:grid-cols-2">
              {c.panes.map((pane) => (
                <figure key={pane.src} className="m-0">
                  <img
                    src={pane.src}
                    alt={pane.alt}
                    className="w-full rounded-sm ring-1 ring-border"
                    loading="lazy"
                    width={1600}
                    height={900}
                  />
                  <figcaption className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className={`font-mono ${MICRO} tracking-[0.14em] ${pane.shipping ? "text-signal" : "text-text-low"}`}>
                      {pane.label}
                    </span>
                    <span className={`font-mono ${MICRO} text-text-low`}>{pane.stack}</span>
                    <span className={`font-mono ${MICRO} text-text-mid`}>{pane.found}</span>
                  </figcaption>
                </figure>
              ))}
            </div>
            <div className={`mt-4 font-mono ${MICRO} text-text-low`}>
              {c.time} · {c.note}
            </div>
          </div>
        ))}

        <h3 data-reveal className={`mt-[clamp(3rem,5vw,6rem)] font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
          BAN ĐÊM · NƠI NHÁNH LÀN GÃY
        </h3>
        <p data-reveal className={`mt-4 max-w-[50ch] ${BODY}`}>
          Hai ảnh đêm, cùng pipeline. Vật thể vẫn bắt được;{" "}
          <span className="text-foreground">làn thì không</span>.
        </p>
        <div data-reveal className="mt-6 grid gap-[clamp(0.75rem,1.1vw,1.5rem)] rounded-lg bg-surface-2 p-[clamp(0.75rem,1.1vw,1.5rem)] md:grid-cols-2">
          {NIGHT.map((n) => (
            <figure key={n.src} className="m-0">
              <img src={n.src} alt={n.alt} className="w-full rounded-sm ring-1 ring-border"
                loading="lazy" width={1600} height={900} />
              <figcaption className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className={`font-mono ${MICRO} tracking-[0.14em] text-text-low`}>{n.label}</span>
                <span className={`font-mono ${MICRO} text-text-mid`}>{n.objects}</span>
                <span className={`font-mono ${MICRO}`} style={{ color: n.laneOk ? "var(--text-mid)" : "var(--state-alert)" }}>
                  {n.lane}
                </span>
              </figcaption>
            </figure>
          ))}
        </div>
        <p data-reveal className={`mt-4 max-w-[54ch] font-mono ${MICRO} leading-relaxed text-text-low`}>
          Ảnh quảng cáo trong <code>data/test/test_im</code>, không phải footage
          của dự án · ảnh tĩnh lặp 60 khung.
        </p>

        <p data-reveal className={`mt-[clamp(1.5rem,2.4vw,2.5rem)] max-w-[50ch] ${BODY}`}>
          Nhiều hộp hơn không phải chính xác hơn.{" "}
          <span className="text-foreground">
            Dòng nghiên cứu chưa qua được cổng biên nên vẫn chưa được triển khai
          </span>.
        </p>

        <dl data-reveal className={`mt-[clamp(1.5rem,2.4vw,2.5rem)] grid gap-x-10 gap-y-6 font-mono ${MICRO} sm:grid-cols-2`}>
          {RESEARCH_COST.map((r) => (
            <div key={r.label}>
              <dt className="tracking-[0.14em] text-text-low">{r.label}</dt>
              <dd className="mt-1 ml-0 text-[clamp(0.95rem,1.1vw,1.35rem)] font-light text-foreground">
                {r.value}
              </dd>
              <dd className="mt-1 ml-0 leading-relaxed text-text-low">{r.note}</dd>
            </div>
          ))}
        </dl>

      </section>

      {/* ==================== DẢI: MÔ HÌNH 3D ==================== */}
      {/* Đặt ngay sau Nhận thức và trước Bằng chứng: mục trên vừa nói Tầng 1
          xuất ra cái gì, mục dưới sẽ đưa số đo. Ở giữa là chỗ duy nhất hợp lý
          để cho xem HÌNH DẠNG của những thứ đó trong không gian.

          Nhúng bằng iframe chứ không import three.js vào bundle: three chỉ tải
          khi người xem cuộn tới, ngữ cảnh WebGL nằm riêng nên không tranh chấp
          với vòng vẽ canvas của hero, và trang chính vẫn chạy nguyên vẹn nếu
          khối này hỏng. */}
      <section id="model3d" className="relative isolate" style={{ background: "var(--band-black)" }}>
        <div className={`${PAD} pt-[clamp(3.5rem,5.5vw,7rem)]`}>
          <div data-reveal className={`font-mono ${MICRO} tracking-[0.18em] text-on-dark-mid`}>
            MÔ HÌNH KHÁI NIỆM · KHÔNG PHẢI ĐẦU RA RUNTIME
          </div>
          <h2 data-reveal className={`mt-3 max-w-[22ch] ${H2} text-on-dark`}>
            Hình học của vùng nguy hiểm
          </h2>
          <p data-reveal className="mt-6 max-w-[46ch] text-[clamp(1rem,1.22vw,1.85rem)] font-light leading-relaxed text-on-dark-mid">
            Khối đặc là thế giới. Trong suốt là suy luận của máy.
          </p>
        </div>

        <div className="mt-[clamp(2rem,3vw,3.5rem)]">
          <iframe
            src="/landing/3d/corridor.html"
            title="Mô hình 3D hành lang xe chủ — bật tắt từng lớp suy luận"
            loading="lazy"
            className="block h-[clamp(24rem,62vh,44rem)] w-full border-0"
          />
        </div>

        <div className={`${PAD} pb-[clamp(3.5rem,5.5vw,7rem)] pt-[clamp(1.5rem,2.4vw,2.5rem)]`}>
          <p data-reveal className={`font-mono ${MICRO} leading-relaxed text-on-dark-mid`}>
            Dựng theo <code>training/Roadwatch 3D Models</code> · spec v1.0
          </p>
        </div>
      </section>

      {/* ==================== DẢI: PHẦN CỨNG ==================== */}
      <MediaBand
        src="/landing/evidence/jetson-orin.jpg"
        alt="Module NVIDIA Jetson Orin, nền tảng tính toán mục tiêu cho bản chạy trên xe"
        bg="var(--band-black)"
        position="76% center"
      >
        <div data-reveal className={`font-mono ${MICRO} tracking-[0.18em] text-on-dark-mid`}>
          NỀN TẢNG MỤC TIÊU
        </div>
        <h2 data-reveal className={`mt-3 max-w-[14ch] ${H2} text-on-dark`}>
          Chạy tại chỗ, không cần mạng
        </h2>
        <p data-reveal className="mt-6 max-w-[40ch] text-[clamp(1rem,1.22vw,1.85rem)] font-light leading-relaxed text-on-dark-mid">
          Đường cảnh báo nhắm tới NVIDIA Jetson Orin NX trên xe. Hiện dự án còn
          chạy trên máy trạm; Jetson vật lý là bước kế tiếp, chưa phải hiện trạng.
        </p>
      </MediaBand>

      {/* ==================== BẰNG CHỨNG ==================== */}
      <section id="evidence" className={`border-t border-border ${PAD} ${SECTION}`}>
        <div data-reveal className={`font-mono ${MICRO} tracking-[0.18em] text-text-low`}>
          BẰNG CHỨNG
        </div>
        <h2 data-reveal className={`mt-3 max-w-[18ch] ${H2}`}>
          Những gì đã đo được
        </h2>
        <h3 data-reveal className={`mt-[clamp(2.5rem,4vw,5rem)] font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
          CỔNG THĂNG HẠNG MODEL
        </h3>
        <div data-reveal className="mt-6 overflow-x-auto">
          <div className="min-w-[560px]">
            <GateChart />
          </div>
        </div>
        <p data-reveal className={`mt-6 max-w-[56ch] font-mono ${MICRO} leading-relaxed text-text-low`}>
          Cùng nguồn: mAP@50-95 <span className="text-text-mid">0.832</span>, bộ
          đọc số tốc độ top-1 <span className="text-text-mid">0.983</span> — tập
          val nội bộ.
        </p>
        <h3 data-reveal className={`mt-[clamp(3rem,5vw,6rem)] font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
          SỔ CỔNG CHẤT LƯỢNG
        </h3>
        <p data-reveal className={`mt-4 max-w-[54ch] ${BODY}`}>
          Sáu cổng trong <code className="font-mono">web_demo/evaluation/</code>,
          có ngày và ký băm.{" "}
          <span className="text-foreground">
            Cổng trượt nằm lại đây cùng cổng đạt
          </span>.
        </p>
        <div data-reveal className="mt-[clamp(1.5rem,2.4vw,2.5rem)]">
          <GateLedger />
        </div>

        <h3 data-reveal className={`mt-[clamp(3rem,5vw,6rem)] font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
          RW-05 · CÁI GIÁ CỦA VIỆC SIẾT NGƯỠNG
        </h3>
        <p data-reveal className={`mt-4 max-w-[54ch] ${BODY}`}>
          Cùng một đoạn 388 giây. Cảnh báo nguy cấp sai về 0, nhưng recall rơi
          một nửa và không lấy lại được.
        </p>
        <div data-reveal className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse text-left">
            <thead>
              <tr className={`border-b border-border font-mono ${MICRO} tracking-[0.12em] text-text-low`}>
                <th className="py-2 pr-4 font-normal">GIỜ</th>
                <th className="py-2 pr-4 font-normal">RECALL</th>
                <th className="py-2 pr-4 font-normal">NGUY CẤP SAI/PHÚT</th>
                <th className="py-2 pr-4 font-normal">ĐÚNG HƯỚNG</th>
                <th className="py-2 font-normal">TRÙNG LẶP</th>
              </tr>
            </thead>
            <tbody className={`font-mono ${MICRO}`}>
              {RW05.map((r) => (
                <tr key={r.time} className="border-b border-border">
                  <td className="py-3 pr-4 text-text-low">{r.time}</td>
                  <td className="py-3 pr-4" style={{ color: r.recall >= 0.9 ? "var(--signal)" : "var(--state-alert)" }}>
                    {r.recall.toFixed(3)}
                  </td>
                  <td className="py-3 pr-4" style={{ color: r.fp > 1 ? "var(--state-alert)" : "var(--signal)" }}>
                    {r.fp.toFixed(2)}
                  </td>
                  <td className="py-3 pr-4 text-text-mid">{r.dir.toFixed(3)}</td>
                  <td className="py-3 text-text-mid">{(r.dup * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p data-reveal className={`mt-4 max-w-[54ch] font-mono ${MICRO} leading-relaxed text-text-low`}>
          Nguồn: rw05_quality_gate.json, _v3, _v4 và _current, 21/08/2026.
        </p>

        <h3 data-reveal className={`mt-[clamp(3rem,5vw,6rem)] font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
          VÌ SAO BASELINE VẪN Ở LẠI
        </h3>
        <div data-reveal className="mt-6 overflow-x-auto">
          <div className="min-w-[38rem]">
            <LatencyChart />
          </div>
        </div>

      </section>


      {/* ==================== GIỌNG NÓI ==================== */}
      <MediaBand
        src="/landing/evidence/voice-cabin.jpg"
        alt="Khoang lái với dải sóng âm hiển thị trên màn hình trung tâm"
        bg="var(--band-night)"
        position="68% center"
      >
        <div data-reveal className={`font-mono ${MICRO} tracking-[0.18em] text-on-dark-mid`}>
          CẢNH BÁO GIỌNG NÓI · PIPER TIẾNG VIỆT · NGOẠI TUYẾN
        </div>
        <h2 data-reveal className={`mt-3 max-w-[16ch] ${H2} text-on-dark`}>
          Một câu thay cho một tiếng bíp
        </h2>
        <p data-reveal className="mt-6 max-w-[44ch] text-[clamp(1rem,1.22vw,1.85rem)] font-light leading-relaxed text-on-dark-mid">
          Mỗi câu nói rõ đối tượng, vị trí và việc cần làm. Banner trên màn hình
          và câu ra loa dùng chung một chuỗi.
        </p>
      </MediaBand>

      <section id="voice" className={`${PAD} ${SECTION}`}>
        <p data-reveal className={`mb-[clamp(1.5rem,2.4vw,3rem)] max-w-[56ch] ${BODY}`}>
          Bấm để nghe —{" "}
          <span className="text-foreground">file do chính Piper trong web_demo sinh ra</span>{" "}
          (<span className="font-mono">vi_VN-vais1000-medium</span>). Hai dòng
          cuối không có nút phát: chúng chỉ hiện trên HUD.
        </p>

        <VoiceList alerts={ALERTS} />

        <p data-reveal className={`mt-[clamp(2rem,3vw,3.5rem)] max-w-[52ch] ${BODY}`}>
          Một cổng duy nhất mở loa: xếp hạng mức độ, chờ đủ khung xác nhận,
          chặn câu trùng, và mỗi lúc chỉ cho một câu ra.
        </p>
      </section>

      {/* ==================== CTA ==================== */}
      {/* Trong web_demo, dashboard kỹ thuật luôn được phục vụ tại /app/. Có thể
          override bằng VITE_DEMO_URL khi landing trỏ sang deployment khác. */}
      <section id="cta" className={`border-t border-border ${PAD} py-[clamp(3rem,5vw,7rem)]`}>
        {HAS_TECHNICAL_DEMO && (
          <a data-reveal href={DEMO_URL} className="group mb-[clamp(2.5rem,4vw,5rem)] inline-flex flex-col gap-3 no-underline">
            <span className={`font-mono ${MICRO} tracking-[0.18em] text-text-low`}>SITE KỸ THUẬT</span>
            <span className="flex items-baseline gap-[clamp(1rem,1.6vw,2.5rem)] text-[clamp(2rem,5.2vw,6.5rem)] font-light leading-none tracking-[-0.02em] transition-colors group-hover:text-signal">
              Mở bảng điều khiển trực tiếp
              <span aria-hidden="true" className="text-signal transition-transform duration-300 group-hover:translate-x-2">
                →
              </span>
            </span>
          </a>
        )}

        <div
          data-reveal
          className={`grid gap-x-[clamp(2rem,3.5vw,5rem)] gap-y-5 font-mono ${MICRO} tracking-[0.12em] md:grid-cols-[1fr_1fr_auto]`}
        >
          {HAS_TECHNICAL_DEMO ? (
            <>
              <div>
                <div className="text-text-low">DRIVER HUD</div>
                <div className="mt-2 text-foreground">driver · driver123</div>
              </div>
              <div>
                <div className="text-text-low">ENGINEER DASHBOARD</div>
                <div className="mt-2 text-foreground">engineer · engineer123</div>
              </div>
            </>
          ) : (
            <>
              <div>
                <div className="text-text-low">GÓI CHẠY</div>
                <div className="mt-2 text-foreground">Docker · static · standalone</div>
              </div>
              <div>
                <div className="text-text-low">DASHBOARD</div>
                <div className="mt-2 text-foreground">Chưa cấu hình cho bản chia sẻ này</div>
              </div>
            </>
          )}
          <a
            href={REPO}
            target="_blank"
            rel="noreferrer"
            className="self-end text-text-mid no-underline transition-colors hover:text-signal"
          >
            MÃ NGUỒN TRÊN GITHUB →
          </a>
        </div>
        {HAS_TECHNICAL_DEMO && (
          <p data-reveal className={`mt-4 font-mono ${MICRO} leading-relaxed text-text-low`}>
            Tài khoản chỉ dùng cho demo; triển khai ngoài phòng lab phải thay secret và thông tin mặc định.
          </p>
        )}
      </section>

      <footer className={`border-t border-border ${PAD} pb-[clamp(2rem,2.6vw,3.5rem)] pt-[clamp(3rem,4vw,5rem)]`}>
        {/* Câu ranh giới đứng riêng và đứng trước mọi thứ khác: đây là thông
            tin duy nhất trong chân trang mà người đọc bắt buộc phải thấy. */}
        <p className="max-w-[64ch] text-[clamp(0.95rem,1.05vw,1.3rem)] font-light leading-relaxed">
          Chỉ hỗ trợ cảnh báo — không tự lái, không phanh, không đánh lái.{" "}
          <span className="text-text-mid">
            Bản thử nghiệm kỹ thuật, chưa được chứng nhận an toàn, không dùng
            thay cho quan sát của người lái.
          </span>
        </p>

        <div className={`mt-[clamp(2.5rem,4vw,4rem)] grid gap-x-[clamp(2rem,3.5vw,5rem)] gap-y-8 border-t border-border pt-8 font-mono ${MICRO} leading-relaxed sm:grid-cols-2 lg:grid-cols-4`}>
          <div>
            <div className="tracking-[0.14em] text-text-low">DỰ ÁN</div>
            <div className="mt-3 text-foreground">RoadWatch Copilot</div>
            <div className="mt-1 text-text-mid">Team P-162 NewbieS · AI20K Build Cohort 3</div>
            <div className="mt-1 text-text-low">R0 · Technical PoC</div>
          </div>

          <div>
            <div className="tracking-[0.14em] text-text-low">BỘ MODEL ĐANG CHẠY</div>
            <ul className="mt-3 space-y-1 text-text-mid">
              <li>yolo11n · vật thể</li>
              <li>yolop_lane_detection_640 · làn</li>
              <li>roadwatch_detector_v2 · biển báo</li>
              <li>vi_VN-vais1000-medium · giọng nói</li>
            </ul>
          </div>

          <div>
            <div className="tracking-[0.14em] text-text-low">TRÊN TRANG NÀY</div>
            <ul className="mt-3 space-y-1">
              {FOOTER_NAV.map(([label, href]) => (
                <li key={href}>
                  <a href={href} className="text-text-mid no-underline transition-colors hover:text-signal">
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="tracking-[0.14em] text-text-low">NGUỒN</div>
            <ul className="mt-3 space-y-1 text-text-mid">
              <li>
                <a href={REPO} target="_blank" rel="noreferrer"
                  className="text-text-mid no-underline transition-colors hover:text-signal">
                  Mã nguồn trên GitHub →
                </a>
              </li>
              <li className="text-text-low">web_demo/configs · evaluation · reports</li>
              <li className="text-text-low">training/layer1_pipeline_v2</li>
            </ul>
          </div>
        </div>

        <div className={`mt-8 flex flex-col gap-2 border-t border-border pt-6 font-mono ${MICRO} text-text-low md:flex-row md:justify-between`}>
          <p>
            Số liệu trên trang lấy nguyên từ artifact trong repo, không làm tròn
            cho đẹp. Bản dựng {__BUILD_DATE__}.
          </p>
          <p className="shrink-0">Trang tĩnh, chạy được ngoại tuyến.</p>
        </div>
      </footer>
    </main>
  );
}
