# RoadWatch — Unified Deployment Architecture

> Phiên bản: 2026-08-24  
> Mục tiêu: một kiến trúc dùng chung cho Web demo công khai, AAOS emulator và
> Edge/ô tô thật.  
> **Official live URL khuyên dùng sau DNS mapping:** `https://c3-roadwatch-162.io.vn`
> Trạng thái: R0 Cloud Run public fallback đã triển khai và acceptance-tested trong
> project `c3-roadwatch-162`; custom domain/DNS và worker/cached-result plane vẫn
> chưa pass acceptance.

## 1. Quyết định kiến trúc

RoadWatch được tổ chức thành ba mặt phẳng có cùng một hợp đồng dữ liệu:

1. **Safety/Edge Plane** — chạy cục bộ trên laptop demo, edge box hoặc Jetson.
   Đây là nơi duy nhất được phép chạy perception, tracking, risk engine và Alert
   Governor. Nó phải tiếp tục hoạt động khi mất Internet.
2. **HMI Plane** — React Driver HUD/Engineer Dashboard và AAOS HMI. HMI chỉ
   hiển thị trạng thái, phát âm thanh theo lệnh của Edge Core và gửi lệnh điều
   khiển phiên replay; không tự quyết định cảnh báo an toàn.
3. **Cloud Control Plane** — GCP lưu video được người dùng cho phép tải lên,
   xếp hàng các lượt replay, lưu evidence/HITL và cung cấp URL HTTPS cho ban tổ
   chức. Cloud là control/evaluation plane, không phải đường FCW/VRU critical.

```text
                         GCP — Control / Evaluation Plane
  Browser ─HTTPS─► Cloud Run Web/API ─► Signed GCS Upload
                         │                       │
                         │                       ▼
                         │                 Pub/Sub Job Queue
                         │                       │
                         │                       ▼
                         │                 Replay Worker/Job
                         │                       │
                         └──────► Cloud SQL ◄────┴────► GCS results
                                    │
                         Cloud Logging/Monitoring/Secret Manager

  ┌────────────────────── Safety/Edge Plane ───────────────────────┐
  │ VideoSource → Perception → Temporal Evidence → Risk Engine      │
  │             → Alert Governor → Audio/TTS + Evidence Store       │
  │                         │                                      │
  │                         └── local HTTP/WebSocket/gRPC ──► HMI   │
  └─────────────────────────────────────────────────────────────────┘
       ▲                 ▲                         ▲
       │                 │                         │
  File replay       USB/CSI camera             AAOS Camera2/EVS*

  * Chỉ dùng được khi OEM/head unit cấp API, permission và camera calibration.
```

### 1.1. Vì sao phải tách ba mặt phẳng

- **Web có URL thật** cần Internet, multi-user, upload, lưu kết quả và scale.
- **Cảnh báo trên xe** cần độ trễ dự đoán được và phải tồn tại khi mất mạng; một
  request tới cloud không được nằm trên critical path của FCW, VRU, LDW hay
  cross-traffic.
- **AAOS** là màn hình/HMI và vehicle contract, không mặc nhiên là nơi được phép
  đọc camera trước hoặc CAN. Android tài liệu hóa Camera2 cho camera service và
  EVS/CarEvsService cho automotive camera; EVS/CarEvsService chỉ dành cho system
  hoặc first-party automotive camera apps. Vì vậy AAOS hiện tại phải được trình
  bày là HMI/replay integration, còn camera thật là OEM-dependent.

## 2. Các runtime thống nhất

Mọi runtime đều dùng cùng `EdgeEvent`, `FramePacket`, `VehicleTelemetry` và
`AlertEvent`. Chỉ `VideoSource`, `VehicleAdapter`, model provider và transport
được thay thế.

| Runtime | Input hiện tại | Nơi chạy Core | Vai trò được tuyên bố |
|---|---|---|---|
| **Web local** | File video trong `media/` | Windows laptop/FastAPI | Demo offline, benchmark và HITL |
| **Web GCP** | Video do browser upload | Cloud Run replay worker | Demo/evaluation không safety-critical |
| **AAOS emulator** | File replay local hoặc file qua bridge | Laptop/edge service; AAOS là HMI | Mô phỏng màn hình xe, playback, mock VHAL |
| **Jetson candidate** | USB/CSI camera hoặc file replay | Jetson Docker + TensorRT | Edge candidate; cần benchmark trên Orin thật để claim R1 |
| **Xe thật** | Camera2/EVS/OEM camera stream | Edge box hoặc head-unit accelerator | Chỉ sau OEM permission, calibration và closed-course gate |

### 2.1. Hai nguồn video cho demo và kiểm thử

Web RoadWatch dùng song song hai nguồn input:

| Nguồn | Nơi lưu | Mục đích | Cách chạy |
|---|---|---|---|
| **Video Library** | Local `media/` và bản publish trong GCS `demo-library/` | Ban tổ chức chọn tình huống có sẵn | `Xem kết quả mẫu` hoặc `Chạy phân tích mới` |
| **Upload Custom Video** | GCS `uploads/{tenant_id}/{run_id}/` | Ban tổ chức đưa video mới vào kiểm thử | Luôn tạo fresh run bất đồng bộ |

Thư mục `roadwatch/media/` tiếp tục phục vụ Web local và AAOS replay. Để Web
GCP truy cập được, các video mẫu phải được upload riêng lên Cloud Storage; không
được giả định rằng thư mục local hoặc Git repository tồn tại trong Cloud Run.

Video mẫu nên được phân loại theo tình huống để ban tổ chức hiểu ngay giá trị
demo:

```text
Video Library
├── Ban ngày
├── Ban đêm
├── Trời mưa / ngược sáng
├── Giao thông đông
├── Xe máy hoặc người đi bộ cắt ngang
├── Xe tạt đầu / cut-in / lead braking
└── Biển báo tốc độ và biển cấm
```

Mỗi video library item có manifest tối thiểu:

```json
{
  "video_id": "dashcam_vietnam_night",
  "display_name": "Dashcam Việt Nam — ban đêm",
  "source_object": "gs://roadwatch-demo-inputs/demo-library/dashcam_vietnam_night/input.mp4",
  "sha256": "...",
  "duration_ms": 180033,
  "fps": 30.0,
  "conditions": ["night", "motorcycle", "cross_traffic"],
  "has_cached_result": true,
  "cached_result_status": "verified_demo_only"
}
```

Giao diện phải tách rõ hai hành động:

- **`Xem kết quả mẫu` / `Cached result`**: mở artifact đã xử lý trước, phản hồi
  gần như ngay lập tức; nhãn này không được gọi là một lần inference mới.
- **`Chạy phân tích mới` / `Fresh analysis`**: gửi video và model manifest qua
  replay worker; kết quả được gắn `run_id`, thời gian chạy và model version.

Video custom upload phải được kiểm tra loại file, dung lượng, thời lượng, codec,
SHA-256 và quota trước khi enqueue. Mỗi run phải độc lập; pause/seek/reset của
video A không được sử dụng state của video B. Video lớn không được đi qua request
đồng bộ của API.

### 2.2. Quy tắc cho AAOS

Có hai chế độ, không được trộn lẫn trong demo:

**AAOS Replay Demo**

- `MainActivity`/WebView hiển thị RoadWatch HMI.
- Người dùng chọn video có sẵn; phiên replay có pause, resume, seek và reset
  theo `run_id`, vì vậy video mới không thể thừa hưởng state của video cũ.
- HMI kết nối tới Edge Core cục bộ qua `http://10.0.2.2:8000` trong emulator
  hoặc qua local TLS/gRPC khi edge là thiết bị riêng.
- Speed/gear chỉ là mock read-only để kiểm thử UX; GPS hiển thị phải gắn nhãn
  `mock`/`emulator`, không được trình bày là vị trí VinFast thật.

**AAOS Vehicle Candidate**

- `CameraSourceAAOS` chỉ được bật nếu OEM cung cấp Camera2/EVS camera handle,
  permission, stream format, camera mount/calibration và lifecycle contract.
- `VehicleAdapterAAOS` chỉ đọc telemetry cần thiết; không có CAN write, không
  điều khiển phanh, ga, lái hoặc ADAS của xe.
- Nếu head unit không đủ GPU/NPU hoặc policy không cho app third-party giữ
  camera/audio background, Edge Core chạy trên Jetson/edge box riêng; AAOS chỉ
  nhận event và render HMI qua local authenticated transport.
- “Chạy nền” trong hồ sơ demo nghĩa là HMI/edge session được duy trì khi người
  dùng không thao tác liên tục; quyền khởi động sau boot, foreground service,
  audio focus, UX restriction và camera background access vẫn cần OEM approval.

## 3. Hợp đồng dữ liệu (Core Contract)

### 3.1. FramePacket

```json
{
  "run_id": "uuid",
  "source_id": "file:test_video10",
  "frame_id": 1820,
  "pts_ms": 60700,
  "monotonic_ns": 0,
  "width": 1920,
  "height": 1080,
  "pixel_format": "BGR",
  "source_kind": "file|usb|csi|aaos_camera2|aaos_evs",
  "is_seekable": true
}
```

`pts_ms` là thời gian nguồn dùng để replay, seek, ground truth và đồng bộ
evidence. `monotonic_ns` là thời gian runtime dùng để đo latency. Không dùng
wall-clock hoặc tên file làm khóa trạng thái.

### 3.2. VehicleTelemetry

```json
{
  "speed_mps": null,
  "gear": "D",
  "yaw_rate_rps": null,
  "turn_signal": "unknown",
  "gps": {"lat": null, "lon": null, "quality": "mock|unavailable|real"},
  "validity": "mock|read_only|unavailable",
  "calibration_profile": "uncalibrated"
}
```

Giá trị `null`/`unavailable` là hợp lệ. Khi chưa có calibration và telemetry,
risk engine chỉ phát `relative_risk`/`image_space_risk`, không ghi “TTC 1.2 s” hay
“cách 5 m” như một số đo vật lý.

### 3.3. AlertEvent duy nhất cho HUD và TTS

```json
{
  "event_id": "uuid",
  "run_id": "uuid",
  "event_type": "fcw|vru|cut_in|cross_traffic|ldw|speed_sign|fallen_rider",
  "severity": "advisory|warning|critical",
  "object_class": "motorcycle",
  "direction": "left|right|ahead|unknown",
  "pts_ms": 60700,
  "display_message": "Xe máy phía trước bên phải, hãy chú ý",
  "spoken_message": "Xe máy phía trước bên phải, hãy chú ý",
  "evidence": {
    "track_id": 7,
    "hits": 6,
    "confidence": 0.87,
    "risk_mode": "image_space_uncalibrated",
    "suppression_reason": null
  },
  "audio": {"action": "tts|beep|none", "state": "queued|started|done|dropped"}
}
```

`Alert Governor` tạo câu một lần. HUD và TTS lấy cùng `display_message`/message
ID; không để frontend tự rút gọn câu hoặc TTS tự tạo câu khác. Đây là điều kiện
chống lỗi “banner một câu, TTS một câu”.

## 4. Đường chạy Web có URL thật

### 4.1. Luồng của ban tổ chức

```text
1. Mở HTTPS URL → đăng nhập driver/engineer
2. Chọn một video trong Video Library hoặc Upload Custom Video
3a. Video Library: lấy input manifest từ GCS; có thể mở Cached result ngay
3b. Custom Video: API tạo upload session; browser upload qua signed URL
4. API tạo run_id + lưu manifest (sha256, duration, fps, size, source_kind)
5. Nếu Fresh analysis: Pub/Sub đưa run vào replay queue
6. Replay worker đọc video từ GCS, chạy RoadWatch Core
7. Worker ghi events/metrics/frames/result video vào GCS + Cloud SQL
8. Browser nhận trạng thái qua polling/SSE (hoặc WebSocket có shared state)
9. Driver HUD xem overlay/timeline; Engineer Dashboard xem metrics/HITL
```

Không gửi file video lớn qua request đồng bộ của API. Mỗi video/run phải có
`run_id` riêng và artifact path riêng, ví dụ:

```text
gs://roadwatch-demo-inputs/demo-library/{video_id}/input.mp4
gs://roadwatch-demo-inputs/demo-library/{video_id}/manifest.json
gs://roadwatch-demo-results/demo-library/{video_id}/cached/events.json
gs://roadwatch-demo-results/demo-library/{video_id}/cached/overlay.mp4
gs://roadwatch-demo-inputs/{tenant_id}/{run_id}/input.mp4
gs://roadwatch-demo-results/{tenant_id}/{run_id}/events.jsonl
gs://roadwatch-demo-results/{tenant_id}/{run_id}/overlay.mp4
gs://roadwatch-demo-results/{tenant_id}/{run_id}/metrics.json
```

`cached/` chỉ là kết quả đã xử lý trước cho mục đích demo và phải được gắn nhãn
`verified_demo_only`. Fresh run luôn ghi vào `{run_id}` riêng, không ghi đè cached
artifact hoặc kết quả của người dùng khác.

### 4.2. GCP services, không dùng Firebase

| Thành phần | Dùng để làm gì | Guardrail |
|---|---|---|
| Cloud Run `roadwatch-web` | phục vụ React build và HTTPS URL | giai đoạn chấm bất định: `min=0,max=1`, startup gate; chỉ dùng `min=1` trong cửa sổ demo cần luôn-warm |
| Cloud Run `roadwatch-api` | auth, run metadata, signed upload URL, status/HITL API | không giữ file lớn trong local disk |
| Cloud Storage | input video, output video, contact sheet, evidence | retention/lifecycle, signed URL, per-run prefix |
| Pub/Sub | queue các replay job và event worker | idempotency bằng `run_id` |
| Cloud Run Job/worker | chạy replay bất đồng bộ đến khi hoàn tất | timeout, retry có giới hạn, không critical safety |
| Cloud SQL PostgreSQL | user/session/run/event/HITL metadata | production source of truth thay SQLite local |
| Artifact Registry | container image và release digest | pin digest, không dùng `latest` |
| Secret Manager | secret/token/runtime config | không commit `.env`, không log secret |
| Cloud Logging/Monitoring | latency, errors, job status, cost signals | alert khi worker fail hoặc quota gần đầy |

Cloud Run hỗ trợ HTTPS endpoint, WebSocket, HTTP/2 và gRPC; tuy nhiên WebSocket
cloud cần shared state khi scale nhiều instance. Vì thế bản đầu nên dùng polling
hoặc SSE cho job status; chỉ bật WebSocket khi có Redis/Memorystore hoặc một
transport shared-state rõ ràng. Cloud Run Jobs phù hợp replay chạy đến khi hoàn
tất, còn Cloud Run Service phù hợp API/web endpoint. Tham chiếu chính thức:
[Cloud Run overview](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run),
[Cloud Run WebSockets](https://docs.cloud.google.com/run/docs/tutorials/websockets),
[Pub/Sub architecture](https://docs.cloud.google.com/pubsub/architecture).

#### 4.2.1. Deployment checkpoint thực tế — 2026-08-24

- GCP project: `c3-roadwatch-162`; region: `asia-southeast1`.
- Artifact Registry: repository `roadwatch`; Cloud Run service: `roadwatch-web`;
  revision acceptance-tested: `roadwatch-web-00010-rbk`.
- Fallback URL: `https://roadwatch-web-bx6lfekcba-as.a.run.app`.
- GCS asset bucket: `gs://c3-roadwatch-162-roadwatch-assets`; allowlist model/video
  nằm ngoài Git, được materialize lúc startup.
- Local parity và public smoke: login, 4-item Video Library, fresh replay
  `frame_id=1`, direct upload 14.55 MB có SHA-256 và `durable=true`, fresh replay
  từ `uploads/{run_id}/...` pass.
- Cloud fast profile dùng object-only `yolo11n_320.onnx`, tắt sign/lane/audio;
  đây là evaluation/replay plane, không phải FCW/LDW/TTS critical path. Local và
  AAOS vẫn giữ full perception. Direct multipart upload giới hạn 25 MB; video
  dài cần signed GCS resumable upload.
- Public latency acceptance trên `test_video1.mp4`: start `189 ms`, warmup
  `874,86 ms`; sau 2 giây có 6 processed frame và track thật; sau 37 sample,
  object model không lỗi, E2E p50 `34,24 ms`, p95 `71,25 ms`, processed FPS
  `5,57`. Preview video hỗ trợ HTTP Range `206`; chuyển sang `test_video10.mp4`
  reset `frame_id/source_time/tracks/signs` về `0/0/[]/[]`.
- Health có thể báo `degraded` theo R0 static release manifest vì container cloud
  không chứa PT/hash artifacts; không dùng trạng thái này để tuyên bố model đã
  được promote hoặc hệ thống production-ready.

#### 4.2.2. On-demand checkpoint — 2026-08-25

- Public Web hiện hành: `roadwatch-web-00021-qd4`; Piper Việt:
  `roadwatch-tts-00004-kdv`; cả hai nhận 100% traffic và dùng `min=0,max=1`.
- FastAPI trả UI shell trước rồi bootstrap GCS/model/TTS ở background. React hiển
  thị full-screen startup gate tiếng Việt, stage và thời gian đã chờ; login và
  phân tích chỉ được mở khi `/api/startup.ready=true`.
- Bốn video mẫu vẫn xuất hiện từ manifest nhưng chỉ được tải từ GCS khi người
  dùng chọn; startup chỉ tải bốn model ONNX đang active. Điều này tránh tải thêm
  khoảng 252 MB video ở mỗi cold start.
- Web image Cloud chuyên dụng không đóng gói PyTorch/CUDA/Ultralytics; local,
  Jetson và training dependency không bị thay đổi.
- Acceptance warm: end-to-end P50/P95 `56,26/77,23 ms`, object P95 `24,22 ms`;
  bốn model ONNX đều loaded, FCW `beep_tts`, Piper WAV HTTP 200.
- Cost/UX trade-off: compute idle giảm vì instance có thể về 0; request đầu sau
  idle chịu cold start. UI thông báo ước lượng 1–3 phút và không trình bày trạng
  thái này như lỗi. Trong một cửa sổ demo đã hẹn giờ có thể tạm đặt `min=1`, sau
  đó trả về `min=0` mà không đổi image hoặc kiến trúc.

### 4.3. Public demo acceptance gate

Trước khi gửi URL cho ban tổ chức, phải có evidence:

- HTTPS URL mở được từ mạng ngoài; không phụ thuộc localhost/`10.0.2.2`.
- URL chính thức sau khi mapping là `https://c3-roadwatch-162.io.vn`; URL
  `run.app` chỉ dùng làm fallback/kỹ thuật, không phải URL gửi chính thức cho ban
  tổ chức.
- Tài khoản demo và engineer role hoạt động; không dùng credential mặc định cho
  môi trường public lâu dài.
- Upload được ít nhất một video mẫu và một video do người dùng chọn, có
  `sha256`, duration, FPS và `run_id` riêng.
- Video Library có ít nhất một `Cached result` mở nhanh và một nút `Fresh
  analysis`; giao diện hiển thị rõ sự khác nhau giữa hai chế độ.
- Một run 60 giây hoàn tất không lỗi, hiển thị event timeline và tải được
  `metrics.json`/overlay result.
- Pause/seek/reset của run A không làm thay đổi run B.
- Cloud mất kết nối không làm hỏng local edge replay; UI phải hiển thị rõ
  `cloud_demo` hay `offline_edge`.
- Có quota upload, giới hạn dung lượng/thời lượng, loại file cho phép, rate
  limit, xóa dữ liệu demo và log audit.

Checkpoint hiện tại mới pass các mục login/library/direct upload/fresh replay
ngắn; chưa pass cached result, run 60 giây, metrics artifact download, signed
resumable upload, quota/rate-limit và official domain mapping.

### 4.4. Chính sách domain và URL public

RoadWatch có mã team `162`, thuộc Cohort `3`. URL public khuyên dùng sau khi
domain mapping hoàn tất là:

```text
https://c3-roadwatch-162.io.vn
```

URL mặc định Cloud Run có dạng tương tự:

```text
https://roadwatch-web-<project-number>.<region>.run.app
```

URL `run.app` là URL kỹ thuật ổn định của service, phù hợp làm fallback và kiểm
tra nội bộ, nhưng không thể tự tùy biến thành cấu trúc `c3-roadwatch-162.io.vn`.

#### 4.4.1. Khi dùng subdomain cộng đồng `io.vn`

Domain owner/Mentor cần tạo DNS records mà GCP cung cấp cho mapping. Quy trình:

1. Deploy Cloud Run service `roadwatch-web` và xác nhận URL `run.app` hoạt động.
2. Tạo custom domain mapping hoặc Global External Application Load Balancer.
3. Nhập `c3-roadwatch-162.io.vn` làm hostname.
4. Xác minh quyền sở hữu/quyền sử dụng domain nếu GCP yêu cầu.
5. Lấy đúng các record `A`/`AAAA`/`CNAME` do GCP sinh ra; không tự đoán record.
6. Domain owner thêm record vào DNS của `io.vn`.
7. Chờ DNS propagation và Google-managed HTTPS certificate.
8. Chạy public URL acceptance gate ở §4.3.

Cloud Run cho phép map subdomain vào service hiện tại và tự cấp/renew managed
certificate. Domain Mapping là lựa chọn đơn giản cho demo nhưng hiện được Google
ghi là Preview; Global External Application Load Balancer là lựa chọn phù hợp
hơn nếu cần CDN, Cloud Armor, nhiều domain hoặc kiểm soát TLS. Tham chiếu:
[Cloud Run custom domains](https://docs.cloud.google.com/run/docs/mapping-custom-domains),
[Cloud Run locations](https://cloud.google.com/run/docs/locations?hl=en).

#### 4.4.2. Khi mua tên miền riêng sau này

Có thể map tên miền mới, ví dụ `roadwatch-162.com` hoặc `app-162.example.vn`,
vào đúng Cloud Run service/Load Balancer đang chạy. Không cần tạo lại Cloud
project, database, bucket, model worker hoặc replay pipeline.

Khi chuyển domain cần kiểm tra và cập nhật:

- `PUBLIC_BASE_URL` và frontend API base URL;
- CORS allowed origins, cookie `Secure`/`SameSite` và WebSocket/SSE origins;
- OAuth redirect URL nếu sau này thêm OAuth;
- link trong README, slide, monitoring uptime check và tài liệu demo.

Không tắt URL `run.app` trước khi custom domain đã hoạt động và acceptance gate
đã pass. GCP cho phép map nhiều custom domain vào cùng service; vì vậy URL cũ có
thể giữ làm fallback trong giai đoạn chuyển đổi.

## 5. Đường chạy offline Edge/ô tô thật

### 5.1. Module boundary

```text
VideoSource
  ├─ FileReplaySource              # hiện có, seekable
  ├─ UsbCameraSource               # laptop/USB camera
  ├─ CsiCameraSource               # Jetson CSI
  ├─ AaosCamera2Source             # OEM permission required
  └─ AaosEvsSource                 # system/1P/OEM required

RoadWatchCore
  ├─ Perception adapters
  ├─ Temporal evidence/tracker
  ├─ Risk Engine
  ├─ deterministic Alert Governor
  ├─ Piper/beep audio adapter
  └─ SQLite/evidence adapter

Transport
  ├─ Local HTTP/WebSocket       # current MVP/demo
  ├─ Local gRPC over TLS        # edge box ↔ AAOS candidate
  └─ Cloud upload mirror        # non-critical telemetry/evidence only
```

### 5.2. Tách AAOS và Edge Agent là phương án triển khai thực tế hơn

Phương án khuyến nghị cho pitch và prototype production:

- **AAOS head unit:** render Driver HUD, audio focus/HMI state, replay control,
  mock/read-only telemetry và health status.
- **Edge Agent:** chạy perception/risk/TTS cache trong Docker trên Jetson Orin
  hoặc edge compute box; nhận USB/CSI camera; xuất `AlertEvent` qua local gRPC.
- **Cloud:** chỉ nhận opt-in telemetry, model/evidence package và HITL; không
  dùng để quyết định cảnh báo cấp critical.

Điều này hạn chế tối đa tài nguyên của màn hình xe và cho phép thay Jetson bằng
NVIDIA/ARM64 edge box mà không viết lại HMI. Nếu OEM chứng minh head unit có
NPU/GPU, quyền camera và thermal budget, Edge Agent mới có thể được chuyển vào
head unit như một service native/container được OEM ký.

### 5.3. Những gì được và không được nói với ban tổ chức

**Được nói chính xác:**

> RoadWatch hiện đã có một pipeline edge-first warning-only. Video replay là
> camera simulator; cùng một `VideoSource` contract có thể nhận file, USB/CSI và
> Camera2/EVS khi OEM cấp quyền. AAOS emulator chứng minh HMI và vehicle contract;
> Docker ARM64/ONNX/TensorRT là đường chuẩn bị cho Jetson. GCP cung cấp dashboard,
> HITL và replay evaluation bằng URL công khai.

**Không được nói:**

- “Đã tích hợp camera trước của VinFast” khi chưa có OEM API/permission.
- “Đã chạy TensorRT/FPS/thermal trên Jetson Orin” khi chỉ chạy AWS ARM64 hoặc
  emulator.
- “Cloud xử lý FCW realtime trên xe” hoặc “mất mạng vẫn dùng cloud cảnh báo”.
- “AAOS emulator là bằng chứng xe VinFast tương thích”.
- “TTC/khoảng cách mét chính xác” khi chưa calibration/telemetry/closed-course.

## 6. Mapping với source hiện tại

| Năng lực | Vị trí hiện tại | Vai trò trong kiến trúc hợp nhất |
|---|---|---|
| FastAPI, session, status, events | `backend/roadwatch/api.py`, `pipeline.py` | Edge API; sau này tách cloud API/worker adapter |
| Perception/model registry | `backend/roadwatch/perception.py`, `models/` | Core perception adapter |
| Risk/kinematics/alert | `risk.py`, `kinematics.py`, `alerts.py`, `sign_arbitration.py` | Safety/Edge Plane |
| TTS/audio lifecycle | `audio.py`, `voices/` | Edge audio; canonical AlertEvent |
| SQLite evidence | `storage.py` | Local source of truth; Cloud SQL adapter cho cloud |
| React HUD/Dashboard | `frontend/` | HMI Plane và cloud web build |
| AAOS WebView/mock telemetry | `android/roadwatch-aaos/` | AAOS Replay Demo |
| Docker profiles | `Dockerfile*`, `docker-compose*` | Local/NVIDIA/ARM64 packaging |
| Dataset/quality/evaluation | `evaluation/`, `reports/`, `kaggle/` | MLOps/evidence plane, không nằm trong safety runtime |

Các thay đổi GCP tiếp theo phải ưu tiên adapter/interface, không copy riêng
business logic sang một bản backend thứ hai. Mục tiêu là cùng một `RoadWatchCore`
được gọi trong local replay worker và cloud replay worker.

## 7. Lộ trình triển khai thống nhất

### Phase A — Contract freeze và local parity

1. Chuẩn hóa `FramePacket`, `VehicleTelemetry`, `AlertEvent`, `run_id` và model
   manifest.
2. Bảo đảm Web local, AAOS emulator và Docker dùng cùng replay state machine.
3. Test canonical HUD/TTS equality, reset giữa video, seek và offline fallback.
4. DoD: test hiện có pass; 3 runtime hiển thị cùng event/message trên cùng video.

### Phase B — GCP public demo

1. Tạo Artifact Registry, Cloud Storage, Pub/Sub, Cloud SQL và Secret Manager.
2. Publish Video Library từ `media/` lên GCS cùng manifest, thumbnail và cached
   result được gắn nhãn; không commit video nặng vào Git.
3. Tách upload/status/HITL API khỏi replay worker; thêm signed upload cho Upload
   Custom Video và validation/quota/hash trước khi enqueue.
4. Đóng gói worker CPU trước; chỉ thêm GPU Cloud Run khi profiling chứng minh cần
   và budget được duyệt.
5. Deploy bằng Cloud Build hoặc GitHub Actions tới Cloud Run với digest pin.
6. DoD: public URL gate ở §4.3 pass; cả Cached result và Fresh analysis đều
   phân biệt đúng; không commit video/model/secret.

### Phase C — AAOS showcase

1. Tạo Automotive AVD 1024×768 hoặc 1080×600; test landscape, rotary/touch,
   audio focus và UX restriction.
2. Chạy Edge Core local trên host/edge; AAOS WebView/native HMI kết nối local.
3. Import video local, replay, pause/seek/reset, hiển thị health/provider và
   `mock` telemetry.
4. DoD: có video demo quay màn hình + log chứng minh AAOS không gọi GCP để cảnh
   báo.

### Phase D — Edge candidate

1. Build ARM64 image; chạy preflight trên môi trường tương thích.
2. Export ONNX, build TensorRT FP16 trên Jetson Orin thật; đo FPS/P95/VRAM/thermal
   30 phút.
3. Chỉ sau parity mới cân nhắc INT8 và calibration set.
4. DoD: R1 gate trong `MASTER_ACTION_PLAN.md` pass; nếu chưa có Orin, trạng thái
   là `prepared/blocked`, không phải `passed`.

### Phase E — Vehicle/OEM readiness

1. Chốt camera mount/FOV/calibration, camera lifecycle, audio route và telemetry
   contract với OEM.
2. Thay `FileReplaySource` bằng Camera2/EVS/CSI adapter; giữ nguyên Core Contract.
3. Chạy closed-course protocol và safety review; chỉ warning-only.
4. DoD: R2 evidence; mọi claim VinFast production vẫn chờ OEM integration và
   formal assessment.

## 8. Trách nhiệm và blocker

| Hạng mục | AI có thể tự làm | Human/OEM bắt buộc |
|---|---|---|
| Core contracts, adapters, API, Docker | Code, test, report 100% | duyệt release profile |
| GCP web/upload/replay | viết IaC/container/API, tạo smoke test | GCP project/billing/IAM và domain |
| HITL/model training | package Kaggle, metrics, gate tooling | label/quality gate/license và GPU approval |
| AAOS replay HMI | scaffold, build config, mock telemetry | mở Android Studio, SDK/AVD, kiểm tra UX |
| ARM64/Jetson | Docker/ONNX/preflight | Jetson/JetPack để benchmark thật |
| Camera VinFast/CAN | interface/mock/read-only adapter | OEM API, permission, calibration, legal/safety |
| Closed-course | protocol/scorer/report | xe, địa điểm kín, safety driver, đo distance |

## 9. Tài liệu tham chiếu chính

- [AAOS camera overview](https://source.android.com/docs/automotive/camera?hl=en)
- [AAOS emulator and vehicle property testing](https://developer.android.com/training/cars/testing/emulator)
- [AAOS platform overview](https://developer.android.com/training/cars/platforms/automotive-os?hl=en)
- [Cloud Run overview](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run)
- [Cloud Run WebSockets](https://docs.cloud.google.com/run/docs/tutorials/websockets)
- [Pub/Sub architecture](https://docs.cloud.google.com/pubsub/architecture)

## 10. Kết luận release

RoadWatch có thể trình bày thuyết phục theo mô hình **“one Core, three
deployments”**:

```text
Một Core Contract
      ├─ Web GCP: public demo + upload + HITL + evaluation
      ├─ AAOS: in-car HMI + local replay + mock vehicle contract
      └─ Edge/Jetson: offline perception + deterministic warning path
```

Hiện trạng cần ghi trên slide là **R0 — Research demo / production-shaped
architecture**. “Có khả năng triển khai trên xe thật” được chứng minh bằng
interface, container, HMI contract, offline boundary và kế hoạch OEM adapter;
không đồng nghĩa đã tích hợp VinFast hoặc đạt chứng nhận an toàn. Để nâng tuyên
bố lên R1/R2 cần benchmark Jetson/Orin, calibration, telemetry và closed-course
evidence theo `MASTER_ACTION_PLAN.md`. URL được gửi cho Mentor/Ban tổ chức sau khi
hoàn tất domain mapping là `https://c3-roadwatch-162.io.vn`; trước thời điểm đó,
`run.app` chỉ là fallback kỹ thuật.
