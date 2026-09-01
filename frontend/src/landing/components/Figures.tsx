/**
 * Hình minh hoạ: sơ đồ kiến trúc và đồ thị.
 *
 * Số liệu lấy nguyên từ artifact thật trong repo, không làm tròn cho đẹp:
 *  - cấu hình đang chạy: web_demo/configs/runtime.json
 *  - hồ sơ model và kết quả cổng kiểm định: web_demo/configs/model_registry.json
 * Chỉ dùng số của hệ ĐANG CHẠY. Số của dòng nghiên cứu yolo26s cố ý không đưa
 * vào đây để tránh đánh tráo ứng viên thành bản triển khai.
 * Sơ đồ bám đúng docs/ARCHITECTURE.md.
 *
 * Quy ước màu: độ lớn chỉ dùng MỘT tông (signal). Giá trị thứ hai của cùng một
 * phép đo (p95) mã hoá bằng VỊ TRÍ — vạch đánh dấu — chứ không bằng sắc độ thứ
 * hai, vì hai sắc độ đủ gần để phân biệt sẽ không đạt ngưỡng tương phản.
 * Đỏ là màu trạng thái (ngưỡng/khẩn cấp), không bao giờ dùng làm series.
 */

const MONO = "font-mono text-[11px] tracking-[0.08em]";

/* ------------------------------------------------------- sơ đồ kiến trúc --- */

type LayerProps = { y: number; h: number; n: string; title: string; sub: string };

function LayerBox({ y, h, n, title, sub }: LayerProps) {
  return (
    <g>
      <rect x={40} y={y} width={820} height={h} rx={10}
        fill="var(--surface-2)" stroke="var(--surface-3)" />
      <text x={62} y={y + 26} className={MONO} fill="var(--text-low)">TẦNG {n}</text>
      <text x={62} y={y + 50} fontSize={19} fontWeight={700} fill="var(--text-hi)">{title}</text>
      <text x={62} y={y + 72} fontSize={14} fill="var(--text-mid)">{sub}</text>
    </g>
  );
}

function Flow({ y, label }: { y: number; label: string }) {
  return (
    <g>
      <path d={`M450 ${y} L450 ${y + 30}`} stroke="var(--signal)" strokeWidth={2}
        markerEnd="url(#arrow)" />
      <text x={466} y={y + 20} className={MONO} fill="var(--text-low)">{label}</text>
    </g>
  );
}

export function ArchitectureDiagram() {
  return (
    <svg viewBox="0 0 900 730" className="h-auto w-full" role="img"
      aria-label="Sơ đồ bốn tầng: nhận thức, động học, ma trận quyết định, SLM bất đồng bộ">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
          markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--signal)" />
        </marker>
        <marker id="arrowRed" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
          markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--state-alert)" />
        </marker>
        <marker id="arrowDim" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
          markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--text-low)" />
        </marker>
      </defs>

      {/* nguồn vào */}
      <rect x={330} y={6} width={240} height={34} rx={17}
        fill="var(--surface-0)" stroke="var(--surface-3)" />
      <text x={450} y={28} textAnchor="middle" className={MONO} fill="var(--text-mid)">
        CAMERA · 30 FPS
      </text>
      <Flow y={40} label="" />

      {/* Tầng 1 */}
      <LayerBox y={78} h={150} n="1" title="Perception · các mô hình rời"
        sub="Bốn ONNX độc lập, chạy so le theo chu kỳ khung — chưa hợp nhất backbone" />
      {[
        ["yolo11n · vật thể · 1/1", 62],
        ["yolop · làn · 1/2", 336],
        ["detector_v2 + digits · 1/5", 610],
      ].map(([t, x]) => (
        <g key={t as string}>
          <rect x={x as number} y={164} width={228} height={44} rx={7}
            fill="var(--surface-0)" stroke="var(--signal)" strokeOpacity={0.45} />
          <text x={(x as number) + 114} y={191} textAnchor="middle" fontSize={13}
            fill="var(--text-hi)">{t}</text>
        </g>
      ))}
      <Flow y={228} label="hộp bao · đường cong làn · nhãn biển báo" />

      {/* Tầng 2 */}
      <LayerBox y={266} h={92} n="2" title="Kinematics Engine"
        sub="CPU C++ · ByteTrack · TTC · phát hiện tạt đầu" />
      <Flow y={358} label="ID xe · khoảng cách pinhole · TTC · cờ tạt đầu" />

      {/* Tầng 3 */}
      <LayerBox y={396} h={118} n="3" title="Priority & Decision Matrix"
        sub="Rule-based · phản xạ cứng, không phụ thuộc suy luận AI" />
      <rect x={470} y={450} width={368} height={46} rx={7}
        fill="var(--surface-0)" stroke="var(--state-alert)" />
      <text x={654} y={470} textAnchor="middle" fontSize={13} fontWeight={700}
        fill="var(--state-alert)">FCW · TTC &lt; 1.0s → BÍP 0ms</text>
      <text x={654} y={487} textAnchor="middle" className={MONO} fill="var(--text-mid)">
        PHÁT CỜ MUTE, CHẶN TẦNG 4
      </text>
      <Flow y={514} label="gói JSON ngữ cảnh" />

      {/* Tầng 4 */}
      <LayerBox y={552} h={100} n="4" title="Asynchronous SLM"
        sub="Luồng nền 1–2s · không chặn 30 FPS của Tầng 1 và 2" />

      {/* phản hồi ngưỡng động về Tầng 3 */}
      <path d="M40 602 L20 602 L20 456 L40 456" fill="none" stroke="var(--text-low)"
        strokeWidth={1.6} strokeDasharray="5 4" markerEnd="url(#arrowDim)" />
      <text x={12} y={529} className={MONO} fill="var(--text-low)"
        transform="rotate(-90 12 529)" textAnchor="middle">NGƯỠNG TTC ĐỘNG</text>

      {/* ra loa — ô loa canh tâm 450 để trùng trục dòng chảy chính;
          mũi tên xanh cắm vào cạnh trên, mũi tên đỏ cắm vào cạnh phải */}
      <path d="M838 496 L878 496 L878 694 L583 694" fill="none"
        stroke="var(--state-alert)" strokeWidth={2} markerEnd="url(#arrowRed)" />
      <path d="M450 652 L450 670" fill="none" stroke="var(--signal)"
        strokeWidth={2} markerEnd="url(#arrow)" />
      <rect x={325} y={676} width={250} height={36} rx={18}
        fill="var(--surface-0)" stroke="var(--surface-3)" />
      <text x={450} y={699} textAnchor="middle" className={MONO} fill="var(--text-mid)">
        LOA · BÍP + TTS VIỆT
      </text>
    </svg>
  );
}

/* ------------------------------------------------------------- đồ thị ----- */

/** Bộ model thực sự được nạp — thông tin định danh, nên trình bày dạng danh sách. */
const STACK = [
  ["Vật thể đường phố", "yolo11n.onnx", "baseline COCO, 6 lớp người dùng đường"],
  ["Làn + vùng chạy được", "YOLOP + twinlitenetplus_medium.onnx", "vùng chạy được cập nhật mỗi 4 khung"],
  ["Biển báo", "roadwatch_detector_v2.onnx", "kèm bộ đọc số tốc độ riêng"],
  ["Giọng nói", "vi_VN-vais1000-medium.onnx", "Piper, chạy tại chỗ"],
];

export function ActiveStack() {
  return (
    <ul className="m-0 list-none border-t border-border p-0">
      {STACK.map(([role, file, note]) => (
        <li key={file}
          className="grid grid-cols-1 gap-1 border-b border-border py-4 md:grid-cols-[clamp(9rem,13vw,15rem)_1fr_1fr] md:items-baseline md:gap-x-8">
          <span className="text-[clamp(0.95rem,1.05vw,1.35rem)]">{role}</span>
          <code className="font-mono text-[clamp(0.6875rem,0.62vw,0.9rem)] text-signal">{file}</code>
          <span className="font-mono text-[clamp(0.6875rem,0.62vw,0.9rem)] text-text-low">{note}</span>
        </li>
      ))}
    </ul>
  );
}

/** Kết quả cổng kiểm định. Đỏ là TRẠNG THÁI trượt, luôn kèm nhãn chữ. */
const GATES = [
  { name: "Biển báo phase 2", metric: 0.9874, pass: true, note: "được duyệt · đang chạy" },
  { name: "Vật thể v1.1", metric: 0.5124, pass: false, note: "trượt cổng recall theo mốc thời gian" },
  { name: "Vật thể v2", metric: 0.4876, pass: false, note: "trượt cổng tĩnh và cổng sự kiện" },
];

export function GateChart() {
  const W = 760, left = 210, rowH = 60, H = GATES.length * rowH + 16;
  const sx = (v: number) => left + v * (W - left - 210);
  return (
    <figure className="m-0">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img"
        aria-label="mAP@50 của từng ứng viên model và kết quả cổng kiểm định">
        <line x1={left} y1={4} x2={left} y2={H - 12} stroke="var(--surface-3)" strokeWidth={1} />
        {GATES.map((g, i) => {
          const y = 8 + i * rowH;
          const c = g.pass ? "var(--signal)" : "var(--state-alert)";
          return (
            <g key={g.name}>
              <text x={0} y={y + 20} fontSize={13} fill="var(--text-hi)">{g.name}</text>
              <text x={0} y={y + 38} className={MONO} fill={c}>
                {g.pass ? "✓ DUYỆT" : "✕ TRƯỢT"}
              </text>
              <rect x={left} y={y + 8} width={Math.max(2, sx(g.metric) - left)} height={20}
                rx={4} fill={c} fillOpacity={g.pass ? 1 : 0.35} />
              <text x={sx(g.metric) + 10} y={y + 23} className={MONO} fill="var(--text-mid)">
                mAP@50 {g.metric.toFixed(3)}
              </text>
              <text x={left} y={y + 44} className={MONO} fill="var(--text-low)">{g.note}</text>
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-3 font-mono text-[clamp(0.6875rem,0.62vw,0.9rem)] leading-relaxed text-text-low">
        Chỉ nhánh biển báo qua được cổng. Vật thể đường phố vì vậy vẫn chạy bằng
        baseline COCO nguyên bản, không phải model tự huấn luyện. Nguồn:{" "}
        <code>web_demo/configs/model_registry.json</code>.
      </figcaption>
    </figure>
  );
}

/* --------------------------------------------------------- dải ảnh ------- */

type BandProps = {
  src: string;
  alt: string;
  /** Nền dải — đặt bằng màu trội ở mép ảnh để không thấy đường ráp. */
  bg: string;
  /** Vị trí cắt, đẩy chủ thể sang phía đối diện với khối chữ. */
  position?: string;
  children: React.ReactNode;
};

/**
 * Dải ảnh tràn viền, chữ đè lên qua lớp scrim.
 *
 * Ba thứ khiến ảnh trông như một phần của trang chứ không phải bị dán vào:
 *  1. nền section trùng màu trội ở mép ảnh — không còn cạnh hình chữ nhật
 *  2. ảnh tràn hết chiều ngang, không viền, không bo góc
 *  3. scrim chuyển dần từ nền sang trong suốt, nên chữ nằm trên vùng đã tối
 *     mà mắt không đọc ra một lớp phủ riêng
 */
export function MediaBand({ src, alt, bg, position = "center", children }: BandProps) {
  return (
    <section className="relative isolate overflow-hidden" style={{ background: bg }}>
      <img
        src={src}
        alt={alt}
        loading="lazy"
        className="absolute inset-0 size-full object-cover"
        style={{ objectPosition: position }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            `linear-gradient(100deg, ${bg} 0%, color-mix(in oklab, ${bg} 88%, transparent) 34%, ` +
            `color-mix(in oklab, ${bg} 30%, transparent) 62%, transparent 86%)`,
        }}
      />
      <div className="relative px-[clamp(1.5rem,3.2vw,5.5rem)] py-[clamp(5rem,11vw,13rem)]">
        {children}
      </div>
    </section>
  );
}

/* ---------------------------------------------------- sổ cổng chất lượng --- */

/**
 * Sổ cổng chất lượng, lấy nguyên từ web_demo/evaluation/*.json. Đây là DANH
 * SÁCH TRẠNG THÁI, không phải đồ thị: sáu cổng không có đại lượng chung nào để
 * so, nên vẽ thành cột chỉ tạo ra một phép so sánh không tồn tại.
 *
 * Cổng trượt và cổng bị chặn được giữ nguyên trên trang. Bỏ chúng đi thì phần
 * còn lại không còn là bằng chứng nữa.
 */
const LEDGER = [
  {
    id: "RW-05",
    name: "Nhận diện chuyển hướng",
    state: "fail" as const,
    verdict: "TRƯỢT",
    detail: "recall 0.44 (8/18) · cổng cần ≥ 0.90",
    file: "rw05_quality_gate_current.json",
  },
  {
    id: "RW-06",
    name: "Sự kiện va chạm & phanh gấp",
    state: "pass" as const,
    verdict: "ĐẠT · R0",
    detail: "recall 2/2 · 0.93 cảnh báo thừa/phút · chỉ 2 sự kiện đã xác minh",
    file: "rw06_quality_gate_v2.json",
  },
  {
    id: "RW-07",
    name: "Hiệu chỉnh camera",
    state: "block" as const,
    verdict: "BỊ CHẶN",
    detail: "thiếu artifact hiệu chỉnh · metric_ttc_alerting_allowed = false",
    file: "rw07_calibration_gate.json",
  },
  {
    id: "RW-10",
    name: "Nhãn làn đường",
    state: "wip" as const,
    verdict: "ĐANG LÀM",
    detail: "0/3000 khung đã xác minh · training_blocked = true",
    file: "rw10_lane_review_gate_v2.json",
  },
  {
    id: "RW-11",
    name: "Trọng tài biển báo",
    state: "pass" as const,
    verdict: "ĐẠT",
    detail: "120 hoán vị · 1 chữ ký đầu ra duy nhất · tất định",
    file: "rw11_quality_gate.json",
  },
  {
    id: "RW-12",
    name: "Hàng đợi giọng nói",
    state: "wip" as const,
    verdict: "ĐẠT PHẦN MỀM",
    detail: "100/100 phát trọn · p95 khởi phát 1.0 ms · chờ cổng người trong cabin",
    file: "rw12_quality_gate.json",
  },
];

const STATE_COLOR = {
  pass: "var(--signal)",
  fail: "var(--state-alert)",
  block: "var(--state-alert)",
  wip: "var(--text-low)",
} as const;

export function GateLedger() {
  return (
    <div className="border-t border-border">
      {LEDGER.map((g) => (
        <div
          key={g.id}
          className="grid grid-cols-1 gap-1 border-b border-border py-[clamp(0.875rem,1.2vw,1.5rem)] md:grid-cols-[7rem_minmax(0,1fr)_10rem] md:items-baseline md:gap-x-6"
        >
          <div className={`${MONO} tracking-[0.14em] text-text-low`}>{g.id}</div>
          <div>
            <div className="text-[clamp(0.95rem,1.1vw,1.5rem)] font-light leading-snug">
              {g.name}
            </div>
            <div className={`mt-1 ${MONO} leading-relaxed text-text-low`}>{g.detail}</div>
          </div>
          <div
            className={`${MONO} tracking-[0.12em]`}
            style={{ color: STATE_COLOR[g.state] }}
          >
            {g.state === "pass" ? "✓ " : g.state === "wip" ? "· " : "✕ "}
            {g.verdict}
          </div>
        </div>
      ))}
    </div>
  );
}

/* --------------------------------------------------------- độ trễ suy luận --- */

/**
 * Vì sao baseline vẫn ở lại: độ trễ CPU trên cùng 72 khung, cùng ngưỡng.
 * Nguồn: web_demo/reports/LAYER1_TEST_MODELS_BENCHMARK_20260828.md
 *
 * Dạng "quả tạ": mỗi nhánh MỘT hàng, hai chấm nối bằng một đoạn thẳng. Thứ cần
 * đọc ra là KHOẢNG CÁCH giữa hai chấm, nên nó được vẽ thành một vật thể duy
 * nhất thay vì hai thanh rời phải tự so. Bội số ghi thẳng ở cuối hàng vì đó
 * mới là kết luận, còn mili-giây chỉ là đường dẫn tới nó.
 *
 * p95 cố ý KHÔNG vào hình. Ở bản trước nó là một vạch đứng lơ lửng cách xa
 * thanh, đọc như một dấu hiệu không liên quan. Nó xuống bảng bên dưới.
 */
const LATENCY = [
  {
    branch: "Vật thể",
    run: "yolo11n", cand: "BEST_detection_bdd7_ep18",
    runP50: 38.764, candP50: 139.111, runP95: 55.204, candP95: 202.281,
  },
  {
    branch: "Biển báo",
    run: "roadwatch_detector_v2", cand: "BEST_signs_vn27_ep21",
    runP50: 71.374, candP50: 256.816, runP95: 101.795, candP95: 322.250,
  },
  {
    branch: "Làn",
    run: "yolop_lane_detection_640", cand: "yolopv2",
    runP50: 197.640, candP50: 303.935, runP95: 264.659, candP95: 473.677,
  },
];

export function LatencyChart() {
  const maxRatio = 4;
  return (
    <figure className="m-0">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className={`border-b border-border ${MONO} tracking-[0.12em] text-text-low`}>
            <th className="py-2 pr-4 font-normal">NHÁNH</th>
            <th className="py-2 pr-4 font-normal">MODEL ĐANG CHẠY</th>
            <th className="py-2 pr-4 font-normal">MODEL ỨNG VIÊN · CHƯA TRIỂN KHAI</th>
            <th className="py-2 font-normal">CHẬM HƠN BAO NHIÊU LẦN</th>
          </tr>
        </thead>
        <tbody>
          {LATENCY.map((r) => {
            const ratio = r.candP50 / r.runP50;
            return (
              <tr key={r.branch} className="border-b border-border align-middle">
                <td className="py-4 pr-4 text-[clamp(0.95rem,1.05vw,1.3rem)]">{r.branch}</td>
                {/* Tên model đứng trước con số. Nhãn vai trò trừu tượng ("đang
                    chạy" / "ứng viên") bắt người đọc phải nhớ cái nào là cái
                    nào; tên thật thì không. */}
                <td className="py-4 pr-4">
                  <div className={`${MONO} text-foreground`}>{r.run}</div>
                  <div className={`mt-1 ${MONO} text-text-low`}>
                    {r.runP50.toFixed(0)} / {r.runP95.toFixed(0)} ms
                  </div>
                </td>
                <td className="py-4 pr-4">
                  <div className={`${MONO} text-text-mid`}>{r.cand}</div>
                  <div className={`mt-1 ${MONO} text-text-low`}>
                    {r.candP50.toFixed(0)} / {r.candP95.toFixed(0)} ms
                  </div>
                </td>
                <td className="py-4">
                  {/* Thanh mã hoá ĐÚNG thứ được kết luận — tỉ lệ — nên thanh dài
                      nhất luôn là bội số lớn nhất. Bản trước mã hoá mili-giây
                      nên hàng "Làn" có đoạn dài nhất mà bội số lại nhỏ nhất. */}
                  <div className="flex items-center gap-3">
                    <div className="h-2.5 min-w-[3rem] flex-1 rounded-sm bg-surface-2">
                      <div
                        className="h-2.5 rounded-sm bg-signal"
                        style={{ width: `${(ratio / maxRatio) * 100}%` }}
                      />
                    </div>
                    <span className="w-[3.5rem] shrink-0 text-right text-[clamp(0.95rem,1.05vw,1.3rem)] font-medium">
                      {ratio.toFixed(1)}×
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <figcaption className="mt-4 font-mono text-[clamp(0.6875rem,0.62vw,0.9rem)] leading-relaxed text-text-low">
        Số là p50 / p95, đo trên cùng 72 khung, cùng ngưỡng, cùng CPU. Nguồn:{" "}
        <code>web_demo/reports/LAYER1_TEST_MODELS_BENCHMARK_20260828.md</code>.
      </figcaption>
    </figure>
  );
}
