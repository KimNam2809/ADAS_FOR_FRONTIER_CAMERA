Chào triển chiêu,

## Kết luận từ góc nhìn giám khảo

RoadWatch hiện đã có phần “AI pipeline” khá đầy đủ, nhưng chưa có một câu chuyện triển khai thống nhất. Nếu trình bày chỉ là “website phân tích video”, giám khảo có thể hỏi đúng rằng:

- Tài xế dùng ứng dụng ở đâu?
- Camera thật kết nối như thế nào?
- Kỹ sư vận hành hệ thống ra sao?
- Nếu mất Internet thì hệ thống còn hoạt động không?
- Làm sao chứng minh có thể đưa lên xe thật?

Hướng hợp lý nhất là định vị RoadWatch như sau:

> RoadWatch là một trợ lý cảnh báo ADAS chạy ưu tiên trên edge. Video hiện tại chỉ là camera surrogate để mô phỏng camera trước xe. Web dashboard phục vụ kỹ sư và đánh giá mô hình; không nằm trong critical path của cảnh báo an toàn.

## 1. Kiến trúc nên chốt

```text
                         ┌─────────────────────┐
                         │ Engineer Dashboard  │
                         │ Web React + FastAPI │
                         │ HITL / Metrics / OTA │
                         └──────────┬──────────┘
                                    │ Metadata, evidence
                                    │ không điều khiển xe
                         ┌──────────▼──────────┐
                         │ GCP Control Plane   │
                         │ GCS / Cloud Run     │
                         │ Model registry     │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────▼─────────────────────┐
              │          Edge Vehicle Runtime             │
              │                                            │
              │ Camera Adapter → Perception Orchestrator   │
              │                → Tracking + Rule Engine    │
              │                → HUD + Beep + Vietnamese TTS│
              └─────────────────────┬─────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │ Driver Display      │
                         │ AAOS / Jetson HUD   │
                         └─────────────────────┘
```

### Phân chia vai trò

| Thành phần | Người sử dụng | Vai trò |
|---|---|---|
| AAOS/Edge app | Tài xế | Hiển thị HUD, phát beep/TTS, chạy offline |
| Web Engineer Dashboard | Kỹ sư ADAS | Theo dõi model, metric, HITL, điều chỉnh ngưỡng |
| GCP | Kỹ sư/vận hành | Lưu model, video, evidence, telemetry, OTA simulation |
| Rule Engine | Hệ thống | FCW, VRU, cut-in, cross-traffic, LDW |
| Camera Adapter | Hệ thống xe | Nhận frame từ video demo hoặc camera thật |

Điểm cốt lõi là: khi triển khai xe thật, chỉ cần thay `VideoFileSource` bằng `VehicleCameraSource`. Perception, tracking, rule engine và TTS không cần thay đổi về mặt nghiệp vụ.

## 2. Tài xế sử dụng RoadWatch như thế nào?

### Trong bản demo hiện tại

1. Tài xế mở ứng dụng AAOS hoặc Driver HUD.
2. Chọn video có sẵn hoặc import video.
3. Bấm bắt đầu mô phỏng.
4. Hệ thống xử lý video như một luồng camera trước.
5. HUD hiển thị:
   - phương tiện;
   - người đi bộ;
   - xe máy;
   - làn đường;
   - biển báo;
   - mức độ nguy hiểm.
6. Loa phát beep hoặc TTS tiếng Việt.
7. Tài xế có thể pause, tua và chuyển video để kiểm tra tình huống.

### Khi triển khai lên xe thật

Luồng sẽ là:

```text
Camera trước xe
→ Camera Adapter
→ Perception
→ Rule Engine
→ HUD + Speaker
```

Tài xế không cần upload video và không cần thao tác với dashboard kỹ sư. Camera sẽ tự động được đọc khi xe khởi động.

Cách trả lời giám khảo:

> Video được dùng ở demo để mô phỏng camera trước do nhóm chưa có xe thật. Trong sản phẩm thực tế, lớp input sẽ được thay bằng camera stream của xe; phần nhận thức và cảnh báo được thiết kế độc lập với nguồn dữ liệu.

## 3. Kỹ sư sử dụng RoadWatch như thế nào?

Kỹ sư đăng nhập tài khoản `engineer` trên Web Dashboard để:

- kiểm tra model đang active;
- xem provider và input size;
- theo dõi Process FPS, E2E P50/P95, Sampling skip;
- xem các event FCW, VRU, LDW, cut-in;
- review frame khó;
- điều chỉnh confidence/threshold;
- xác nhận false positive;
- so sánh model baseline và candidate;
- kiểm tra TTS/banner có cùng nội dung;
- theo dõi model version và hash;
- chuẩn bị model mới cho OTA.

Kỹ sư không được phép:

- phanh xe;
- đánh lái;
- gửi actuator command;
- thay đổi an toàn trực tiếp không qua audit;
- dùng SLM để tự quyết định hành động điều khiển xe.

Điều này phù hợp với guardrail hiện tại: RoadWatch chỉ cảnh báo và hỗ trợ tài xế.

## 4. RoadWatch hiện đã có cơ sở nào để nói là triển khai được?

### Đã có

| Năng lực | Bằng chứng hiện tại |
|---|---|
| Perception nhiều nhiệm vụ | Object, traffic sign, speed classifier, YOLOP lane |
| Runtime edge | ONNX, DirectML local, cấu trúc có thể chuyển sang CUDA/TensorRT |
| Rule-based safety | FCW, VRU, cut-in, cross-traffic, LDW |
| Offline replay | Local Web/AAOS không phụ thuộc cloud |
| Vietnamese TTS | Piper tiếng Việt |
| Driver UI | React HUD, video playback, seek/pause |
| Engineer UI | Metrics, model health, event evidence, HITL |
| Cloud deployment | GCP Cloud Run, GCS, TTS service |
| Containerization | Docker và cloud build |
| Fallback | Baseline model, Piper, YOLOP và cloud/local fallback |
| Safety boundary | Không có actuator command |
| Multi-platform direction | Windows AMD, Linux CUDA, ARM64 target |

Các tài liệu kiến trúc hiện có:

- [UNIFIED_DEPLOYMENT_ARCHITECTURE.md](D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md)
- [CLOUD_FULL_PERCEPTION_DEPLOYMENT.md](D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/docs/CLOUD_FULL_PERCEPTION_DEPLOYMENT.md)
- [MASTER_ACTION_PLAN.md](D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/docs/MASTER_ACTION_PLAN.md)

## 5. Những gì chưa thể tuyên bố là đã hoàn thành?

| Hạng mục | Trạng thái thực tế |
|---|---|
| Camera trước VinFast thật | Chưa có |
| OEM camera API | Chưa có quyền truy cập |
| CAN/OBD/ego speed | Chưa tích hợp |
| Calibration camera thật | Chưa thực hiện |
| Jetson Orin thật | Chưa benchmark trực tiếp |
| TensorRT trên Jetson | Chưa có bằng chứng phần cứng thật |
| Closed-course test | Chưa hoàn thành |
| Chứng nhận ISO 26262/SOTIF | Chưa thực hiện |
| OTA trên fleet thật | Mới ở mức mô phỏng |
| Tự động phanh/đánh lái | Cố ý không triển khai |

Đây không phải điểm yếu nếu trình bày đúng. Câu trả lời nên là:

> RoadWatch hiện là một technology demonstrator có kiến trúc edge-ready, chưa phải hệ thống ADAS đã được chứng nhận hoặc tích hợp OEM. Những phần còn thiếu phụ thuộc vào quyền truy cập camera, CAN, calibration và xe thử nghiệm của nhà sản xuất.

## 6. GCP nên đóng vai trò gì?

Không nên nói GCP là nơi hệ thống ADAS chính chạy để cảnh báo tài xế.

Nên trình bày:

- Edge/AAOS xử lý critical warning.
- GCP lưu model, video, telemetry và evidence.
- GCP cung cấp Engineer Dashboard.
- GCP hỗ trợ HITL, model evaluation và OTA.
- Khi mất Internet, cảnh báo trên xe vẫn hoạt động.
- GCP không nằm trên đường truyền FCW/LDW.

Đối với bản GCP hiện tại, cần nói rõ đây là:

> Cloud replay and engineering evaluation plane.

Nếu giám khảo hỏi tại sao Web chậm hơn edge:

> Web phải truyền video và kết quả qua mạng nên có network latency. Bản edge xử lý trực tiếp trên thiết bị, không phải upload từng frame lên cloud.

## 7. Kịch bản demo nên thực hiện

### Phần A — Driver Demo

1. Mở AAOS hoặc Local Edge Demo.
2. Tắt Internet để chứng minh offline.
3. Chọn video ban ngày có xe máy cắt ngang.
4. Hiển thị cảnh báo object, hazard và TTS.
5. Chọn video ban đêm/mưa.
6. Trình diễn pause, tua và chuyển video.
7. Chứng minh trạng thái video không bị giữ nhầm giữa các phiên.

### Phần B — Engineer Demo

1. Đăng nhập bằng tài khoản `engineer`.
2. Hiển thị model health.
3. Chạy video replay.
4. Chỉ ra:
   - Process FPS;
   - E2E P50/P95;
   - lane quality;
   - event lifecycle;
   - audio status.
5. Mở event evidence.
6. Thay đổi một threshold.
7. Cho thấy thay đổi được audit.
8. Giải thích baseline/candidate và cơ chế rollback.

### Phần C — Deployment Feasibility

Trình bày sơ đồ:

```text
Demo video
    ↓ thay thế camera thật
Camera Adapter
    ↓
Edge Perception
    ↓
Rule Engine
    ↓
AAOS HUD + Piper TTS
```

Sau đó nói:

> Nhóm chưa tuyên bố tích hợp VinFast vì chưa có OEM API. Nhưng ranh giới tích hợp đã được tách riêng ở Camera Adapter, Display Adapter và Vehicle Telemetry Adapter.

## 8. Cách trả lời các câu hỏi khó của giám khảo

| Câu hỏi | Câu trả lời nên dùng |
|---|---|
| Tài xế dùng app thế nào? | App chạy nền trên màn hình xe, tự nhận camera và chỉ phát cảnh báo khi cần |
| Tại sao demo bằng video? | Video là camera surrogate vì nhóm chưa có xe thử nghiệm |
| Có cần Internet không? | Critical perception và cảnh báo chạy offline; cloud chỉ phục vụ dashboard/evidence |
| Có tự lái không? | Không. Không có actuator interface; chỉ cảnh báo bằng HUD, beep và TTS |
| Làm sao đưa lên xe thật? | Thay Video Adapter bằng camera API của xe, giữ nguyên perception/risk/alert pipeline |
| Có tích hợp VinFast chưa? | Chưa có OEM API; hiện mới chuẩn bị profile màn hình, AAOS và adapter boundary |
| Model có đảm bảo mọi video không? | Không tuyên bố tuyệt đối; quality gate được đánh giá trên bộ test có ground truth và các điều kiện day/night/rain |
| Web có phải sản phẩm chính không? | Không. Web là engineer/evaluation plane; sản phẩm chính là edge runtime |
| Vì sao cloud và local khác nhau? | Cloud dùng profile tối ưu CPU và sampling thấp; edge dùng profile chất lượng/thời gian thực |
| Nếu model lỗi thì sao? | Có baseline fallback, health check, model hash, release gate và rollback |

## 9. Hướng triển khai hợp lý nhất

### Bước 1 — Chốt bản demo theo mô hình “Edge-ready”

Không nên tiếp tục mở rộng quá nhiều model trước khi hoàn thiện câu chuyện triển khai. Cần đóng gói rõ ba profile:

```text
DEMO_REPLAY
EDGE_LOCAL
AAOS_SIMULATION
```

Mỗi profile phải hiển thị rõ:

- model;
- runtime;
- input source;
- FPS;
- cảnh báo đang được xử lý offline hay cloud.

### Bước 2 — Chuẩn hóa Camera Adapter

Tạo giao diện thống nhất:

```text
VideoFileSource       → dùng cho demo
Camera2Source         → dùng cho Android/AAOS
JetsonCameraSource    → dùng cho CSI/USB camera
```

Đây là bằng chứng kỹ thuật quan trọng nhất để chứng minh video demo không làm kiến trúc phụ thuộc vào video file.

### Bước 3 — Đóng gói edge runtime

Mục tiêu:

```text
Docker ARM64
ONNX Runtime CUDA hoặc TensorRT
YOLO object
Traffic sign
YOLOP lane
Piper TTS
FastAPI local service
AAOS display client
```

AWS `g5g.xlarge` có thể dùng để kiểm thử Linux ARM64 + NVIDIA CUDA, nhưng không được gọi là benchmark Jetson Orin.

### Bước 4 — Giữ GCP làm control plane

GCP tiếp tục dùng cho:

- Web Engineer Dashboard;
- GCS model/video;
- model registry;
- event evidence;
- OTA simulation;
- fleet telemetry simulation.

Không nên dùng GCP CPU hiện tại làm bằng chứng cho critical realtime ADAS.

### Bước 5 — Tạo một bộ “Deployment Evidence”

Bộ bằng chứng cần có:

- sơ đồ kiến trúc;
- video demo driver;
- ảnh AAOS;
- ảnh engineer dashboard;
- log offline;
- model health;
- benchmark FPS/latency;
- model manifest và SHA-256;
- rollback demo;
- bảng giới hạn thực tế;
- kế hoạch tích hợp camera OEM;
- closed-course test plan.

## Định vị cuối cùng nên dùng

RoadWatch không nên được giới thiệu là:

> Một hệ thống tự lái hoàn chỉnh đã sẵn sàng đưa vào xe.

Nên giới thiệu là:

> RoadWatch Copilot là một nền tảng trợ lý cảnh báo ADAS edge-first dành cho giao thông hỗn hợp Việt Nam. Sản phẩm phân tích camera trước, xác định nguy cơ theo thời gian, ưu tiên cảnh báo bằng hazard/beep/TTS tiếng Việt và hoạt động không phụ thuộc cloud. Bản demo dùng video làm camera surrogate; kiến trúc đã tách riêng lớp camera adapter để có thể thay thế bằng camera OEM khi có quyền truy cập phần cứng và API xe.

Đây là cách trả lời vừa thực tế, vừa thuyết phục, không phóng đại những phần hiện chưa có bằng chứng.