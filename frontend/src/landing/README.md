# RoadWatch — Landing Page

Trang giới thiệu song ngữ (VI/EN) cho RoadWatch Copilot, viết bằng React + TypeScript,
dùng chung toolchain Vite với HMI hiện có. Không phụ thuộc thư viện ngoài.

## Cấu trúc

```text
frontend/
├── landing.html                  # entry HTML thứ hai (multi-page Vite)
└── src/
    ├── landing-main.tsx          # entry point React
    └── landing/
        ├── LandingPage.tsx       # toàn bộ 14 section
        ├── DashcamScene.tsx      # canvas mô phỏng khung nhìn perception
        ├── content.ts            # copy VI/EN + số liệu benchmark
        ├── landing.css           # design tokens + layout (prefix `rw-`)
        └── README.md
```

Mọi class CSS đều có tiền tố `rw-`, nên `landing.css` không va chạm với
`src/styles.css` của Driver HUD / Engineer Console.

## Cách bật (Vite multi-page)

Thêm `rollupOptions.input` vào `frontend/vite.config.ts`:

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        landing: resolve(__dirname, "landing.html"),
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
```

Sau khi build, trang nằm ở `dist/landing.html`. Dev: `npm run dev` rồi mở
`http://127.0.0.1:5173/landing.html`.

Muốn FastAPI phục vụ trang tại `/landing`, thêm một route trả về
`landing.html` trong bundle frontend đang dùng — cùng cách `index.html` đang
được phục vụ ở `backend/roadwatch/api.py`.

## Dùng như một component

```tsx
import LandingPage from "./landing/LandingPage";

<LandingPage
  defaultLang="vi"                 // "vi" | "en"
  demoHref="/"                     // link nút "Xem demo"
  streamUrl="/api/stream.mjpg"     // tuỳ chọn: thay canvas mô phỏng bằng stream thật
/>
```

| Prop | Mặc định | Ý nghĩa |
|---|---|---|
| `defaultLang` | `"vi"` | Ngôn ngữ khởi tạo. Lựa chọn của người xem được nhớ trong `localStorage` (có `try/catch`). |
| `demoHref` | `"/"` | Đích của nút "Xem demo" / "Xem bản demo". |
| `streamUrl` | — | Khi truyền, `DashcamScene` render `<img>` MJPEG thay cho canvas mô phỏng. |

## Về khung hình perception

`DashcamScene.tsx` là **mô phỏng giao diện**, không phải suy luận model. Kịch bản
được viết cứng theo đúng thứ tự quyết định của hệ thống thật:
detection → temporal evidence → risk → Alert Governor → một kênh phát duy nhất.
Chuỗi 18 giây gồm ba sự kiện (cut-in xe máy → biển 40 km/h HUD-only → FCW critical)
và các khoảng im lặng ở giữa — đúng với hành vi "biết im lặng" của sản phẩm.
Dòng chú thích ngay dưới khung hình nói rõ điều này; **không nên bỏ dòng đó**.

Ba kịch bản `day` / `night` / `rain` đổi bảng màu và chất lượng lane. Ở `night`
và `rain`, `laneQuality` xuống dưới `0.5` nên khung hiển thị `LDW LOCKED` — phản
ánh đúng luật khoá LDW khi lane không đủ tin cậy.

## Số liệu trên trang

Toàn bộ con số nằm trong `content.ts` (`EVIDENCE`, `SPEC_ROWS`, `BENCH_CONDITIONS`),
lấy từ:

- `docs/PERFORMANCE_STREAMING_OPTIMIZATION_2026-08-29.md` — 11.28 processed FPS,
  23.07 display FPS, E2E P50 89.96 ms, P95 149.91 ms, warmup 7 990.83 ms, 0 lỗi pipeline.
- `docs/VALIDATION.md` — lịch sử v0.1 → v0.2.
- `docs/ROADWATCH_TECHNICAL_REPORT.md` §3.2 — sign mAP50 0.9874, speed top-1 0.9825,
  object baseline event recall 0.8000 vs V3 candidate 0.6000, UFLDv2 3.04 FPS.
- `docs/MASTER_ACTION_PLAN.md` §1.3 — gate R1: ≥ 12 FPS, E2E P95 ≤ 150 ms.

Điều kiện **Ban đêm / Trời mưa / Đường đông** để trạng thái `no-gt` và hiển thị
"Chưa đủ dữ liệu", vì chưa có ground truth theo timestamp cho các điều kiện đó.
Khi có report, đổi `status` thành `"measured"` và điền số — không cần sửa JSX.

Trang cố ý **không** dùng các phát ngôn kiểu "99% accuracy", "prevents accidents",
"realtime 30 FPS", hay khoảng cách theo mét — đúng theo `docs/SAFETY.md`.

## Khả năng truy cập

- Màu không bao giờ là tín hiệu duy nhất: mỗi mức cảnh báo có cả chữ (`CRITICAL`),
  chấm màu và vị trí riêng.
- Ba trạng thái theme được xử lý ở mức token: `:root`, `@media (prefers-color-scheme: dark)`
  có guard `:not([data-theme="light"])`, và `:root[data-theme="dark"]`.
- `prefers-reduced-motion: reduce` tắt scroll-reveal và đóng băng canvas ở một
  khung hình đại diện.
- Tab scenario dùng `role="tab"` / `role="tabpanel"`, bộ lọc dùng `aria-pressed`,
  FAQ dùng `<details>` gốc nên hoạt động cả khi JavaScript lỗi.

---

## v2 — những gì thêm vào (2026-08-30)

### Evidence Inspector
Thanh tua 18 giây dưới khung hình + panel bên phải hiển thị **đúng thứ tự Alert
Governor kiểm tra**: ứng viên event → 5 cổng (`temporal`, `corridor`, `lane`,
`risk`, `budget`) → kết quả. Chuỗi quyết định nằm trong hằng `TRACE` của
`DashcamScene.tsx`; các vạch màu trên thanh tua đến từ `TRACE_MARKS`.

Bốn cửa sổ im lặng đều có lý do khác nhau — đó là điểm mà một trang chỉ khoe
detection không thể trình bày:

| t (s) | Ứng viên | Kết quả | Vì sao |
|---|---|---|---|
| 2.6 – 5.0 | cut-in xe máy | Bị chặn | mới 2/3 frame xác nhận |
| 5.0 – 7.3 | cut-in xe máy | Đã nói | đủ cả 5 cổng |
| 7.7 – 9.1 | biển 40 km/h | Chỉ HUD | đường đông, nhường kênh âm thanh |
| 9.1 – 11.2 | FCW xe #7 | Bị chặn | risk 0.41 < ngưỡng 0.55 |
| 11.2 – 14.4 | FCW xe #7 | Đã nói | risk 0.83 ≥ 0.72 |
| 14.4 – 16.4 | FCW xe #7 | Bị chặn | cooldown 12 s |

Ở kịch bản **Ban đêm / Trời mưa**, `laneQuality` tụt dưới 0.5 nên cổng `lane`
chuyển sang trạng thái fail ngay trên panel — phản ánh đúng luật khoá LDW.

### Âm thanh
Nút "Bật âm thanh" tổng hợp beep bằng Web Audio theo thông số trong
`docs/TRAFFIC_CONTEXT_ALERT_POLICY.md` (xung 70 ms, nghỉ 110 ms; critical 3 xung,
warning 2, advisory 1). `AudioContext` chỉ được tạo sau cú bấm của người dùng —
trang không bao giờ tự phát tiếng. Giọng nói tiếng Việt thật vẫn là Piper offline;
trang nói rõ điều này ngay dưới khung demo.

### Sơ đồ pipeline (`Diagrams.tsx`)
SVG vẽ tay, không thư viện. Dấu ngoặc ngang bao toàn bộ đường quyết định, nhánh
SLM nằm dưới dấu ngoặc — biến câu "SLM không nằm trên critical path" thành hình.

### Biểu đồ độ trễ (`Diagrams.tsx`)
Dải P50 → P95 cho ba phiên bản, một màu duy nhất (không dùng cặp xanh–tím vì
chúng không tách được với người mù màu deutan), đường ngưỡng R1 150 ms vẽ nét
đứt kèm nhãn chữ. Số liệu trực tiếp từ `EVIDENCE.history`.

### Tiện ích
- Bảng lệnh `⌘K` / `Ctrl+K`: nhảy section, đổi ngôn ngữ, bật/tắt âm thanh.
- Thanh tiến độ cuộn trên navbar.
