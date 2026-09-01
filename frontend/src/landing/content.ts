/**
 * RoadWatch Copilot — landing page content (VI / EN).
 *
 * Mọi con số trong file này đến từ artifact đã đo trong repo:
 *  - docs/PERFORMANCE_STREAMING_OPTIMIZATION_2026-08-29.md
 *  - docs/VALIDATION.md
 *  - docs/ROADWATCH_TECHNICAL_REPORT.md  (§3.2, §5.2, §7)
 *  - docs/MASTER_ACTION_PLAN.md          (§1.3 release gates)
 * Không thêm số liệu chưa có report tương ứng. Điều kiện chưa có ground truth
 * được đánh dấu `status: "no-gt"` và hiển thị là "chưa đủ dữ liệu".
 */

export type Lang = "vi" | "en";

export const LANGS: { id: Lang; label: string; full: string }[] = [
  { id: "vi", label: "VI", full: "Tiếng Việt" },
  { id: "en", label: "EN", full: "English" },
];

/* ------------------------------------------------------------------ */
/* Bằng chứng đã đo — dùng chung cho cả hai ngôn ngữ                    */
/* ------------------------------------------------------------------ */

export const EVIDENCE = {
  runtime: {
    hardware: "Windows 11 · AMD Ryzen 5 7535HS · Radeon RX 6550M/660M",
    clip: "test_video10.mp4 · 1920×1080 · 30 FPS",
    provider: "ONNX Runtime DirectML",
    date: "2026-08-29",
    note: "audio off",
    processedFps: 11.28,
    displayFps: 23.07,
    p50: 89.96,
    p95: 149.91,
    warmupMs: 7990.83,
    pipelineErrors: 0,
  },
  history: [
    { version: "v0.1", fps: 4.31, p50: 148.44, p95: 245.4 },
    { version: "v0.2", fps: 9.03, p50: 99.29, p95: 148.86 },
    { version: "2026-08-29", fps: 11.28, p50: 89.96, p95: 149.91 },
  ],
  gates: {
    fps: 12,
    p95: 150,
  },
  sign: {
    precision: 0.95847,
    recall: 0.96651,
    map50: 0.98741,
    map5095: 0.83217,
    speedTop1: 0.98254,
  },
  objectRecall: { baseline: 0.8, candidateV3: 0.6 },
  lane: { ufldv2Coverage: 0.8571, ufldv2Fps: 3.04 },
  groundTruth: { verifiedSeconds: 600, negativeSeconds: 440, disagreement: 0 },
};

export const SPEC_ROWS = [
  ["Object detection", "YOLO11n · 6 road-user classes", "Active baseline"],
  ["Traffic sign", "roadwatch_detector_v2 + speed classifier", "Active"],
  ["Lane / drivable", "YOLOP ONNX 640", "Active baseline"],
  ["Lane candidate", "UFLDv2 · TwinLiteNet+ Medium", "Candidate"],
  ["Runtime", "ONNX Runtime · DirectML / CUDA / CPU", "Active"],
  ["Edge target", "TensorRT FP16 · Jetson Orin", "Planned"],
  ["Voice", "Piper vi_VN-vais1000-medium", "Active"],
  ["Explanation SLM", "Qwen2.5-0.5B ONNX Q4F16", "Optional · off"],
] as const;

/* Benchmark theo điều kiện — chỉ có ground truth cho replay ban ngày.  */
export const BENCH_CONDITIONS = [
  {
    id: "day",
    fps: 11.28,
    p50: 89.96,
    p95: 149.91,
    errors: 0,
    status: "measured" as const,
  },
  { id: "night", status: "no-gt" as const },
  { id: "rain", status: "no-gt" as const },
  { id: "dense", status: "no-gt" as const },
];

/* ------------------------------------------------------------------ */
/* Copy song ngữ                                                       */
/* ------------------------------------------------------------------ */

export interface Copy {
  nav: { product: string; how: string; benchmark: string; safety: string; cta: string; menu: string };
  hero: {
    eyebrow: string;
    h1a: string;
    h1b: string;
    lede: string;
    ctaPrimary: string;
    ctaSecondary: string;
    badges: string[];
    sceneLabel: string;
    sceneDisclaimer: string;
  };
  trust: { label: string; items: { value: string; label: string }[] };
  demo: {
    eyebrow: string;
    title: string;
    lede: string;
    scenarios: { id: string; label: string }[];
    panelTitle: string;
    objects: string;
    context: string;
    alert: string;
    laneDetected: string;
    drivable: string;
    density: string;
    audioRoute: string;
    silent: string;
    silentNote: string;
    playing: string;
    paused: string;
    play: string;
    pause: string;
    severity: Record<string, string>;
    classNames: Record<string, string>;
    routeNames: Record<string, string>;
    note: string;
  };
  capability: {
    eyebrow: string;
    title: string;
    lede: string;
    cards: { tag: string; title: string; body: string; items: string[] }[];
  };
  how: {
    eyebrow: string;
    title: string;
    steps: { step: string; title: string; body: string }[];
    highlight: string;
  };
  scenarios: {
    eyebrow: string;
    title: string;
    lede: string;
    labels: { trigger: string; level: string; output: string; control: string; none: string };
    tabs: {
      id: string;
      tab: string;
      title: string;
      body: string;
      trigger: string;
      level: string;
      levelTone: "critical" | "warning" | "advisory";
      output: string;
      voice: string;
    }[];
  };
  edge: {
    eyebrow: string;
    title: string;
    lede: string;
    cards: { title: string; body: string }[];
    tableTitle: string;
    tableHead: [string, string, string];
  };
  bench: {
    eyebrow: string;
    title: string;
    lede: string;
    conditionLabels: Record<string, string>;
    noGt: string;
    noGtNote: string;
    metrics: { processed: string; display: string; p50: string; p95: string; errors: string; warmup: string };
    gate: string;
    gateNote: string;
    historyTitle: string;
    historyNote: string;
    modelTitle: string;
    modelRows: { name: string; metric: string; value: string; state: string; tone: "active" | "candidate" }[];
    conditions: string;
    footnote: string;
  };
  safety: {
    eyebrow: string;
    title: string;
    lede: string;
    nots: string[];
    dos: string[];
    notsTitle: string;
    dosTitle: string;
    footer: string;
  };
  privacy: { eyebrow: string; title: string; lede: string; items: { title: string; body: string }[] };
  faq: { eyebrow: string; title: string; items: { q: string; a: string }[] };
  inspector: {
    eyebrow: string;
    title: string;
    lede: string;
    candidate: string;
    noCandidate: string;
    gatesTitle: string;
    tracksTitle: string;
    outcomeTitle: string;
    gates: Record<string, { name: string; help: string }>;
    outcomes: Record<string, string>;
    reasons: Record<string, string>;
    ledger: { title: string; considered: string; spoken: string; hud: string; suppressed: string; note: string };
    cols: { track: string; conf: string; hits: string; ego: string };
    yes: string;
    no: string;
    scrub: string;
  };
  audio: { off: string; on: string; note: string; label: string };
  pipeline: {
    title: string;
    caption: string;
    aria: string;
    nodes: Record<string, string>;
    edges: Record<string, string>;
    offPath: string;
    critical: string;
  };
  chart: { title: string; sub: string; axis: string; gate: string; p50: string; p95: string; note: string };
  cta: { title: string; lede: string; primary: string; secondary: string; tertiary: string };
  footer: {
    tagline: string;
    cols: { title: string; links: string[] }[];
    legal: string;
    guardrail: string;
  };
}

const vi: Copy = {
  nav: {
    product: "Sản phẩm",
    how: "Cách hoạt động",
    benchmark: "Benchmark",
    safety: "Giới hạn an toàn",
    cta: "Xem demo",
    menu: "Mở menu",
  },
  hero: {
    eyebrow: "ROADWATCH COPILOT · L0 DRIVER ALERT",
    h1a: "Cảnh báo sớm.",
    h1b: "Và biết khi nào nên im lặng.",
    lede:
      "Trợ lý cảnh báo chạy ngay trên thiết bị, đọc camera phía trước để nhận biết xe, xe máy, người đi bộ, làn đường và biển báo Việt Nam — rồi chỉ lên tiếng khi bằng chứng thực sự đủ. RoadWatch không đánh lái, không phanh, không thay tài xế.",
    ctaPrimary: "Xem demo trực tiếp",
    ctaSecondary: "Đọc benchmark",
    badges: ["On-device AI", "82 lớp biển báo Việt Nam", "Không cần Internet", "L0 · chỉ cảnh báo"],
    sceneLabel: "PERCEPTION VIEW",
    sceneDisclaimer:
      "Mô phỏng giao diện perception theo đúng logic cảnh báo. Không phải suy luận model thời gian thực.",
  },
  trust: {
    label: "Năng lực nhận thức",
    items: [
      { value: "6", label: "lớp tác nhân giao thông" },
      { value: "82", label: "lớp biển báo Việt Nam" },
      { value: "3", label: "model perception độc lập" },
      { value: "600 s", label: "ground truth đã kiểm định" },
      { value: "0", label: "lệnh điều khiển xe" },
    ],
  },
  demo: {
    eyebrow: "LIVE ROAD DEMO",
    title: "Xem pipeline làm việc, không chỉ nghe mô tả",
    lede:
      "Khung bên dưới tái hiện đúng thứ tự quyết định của RoadWatch: nhận diện → bằng chứng theo thời gian → risk → Alert Governor. Phần lớn thời gian hệ thống không nói gì — đó là thiết kế, không phải lỗi.",
    scenarios: [
      { id: "day", label: "Ban ngày" },
      { id: "night", label: "Ban đêm" },
      { id: "rain", label: "Trời mưa" },
    ],
    panelTitle: "LIVE PERCEPTION",
    objects: "Đối tượng",
    context: "Bối cảnh đường",
    alert: "Cảnh báo",
    laneDetected: "Lane phát hiện",
    drivable: "Drivable area",
    density: "Mật độ giao thông",
    audioRoute: "Kênh phát",
    silent: "Không có nguy cơ cần cảnh báo",
    silentNote: "Đối tượng vẫn được theo dõi và hiển thị, nhưng không đủ điều kiện phát âm thanh.",
    playing: "Đang chạy",
    paused: "Tạm dừng",
    play: "Chạy",
    pause: "Dừng",
    severity: { critical: "Nguy cấp", warning: "Cảnh báo", advisory: "Nhắc nhở" },
    classNames: {
      car: "Ô tô",
      motorcycle: "Xe máy",
      pedestrian: "Người đi bộ",
      truck: "Xe tải",
      sign: "Biển báo",
    },
    routeNames: {
      beep_tts: "Beep + giọng nói",
      tts: "Giọng nói + banner",
      hud: "Chỉ hiển thị HUD",
      none: "Im lặng",
    },
    note:
      "Muốn xem pipeline thật: chạy backend rồi truyền `streamUrl=\"/api/stream.mjpg\"` cho component này.",
  },
  capability: {
    eyebrow: "DETECTION CAPABILITIES",
    title: "Một hệ thống nhận thức, không phải một object detector",
    lede:
      "Ba model chạy độc lập rồi được hợp nhất bằng bằng chứng theo thời gian. Không model nào một mình được quyền tạo ra cảnh báo.",
    cards: [
      {
        tag: "Phương tiện",
        title: "Nhận biết phương tiện",
        body: "Theo dõi xe phía trước và hai bên bằng track ID ổn định, có lịch sử kích thước và xu hướng tiến gần.",
        items: ["Ô tô", "Xe buýt", "Xe tải", "Xe máy", "Xe đạp"],
      },
      {
        tag: "Người tham gia dễ tổn thương",
        title: "Người đi bộ và xe hai bánh",
        body: "Ưu tiên nhóm dễ tổn thương trong vùng có thể lái và hành lang ego — đặc thù giao thông hỗn hợp Việt Nam.",
        items: ["Người đi bộ", "Người đi xe đạp", "Người cắt ngang", "Người sát mép đường"],
      },
      {
        tag: "Biển báo Việt Nam",
        title: "Đọc biển báo trong nước",
        body: "Detector biển kết hợp classifier riêng cho giá trị tốc độ, có gate độ tin cậy và lớp `unknown` để không đoán bừa.",
        items: ["82 lớp biển", "Biển cấm và nguy hiểm", "Giới hạn tốc độ", "Xác nhận theo thời gian"],
      },
      {
        tag: "Hiểu mặt đường",
        title: "Làn đường và vùng lái được",
        body: "Lane mask và drivable-area quyết định một đối tượng có nằm trên đường đi của xe hay không.",
        items: ["Lane detection", "Drivable area", "Hành lang ego", "Khóa LDW khi lane kém"],
      },
    ],
  },
  how: {
    eyebrow: "HOW ROADWATCH WORKS",
    title: "Bốn bước từ khung hình tới lời nói",
    steps: [
      { step: "Camera", title: "Thu nhận", body: "Đọc camera trước hoặc video replay, mỗi frame có timestamp và chính sách bỏ frame cũ." },
      { step: "On-device AI", title: "Nhận diện", body: "Ba model chạy ngay trên thiết bị để tìm tác nhân giao thông, biển báo và làn đường." },
      { step: "Risk analysis", title: "Đánh giá rủi ro", body: "Tracker giữ ID, hệ thống theo dõi vị trí và mức tiến gần qua nhiều frame trước khi kết luận." },
      { step: "Driver alert", title: "Cảnh báo", body: "Alert Governor chọn đúng một cảnh báo quan trọng nhất, phát beep hoặc giọng nói tiếng Việt." },
    ],
    highlight:
      "RoadWatch phân tích tại chỗ trước, nên cảnh báo không phụ thuộc vào một vòng đi–về tới cloud. Bằng chứng có thể đồng bộ lên cloud sau, khi có kết nối và khi người dùng bật.",
  },
  scenarios: {
    eyebrow: "ALERT SCENARIOS",
    title: "Nhận diện tạo ra giá trị gì trên đường thật",
    lede: "Mỗi loại cảnh báo có điều kiện kích hoạt riêng, mức ưu tiên riêng và một kênh phát duy nhất.",
    labels: {
      trigger: "Điều kiện kích hoạt",
      level: "Mức cảnh báo",
      output: "Cách phát ra",
      control: "Can thiệp điều khiển",
      none: "Không có",
    },
    tabs: [
      {
        id: "fcw",
        tab: "Va chạm phía trước",
        title: "Forward collision warning",
        body: "RoadWatch phát hiện khoảng cách hình ảnh tới xe phía trước đang thu hẹp nhanh và phát cảnh báo nhìn thấy được lẫn nghe được.",
        trigger: "Box mở rộng nhanh liên tục nhiều frame, đối tượng nằm trong hành lang ego",
        level: "Nguy cấp",
        levelTone: "critical",
        output: "Beep ưu tiên + giọng nói + banner đỏ",
        voice: "“Xe phía trước phanh gấp, giảm tốc.”",
      },
      {
        id: "vru",
        tab: "Người đi bộ",
        title: "Vulnerable road user",
        body: "Người đi bộ trong vùng lái được hoặc đang cắt ngang được ưu tiên hơn phương tiện có cùng mức rủi ro.",
        trigger: "Người trong drivable area, có chuyển động ngang hướng vào hành lang ego",
        level: "Cảnh báo",
        levelTone: "warning",
        output: "Giọng nói + banner",
        voice: "“Người đi bộ phía trước bên trái.”",
      },
      {
        id: "moto",
        tab: "Xe máy tạt đầu",
        title: "Cut-in xe hai bánh",
        body: "Xe máy chuyển hướng vào làn của xe được xử lý bằng cửa sổ chuyển động ngắn để phản ứng kịp mà vẫn cần xác nhận.",
        trigger: "Track xe hai bánh dịch ngang vào ego lane, xác nhận qua nhiều frame",
        level: "Cảnh báo",
        levelTone: "warning",
        output: "Giọng nói + banner",
        voice: "“Xe máy phía trước bên phải, giảm tốc.”",
      },
      {
        id: "ldw",
        tab: "Lệch làn",
        title: "Lane departure",
        body: "Cảnh báo lệch làn chỉ được mở khi chất lượng lane đủ tin cậy; lane kém thì hệ thống khóa LDW thay vì đoán.",
        trigger: "Độ lệch vượt ngưỡng và lane quality đạt gate",
        level: "Cảnh báo",
        levelTone: "warning",
        output: "Giọng nói + banner",
        voice: "“Xe đang lệch làn bên phải.”",
      },
      {
        id: "sign",
        tab: "Biển báo",
        title: "Biển báo và giới hạn tốc độ",
        body: "Biển chỉ được đọc lên khi qua xác nhận thời gian và gate độ tin cậy; trong giao thông đông, biển tốc độ được hạ xuống chỉ hiển thị.",
        trigger: "Biển được xác nhận nhiều lần, có liên quan tới làn đang đi",
        level: "Nhắc nhở",
        levelTone: "advisory",
        output: "Giọng nói, hoặc chỉ HUD khi đường đông",
        voice: "“Giới hạn tốc độ 40 km/h.”",
      },
    ],
  },
  edge: {
    eyebrow: "BUILT FOR THE EDGE",
    title: "Chạy tại chỗ, đo được, và có đường lùi",
    lede:
      "Model, rule engine, cơ sở dữ liệu, giọng nói và giao diện đều nằm trên thiết bị. Mất mạng thì đường cảnh báo vẫn chạy.",
    cards: [
      { title: "Độ trễ thấp", body: "Hàng đợi một frame, bỏ frame cũ thay vì tích lũy trễ, và tách hẳn luồng hiển thị khỏi luồng suy luận." },
      { title: "Nhiều runtime", body: "Một đồ thị ONNX chạy trên DirectML, CUDA hoặc CPU; đường TensorRT FP16 dành cho edge NVIDIA." },
      { title: "Offline-first", body: "Đăng nhập, replay, suy luận và giọng nói tiếng Việt đều không cần Internet." },
      { title: "Tôn trọng dữ liệu", body: "Video không rời khỏi thiết bị theo mặc định; chỉ bằng chứng sự kiện được ghi lại cục bộ." },
    ],
    tableTitle: "Cấu hình runtime",
    tableHead: ["Thành phần", "Đang dùng", "Trạng thái"],
  },
  bench: {
    eyebrow: "BENCHMARK",
    title: "Có số đo, và có ghi rõ số đó đo ở đâu",
    lede:
      "Toàn bộ số dưới đây đến từ một phiên replay cụ thể trên laptop AMD, audio tắt để tách riêng thời gian perception. Đây không phải benchmark trên phần cứng ô tô.",
    conditionLabels: { day: "Ban ngày", night: "Ban đêm", rain: "Trời mưa", dense: "Đường đông" },
    noGt: "Chưa đủ dữ liệu",
    noGtNote:
      "Điều kiện này chưa có ground truth theo timestamp nên chưa công bố số. Đang nằm trong hàng đợi gán nhãn.",
    metrics: {
      processed: "Processed FPS",
      display: "Display FPS",
      p50: "E2E P50",
      p95: "E2E P95",
      errors: "Lỗi pipeline",
      warmup: "Warmup",
    },
    gate: "Mục tiêu edge candidate",
    gateNote: "≥ 12 processed FPS và E2E P95 ≤ 150 ms. Hiện đã đạt P95, còn thiếu FPS.",
    historyTitle: "Tiến triển qua các phiên bản",
    historyNote: "Cùng clip replay, khác cấu hình runtime. Cột càng cao càng nhanh.",
    modelTitle: "Chất lượng model",
    modelRows: [
      { name: "Detector biển báo", metric: "mAP50", value: "0.9874", state: "Đang dùng", tone: "active" },
      { name: "Classifier tốc độ", metric: "Top-1", value: "0.9825", state: "Đang dùng", tone: "active" },
      { name: "Object baseline", metric: "Event recall", value: "0.8000", state: "Đang dùng", tone: "active" },
      { name: "Object V3 candidate", metric: "Event recall", value: "0.6000", state: "Bị từ chối", tone: "candidate" },
      { name: "Lane UFLDv2 candidate", metric: "Fusion FPS", value: "3.04", state: "Bị từ chối", tone: "candidate" },
    ],
    conditions: "Điều kiện đo",
    footnote:
      "RoadWatch giữ lại model baseline ngay cả khi candidate có chỉ số huấn luyện đẹp hơn, nếu candidate làm giảm recall của sự kiện nguy hiểm. Promotion dựa trên an toàn ở mức sự kiện, không dựa trên mAP đơn lẻ.",
  },
  safety: {
    eyebrow: "SAFETY BOUNDARY",
    title: "RoadWatch là trợ lý cảnh báo, không phải hệ thống tự lái",
    lede:
      "Đây là ranh giới thiết kế, không phải một dòng miễn trừ trách nhiệm. Trong mã nguồn không tồn tại API gửi lệnh tới phanh, ga hay vô-lăng.",
    notsTitle: "RoadWatch không làm",
    dosTitle: "RoadWatch làm",
    nots: [
      "Không đánh lái",
      "Không tự phanh hoặc điều khiển ga",
      "Không ghi lên CAN bus của xe",
      "Không thay thế việc quan sát của tài xế",
      "Không tuyên bố khoảng cách mét hay TTC theo giây khi chưa hiệu chuẩn camera",
    ],
    dos: [
      "Cảnh báo bằng hình ảnh và giọng nói tiếng Việt",
      "Xếp hạng nguy cơ và chỉ phát một cảnh báo tại một thời điểm",
      "Giữ lại bằng chứng cho từng quyết định",
      "Khóa cảnh báo khi bằng chứng không đủ tin cậy",
      "Ghi rõ điều kiện mà cảnh báo có hiệu lực",
    ],
    footer:
      "Cảnh báo có thể sai. Thời tiết, ánh sáng, góc lắp camera và che khuất đều ảnh hưởng tới kết quả. Tài xế luôn chịu trách nhiệm quan sát và điều khiển xe.",
  },
  privacy: {
    eyebrow: "PRIVACY",
    title: "Camera trong xe nhìn thấy khuôn mặt, biển số và hành trình",
    lede: "Vì vậy quyền riêng tư được đặt ở đây, trên trang chính, chứ không giấu trong điều khoản sử dụng.",
    items: [
      { title: "Suy luận tại thiết bị", body: "Đường cảnh báo chạy hoàn toàn cục bộ. Không cần gửi video lên máy chủ để nhận cảnh báo." },
      { title: "Chỉ lưu bằng chứng sự kiện", body: "Hệ thống ghi sự kiện và số đo vào cơ sở dữ liệu cục bộ, không lưu toàn bộ video theo mặc định." },
      { title: "Đồng bộ là tùy chọn", body: "Việc đưa dữ liệu lên cloud để đánh giá là hành động có chủ đích, không bật sẵn." },
      { title: "Che thông tin khi chia sẻ", body: "Video demo công khai cần làm mờ khuôn mặt và biển số trước khi phát hành." },
    ],
  },
  faq: {
    eyebrow: "FAQ",
    title: "Câu hỏi thường gặp",
    items: [
      {
        q: "RoadWatch có tự điều khiển xe không?",
        a: "Không. RoadWatch thuộc mức L0 — chỉ cảnh báo. Trong mã nguồn không có đường gửi lệnh tới phanh, ga, vô-lăng hay ECU, và cũng không có thao tác ghi lên CAN bus.",
      },
      {
        q: "Có hoạt động khi không có Internet không?",
        a: "Có. Model, rule engine, cơ sở dữ liệu, giọng nói tiếng Việt và giao diện đều chạy cục bộ. Ngắt mạng thì đăng nhập, replay, suy luận và cảnh báo vẫn tiếp tục.",
      },
      {
        q: "Hệ thống nhận diện được những gì?",
        a: "Sáu lớp tác nhân giao thông (người, xe đạp, xe máy, ô tô, xe buýt, xe tải), 82 lớp biển báo Việt Nam kèm nhận dạng giá trị tốc độ, cùng lane mask và vùng có thể lái.",
      },
      {
        q: "Cảnh báo được tạo ra như thế nào?",
        a: "Một khung hình đơn lẻ không đủ. Đối tượng phải được theo dõi qua nhiều frame, nằm đúng vùng liên quan tới đường đi của xe, vượt ngưỡng rủi ro, rồi mới đi qua Alert Governor — nơi áp cooldown, hysteresis và chọn đúng một cảnh báo được phát.",
      },
      {
        q: "Ban đêm và trời mưa thì sao?",
        a: "Pipeline vẫn chạy, nhưng chưa có ground truth theo timestamp cho các điều kiện này nên chưa công bố số. Khi chất lượng lane thấp, hệ thống khóa cảnh báo lệch làn thay vì đưa ra phỏng đoán.",
      },
      {
        q: "Vì sao không thấy con số khoảng cách theo mét?",
        a: "Vì chưa hiệu chuẩn camera và chưa có tốc độ xe đáng tin cậy. RoadWatch dùng rủi ro trong không gian ảnh và ghi rõ điều đó trong từng gói bằng chứng, thay vì đưa ra một con số mét không kiểm chứng được.",
      },
      {
        q: "Dữ liệu được lưu ở đâu?",
        a: "Sự kiện, bằng chứng, số đo và nhật ký kiểm toán nằm trong cơ sở dữ liệu cục bộ trên chính thiết bị. Việc đưa lên cloud là tùy chọn phục vụ đánh giá.",
      },
      {
        q: "Thiết bị nào chạy được?",
        a: "Hiện đã chạy trên laptop Windows dùng GPU AMD qua DirectML, và trên CPU. Đường TensorRT FP16 cho Jetson Orin đã chuẩn bị nhưng số đo trên phần cứng thật vẫn đang chờ.",
      },
    ],
  },
  inspector: {
    eyebrow: "EVIDENCE INSPECTOR",
    title: "Vì sao cảnh báo này được phát — và vì sao ba cái kia thì không",
    lede:
      "Kéo thanh thời gian để dừng ở bất kỳ thời điểm nào trong vòng lặp. Panel bên phải hiển thị đúng những gì Alert Governor nhìn thấy: ứng viên event, năm cổng kiểm tra theo thứ tự, và kết quả cuối cùng.",
    candidate: "Ứng viên đang xét",
    noCandidate: "Không có ứng viên nào vượt ngưỡng rủi ro",
    gatesTitle: "Cổng kiểm tra",
    tracksTitle: "Track đang theo dõi",
    outcomeTitle: "Kết quả",
    gates: {
      temporal: { name: "Xác nhận thời gian", help: "Đối tượng phải xuất hiện đủ số frame liên tiếp." },
      corridor: { name: "Hành lang ego", help: "Phải nằm trên đường đi thực tế của xe, không chỉ trong khung hình." },
      lane: { name: "Chất lượng lane", help: "Lane phải đủ tin cậy; dưới ngưỡng thì LDW bị khoá." },
      risk: { name: "Ngưỡng rủi ro", help: "Điểm risk phải vượt ngưỡng của mức cảnh báo tương ứng." },
      budget: { name: "Ngân sách âm thanh", help: "Cooldown, chống lặp và luật giao thông đông." },
    },
    outcomes: {
      spoken: "Đã phát cảnh báo",
      hud: "Chỉ hiển thị HUD",
      suppressed: "Bị chặn",
      idle: "Không có gì để nói",
    },
    reasons: {
      temporal: "Mới 2/3 frame xác nhận — một khung hình đơn lẻ không được phép thành lời nói.",
      dense: "Đường đông: biển tốc độ hạ xuống HUD để nhường kênh âm thanh cho nguy cơ thật.",
      risk: "Risk 0.41 dưới ngưỡng warning 0.55 — xe phía trước gần nhưng chưa thu hẹp khoảng cách.",
      cooldown: "Cùng đối tượng vừa được cảnh báo — cooldown 12 giây chặn việc nói lại.",
    },
    ledger: {
      title: "Sổ ghi 18 giây",
      considered: "Ứng viên",
      spoken: "Đã nói",
      hud: "Chỉ HUD",
      suppressed: "Bị chặn",
      note: "Ba trong năm ứng viên không thành tiếng nói. Đó là tỉ lệ mà một hệ thống chống alert fatigue cần có.",
    },
    cols: { track: "Track", conf: "Conf", hits: "Frame", ego: "Ego" },
    yes: "có",
    no: "không",
    scrub: "Thời điểm trong vòng lặp",
  },
  audio: {
    off: "Bật âm thanh",
    on: "Tắt âm thanh",
    label: "Beep",
    note:
      "Beep được tổng hợp ngay trong trình duyệt theo đúng thông số của sản phẩm (70 ms, nghỉ 110 ms). Giọng nói tiếng Việt thật do Piper tạo và chạy offline trên thiết bị.",
  },
  pipeline: {
    title: "Đường đi của một khung hình",
    caption:
      "Nhánh SLM nằm ngoài đường quyết định: nó chỉ nhận event đã được chấp nhận và không bao giờ tạo, sửa hay chặn một cảnh báo.",
    aria:
      "Sơ đồ pipeline RoadWatch: camera qua ba model perception, tracking, risk engine, traffic context, tới Alert Governor — nơi chỉ một cảnh báo được phát ra HUD và giọng nói; nhánh SLM tách khỏi đường này.",
    nodes: {
      camera: "Camera / replay",
      gateway: "Frame Gateway",
      object: "Object",
      sign: "Biển báo",
      lane: "Lane + drivable",
      track: "Tracking",
      risk: "Risk Engine",
      ctx: "Traffic Context",
      gov: "Alert Governor",
      out: "HUD · beep · TTS",
      store: "SQLite evidence",
      slm: "SLM giải thích",
    },
    edges: {
      drop: "bỏ frame cũ",
      evidence: "bằng chứng theo thời gian",
      one: "đúng một event",
      audit: "ghi audit",
      async: "bất đồng bộ",
    },
    offPath: "ngoài đường quyết định",
    critical: "đường quyết định — chỉ logic deterministic",
  },
  chart: {
    title: "Độ trễ đầu–cuối qua ba phiên bản",
    sub: "Dải từ P50 tới P95 trên cùng một clip replay, cùng một máy AMD.",
    axis: "mili giây",
    gate: "Gate R1 · 150 ms",
    p50: "P50",
    p95: "P95",
    note:
      "P95 là con số quan trọng: 95% khung hình không chậm hơn mức đó. Dải hẹp dần nghĩa là pipeline ổn định hơn, không chỉ nhanh hơn ở trung vị.",
  },
  cta: {
    title: "Xem RoadWatch hoạt động",
    lede: "Bản demo chạy trên video replay, có Driver HUD, Engineer Console và toàn bộ bằng chứng phía sau mỗi cảnh báo.",
    primary: "Xem bản demo",
    secondary: "Đọc benchmark",
    tertiary: "Tham gia pilot",
  },
  footer: {
    tagline: "Trợ lý cảnh báo hỗ trợ lái chạy trên thiết bị, dành cho giao thông hỗn hợp Việt Nam.",
    cols: [
      { title: "Sản phẩm", links: ["Năng lực nhận diện", "Kịch bản cảnh báo", "Chạy trên edge"] },
      { title: "Kỹ thuật", links: ["Kiến trúc", "Benchmark", "Model promotion"] },
      { title: "Trách nhiệm", links: ["Giới hạn an toàn", "Quyền riêng tư", "Câu hỏi thường gặp"] },
    ],
    legal: "RoadWatch Copilot — prototype nghiên cứu. Chưa phải hệ thống ADAS thương mại đã chứng nhận.",
    guardrail: "Chỉ hỗ trợ cảnh báo — không tự lái, không phanh, không đánh lái.",
  },
};

const en: Copy = {
  nav: {
    product: "Product",
    how: "How it works",
    benchmark: "Benchmark",
    safety: "Safety",
    cta: "View demo",
    menu: "Open menu",
  },
  hero: {
    eyebrow: "ROADWATCH COPILOT · L0 DRIVER ALERT",
    h1a: "Warn earlier.",
    h1b: "And know when to stay quiet.",
    lede:
      "An alerting assistant that runs on the device itself, reading the forward camera to recognise cars, motorcycles, pedestrians, lanes and Vietnamese road signs — then speaking only when the evidence is actually there. RoadWatch never steers, never brakes, never replaces the driver.",
    ctaPrimary: "See the live demo",
    ctaSecondary: "Read the benchmark",
    badges: ["On-device AI", "82 Vietnam sign classes", "No cloud required", "L0 · alerts only"],
    sceneLabel: "PERCEPTION VIEW",
    sceneDisclaimer: "A simulation of the perception interface and its alert logic. Not live model inference.",
  },
  trust: {
    label: "Perception coverage",
    items: [
      { value: "6", label: "road-user classes" },
      { value: "82", label: "Vietnam sign classes" },
      { value: "3", label: "independent perception models" },
      { value: "600 s", label: "verified ground truth" },
      { value: "0", label: "vehicle control commands" },
    ],
  },
  demo: {
    eyebrow: "LIVE ROAD DEMO",
    title: "Watch the pipeline work, not a description of it",
    lede:
      "The frame below replays RoadWatch's actual order of decisions: detection → temporal evidence → risk → Alert Governor. Most of the time it says nothing at all — that is the design, not a failure.",
    scenarios: [
      { id: "day", label: "Day" },
      { id: "night", label: "Night" },
      { id: "rain", label: "Rain" },
    ],
    panelTitle: "LIVE PERCEPTION",
    objects: "Objects",
    context: "Road context",
    alert: "Alert",
    laneDetected: "Lane detected",
    drivable: "Drivable area",
    density: "Traffic density",
    audioRoute: "Output channel",
    silent: "No hazard worth interrupting for",
    silentNote: "Objects are still tracked and shown, but none of them clears the bar for audio.",
    playing: "Running",
    paused: "Paused",
    play: "Play",
    pause: "Pause",
    severity: { critical: "Critical", warning: "Warning", advisory: "Advisory" },
    classNames: {
      car: "Car",
      motorcycle: "Motorcycle",
      pedestrian: "Pedestrian",
      truck: "Truck",
      sign: "Traffic sign",
    },
    routeNames: {
      beep_tts: "Beep + voice",
      tts: "Voice + banner",
      hud: "HUD only",
      none: "Silent",
    },
    note: "To watch the real pipeline: run the backend and pass `streamUrl=\"/api/stream.mjpg\"` to this component.",
  },
  capability: {
    eyebrow: "DETECTION CAPABILITIES",
    title: "A perception system, not an object detector",
    lede:
      "Three models run independently and are fused through temporal evidence. No single model is allowed to raise an alert on its own.",
    cards: [
      {
        tag: "Vehicles",
        title: "Vehicle awareness",
        body: "Tracks the vehicles ahead and alongside with stable track IDs, size history and a closing-rate trend.",
        items: ["Car", "Bus", "Truck", "Motorcycle", "Bicycle"],
      },
      {
        tag: "Vulnerable road users",
        title: "Pedestrians and two-wheelers",
        body: "Prioritises vulnerable road users inside the drivable area and ego corridor — the defining trait of Vietnamese mixed traffic.",
        items: ["Pedestrian", "Cyclist", "Crossing on foot", "Walking at the road edge"],
      },
      {
        tag: "Vietnam traffic signs",
        title: "Local sign reading",
        body: "A sign detector paired with a dedicated speed-value classifier, gated by confidence and an explicit `unknown` class so it never guesses.",
        items: ["82 sign classes", "Prohibitory and warning", "Speed limits", "Temporal confirmation"],
      },
      {
        tag: "Road understanding",
        title: "Lanes and drivable area",
        body: "The lane mask and drivable-area mask decide whether an object actually sits in the vehicle's path.",
        items: ["Lane detection", "Drivable area", "Ego corridor", "LDW locked on poor lanes"],
      },
    ],
  },
  how: {
    eyebrow: "HOW ROADWATCH WORKS",
    title: "Four steps from frame to spoken warning",
    steps: [
      { step: "Camera", title: "Capture", body: "Reads the forward camera or a replay clip; every frame is timestamped and stale frames are dropped." },
      { step: "On-device AI", title: "Detect", body: "Three models run on the device to find road users, traffic signs and lane geometry." },
      { step: "Risk analysis", title: "Assess risk", body: "The tracker holds IDs while the system watches position and closing rate across frames before it concludes anything." },
      { step: "Driver alert", title: "Warn", body: "The Alert Governor picks exactly one alert that matters most and sends a beep or Vietnamese voice line." },
    ],
    highlight:
      "RoadWatch analyses locally first, so alerts never wait on a round trip to the cloud. Evidence can be synchronised later, when connectivity exists and the operator opts in.",
  },
  scenarios: {
    eyebrow: "ALERT SCENARIOS",
    title: "What detection is actually worth on the road",
    lede: "Every alert type has its own trigger, its own priority and exactly one output channel.",
    labels: {
      trigger: "Trigger condition",
      level: "Alert level",
      output: "How it reaches the driver",
      control: "Control action",
      none: "None",
    },
    tabs: [
      {
        id: "fcw",
        tab: "Forward collision",
        title: "Forward collision warning",
        body: "RoadWatch detects the image-space gap to the vehicle ahead closing rapidly and issues both a visual and a spoken warning.",
        trigger: "Sustained box expansion across frames with the object inside the ego corridor",
        level: "Critical",
        levelTone: "critical",
        output: "Priority beep + voice + red banner",
        voice: "“Vehicle ahead braking hard, slow down.”",
      },
      {
        id: "vru",
        tab: "Pedestrian",
        title: "Vulnerable road user",
        body: "A pedestrian inside the drivable area or crossing into it outranks a vehicle carrying the same nominal risk.",
        trigger: "Person on drivable area with lateral motion toward the ego corridor",
        level: "Warning",
        levelTone: "warning",
        output: "Voice + banner",
        voice: "“Pedestrian ahead on the left.”",
      },
      {
        id: "moto",
        tab: "Motorcycle cut-in",
        title: "Two-wheeler cut-in",
        body: "A motorcycle moving into the ego lane is handled on a short motion window so the warning lands in time, while still requiring confirmation.",
        trigger: "Two-wheeler track moving laterally into the ego lane, confirmed over frames",
        level: "Warning",
        levelTone: "warning",
        output: "Voice + banner",
        voice: "“Motorcycle ahead on the right, slow down.”",
      },
      {
        id: "ldw",
        tab: "Lane departure",
        title: "Lane departure",
        body: "Lane departure warnings only unlock when lane quality clears its gate; on poor lanes the system locks LDW rather than guessing.",
        trigger: "Lateral offset over threshold while lane quality passes its gate",
        level: "Warning",
        levelTone: "warning",
        output: "Voice + banner",
        voice: "“Drifting right out of your lane.”",
      },
      {
        id: "sign",
        tab: "Traffic sign",
        title: "Signs and speed limits",
        body: "A sign is spoken only after temporal confirmation and a confidence gate; in dense traffic, speed signs drop to display only.",
        trigger: "Sign confirmed repeatedly and relevant to the current lane",
        level: "Advisory",
        levelTone: "advisory",
        output: "Voice, or HUD only in dense traffic",
        voice: "“Speed limit 40.”",
      },
    ],
  },
  edge: {
    eyebrow: "BUILT FOR THE EDGE",
    title: "Runs locally, measures itself, and keeps a way back",
    lede:
      "Models, rule engine, database, voice and interface all live on the device. Lose the network and the alerting path keeps running.",
    cards: [
      { title: "Low latency", body: "A one-frame queue that drops stale frames instead of accumulating delay, with display fully separated from the inference thread." },
      { title: "Multi-runtime", body: "One ONNX graph across DirectML, CUDA or CPU; a TensorRT FP16 path is prepared for NVIDIA edge hardware." },
      { title: "Offline-first", body: "Login, replay, inference and Vietnamese speech all work with no Internet at all." },
      { title: "Data-respecting", body: "Video does not leave the device by default; only event evidence is written, and it is written locally." },
    ],
    tableTitle: "Runtime configuration",
    tableHead: ["Component", "In use", "State"],
  },
  bench: {
    eyebrow: "BENCHMARK",
    title: "Numbers, with the conditions they were measured under",
    lede:
      "Everything below comes from one specific replay session on an AMD laptop, audio disabled so perception time can be isolated. This is not an automotive-hardware benchmark.",
    conditionLabels: { day: "Day", night: "Night", rain: "Rain", dense: "Dense traffic" },
    noGt: "Not enough data",
    noGtNote:
      "This condition has no timestamp ground truth yet, so no figure is published. It sits in the annotation queue.",
    metrics: {
      processed: "Processed FPS",
      display: "Display FPS",
      p50: "E2E P50",
      p95: "E2E P95",
      errors: "Pipeline errors",
      warmup: "Warmup",
    },
    gate: "Edge candidate target",
    gateNote: "≥ 12 processed FPS and E2E P95 ≤ 150 ms. P95 is met; FPS is not there yet.",
    historyTitle: "Progress across versions",
    historyNote: "Same replay clip, different runtime configuration. Taller is faster.",
    modelTitle: "Model quality",
    modelRows: [
      { name: "Sign detector", metric: "mAP50", value: "0.9874", state: "Active", tone: "active" },
      { name: "Speed classifier", metric: "Top-1", value: "0.9825", state: "Active", tone: "active" },
      { name: "Object baseline", metric: "Event recall", value: "0.8000", state: "Active", tone: "active" },
      { name: "Object V3 candidate", metric: "Event recall", value: "0.6000", state: "Rejected", tone: "candidate" },
      { name: "Lane UFLDv2 candidate", metric: "Fusion FPS", value: "3.04", state: "Rejected", tone: "candidate" },
    ],
    conditions: "Measured condition",
    footnote:
      "RoadWatch keeps the baseline model even when a candidate has prettier training metrics, if that candidate lowers recall on dangerous events. Promotion is decided on event-level safety, never on mAP alone.",
  },
  safety: {
    eyebrow: "SAFETY BOUNDARY",
    title: "RoadWatch is an alerting assistant — not an autonomous driving system",
    lede:
      "This is a design boundary, not a disclaimer line. No API exists anywhere in the codebase that sends a command to the brakes, throttle or steering.",
    notsTitle: "What RoadWatch will not do",
    dosTitle: "What RoadWatch does",
    nots: [
      "Never steers",
      "Never brakes or touches the throttle",
      "Never writes to the vehicle CAN bus",
      "Never replaces the driver's own observation",
      "Never claims distance in metres or TTC in seconds without camera calibration",
    ],
    dos: [
      "Warns visually and by Vietnamese voice",
      "Ranks risk and plays one alert at a time",
      "Keeps the evidence behind every decision",
      "Locks an alert when the evidence is not trustworthy",
      "States the conditions under which each warning is valid",
    ],
    footer:
      "Alerts can be wrong. Weather, light, camera mounting and occlusion all affect the result. The driver remains responsible for watching the road and controlling the vehicle.",
  },
  privacy: {
    eyebrow: "PRIVACY",
    title: "A camera in a car sees faces, plates and where you went",
    lede: "So privacy belongs here, on the front page, not buried in the terms of service.",
    items: [
      { title: "Inference on device", body: "The alerting path is entirely local. No video needs to reach a server for a warning to be raised." },
      { title: "Event evidence only", body: "The system writes events and metrics to a local database rather than storing whole videos by default." },
      { title: "Sync is opt-in", body: "Sending anything to the cloud for evaluation is a deliberate act, never the default." },
      { title: "Redact before sharing", body: "Public demo footage should have faces and plates blurred before it is released." },
    ],
  },
  faq: {
    eyebrow: "FAQ",
    title: "Frequently asked questions",
    items: [
      {
        q: "Does RoadWatch drive the car?",
        a: "No. RoadWatch is L0 — warnings only. There is no code path that sends a command to the brakes, throttle, steering or ECU, and nothing writes to the CAN bus.",
      },
      {
        q: "Does it work without Internet?",
        a: "Yes. Models, rule engine, database, Vietnamese voice and the interface all run locally. Pull the network and login, replay, inference and alerts carry on.",
      },
      {
        q: "What can it recognise?",
        a: "Six road-user classes (person, bicycle, motorcycle, car, bus, truck), 82 Vietnamese traffic-sign classes with speed-value recognition, plus lane masks and drivable area.",
      },
      {
        q: "How is an alert produced?",
        a: "A single frame is never enough. An object has to be tracked across frames, sit in a region relevant to the vehicle's path, and clear a risk threshold — then it passes through the Alert Governor, which applies cooldown and hysteresis and picks exactly one alert to play.",
      },
      {
        q: "What about night and rain?",
        a: "The pipeline still runs, but there is no timestamp ground truth for those conditions yet, so no figures are published. When lane quality drops, the system locks lane-departure warnings instead of guessing.",
      },
      {
        q: "Why are there no distances in metres?",
        a: "Because the camera is not calibrated and there is no trusted vehicle speed. RoadWatch uses image-space risk and says so inside every evidence packet, rather than publishing a metre figure nobody can verify.",
      },
      {
        q: "Where is the data stored?",
        a: "Events, evidence, metrics and the audit log live in a local database on the device itself. Cloud upload is an optional evaluation path.",
      },
      {
        q: "What hardware does it run on?",
        a: "Today: Windows laptops using an AMD GPU through DirectML, and CPU. A TensorRT FP16 path for Jetson Orin is prepared, but physical-hardware measurements are still pending.",
      },
    ],
  },
  inspector: {
    eyebrow: "EVIDENCE INSPECTOR",
    title: "Why this alert was spoken — and why three others were not",
    lede:
      "Drag the timeline to stop anywhere in the loop. The panel on the right shows exactly what the Alert Governor sees: the candidate event, the five gates in order, and the outcome.",
    candidate: "Candidate under review",
    noCandidate: "No candidate above the risk threshold",
    gatesTitle: "Gates",
    tracksTitle: "Active tracks",
    outcomeTitle: "Outcome",
    gates: {
      temporal: { name: "Temporal confirmation", help: "The object must persist across enough consecutive frames." },
      corridor: { name: "Ego corridor", help: "It has to sit in the vehicle's actual path, not merely in frame." },
      lane: { name: "Lane quality", help: "Lane geometry must be trustworthy; below the gate, LDW locks." },
      risk: { name: "Risk threshold", help: "The risk score must clear the threshold for that severity." },
      budget: { name: "Audio budget", help: "Cooldown, repeat suppression and the dense-traffic policy." },
    },
    outcomes: {
      spoken: "Alert spoken",
      hud: "HUD only",
      suppressed: "Suppressed",
      idle: "Nothing worth saying",
    },
    reasons: {
      temporal: "Only 2 of 3 confirmation frames — a single frame is never allowed to become speech.",
      dense: "Dense traffic: the speed sign drops to HUD so the audio channel stays free for real hazards.",
      risk: "Risk 0.41 is under the 0.55 warning threshold — the vehicle ahead is close but not closing.",
      cooldown: "Same object was just announced — a 12-second cooldown blocks saying it again.",
    },
    ledger: {
      title: "18-second ledger",
      considered: "Candidates",
      spoken: "Spoken",
      hud: "HUD only",
      suppressed: "Suppressed",
      note: "Three of five candidates never became speech. That ratio is what an anti-alert-fatigue system is for.",
    },
    cols: { track: "Track", conf: "Conf", hits: "Frames", ego: "Ego" },
    yes: "yes",
    no: "no",
    scrub: "Position in loop",
  },
  audio: {
    off: "Enable sound",
    on: "Mute",
    label: "Beep",
    note:
      "The beep is synthesised in your browser to the product's own spec (70 ms on, 110 ms gap). The real Vietnamese voice is produced by Piper and runs offline on the device.",
  },
  pipeline: {
    title: "The path of a single frame",
    caption:
      "The SLM branch sits off the decision path: it only receives accepted events and can never create, alter or block an alert.",
    aria:
      "RoadWatch pipeline diagram: camera through three perception models, tracking, risk engine and traffic context into the Alert Governor, which releases exactly one alert to HUD and voice; the SLM branch hangs off that path.",
    nodes: {
      camera: "Camera / replay",
      gateway: "Frame gateway",
      object: "Objects",
      sign: "Signs",
      lane: "Lane + drivable",
      track: "Tracking",
      risk: "Risk engine",
      ctx: "Traffic context",
      gov: "Alert Governor",
      out: "HUD · beep · TTS",
      store: "SQLite evidence",
      slm: "SLM explanation",
    },
    edges: {
      drop: "drops stale frames",
      evidence: "temporal evidence",
      one: "exactly one event",
      audit: "audit trail",
      async: "async",
    },
    offPath: "off the decision path",
    critical: "decision path — deterministic logic only",
  },
  chart: {
    title: "End-to-end latency across three releases",
    sub: "The P50-to-P95 band on the same replay clip and the same AMD machine.",
    axis: "milliseconds",
    gate: "R1 gate · 150 ms",
    p50: "P50",
    p95: "P95",
    note:
      "P95 is the number that matters: 95% of frames are no slower than that. A narrowing band means the pipeline got steadier, not just faster at the median.",
  },
  cta: {
    title: "See RoadWatch in action",
    lede: "The demo runs on replay footage, with the Driver HUD, the Engineer Console and the full evidence behind every alert.",
    primary: "Open the demo",
    secondary: "Read the benchmark",
    tertiary: "Join the pilot",
  },
  footer: {
    tagline: "An on-device driver-alerting assistant built for Vietnamese mixed traffic.",
    cols: [
      { title: "Product", links: ["Detection capabilities", "Alert scenarios", "Built for the edge"] },
      { title: "Engineering", links: ["Architecture", "Benchmark", "Model promotion"] },
      { title: "Responsibility", links: ["Safety boundary", "Privacy", "FAQ"] },
    ],
    legal: "RoadWatch Copilot — research prototype. Not a certified commercial ADAS.",
    guardrail: "Warning support only — no self-driving, no braking, no steering.",
  },
};

export const COPY: Record<Lang, Copy> = { vi, en };
