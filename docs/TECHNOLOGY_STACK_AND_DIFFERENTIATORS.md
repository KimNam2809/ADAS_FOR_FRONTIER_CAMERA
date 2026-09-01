# RoadWatch Copilot — Technology Stack, Tiêu chí lựa chọn và Điểm khác biệt

> **Ngày kiểm kê:** 2026-08-26  
> **Trạng thái:** Technical PoC / Demo-ready / Edge-oriented  
> **Safety boundary:** RoadWatch chỉ cảnh báo và hỗ trợ người lái; không tự lái,
> không phanh, không tăng ga và không đánh lái.

Tài liệu này giải thích RoadWatch đang sử dụng công nghệ gì, vì sao chọn chúng,
tiêu chí nào được dùng để quyết định, các bài toán đã giải quyết đến đâu và
RoadWatch khác các nhóm sản phẩm ADAS tương tự ở điểm nào.

Các kết luận trong tài liệu được chia thành ba trạng thái:

- **Active:** đang được sử dụng trong runtime mặc định.
- **Candidate:** đã thử nghiệm nhưng chưa đủ điều kiện promote.
- **Planned/blocked:** có hướng triển khai nhưng còn thiếu dữ liệu, hardware,
  calibration, quyền OEM hoặc bằng chứng kiểm thử.

Không được dùng tài liệu này để tuyên bố RoadWatch đã được chứng nhận an toàn,
đã tích hợp xe VinFast thật hoặc có khả năng tự hành.

## 1. RoadWatch đang xây dựng sản phẩm gì?

RoadWatch Copilot là trợ lý cảnh báo ADAS đa phương thức cho camera trước ô tô,
ưu tiên giao thông hỗn hợp tại Việt Nam. Hệ thống phân tích video/camera, nhận
diện tác nhân giao thông, làn đường, vùng có thể lái và biển báo, sau đó dùng
tracking cùng rule engine để quyết định mức nguy hiểm và phát cảnh báo ngắn
gọn bằng banner, beep hoặc TTS tiếng Việt.

Luồng logic cốt lõi:

```text
Video / camera frame
        ↓
Perception: object + traffic sign + lane/drivable area
        ↓
Temporal evidence: track ID + history + motion
        ↓
Risk Engine: FCW / VRU / cut-in / cross-traffic / LDW / signs
        ↓
Alert Governor: severity + confirmation + cooldown + deduplication
        ↓
Canonical AlertEvent
        ├── Driver HUD / Engineer Dashboard
        ├── Beep / Vietnamese TTS
        └── Evidence / metrics / regression report
```

Kiến trúc được thiết kế theo nguyên tắc **one Core, three deployments**:

1. **Local/Edge plane:** chạy offline trên laptop, NVIDIA hoặc Jetson candidate;
   đây là đường hướng tới cảnh báo realtime.
2. **AAOS HMI plane:** Android Automotive emulator/app mô phỏng màn hình xe,
   playback và vehicle contract; chưa phải Camera HAL/OEM integration.
3. **GCP evaluation plane:** public web, upload, model asset bootstrap, HITL và
   replay; không nằm trên critical path của cảnh báo xe thật.

## 2. Technology stack hiện tại

### 2.1. Bảng tổng quan

| Lớp | Công nghệ/trạng thái | Lý do chọn | Tiêu chí quyết định | Giới hạn hiện tại |
|---|---|---|---|---|
| Ngôn ngữ runtime | Python | Tốc độ phát triển, hệ sinh thái CV/ML, dễ chạy local và cloud | Khả năng tích hợp OpenCV, ONNX Runtime, FastAPI, test nhanh | Không phải lựa chọn tối ưu cuối cùng cho mọi hard real-time path |
| API | FastAPI + Uvicorn | Async HTTP/WebSocket, type/schema rõ, dễ đóng gói | API latency, startup lifecycle, testability, container support | Pipeline MVP còn chạy worker thread; production nên tách core/API process |
| Frontend | React + TypeScript + Vite | Hợp với HUD, dashboard, playback và state realtime | Component hóa, build static, dễ phục vụ từ FastAPI/Cloud Run | Browser network/audio không đại diện hoàn toàn cho HMI xe |
| Video | OpenCV + NumPy | Decode, resize, annotate và xử lý tensor phổ biến | Cross-platform, dependency vừa phải, đủ cho replay realtime | Codec/video lỗi cần FFmpeg fallback; camera thật cần adapter khác |
| Object model | YOLO11n COCO — **Active baseline** | Nhẹ, taxonomy road-user ổn định, có ONNX export | Event recall, false alerts, latency, portability | Không tối ưu đầy đủ cho mọi cảnh giao thông Việt Nam |
| Traffic sign | Detector Phase 2 + speed classifier ONNX — **Active/promoted** | Giữ chi tiết biển nhỏ và tách recognition số tốc độ | mAP, precision/recall, top-1 speed, temporal/negative regression | Orientation, biển mâu thuẫn và low-light vẫn cần mở rộng |
| Lane/drivable | YOLOP ONNX 640 — **Active baseline** | Một model cho lane mask và drivable-area, đã nối LDW | Lane quality, coverage, LDW stability, latency | Multi-lane trong video xấu/đêm/mưa chưa đủ mạnh |
| Lane candidate | UFLDv2 ResNet-18 — **Candidate rejected** | Geometry tiềm năng và nhẹ hơn trên một số sample | Fusion FPS, E2E P95, coverage, multi-lane evidence | DirectML fusion chỉ khoảng 3.04 FPS, chưa đạt edge gate |
| Runtime inference | ONNX Runtime | Một API cho CPU, DirectML, CUDA/TensorRT và nhiều platform | Portability, provider fallback, reproducible graph | Provider/driver/version phải khớp phần cứng |
| Windows AMD | ONNX Runtime DirectML | Tận dụng Radeon/DirectX trên laptop hiện có | Có thể chạy trên AMD mà không cần CUDA | DirectML sustained engineering; hiệu năng phụ thuộc driver/model |
| NVIDIA/Jetson | CUDA/TensorRT path | Phù hợp GPU NVIDIA và edge deployment mục tiêu | FPS, p95, memory, FP16/INT8, thermal | Chưa có benchmark trên Jetson Orin vật lý |
| Tracking | Deterministic IoU tracker | Đủ nhẹ để tạo temporal evidence, dễ debug | Track continuity, class stability, CPU cost | Chưa phải ByteTrack/DeepSORT đầy đủ |
| Risk | Python deterministic Risk Engine | Explainable, bounded latency, không phụ thuộc LLM | Rule coverage, event recall, false alert, replayability | Image-space proxy chưa thay TTC mét/calibrated telemetry |
| Alerting | Alert Governor | Một cổng duy nhất cho severity, cooldown và audio | Không duplicate/overlap, preemption, canonical equality | Ngưỡng phải được calibration bằng dữ liệu target-domain |
| TTS release | Piper Vietnamese — **Active fallback/release** | Offline, cache được, giọng Việt xác định, dễ chạy edge | Audio completion, first-audio latency, clarity, license | Chất lượng tự nhiên thấp hơn candidate VieNeu ở một số tiêu chí |
| TTS candidate | VieNeu-TTS v3 Turbo / Minh Triết — **Candidate** | Giọng rõ, tự nhiên và dứt khoát trong human listening sơ bộ | 149/149 câu, latency, audio integrity, 3-person listening gate | Chưa promote vì còn gate âm đầu, hướng và số cần kiểm chứng |
| Local evidence | SQLite + JSON/Markdown reports | Audit event, audio lifecycle và regression dễ truy vết | Deterministic evidence, không phụ thuộc cloud | Filesystem container không phải persistence production |
| Packaging | Docker + Docker Compose | Tái lập local/CPU/NVIDIA/ARM64 profiles | Build reproducibility, profile isolation, rollback | TensorRT/JetPack vẫn phụ thuộc image và hardware cụ thể |
| AAOS | Android Studio + Kotlin/AAOS emulator | Mô phỏng HMI màn hình xe và vehicle contract | Offline replay, UI behavior, safe read-only boundary | Chưa có Camera2/EVS handle hoặc VinFast OEM API |
| Cloud build | Cloud Build + Docker | Build/deploy không phụ thuộc Docker daemon local | Audit build, image immutability, CI repeatability | GCP build vẫn tốn thời gian/chi phí |
| Cloud compute | Cloud Run Web + private TTS | HTTPS public demo, scale-to-zero, service isolation | Startup behavior, request reliability, access control | Cloud CPU replay không phải edge benchmark |
| Asset | Cloud Storage + allowlist/checksum | Tách model/video nặng khỏi Git và image | Integrity, lazy loading, artifact rollback | Cần quota/IAM/GCS configuration |
| Registry/logging | Artifact Registry + Cloud Logging | Lưu image và theo dõi deployment | Digest pinning, logs, health/rollback | Chưa phải fleet OTA/model registry production |
| Training | Kaggle GPU | Offload fine-tune khỏi laptop AMD 16 GB RAM | GPU preflight, reproducibility, Quality Gate, cost | Job/asset lifecycle phụ thuộc Kaggle |

### 2.2. Backend và API

FastAPI được chọn vì RoadWatch cần nhiều loại giao tiếp đồng thời:

- HTTP API cho login, media catalog, upload và session control.
- Polling `/api/status` cho metrics/event/playback state.
- MJPEG stream cho frame annotate.
- Endpoint WAV theo `event_id` cho TTS.
- Startup/health endpoint cho Cloud Run cold-start gate.

FastAPI không quyết định cảnh báo. Nó chỉ là lớp điều phối và truyền kết quả.
Safety logic nằm trong perception, risk và Alert Governor để khi browser đóng,
core vẫn có thể tiếp tục chạy trong edge profile.

### 2.3. Frontend React/TypeScript

React + TypeScript + Vite được chọn vì UI có hai người dùng khác nhau:

- **Driver HUD:** ít thông tin, ưu tiên cảnh báo nguy hiểm, hướng và hành động.
- **Engineer Dashboard:** metrics, model health, evidence packet, threshold,
  lifecycle/audio state, playback và HITL.

Vite tạo static bundle nhanh và bundle đó có thể được phục vụ bởi FastAPI trong
local hoặc Cloud Run. Cùng một frontend được dùng để kiểm tra local và public
replay, giúp giảm sai lệch giữa demo và development.

### 2.4. OpenCV và NumPy

OpenCV đảm nhiệm:

- Đọc video và truy xuất timestamp/frame.
- Resize, color conversion và preprocessing.
- Vẽ bounding box, lane mask và hazard banner.
- Encode JPEG cho MJPEG stream.
- Một số kiểm tra hình học/visual validation của biển báo.

NumPy là lớp dữ liệu trung gian giữa frame, tensor, mask và post-processing.
Lựa chọn này phù hợp với prototype vì ít thành phần, dễ debug và hoạt động trên
Windows/Linux/ARM64. Khi chuyển sang xe thật, camera source có thể thay nhưng
schema `FramePacket` và downstream contract nên được giữ nguyên.

## 3. Vì sao chọn các model hiện tại?

### 3.1. Nguyên tắc quyết định model

RoadWatch không promote model chỉ vì một con số mAP tăng. Mỗi candidate phải
được đánh giá ở ba cấp:

1. **Static model metrics:** precision, recall, mAP50, mAP50-95, confusion matrix.
2. **Event metrics:** critical event recall, hướng, path conflict, miss và false
   alert trong các window có ground truth.
3. **System metrics:** FPS, latency P50/P95, memory, dropped frame, audio và
   session correctness.

Thứ tự ưu tiên:

```text
Critical-event recall
→ false-alert budget
→ semantic correctness/direction
→ latency/FPS
→ size/memory/portability
→ maintainability and rollback
```

### 3.2. Object detection

#### Model active

```text
YOLO11n COCO / yolo11n.onnx hoặc yolo11n.pt
```

Taxonomy được dùng cho road users:

```text
person, bicycle, motorcycle, car, bus, truck
```

Lý do giữ baseline:

- Nhẹ và phù hợp pipeline realtime hơn các model lớn.
- COCO taxonomy có tính ổn định và có pretrained prior tốt.
- Có thể export ONNX.
- Có đường chạy CPU, DirectML, CUDA và TensorRT.
- Dễ rollback khi candidate fine-tune làm giảm event recall.

#### Vì sao Object V1.1 chưa được promote?

Kết quả đã ghi nhận:

```text
mAP50: 0.5124
event recall: 0.5000 → 0.3750
false alerts: 10.3846 → 5.7692/phút
```

False alert giảm nhưng critical event recall giảm. Với hệ thống cảnh báo, bỏ
lỡ nguy cơ quan trọng nghiêm trọng hơn việc giảm một phần cảnh báo dư thừa.

#### Vì sao Object V2 chưa được promote?

```text
baseline event recall: 0.80
candidate event recall: 0.60

baseline false alerts: 3.8462/phút
candidate false alerts: 4.6154/phút
```

Candidate có object latency tốt hơn trong một số benchmark nhưng chất lượng
event giảm và false alert tăng. Vì vậy runtime mặc định vẫn là `baseline_coco`.

### 3.3. Traffic sign

Traffic sign được tách thành detector và speed classifier thay vì ép một model
nhỏ vừa nhận diện biển vừa đọc chính xác chữ/số nhỏ:

```text
roadwatch_detector_v2.onnx
roadwatch_speed_digits_v2.onnx
```

Evidence promotion:

```text
Detector precision: 0.95847
Detector recall:    0.96651
Detector mAP50:     0.98741
Detector mAP50-95:   0.83217
Speed top-1:        0.98254
Speed top-5:        0.99501
```

Locked replay đã ghi nhận:

- Nhận diện biển 60 trong `test_video10`.
- Nhận diện biển 80 trong `test_video11`.
- Banner và TTS dùng cùng canonical message.
- Negative window không tạo speed false positive theo evidence đã khóa.

Đây là model/profile được promote vì vượt cả static gate lẫn video regression,
không chỉ vì nhìn tốt trên vài frame.

### 3.4. Lane và drivable area

YOLOP được giữ làm active baseline vì một model cung cấp:

- Lane mask.
- Drivable-area mask.
- Integration sẵn với lane quality và LDW.

UFLDv2 ResNet-18 là candidate nghiên cứu, chưa promote:

```text
Usable coverage:       0.8571
DirectML fusion FPS:   3.04
Lane P95:              124.68 ms
E2E P95:               149.37 ms
```

UFLDv2 có thể tạo geometry tốt hơn trong một số trường hợp, nhưng tốc độ fusion
trên AMD không phù hợp edge gate và chưa đủ evidence multi-lane trong đêm/mưa/
video nén. Vì vậy YOLOP vẫn là runtime an toàn hơn về mặt triển khai hiện tại,
dù chất lượng lane chưa hoàn hảo.

### 3.5. Vì sao chưa gộp ba model thành một neural network?

Có thể nghiên cứu multi-task model gồm object head, sign head và lane head dùng
shared backbone, nhưng không thể ghép trực tiếp ba file weights hiện tại vì:

- Kiến trúc, preprocessing và output tensor khác nhau.
- Biển báo nhỏ cần input/feature resolution khác object detection.
- Lane cần spatial prediction dày, object cần instance prediction.
- Dataset chưa có annotation đồng bộ trên cùng frame.
- Multi-task training có thể gây task interference.
- Một backbone chung chưa đảm bảo latency thấp hơn.
- Debug, quantization, rollback và promotion sẽ khó hơn.

Do đó quyết định hiện tại là:

```text
Ba model độc lập
→ Perception Orchestrator
→ unified schema
→ risk/alert engine
```

Đây là lựa chọn thực tế nhất cho khả năng rollback và kiểm chứng. Multi-task
model chỉ được mở lại khi có annotation đồng bộ, split khóa và benchmark chứng
minh critical event recall không giảm.

## 4. Vì sao chọn ONNX Runtime và các execution provider?

RoadWatch cần chạy trên nhiều môi trường mà không muốn viết lại perception code:

| Môi trường | Provider/profile | Mục tiêu |
|---|---|---|
| Windows laptop AMD | DirectML hoặc CPU fallback | Development/demo hiện tại |
| NVIDIA PC/EC2 | CUDA/TensorRT hoặc CPU fallback | Benchmark GPU và mô phỏng server |
| Jetson Orin | TensorRT/ONNX Runtime ARM64 | Edge target cần benchmark phần cứng thật |
| Cloud Run | ONNX Runtime CPU | Public replay/evaluation, không có GPU quota |
| Android/AAOS | HMI/app; inference nên ở local edge service | Mô phỏng integration, không tự suy đoán Camera HAL |

ONNX Runtime cung cấp Execution Provider abstraction giúp cùng một ONNX graph có
thể chọn CPU, DirectML, CUDA hoặc TensorRT tùy môi trường. Provider thực tế phải
được xác nhận bằng health/status và benchmark trên thiết bị cụ thể.

Nguồn kỹ thuật chính thức:

- [ONNX Runtime Execution Providers](https://onnxruntime.ai/docs/execution-providers/)
- [ONNX Runtime DirectML](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [ONNX Runtime TensorRT](https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html)

## 5. Rule Engine, Tracking và Alert Governor giải quyết vấn đề gì?

### 5.1. Tracking

Một detection đơn lẻ chưa đủ để kết luận xe đang tiến gần hay cắt ngang. Tracker
giữ:

- `track_id`.
- Lịch sử bounding box.
- Class votes theo thời gian.
- Hit/miss count.
- Expansion rate.
- Lateral velocity.

RoadWatch hiện dùng deterministic IoU tracker nhẹ. Nó chưa phải ByteTrack đầy đủ,
nhưng tạo được temporal evidence để giảm cảnh báo từ một frame nhiễu.

### 5.2. Risk Engine

Risk Engine kết hợp:

- Proximity trong image space.
- Vị trí so với vùng ego path.
- Box expansion/approach.
- Lane/drivable context.
- Track confidence và stability.

Risk score hiện là điểm chuẩn hóa `0..1`, không phải xác suất va chạm, không phải
khoảng cách mét và không phải TTC ground truth khi chưa có calibration/telemetry.

### 5.3. Các event đã có đường xử lý

| Event | Cách xử lý hiện tại | Mức độ hoàn thiện |
|---|---|---|
| FCW | Proximity + center/path + approach + temporal confirmation + severity | Đã có logic; cần mở rộng closed-course/ground truth |
| VRU | Phân loại person/motorcycle/bicycle và xét ego path | Đã có logic; target-domain recall còn thiếu |
| Cut-in | Lateral movement, displacement và path conflict | Đã có logic; góc khuất cần thêm data |
| Cross-traffic | Lateral motion, dominance và collision path | Đã có logic; ngã tư/occlusion cần thêm regression |
| Lead braking | Image-space relative expansion/closing trend | Chỉ là proxy, chưa có brake-light/CAN/ego speed ground truth |
| LDW | Lane quality + smoothed offset + confirmation frames | Đã có cảnh báo; multi-lane và low-light còn hạn chế |
| Speed sign | Detector + classifier + temporal confirmation + arbitration | Đã promote với locked sign evidence |
| Fallen rider | Taxonomy/pipeline candidate | Chưa promote; target dataset quality gate còn block |

### 5.4. Alert Governor

Alert Governor là lớp duy nhất có quyền cấp HMI/audio. Nó thực hiện:

- Severity ranking: informational → advisory → warning → critical.
- Temporal confirmation.
- Debounce/cooldown.
- Duplicate suppression.
- Critical preemption.
- Một audio winner tại mỗi thời điểm.
- Ghi suppression reason.

Banner và TTS lấy cùng `canonical AlertEvent`, nên hệ thống không để frontend tự
viết lại câu hoặc TTS tự suy diễn class/hướng. Đây là cách RoadWatch giải quyết
nhóm lỗi banner đọc khác TTS.

## 6. TTS và trải nghiệm người lái

### 6.1. Piper release baseline

Piper được giữ làm release provider vì:

- Chạy offline.
- Có voice tiếng Việt cố định.
- Dễ cache trước các câu cảnh báo canonical.
- Phù hợp edge hơn một service ngôn ngữ lớn.
- Có rollback rõ ràng nếu candidate lỗi.

### 6.2. VieNeu candidate

VieNeu-TTS v3 Turbo với voice `Minh Triết` đã được tích hợp theo provider
abstraction và benchmark độc lập. Human listening sơ bộ cho kết quả tốt về:

```text
Độ rõ:       5/5
Tự nhiên:    5/5
Dứt khoát:   5/5
Đúng nghĩa:  Có
Chồng âm:    Không
```

Tuy nhiên candidate chưa được promote vì còn phải kiểm chứng:

- Không mất một hoặc hai từ đầu câu.
- Không sai trái/phải do upstream perception/geometry.
- Không sai số tốc độ do sign detector/classifier/arbitration.
- 149/149 canonical messages.
- Cached start P95 `<=750 ms`.
- Uncached short alert P95 `<=2.0 s`.
- Human gate tối thiểu ba người nghe tiếng Việt, điểm trung bình `>=4/5`.

Điểm quan trọng: TTS chịu trách nhiệm phát câu đúng và rõ; nếu câu đã đúng text
nhưng nói sai trái/phải hoặc số tốc độ, nguyên nhân thường nằm ở perception,
sign arbitration hoặc risk event trước TTS.

## 7. Các vấn đề RoadWatch đã giải quyết

### 7.1. User story và bằng chứng

| User story | Đã giải quyết bằng | Bằng chứng hiện có | Trạng thái thực tế |
|---|---|---|---|
| Là tài xế, tôi muốn biết có người/xe phía trước | YOLO11n + tracking + risk + HUD | Có object/track/evidence trên video replay | Pass ở mức software path; recall chưa production-certified |
| Tôi muốn cảnh báo xe máy/người dễ gặp ở Việt Nam | Road-user taxonomy, VRU rules, target-domain data | Có RW-05 windows và event regression tooling | Partial; cần thêm labeled night/rain/cut-in data |
| Tôi muốn biết nguy cơ va chạm trước khi quá muộn | FCW warning/critical + path/approach + temporal confirmation | Risk score, severity và audio event | Partial; chưa có closed-course calibrated validation |
| Tôi muốn được cảnh báo lệch làn | YOLOP lane/drivable mask + smoothing + lane gate | Lane quality và LDW event trong replay | Partial; video xấu/multi-lane còn miss |
| Tôi muốn nhận diện biển tốc độ Việt Nam | Sign detector + speed classifier + arbitration | Precision `0.95847`, recall `0.96651`, speed top-1 `0.98254`; replay biển 60/80 | Pass trong locked scope |
| Tôi không muốn bị đọc lặp gây mệt mỏi | Alert Governor, cooldown, token budget, deduplication | Audio/lifecycle/suppression evidence | Pass ở mức contract; cần test dài hơn trên cabin noise |
| Banner và TTS phải thống nhất | Canonical message/event ID | `display_message == spoken_message` contract | Pass trong software contract |
| Tôi muốn chạy offline | ONNX model, local Python, Piper, Docker | Local profile và offline source/media | Pass cho replay; camera thật còn cần adapter |
| Kỹ sư cần biết vì sao hệ thống cảnh báo | Evidence packet + SQLite + metrics + reports | Risk/confidence/lifecycle/audio/frame/time | Pass ở mức observability |
| Tôi muốn chạy trên nhiều thiết bị | ONNX provider + Docker profiles + AAOS HMI | Windows AMD, CPU Cloud, NVIDIA/ARM64 packaging | Partial; Jetson Orin thật chưa benchmark |
| Ban tổ chức cần URL để demo | React/FastAPI/Cloud Run/GCS/TTS private service | Public replay, startup gate, asset bootstrap | Pass cho public evaluation plane |
| Tôi muốn pause/seek/đổi video không lẫn state | Session ID + playback reset + stream isolation | Playback smoke tests và session regression | Pass trong implementation hiện tại |

### 7.2. Các vấn đề chưa được coi là đã giải quyết hoàn toàn

RoadWatch hiện chưa thể tuyên bố đã giải quyết đầy đủ:

- Camera thật từ xe VinFast.
- Camera HAL/EVS permission trên head unit.
- CAN bus, ego speed, yaw rate, turn signal và brake signal thật.
- Khoảng cách/TTC tuyệt đối theo mét.
- Closed-course validation có safety driver và ground truth vật lý.
- Multi-lane ổn định ở mọi đêm/mưa/ngược sáng.
- Fallen rider model đã được promote.
- Jetson Orin thermal/FPS benchmark thật.
- OTA fleet model management và certification.

## 8. So sánh với các sản phẩm tương tự

### 8.1. Phạm vi so sánh

RoadWatch không cùng mức trưởng thành với hệ thống OEM thương mại hoặc sản phẩm
đã có hàng triệu km vận hành. So sánh dưới đây tập trung vào định hướng công
nghệ, phạm vi tính năng và khả năng kiểm chứng; không phải benchmark accuracy
giữa các sản phẩm.

Các nguồn tham khảo công khai:

- [Mobileye Products — Base Driver Assist](https://www.mobileye.com/products/)
- [Tesla Autopilot and Full Self-Driving Capability](https://www.tesla.com/en_GB/support/autopilot)
- [Volvo EC40 owner manual — collision risk/lane keeping](https://www.volvocars.com/static/support/pdf/ca_en-US_ec40_2026_UM_adc6b6ff4aba27d80584a0803f109c81.pdf)
- [openpilot official documentation](https://docs.comma.ai/)

### 8.2. So sánh theo nhóm sản phẩm

| Tiêu chí | OEM/ADAS tích hợp như Mobileye/Volvo | Tesla Autopilot/FSD Supervised | openpilot | RoadWatch hiện tại |
|---|---|---|---|---|
| Mục tiêu | Tính năng ADAS tích hợp xe, thường có nhiều sensor/ECU và validation OEM | Driver assistance có active steering/braking tùy feature, cần driver supervision | Open-source driver assistance cho xe/model được hỗ trợ | Warning-only copilot cho front camera/video, hướng edge |
| Perception hardware | Có tích hợp theo vehicle program; Mobileye có EyeQ và front-facing/surround variants | Nhiều camera và onboard compute của xe | Dùng camera/hardware của comma và vehicle APIs | Một front-camera/video source; edge model adapters |
| Tác động lên xe | Có thể tích hợp active safety/control tùy sản phẩm và cấu hình | Có tính năng điều khiển dưới supervision | Tài liệu openpilot mô tả ACC/ALC và vehicle inputs | Không có actuator command; không phanh/đánh lái |
| Tác nhân/ADAS | Collision, lane, pedestrian/cyclist, headway/speed tùy package | Lane, object, traffic control và nhiều feature supervised | ACC, lane centering, FCW, LDW và driver monitoring tùy hỗ trợ | Object, VRU, FCW, cut-in, cross-traffic, LDW, signs và TTS Việt |
| Localisation Việt Nam | Tùy OEM/model/region; thường không mở taxonomy nội bộ | Feature phụ thuộc region/hardware/software | Phụ thuộc model/car support, không chuyên Việt Nam | Vietnamese traffic sign taxonomy, hướng trái/phải và TTS tiếng Việt là trọng tâm |
| Explainability | Thường proprietary, người dùng thấy cảnh báo/HMI | Có visualization nhưng model/rule internals proprietary | Code mở hơn nhưng vehicle integration phức tạp | Evidence packet, risk, confidence, track, lifecycle/audio và suppression reason |
| Cloud dependency | Chủ yếu onboard với backend OEM/OTA riêng | Onboard neural processing và OTA ecosystem | Chủ yếu local device + vehicle APIs | Local/edge-first; GCP chỉ evaluation/control/replay plane |
| HMI | Cluster/head unit OEM | Vehicle touchscreen/cluster/audio | comma device/vehicle HMI | React HUD, Engineer Dashboard và AAOS replay HMI |
| MLOps/HITL | Quy trình nội bộ OEM | Quy trình nội bộ hãng | Community development/model updates | Có queue, ground truth, promotion gate, rollback và report trong repo |
| Mức trưởng thành | Production vehicle program | Commercial supervised ADAS | Open-source production-adjacent ecosystem | Technical PoC/Demo-ready, chưa production-certified |

### 8.3. RoadWatch nổi bật ở đâu?

#### 1. Vietnam-first, không chỉ dịch câu cảnh báo

RoadWatch không chỉ dịch TTS sang tiếng Việt. Nó đặt bài toán Việt Nam vào các
contract cụ thể:

- Xe máy xuất hiện dày đặc.
- Người đi bộ/xe máy cắt ngang tại ngã tư.
- Xe tạt đầu từ cả trái và phải.
- Occlusion sau xe tải, xe buýt hoặc xe đỗ.
- Biển báo tốc độ và biển cấm có orientation khác nhau.
- TTS phải nói rõ đối tượng, vị trí và hành động.

#### 2. Explainable alert thay cho “beep cứng”

Mỗi cảnh báo có thể truy ngược:

```text
object/track → motion/path → risk → severity → message → audio lifecycle
```

Điểm khác biệt là kỹ sư có thể giải thích tại sao event được accept, tại sao bị
suppress hoặc tại sao chỉ hiển thị HUD mà không phát audio.

#### 3. Safety boundary rõ ràng

RoadWatch cố ý không có actuator command. Đây là lựa chọn phù hợp cho prototype
khi chưa có quyền OEM, CAN, calibration và closed-course. Nó giúp nhóm chứng minh
giá trị cảnh báo mà không giả vờ đã xây hệ thống tự lái.

#### 4. Edge-first nhưng vẫn demo được bằng web

Nhiều prototype chỉ chạy tốt trên laptop hoặc chỉ có dashboard. RoadWatch duy trì
một Core contract có thể chạy:

```text
Local Windows/AMD
→ NVIDIA/CPU
→ ARM64/Jetson candidate
→ AAOS HMI
→ GCP public replay
```

Cloud không được đưa vào critical warning path, nên khi mất mạng mô hình edge vẫn
có định hướng hoạt động offline.

#### 5. Model promotion dựa trên event-level safety

RoadWatch giữ baseline dù candidate có latency tốt hơn nếu candidate làm giảm
critical event recall hoặc tăng false alert. Đây là tư duy gần với hệ thống ADAS
hơn việc chỉ tối ưu mAP.

#### 6. HMI và MLOps nằm trong cùng sản phẩm

RoadWatch không chỉ có model inference. Nó kết hợp:

- Driver HUD.
- Engineer dashboard.
- Playback/seek/ground truth.
- Evidence packets.
- TTS lifecycle.
- Model registry.
- Kaggle fine-tune pipeline.
- Cloud asset/bootstrap/deployment.
- AAOS replay.

Điểm này giúp sản phẩm có câu chuyện hoàn chỉnh từ dữ liệu → model → decision →
HMI → evidence → rollback.

### 8.4. RoadWatch chưa nổi bật hơn ở đâu?

RoadWatch chưa có cơ sở để tuyên bố vượt các sản phẩm thương mại về:

- Sensor fusion.
- Automatic braking/steering.
- Driver monitoring production.
- Vehicle integration.
- Safety validation hàng triệu km.
- Hardware optimization độc quyền.
- Regulatory certification.

Điểm nổi bật của RoadWatch là **tập trung, minh bạch và có khả năng chuyển giao**,
không phải mức tự động hóa cao hơn.

## 9. Tiêu chí đánh giá công nghệ trong các phiên bản tiếp theo

Mọi thay đổi công nghệ hoặc model mới nên được chấm theo ma trận sau:

| Nhóm tiêu chí | Câu hỏi kiểm tra | Gate định lượng/định tính |
|---|---|---|
| Safety | Có làm giảm critical event recall không? | Không thấp hơn baseline trên locked set |
| False alert | Có làm tài xế bị cảnh báo mệt mỏi không? | Critical false alert `<=0.1/phút`; all-alert budget theo release gate |
| Semantic correctness | Class/hướng/số có đúng không? | Mục tiêu semantic accuracy `>=0.95` trên labeled set |
| Temporal stability | Có cần nhiều frame xác nhận không? | Không cảnh báo từ một frame đơn nếu event không emergency |
| Runtime | Có đủ nhanh trên thiết bị đích không? | Demo `>=20 FPS`; edge release `>=30 FPS` khi benchmark đúng hardware |
| Latency tail | Có frame chậm bất thường không? | E2E P95 mục tiêu `<=150 ms` trong profile đã định danh |
| Memory | Có vượt RAM/VRAM không? | Ghi peak memory; TTS candidate không vượt service budget 2 GiB |
| Portability | Có chạy qua provider/profile khác không? | CPU fallback + provider smoke trên target |
| Offline | Mất mạng có tiếp tục cảnh báo không? | Core không phụ thuộc GCP cho critical path |
| Reproducibility | Có tái lập được model/result không? | Config, seed, hash, split, version và evidence đầy đủ |
| Rollback | Có quay lại baseline trong một bước không? | Model/profile/revision có manifest và checksum |
| Maintainability | Thay model có phải sửa toàn hệ thống không? | Adapter/orchestrator contract không đổi |
| UX/audio | Câu có rõ, ngắn, không overlap không? | Banner/TTS 100% canonical; completion và listening gate pass |

## 10. Định hướng tối ưu tiếp theo

Thứ tự ưu tiên được đề xuất:

### P0 — Khóa chất lượng cảnh báo

- Mở rộng labeled windows cho night/rain/dense traffic/day.
- Đo riêng FCW, VRU, cut-in, cross-traffic và fallen rider.
- Xác minh left/right theo ego camera bằng ground truth.
- Tách perception error khỏi rule/audio error.
- Giữ baseline nếu candidate không vượt event gate.

### P1 — Hoàn thiện lane/multi-lane

- Hoàn tất RW-10 verified polyline quota.
- Đánh giá lane count accuracy, boundary jitter và LDW precision/recall.
- Benchmark YOLOP/UFLDv2 trên cùng condition slices.
- Chỉ promote nếu vừa đạt multi-lane quality vừa đạt FPS target.

### P2 — Hoàn thiện TTS candidate

- Chạy human listening gate ba người trong môi trường yên tĩnh và có noise.
- Kiểm tra âm đầu bằng waveform/audio completion.
- Khóa corpus câu cảnh báo do owner duyệt.
- Chỉ promote VieNeu khi vượt đầy đủ static, performance và listening gate.

### P3 — Camera/calibration/hardware

- Bổ sung camera calibration và xác định FOV/lens distortion.
- Có ego speed/yaw/turn signal/brake telemetry read-only.
- Chạy closed-course với safety driver.
- Benchmark ARM64/Jetson Orin thật; không suy diễn từ EC2 g5g.xlarge.

### P4 — Production engineering

- Tách `roadwatch-core` khỏi API/HMI bằng process boundary và watchdog.
- Signed resumable upload và asynchronous replay worker trên cloud.
- Durable event/HITL store thay SQLite ephemeral.
- Model registry, canary, OTA và rollback theo digest.
- Security hardening, password hashing, secret manager và audit access.

## 11. Kết luận

RoadWatch hiện đã vượt qua phạm vi một demo nhận diện object đơn giản. Nó có:

```text
Perception adapters
→ temporal tracking
→ deterministic risk/alert decision
→ Vietnamese TTS/beep
→ Driver HUD/Engineer Dashboard
→ evidence and regression
→ local/AAOS/GCP deployment paths
```

Điểm mạnh có thể trình bày với doanh nghiệp là sự kết hợp giữa:

1. Bài toán giao thông Việt Nam cụ thể.
2. Thiết kế edge/offline có đường chuyển tiếp sang xe thật.
3. Alert logic có thể giải thích và kiểm chứng.
4. Model promotion dựa trên event-level safety.
5. HMI, MLOps và rollback được thiết kế cùng nhau.

Điểm cần trung thực khi giới thiệu là RoadWatch vẫn là Technical PoC/Demo-ready.
Các bước để trở thành sản phẩm triển khai thật còn phụ thuộc dữ liệu gán nhãn,
calibration, camera/CAN/OEM access, closed-course validation, Jetson benchmark
và quy trình chứng nhận an toàn.

## 12. Nguồn nội bộ và nguồn tham khảo

### Nguồn nội bộ

- [`configs/model_registry.json`](../configs/model_registry.json): active model,
  candidate và promotion metrics.
- [`configs/default.json`](../configs/default.json): runtime, risk, tracking,
  audio và vehicle profile.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): core pipeline và process boundary.
- [`MODEL_PROMOTION.md`](MODEL_PROMOTION.md): promotion gate.
- [`TRAFFIC_SIGN_ALERTING.md`](TRAFFIC_SIGN_ALERTING.md): sign policy và TTS.
- [`UNIFIED_DEPLOYMENT_ARCHITECTURE.md`](UNIFIED_DEPLOYMENT_ARCHITECTURE.md):
  local/AAOS/GCP/edge deployment boundary.
- [`UI_METRICS_AND_CLOUD_FLOW.md`](UI_METRICS_AND_CLOUD_FLOW.md): metrics và
  cloud user flow.
- [`TTS_PROVIDER_AB.md`](TTS_PROVIDER_AB.md): Piper/VieNeu provider strategy.
- [`VALIDATION.md`](VALIDATION.md): validation contract.

### Nguồn kỹ thuật/sản phẩm công khai

- [ONNX Runtime Execution Providers](https://onnxruntime.ai/docs/execution-providers/)
- [ONNX Runtime DirectML](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
- [ONNX Runtime TensorRT](https://onnxruntime.ai/docs/execution-providers/TensorRT-ExecutionProvider.html)
- [Android Automotive OS overview](https://developer.android.com/training/cars/platforms/automotive-os)
- [Cloud Run overview](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run)
- [Mobileye Products](https://www.mobileye.com/products/)
- [Tesla Autopilot support](https://www.tesla.com/en_GB/support/autopilot)
- [Volvo EC40 owner manual](https://www.volvocars.com/static/support/pdf/ca_en-US_ec40_2026_UM_adc6b6ff4aba27d80584a0803f109c81.pdf)
- [openpilot documentation](https://docs.comma.ai/)

