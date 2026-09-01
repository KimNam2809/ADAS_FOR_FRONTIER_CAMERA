# RoadWatch Landing v1.0 — vận hành, bằng chứng và rollback

Ngày: 2026-08-30 · Work ID: WORK-20260830-LP-002

## 1. Trạng thái

**Đã triển khai bản local có tương tác và build tĩnh prerender. Chưa public deploy.**
Landing không thay trang đăng nhập, Driver/Engineer, `dist-ui-v4`, model, Piper,
Traffic Context hoặc ngưỡng cảnh báo của ứng dụng RoadWatch hiện tại.

## 2. Mở ngay trên máy hiện tại

Từ thư mục `roadwatch`, mở PowerShell:

```powershell
.\scripts\start-landing.ps1
```

Mở **http://127.0.0.1:4174/**. Script build riêng rồi phục vụ bản production.
Nếu preview này đã chạy thì mở URL trực tiếp, không khởi động thêm process cùng port.
`Ctrl+C` tại terminal của landing để dừng, không ảnh hưởng app RoadWatch khác.

Muốn nút “Mở demo” đi vào ứng dụng local thay vì GCP:

```powershell
# Terminal 1: ứng dụng phân tích như trước
.\scripts\start.ps1
# Terminal 2: landing
.\scripts\start-landing.ps1 -DemoUrl "http://127.0.0.1:8000"
```

Mặc định CTA vẫn là URL demo GCP đã có; landing không kiểm soát cold start hoặc
quyền đăng nhập của service đó. Tài khoản demo của app: `driver/driver123` và
`engineer/engineer123`. Không đưa credential cloud/Kaggle vào frontend.

Các script gọi trực tiếp Node/Vite/TypeScript đã cài, tránh npm shim đang lỗi
trên máy này. Không sửa cài đặt npm toàn máy.

## 3. Nội dung và tương tác đã có

| Khối | Hành vi |
|---|---|
| Hero | Logo thật, khung hình dashcam thật, CTA demo và trải nghiệm |
| Bài toán | Giải thích chạy gần không đồng nghĩa nguy hiểm |
| Scenario explorer | 4 replay, video 16:9 không kéo méo, native pause/seek, chọn mốc sự kiện |
| Traffic Context | Thay mật độ/nguy cơ để hiểu HUD-only, TTS, critical; gắn nhãn mô phỏng chính sách |
| Voice samples | 3 WAV Piper release, transcript, một audio element, không autoplay tiếng |
| Product tour | Ảnh chụp local Driver/Engineer; role switch, giải thích từng chức năng, mở ảnh đầy đủ |
| Pipeline | 6 bước tương tác, phân biệt perception/risk/governor/TTS/evidence |
| Deployment | Local/edge, AAOS, GCP: công dụng và giới hạn riêng |
| Evidence | Runtime JSON, sign metrics, quyết định không promote model recall thấp |
| Safety/FAQ/CTA | Warning-only, giới hạn OEM/calibration, câu hỏi thường gặp, báo cáo và repo |

Typography hệ thống, navy/trắng/xanh, animation transform ngắn, không WebGL,
không thư viện motion nặng, không polling. `prefers-reduced-motion` tắt motion.
Nội dung chính được prerender vào HTML; FAQ native vẫn đọc/mở khi JS tắt.
Những tương tác thay state và tải media cần JavaScript.

## 4. Media và provenance

| Replay | Nguồn | Bắt đầu nguồn | Thời lượng ghi | Event ghi nhận |
|---|---|---:|---:|---:|
| dense | dashcam_vietnam_traffic_multi.mp4 | 6s | 18s | 14 |
| day | test_video10.mp4 | 0s | 18s | 4 |
| night | dashcam_vietnam_night.mp4 | 0s | 18s | 14 |
| rain | dashcam_vietnam_rain+night.mp4 | 0s | 18s | 5 |

Replay là JPEG output thật của service được ghi thành MP4 ở **12 Hz wall-clock**,
không phải phép đo FPS của camera hoặc inference. Thời gian player và thời gian
video nguồn có thể khác do cadence/warmup; JSON giữ hai trường riêng.
Đã tắt audio khi ghi, không tự tạo event. `audio_action` là kênh dự kiến của
event, không phải bằng chứng đã phát âm trong replay. UI hiển thị suppression reason.
Một event xuất hiện không chứng minh model nhận đúng: chưa có human GT cho các clip này.

Ảnh Driver/Engineer chụp từ ứng dụng local thực tế, có caption. Clip H264
`media/landing_preview_day.mp4` được tạo riêng cho phiên screenshot; bản gốc không đổi.
Screenshot có thể chứa box sai của model; không chỉnh ảnh để làm đẹp kết quả nhận diện.

Mẫu giọng sinh trực tiếp bằng `PiperSynthesizer` và canonical copy `vnext`:

- “Cảnh báo va chạm” — 0.78s.
- “Xe máy bên phải; giảm tốc độ.” — 1.44s.
- “Giới hạn 60 ki-lô-mét/giờ phía trước.” — 2.17s.

Provider `piper/vi_VN-vais1000-medium`, sample rate 22050 Hz. “Trúc Ly” là alias
release, không phải speaker ID được model công bố.

`frontend/landing-public/media-manifest.json` chứa SHA-256 cho 25 tài sản.
Video, ảnh, WAV, documents projection và dist không commit Git. Sau khi clone,
cần tài sản local hoặc chuẩn bị lại. Chưa công bố media ra ngoài: phải duyệt
quyền tái phân phối, biển số/khuôn mặt, nội dung tài liệu và license voice trước.
Không tải stock bên thứ ba; dùng tư liệu dự án để tránh minh họa sai năng lực.

## 5. Chuẩn bị lại sau khi clone hoặc thay dữ liệu

Cần Node dependencies của frontend, Python `.venv`, model và voice của RoadWatch.
Gói FFmpeg được cài tách khỏi môi trường inference:

```powershell
& .\.venv\Scripts\python.exe -m pip install --target artifacts/landing-tools imageio-ffmpeg==0.6.0
.\scripts\build-landing.ps1 -PrepareMedia
& .\.venv\Scripts\python.exe scripts/capture_landing_replays.py --runtime directml
# CPU khác máy có thể dùng --runtime cpu; không coi kết quả đó là benchmark AMD.
& .\.venv\Scripts\python.exe scripts/finalize_landing_assets.py
.\scripts\build-landing.ps1
& .\.venv\Scripts\python.exe scripts/audit_landing_build.py
```

Capture tạo SQLite riêng trong `reports/landing-v1`; không ghi `configs/runtime.json`.
Không train, không gọi cloud hoặc tải model tự động. Để chụp ảnh UI mới, chạy app,
đăng nhập, chạy clip, lưu screenshot thật thành `driver-capture.png` và
`engineer-capture.png` ở `frontend/landing-public/media`, rồi chạy finalize/build.
Nếu không có screenshot, tour có fallback rõ ràng; không bịa ảnh runtime.

## 6. Bằng chứng kiểm thử

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_landing_v1.py tests/test_ui_contract.py -q
.\scripts\build-landing.ps1
& .\.venv\Scripts\python.exe scripts/audit_landing_build.py
```

- **18/18 tests PASS** (6 landing contract + 12 UI contract hiện có).
- TypeScript và Vite client/SSR build PASS; prerender xuất `index.html`.
- JS gzip khoảng **69 KB**, CSS gzip khoảng **4.4 KB**; xem số chính xác trong
  `reports/landing-v1/build-audit.json` (gzip level khác Vite nên không giống tuyệt đối).
- 25/25 file trong asset manifest đúng SHA-256; tổng dist khoảng 25 MB bao gồm
  video chỉ tải sau tương tác. Đây không phải lượng tải ban đầu.
- Browser QA: desktop và viewport 390px; policy switches; timeline seek 17.8s;
  đổi clip reset về 0; replay dense/night/rain; role tour; pipeline/deployment/
  evidence tabs; mobile menu; Piper sample switching. Không có lỗi console
  trong các lượt đã kiểm tra; không ảnh hỏng/overflow ngang tại viewport kiểm tra.
- Chưa đo Lighthouse/throttled Core Web Vitals/INP/CLS hoặc test mọi browser;
  không công bố đã đạt tất cả performance target.
- Chưa làm 5-person comprehension/human listening gate. Browser play success
  và WAV hợp lệ không thay cho đánh giá phát âm/cảm giác dễ chịu của người nghe.

Số liệu runtime trình bày lấy từ JSON gốc `benchmark-performance-release-20260829.json`:
11.48 processed FPS, 19.4 display FPS, P50 89.26ms, P95 145.01ms, 20s test_video10,
audio off, AMD local. Summary Markdown cũ chứa số khác; không sửa lịch sử,
landing chọn JSON gốc có timestamp. Đây **không phải benchmark mới của landing**.

## 7. GCP: gói tách biệt, chưa triển khai

`deploy/gcp/landing/Dockerfile` + `nginx.conf`: chỉ static files, port 8080,
gzip/cache theo loại tài sản, security headers, `/api/*` trả 404, không model/GPU.
Context Docker chỉ là `frontend/dist-landing`, không phải toàn repo.
Docker daemon hiện chưa chạy trên máy: đã kiểm tra và ghi nhận named pipe missing;
chưa thực hiện `docker build`, Nginx runtime smoke hoặc Cloud Run rollout.

Sau khi human media/privacy gate PASS:

```powershell
.\scripts\package-landing.ps1 -PublicMediaApproved
docker build -t roadwatch-landing:1.0 frontend/dist-landing
docker run --rm -p 8088:8080 roadwatch-landing:1.0
```

Kiểm tra localhost:8088, healthz, HTTP Range/seek, CSP/audio, lỗi asset. Sau đó
mới chọn registry/service mới trong `c3-roadwatch-162`, build/push image có digest,
Cloud Run CPU nhỏ (đề xuất 1 CPU/256–512 MiB, max instances được giới hạn) và canary.
Đây là cấu hình dự kiến, chưa benchmark container. Không đổi service inference,
domain, IAM hoặc billing trong phiên này. Không dùng `gcloud run deploy --source .`
từ repository root. Domain/sitemap/canonical/OG absolute URL chốt sau khi có
URL landing được duyệt; không gắn tên miền chưa sở hữu.

## 8. Fallback và cấu trúc chỉnh sửa

- App cũ vẫn chạy bằng `scripts/start.ps1`; landing không thay entry của app.
- Legacy landing source được giữ nguyên. Preview bằng:

```powershell
.\scripts\start-landing.ps1 -Legacy -Port 4175
# http://127.0.0.1:4175/landing-legacy.html
```

- Legacy dùng dev server/source cũ, không phải bản production mới; chưa browser
  acceptance lại legacy trong phiên này. Snapshot file cấu hình/entry trước sửa
  ở `artifacts/landing-v1-backup`. Không reset toàn worktree để rollback landing.
- Copy/content/interactions: `frontend/src/landing/v1/LandingV1.tsx`.
- Style/responsive/motion: `frontend/src/landing/v1/landing-v1.css`.
- Client/SSR entry: `landing-v1-main.tsx`, `landing-prerender.tsx`.
- Build: `vite.landing.config.ts`, `vite.landing.ssr.config.ts`, `prerender-landing.mjs`.
- Clip/canonical WAV projection: `scripts/prepare_landing_assets.py`.
- Real replay: `scripts/capture_landing_replays.py`.
- Hash/media conversion: `scripts/finalize_landing_assets.py`.

Đổi source/voice/copy/model phải ghi lại media và hash, chạy tests + browser QA;
không chỉ sửa nhãn của kết quả cũ thành tên model mới.

## 9. Triển chiêu duyệt bản 1.0 như thế nào?

1. Mở localhost:4174, đọc hero: có hiểu đây là cảnh báo hỗ trợ, không tự lái?
2. Chọn 4 clip, phát/pause/tua; chọn một event và đối chiếu khung hình.
3. Chuyển ngữ cảnh đông/thưa và 3 mức risk: có hiểu vì sao HUD-only/âm thanh?
4. Nghe 3 mẫu riêng rồi bấm chuyển nhanh: có bị cắt, sai tiếng hoặc chồng không?
5. Chuyển Driver/Engineer, mở ảnh lớn và kiểm tra mô tả.
6. Mở mục số liệu, kiểm tra có phân biệt snapshot/model/system không.
7. Trên điện thoại, thử menu, video và FAQ.
8. Gửi `PASS LANDING LOCAL V1` hoặc `REJECT + section + ảnh/lỗi`.

Duyệt giao diện không đồng nghĩa duyệt công bố video. Trước public cần xác nhận
riêng quyền media/privacy và kết quả human comprehension; không tự gắn PASS thay người.
