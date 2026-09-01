# RoadWatch — UI Metrics và Luồng Build/Cloud Deployment

Tài liệu này giải thích các thông số quan trọng đang hiển thị trên RoadWatch
Engineer Dashboard/Driver HUD và cách hệ thống được build, triển khai lên GCP.
Mục tiêu là giúp người phát triển, kỹ sư đánh giá và ban tổ chức hiểu đúng số
liệu, tránh nhầm giữa độ chính xác AI, độ trễ inference và thời gian người dùng
thực sự chờ đợi.

> RoadWatch chỉ là hệ thống cảnh báo/hỗ trợ lái. Nó không tự lái, không phanh,
> không tăng ga và không đánh lái.

## 1. Phạm vi và nguồn sự thật

Các metric runtime được thu thập trong:

- `backend/roadwatch/metrics.py`: bộ đếm frame, latency, warmup và percentile.
- `backend/roadwatch/pipeline.py`: vòng đời session, chọn frame, inference,
  annotation và đo end-to-end frame processing.
- `backend/roadwatch/risk.py`: risk score và điều kiện FCW/LDW.
- `backend/roadwatch/alerts.py`: severity, deduplication, cooldown và audio
  authorization.
- `frontend/src/main.tsx`: cách metric và evidence packet được hiển thị.

Các metric này là **runtime/observability metrics**, không thay thế cho mAP,
precision, recall, event recall hoặc ground-truth evaluation.

## 2. Các thông số hiển thị trên UI

### 2.1. Processed FPS

#### Ý nghĩa

`Processed FPS` là số frame mà RoadWatch thực sự phân tích trung bình trong một
giây. Nó khác với FPS của video đầu vào.

Video có thể là 30 FPS nhưng hệ thống chỉ xử lý 12 FPS để cân bằng realtime và
tài nguyên. Những frame còn lại có thể được bỏ qua theo sampling cadence.

#### Cách tính

```text
Processed FPS = processed_frames / metrics_uptime_seconds
```

Trong đó:

- `processed_frames`: số frame đã đi qua perception/risk/annotation.
- `metrics_uptime_seconds`: thời gian kể từ khi metrics của session được reset.

#### Ví dụ

Giả sử sau 10 giây:

```text
Tổng frame đọc từ video: 300
Frame được phân tích: 120

Processed FPS = 120 / 10 = 12 FPS
```

Điều đó cho biết tốc độ xử lý của pipeline là khoảng 12 FPS. Nó không cho biết
model nhận diện đúng bao nhiêu phần trăm.

#### Cách diễn giải

- FPS cao hơn thường giúp theo dõi chuyển động và cảnh báo nhanh hơn.
- FPS thấp có thể làm bỏ lỡ đối tượng xuất hiện rất ngắn.
- Processed FPS thấp chưa chắc là lỗi nếu hệ thống chủ động giới hạn FPS để bảo
  vệ tài nguyên.
- Cần ghi kèm thiết bị, backend, input resolution và model profile khi so sánh.

### 2.2. Sampling skip

#### Ý nghĩa

`Sampling skip` là tỷ lệ frame bị bỏ qua có chủ đích trước khi đưa vào model.
Mục đích là giảm tải khi video đầu vào có FPS cao hơn khả năng xử lý hoặc mục
tiêu runtime.

#### Cách tính

```text
Sampling skip ratio = scheduled_skipped_frames / captured_frames
```

Trong UI, tỷ lệ này được hiển thị dưới dạng phần trăm. Pipeline tăng
`scheduled_skipped_frames` khi frame không thuộc stride đã chọn.

#### Ví dụ

```text
Frame đã thu nhận: 300
Frame được phân tích: 150
Frame bị bỏ qua theo cadence: 150

Sampling skip = 150 / 300 = 50%
```

Nếu nguồn là 30 FPS và hệ thống xử lý khoảng 15 FPS thì việc bỏ một nửa frame
có thể là chủ động và có kiểm soát.

#### Không nên nhầm với các loại drop khác

| Loại frame bị bỏ | Nguyên nhân |
|---|---|
| Sampling skip | Bỏ theo cadence/stride đã định trước |
| Overload drop | Pipeline không xử lý kịp |
| Decode error | Video hoặc frame không đọc được |

Sampling skip cao có thể làm giảm khả năng phát hiện sự kiện rất ngắn như xe máy
cắt ngang nhanh hoặc một đối tượng vừa xuất hiện trong vùng khuất. Vì vậy phải
đánh giá cùng event recall, không chỉ nhìn FPS.

### 2.3. E2E P50

#### Ý nghĩa

`E2E P50` là latency trung vị của một frame **đã được chọn để phân tích**. P50
còn gọi là median hoặc percentile thứ 50.

Đoạn đo bắt đầu khi pipeline bắt đầu xử lý frame và kết thúc sau khi đã:

1. Chạy perception cần thiết.
2. Chạy tracking và risk engine.
3. Tạo cảnh báo/annotation.
4. Encode frame annotate thành JPEG.

#### Cách tính

Với mỗi frame:

```text
frame_started = perf_counter()
...
elapsed_ms = (perf_counter() - frame_started) * 1000
```

Các mẫu latency được sắp xếp và lấy percentile bằng nội suy tuyến tính. Bộ
metrics giữ tối đa 240 mẫu gần nhất, nên đây là rolling window chứ không phải
toàn bộ lịch sử vĩnh viễn.

#### Ví dụ

Năm frame có latency:

```text
40 ms, 45 ms, 50 ms, 80 ms, 200 ms
```

Sau khi sắp xếp, P50 là khoảng:

```text
E2E P50 = 50 ms
```

Nghĩa là khoảng một nửa frame nhanh hơn hoặc bằng 50 ms.

#### Giới hạn quan trọng

E2E P50 trên UI hiện là latency xử lý frame bên trong pipeline, không phải toàn
bộ thời gian từ lúc người dùng bấm **Phân tích** đến lúc nhận được hình ảnh đầu
tiên. Nó không phản ánh đầy đủ:

- Thời gian upload video.
- Cloud Run cold start.
- Tải model/video từ GCS.
- Độ trễ mạng.
- Thời gian truyền MJPEG đến trình duyệt.
- Thời gian khởi tạo hoặc lấy audio TTS.

### 2.4. E2E P95

#### Ý nghĩa

`E2E P95` là latency mà 95% frame xử lý không vượt quá. Khoảng 5% mẫu còn lại
có thể chậm hơn giá trị này.

#### Ví dụ

```text
E2E P50 = 48 ms
E2E P95 = 110 ms
```

Diễn giải:

- Thông thường pipeline xử lý quanh mức 48 ms.
- 95% frame không vượt quá 110 ms.
- Khoảng 5% frame bị chậm hơn 110 ms.

P95 đặc biệt quan trọng với ADAS vì những frame chậm bất thường có thể xảy ra
đúng lúc có nhiều object, nhiều biển báo, occlusion hoặc CPU bị tranh chấp.

#### Ví dụ nguyên nhân P95 tăng

- Dense traffic làm tăng số lượng object và chi phí tracking.
- Nhiều candidate traffic sign cần được arbitration.
- Lane model hoặc ONNX Runtime có frame xử lý chậm bất thường.
- Frame độ phân giải lớn làm tăng thời gian resize/encode.
- Cloud Run instance bị giới hạn hoặc đang cold-start.

P95 cần được báo cáo kèm điều kiện test; không được lấy P95 trên Cloud CPU để
khẳng định hiệu suất Jetson Orin.

### 2.5. Warmup

#### Ý nghĩa

`Warmup` là thời gian chuẩn bị perception model trước khi session xử lý chính
thức. Nó có thể bao gồm:

- Load model và tạo ONNX Runtime session.
- Khởi tạo tensor/buffer.
- Chạy inference khởi động.
- Chuẩn bị graph hoặc kernel cần thiết.

#### Cách tính

```text
warmup_ms = thời điểm kết thúc perception.warmup()
            - thời điểm bắt đầu perception.warmup()
```

#### Ví dụ

```text
Warmup = 2.8 giây
```

Điều đó có nghĩa perception cần khoảng 2.8 giây để sẵn sàng sau khi được khởi
động. Sau warmup, latency từng frame được tính riêng bằng E2E P50/P95.

#### Warmup khác cold start

| Thông số | Đo lường |
|---|---|
| Warmup | Chuẩn bị perception model |
| E2E P50/P95 | Xử lý một frame sau khi sẵn sàng |
| Cloud startup time | Khởi động container, tải asset, warmup perception/TTS và mở API |

Trên Cloud Run, startup gate `/api/startup` có thể bao gồm nhiều công việc hơn
giá trị Warmup hiển thị trong metrics của session. Vì vậy không dùng Warmup card
để đại diện cho toàn bộ thời gian cold start của public URL.

### 2.6. FCW Thresholds: Warning và Critical

#### Ý nghĩa chung

Các ngưỡng FCW hiện là ngưỡng của `risk_score` chuẩn hóa trong khoảng `0..1`.
Chúng không phải:

- TTC tính bằng giây.
- Khoảng cách tính bằng mét.
- Xác suất va chạm chính xác.
- Tốc độ xe.

Ví dụ cấu hình hiện tại:

```text
FCW Warning  = 0.56
FCW Critical = 0.78
```

#### Công thức risk score

```text
risk = (
    0.30 × proximity
  + 0.22 × center_score
  + 0.25 × approach
  + 0.13 × context
  + 0.10 × track_confidence
) × stability
```

Các thành phần:

- `proximity`: object càng gần vùng đầu xe thì càng nguy hiểm.
- `center_score`: object càng nằm trên hướng đi của ego vehicle thì càng cao.
- `approach`: object có xu hướng tiến gần hay không.
- `context`: thông tin lane, drivable area, loại đối tượng và bối cảnh.
- `track_confidence`: độ ổn định/tin cậy của object track.
- `stability`: mức ổn định qua nhiều frame.

#### Ví dụ tính toán

Giả sử:

```text
proximity        = 0.80
center_score     = 0.90
approach         = 0.70
context          = 1.00
track_confidence = 0.90
stability        = 0.90
```

Khi đó:

```text
risk_raw =
    0.30×0.80
  + 0.22×0.90
  + 0.25×0.70
  + 0.13×1.00
  + 0.10×0.90
  = 0.833

risk = 0.833 × 0.90 = 0.75
```

Vì `0.75 > 0.56`, object có thể đủ risk cho Warning nếu các điều kiện khác
như class, path conflict, track age, temporal confirmation và trạng thái armed
cũng đạt.

#### Warning threshold

Khi risk vượt Warning, hệ thống có thể phát cảnh báo mức Warning, ví dụ:

```text
Ô tô phía trước; tiến gần.
```

Nhưng vượt ngưỡng một mình chưa đủ để phát cảnh báo. Rule engine còn kiểm tra
đường đi, độ ổn định và các điều kiện an toàn khác.

#### Critical threshold

Khi risk vượt Critical và có thêm các điều kiện nghiêm ngặt, hệ thống có thể
phát cảnh báo Critical. Các điều kiện bổ sung có thể gồm:

- Object ở near field/imminent field.
- Có path conflict hoặc emergency override.
- Proximity và approach đủ lớn.
- Confidence và track age đủ cao.
- Temporal confirmation đã đạt.

Trong tình huống khẩn cấp, risk có thể được nâng lên khoảng `0.96` bởi emergency
override. Critical event có quyền ưu tiên beep và preempt advisory audio.

Việc đặt `Warning < Critical` giúp tách cảnh báo sớm khỏi cảnh báo khẩn cấp,
tránh việc mọi object đều phát âm thanh nguy hiểm cao.

### 2.7. Evidence packets: risk, confidence, lifecycle/audio

Evidence packet là bản ghi giải thích một cảnh báo hoặc quyết định của hệ thống.
Nó thường chứa event type, object/track ID, frame ID, source time, hướng, risk,
confidence, lifecycle và audio state.

#### Risk

Ví dụ:

```text
risk_score = 0.82
```

Đây là điểm nguy hiểm do RoadWatch tính từ proximity, path, motion, context và
stability. Nó không phải xác suất chắc chắn sẽ va chạm và cũng không phải TTC
theo đơn vị giây.

Ví dụ:

| Tình huống | Confidence | Risk |
|---|---:|---:|
| Xe đỗ bên lề, nhận diện rõ | 0.98 | 0.10 |
| Xe máy mờ nhưng đi vào ego path | 0.76 | 0.90 |

Object có confidence cao vẫn có thể không nguy hiểm; object confidence thấp hơn
có thể vẫn nguy hiểm nếu path conflict lớn.

#### Confidence

Ví dụ:

```text
confidence = 0.91
```

Confidence mô tả độ tin cậy của model/track đối với việc object thuộc class nào.
Nó trả lời:

> Model có chắc đây là xe máy, người đi bộ hoặc ô tô không?

Risk trả lời một câu khác:

> Object đó có nguy hiểm với xe hiện tại không?

Hai giá trị phải được đánh giá độc lập.

#### Lifecycle

Lifecycle mô tả vòng đời của event:

```text
candidate → accepted → active → expired/superseded
```

Các trạng thái thường gặp:

- `candidate`: rule engine mới tạo một ứng viên cảnh báo.
- `accepted`: AlertGovernor chấp nhận cho HMI.
- `suppressed`: bị chặn do duplicate, cooldown hoặc ưu tiên thấp.
- `expired`: hết thời gian hiển thị.
- `superseded`: bị event mới nghiêm trọng hơn thay thế.

#### Audio status/action

`audio_action` mô tả loại âm thanh được phép, ví dụ:

- `hud`: chỉ hiển thị trên màn hình.
- `tts`: phát TTS.
- `beep_tts`: phát beep ưu tiên rồi phát TTS.

`audio_status` mô tả trạng thái thực tế của audio:

```text
not_requested → queued → playing → completed
```

Các trạng thái lỗi hoặc loại bỏ có thể gồm:

- `failed`: tạo hoặc phát audio bị lỗi.
- `dropped_stale`: audio cũ bị loại vì event mới thay thế hoặc session thay đổi.
- `suppressed`: event không được phép phát audio.

Ví dụ:

| Lifecycle | Audio | Ý nghĩa |
|---|---|---|
| accepted | queued | Event được chấp nhận, audio đang chờ |
| accepted | playing | Audio đang phát |
| accepted | completed | Audio đã phát xong |
| accepted | not_requested | Được hiển thị nhưng không yêu cầu âm thanh |
| suppressed | suppressed | Event bị governor chặn |
| accepted | failed | Event tồn tại nhưng audio lỗi |

Evidence packet giúp kỹ sư biết hệ thống đã nhìn thấy gì, tính risk ra sao và
đã cấp quyền HMI/audio thế nào. Nó vẫn không tự chứng minh rằng cảnh báo đúng
ngoài thực tế; muốn kết luận đúng/sai phải so với ground truth.

## 3. Kiến trúc build và triển khai Cloud

### 3.1. Các thành phần sử dụng

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| Frontend | React + Vite | Driver HUD và Engineer Dashboard |
| Backend | FastAPI + Uvicorn | API, auth, session và orchestration |
| Computer Vision | YOLO, ONNX Runtime, OpenCV, NumPy | Object, traffic sign, lane và preprocessing |
| TTS | Piper qua service riêng | Sinh WAV tiếng Việt |
| Container | Docker | Đóng gói frontend/backend/runtime |
| Build | Cloud Build | Build image và deploy tự động |
| Registry | Artifact Registry | Lưu Docker image |
| Compute | Cloud Run | Chạy web và TTS service |
| Asset storage | Cloud Storage | Lưu model, video và voice |
| Logging | Cloud Logging | Theo dõi log, health và lỗi |
| Domain | Cloud Run domain mapping/DNS | URL public cho demo |

RoadWatch không cần Firebase trong kiến trúc hiện tại.

### 3.2. GCP target hiện tại

```text
Project:
c3-roadwatch-162

Region:
asia-southeast1

Artifact Registry repository:
roadwatch

Cloud Run web service:
roadwatch-web

Cloud Run TTS service:
roadwatch-tts

Cloud Storage bucket:
gs://c3-roadwatch-162-roadwatch-assets
```

### 3.3. Cấu hình Cloud Run

Web service:

```text
CPU: 8 vCPU
Memory: 8 GiB
Timeout: 3600 giây
Concurrency: 80
Min instances: 0
Max instances: 1
Session affinity: bật
CPU boost: bật
CPU throttling: tắt
```

TTS service:

```text
CPU: 2 vCPU
Memory: 2 GiB
Concurrency: 4
Min instances: 0
Max instances: 1
Timeout: 120 giây
```

TTS service là private. Web service được cấp quyền IAM để gọi TTS; người dùng
không gọi trực tiếp private TTS endpoint.

Cloud profile hiện chạy CPU và sử dụng model/input profile nhẹ hơn để phù hợp
Cloud Run. Nó là replay/evaluation plane cho demo, không phải safety-critical
edge path của xe.

### 3.4. Vì sao model/video không nằm trong Git hoặc Docker image

Các file lớn được phân phối qua GCS thay vì commit vào Git để:

- Không vượt giới hạn GitHub.
- Giảm kích thước Docker image.
- Giảm thời gian build.
- Cho phép thay asset mà không cần sửa source.
- Giữ source code, model release và demo media độc lập.

`.gcloudignore` loại model/video/voice/dataset nặng khỏi build context, nhưng
Cloud runtime vẫn sử dụng chúng thông qua asset bootstrap:

```text
GCS bucket
  → asset bootstrap
  → tải allowlisted asset
  → lưu vào filesystem tạm của container
  → tạo ONNX Runtime session
  → warmup perception
  → startup ready
```

GCS là nơi lưu trữ bền vững. Filesystem của Cloud Run chỉ là vùng tạm theo
instance và không nên được coi là database lâu dài.

Các model cloud hiện được allowlist gồm:

```text
yolo11n_320.onnx
roadwatch_detector_v2_416.onnx
roadwatch_speed_digits_v2.onnx
yolop_lane_detection_640.onnx
```

### 3.5. Các bước build/deploy

#### Bước 1 — Chuẩn bị dịch vụ GCP

Bật Cloud Run, Cloud Build, Artifact Registry, Cloud Storage và Cloud Logging.
Sau đó chuẩn bị Artifact Registry, GCS bucket, service account và IAM reader
cho asset.

#### Bước 2 — Submit Cloud Build

```bash
gcloud builds submit roadwatch \
  --project=c3-roadwatch-162 \
  --config=roadwatch/deploy/gcp/cloudbuild.yaml
```

#### Bước 3 — Build frontend

`Dockerfile.cloud` dùng stage Node để:

```text
npm ci
→ npm run build
→ frontend/dist
```

Frontend đã compile được copy vào Python runtime image, nên người dùng chỉ cần
một URL duy nhất.

#### Bước 4 — Build backend

Backend được đóng gói với Python/FastAPI/Uvicorn và các dependency CV cần thiết.
Nó cung cấp auth, media catalog, upload, session, stream, status, event và TTS
endpoint.

#### Bước 5 — Push image

Cloud Build push web image và TTS image vào Artifact Registry theo build ID.

#### Bước 6 — Deploy TTS trước

Cloud Build deploy `roadwatch-tts` ở chế độ private, sau đó cấp quyền invoker
cho runtime service account của web.

#### Bước 7 — Deploy web

Cloud Build deploy `roadwatch-web` public với các biến môi trường chính:

```text
ROADWATCH_CLOUD_MODE=web_demo
ROADWATCH_DEFERRED_STARTUP=1
ROADWATCH_CLOUD_FULL=1
ROADWATCH_CLOUD_IMAGE_SIZE=320
ROADWATCH_DISABLE_AUDIO=1
ROADWATCH_MAX_UPLOAD_MB=25
ROADWATCH_GCS_ASSET_BUCKET=c3-roadwatch-162-roadwatch-assets
ROADWATCH_ASSET_GROUPS=models
ROADWATCH_ASSET_PATHS=<allowlisted model paths>
<private TTS service URL>
```

`ROADWATCH_DISABLE_AUDIO=1` có nghĩa server không sử dụng loa vật lý của máy chủ.
Browser sẽ nhận WAV và phát audio trên máy của người dùng.

## 4. Luồng hoạt động user → Cloud → user

```text
Người dùng mở URL public
        ↓
Cloud Run Web trả React UI
        ↓
Frontend polling /api/startup
        ↓
Cloud tải asset từ GCS và warmup model
        ↓
Frontend hiển thị Ready
        ↓
Người dùng đăng nhập/chọn hoặc upload video
        ↓
FastAPI tạo session_id
        ↓
Pipeline chạy object + sign + lane
        ↓
Tracking + Risk Engine + AlertGovernor
        ↓
MJPEG frame + status JSON + evidence packet
        ↓
Browser cập nhật HUD/Dashboard
        ↓
Browser yêu cầu WAV TTS
        ↓
Web service gọi private TTS Cloud Run
        ↓
WAV trả về browser và được phát trên loa người dùng
```

### Bước 1 — Người dùng mở URL

URL chính thức được định hướng:

```text
https://c3-roadwatch-162.io.vn
```

URL `run.app` là fallback khi domain riêng chưa được map hoặc DNS chưa sẵn sàng.

### Bước 2 — React tải giao diện

Giao diện hiển thị login, Driver HUD, Engineer Dashboard, video catalog, upload
area và trạng thái startup.

### Bước 3 — Startup gate

Frontend gọi:

```text
/api/startup
```

Cloud có thể đang tải model/video/voice, khởi tạo runtime và warmup. Trong thời
gian đó `/api/session/start` chưa được phép chạy để tránh session lỗi do model
chưa sẵn sàng.

### Bước 4 — Đăng nhập

FastAPI xác thực tài khoản demo và trả token cho các API được bảo vệ:

```text
driver / driver123
engineer / engineer123
```

Đây chỉ là credentials phục vụ demo, không phải cấu hình production.

### Bước 5 — Chọn hoặc upload video

Video có thể đến từ:

- Video có sẵn trong media catalog.
- File người dùng upload.
- Asset đã lưu trong GCS.

Upload multipart hiện có giới hạn khoảng 25 MB. Video lớn hơn cần signed
resumable upload để phù hợp production.

### Bước 6 — Bắt đầu phân tích

Frontend gọi `/api/session/start`. Backend kiểm tra token/startup, materialize
video nếu cần, tạo session ID và reset playback, tracker, risk, alert và audio
state. Việc reset này ngăn trạng thái của video trước rò sang video mới.

### Bước 7 — Pipeline phân tích

```text
Object detection
→ Traffic sign detection/classification
→ Lane/drivable-area inference
→ Object tracking
→ Motion/path/risk estimation
→ AlertGovernor
→ Frame annotation và JPEG encode
```

Kết quả gồm bounding box, lane mask, drivable area, sign, track ID, risk score,
event và evidence packet.

### Bước 8 — Hình ảnh và trạng thái trả về browser

Frame annotate được stream qua:

```text
/api/stream.mjpg
```

Frontend polling `/api/status` khoảng mỗi 500 ms để nhận metrics, event, playback
time, model state và audio state.

### Bước 9 — TTS và beep

Với Critical event:

```text
AlertGovernor: beep_tts
  → browser phát beep
  → browser lấy WAV từ /api/tts/events/{event_id}.wav
  → browser phát TTS
```

Advisory event có thể chỉ hiển thị HUD hoặc phát TTS tùy severity, cooldown,
global audio gap, audio budget và việc event đã được phát trước đó hay chưa.

## 5. Phân biệt các loại độ trễ khi demo Cloud

Thời gian người dùng cảm nhận được thường gồm:

```text
Upload/network
+ Cloud Run cold start
+ Asset/model loading
+ Perception warmup
+ Session startup
+ Frame inference
+ MJPEG delivery
+ Browser rendering
+ TTS request/playback
```

Trong khi đó, `E2E P50/P95` hiện chỉ tập trung vào phần xử lý frame bên trong
pipeline. Vì vậy:

- E2E P95 thấp không đảm bảo URL public không có cold-start.
- Warmup thấp không đồng nghĩa container đã tải xong toàn bộ asset.
- User-perceived latency có thể cao hơn latency inference.
- Cloud CPU không thể dùng để khẳng định hiệu suất Jetson Orin.

Cloud Run hiện là **public replay/evaluation plane**. Local/AAOS là hướng critical
deployment khi có camera, calibration, telemetry và phần cứng xe thực tế.

## 6. Giới hạn và định hướng production

### Đã có

- Một URL public cho demo.
- React HUD/Dashboard.
- FastAPI session/auth/status/stream.
- Model tải từ GCS thay vì commit Git.
- Private TTS service.
- Startup gate và health endpoint.
- Evidence packet phục vụ truy vết.
- Session isolation cho chọn video, pause và seek.
- Cloud Logging.

### Chưa nên tuyên bố quá mức

- Cloud Run không phải Jetson Orin.
- Chưa có camera thật, CAN bus, radar hoặc calibration xe VinFast.
- TTC hiện chưa phải khoảng cách mét ground truth nếu thiếu calibration/telemetry.
- Public web không phải safety-critical warning path.
- SQLite/filesystem trong container không thay thế hệ thống persistence production.
- Chưa có quyền điều khiển phanh, ga hoặc vô-lăng.

### Kết luận

Kiến trúc hiện tại chứng minh được RoadWatch có thể được đóng gói thành sản phẩm
chạy qua URL public, có perception, risk engine, evidence, dashboard và TTS.
Đồng thời, kiến trúc vẫn giữ đường chuyển tiếp rõ ràng sang edge/AAOS: các model,
rule engine và canonical alert contract có thể được đóng gói vào edge runtime khi
được cung cấp phần cứng, calibration và interface xe phù hợp.
