# RoadWatch Copilot

RoadWatch là ứng dụng cảnh báo hỗ trợ lái chạy offline trên edge: camera/video → perception → bằng chứng theo thời gian → risk engine → Alert Governor → HUD/TTS tiếng Việt. Giao diện web được phục vụ tại `localhost`; đường cảnh báo vẫn chạy khi trình duyệt đóng.

> **Safety guardrail:** RoadWatch chỉ hỗ trợ cảnh báo. Project không có API điều khiển ga, phanh hoặc đánh lái; không được dùng như một hệ thống tự lái hay thiết bị an toàn đã chứng nhận.

## Điểm khác biệt

- Cảnh báo có `evidence packet`: track ID, số frame xác nhận, lane/drivable context, risk và confidence.
- “Biết im lặng”: temporal confirmation, lane-quality gate, cooldown, hysteresis và audio budget giảm alert fatigue.
- Giao thông hỗn hợp Việt Nam: ưu tiên xe máy, xe đạp và người đi bộ trong drivable/ego path.
- Edge-first: model, rule engine, SQLite, Piper Vietnamese TTS và UI đều local.
- Multi-runtime: AMD ưu tiên YOLO/YOLOP ONNX DirectML (fallback `.pt` CPU); NVIDIA/Jetson có profile CUDA/TensorRT.
- Event lifecycle v0.2: HUD/TTS dùng cùng event UUID, có TTL, stale-event dropping và suppression reason.
- Traffic Sign Phase 2 mặc định: generic sign detector + speed-value classifier,
  confidence gate 0.95 và lớp `unknown` để chặn tuyên bố tốc độ không chắc chắn.

## Tài sản model local

Đặt các file sau trong `models/` (đã bị `.gitignore` loại khỏi Git):

```text
models/
├── yolo11n.pt
├── roadwatch_objects_v1.pt          # candidate 7 lớp, chưa phải mặc định
├── roadwatch_objects_v1.onnx        # candidate cho DirectML/CUDA
├── roadwatch_objects_v1_1.pt        # Phase 2.1 cân bằng VRU
├── roadwatch_objects_v1_1.onnx      # Phase 2.1 cho DirectML/CUDA
├── yolo11s_vietnam_traffic.pt
├── roadwatch_detector_v2.pt          # Sign Phase 2 candidate
├── roadwatch_detector_v2.onnx        # Sign Phase 2 cho DirectML/CUDA
├── yolo11n.onnx                     # tạo bằng scripts/export_models.py
├── yolo11s_vietnam_traffic.onnx     # tạo bằng scripts/export_models.py
├── yolop_lane_detection_640.onnx
├── yolop_lane_detection.pth
├── ufldv2_culane_res18_320x1600.onnx # lane candidate; optional
├── roadwatch_speed_digits_v2.pt      # sinh bởi Sign Phase 2; optional
└── roadwatch_speed_digits_v2.onnx    # classifier export; optional
```

Video demo đặt trong `media/`. Voice Piper đặt trong `voices/`. Không commit các thư mục nặng này.

## Chạy nhanh trên Windows

Yêu cầu Python 3.10–3.12, Node.js 20+, npm và PowerShell:

```powershell
cd roadwatch
.venv\Scripts\activate
.\scripts\setup.ps1 -PythonExe "C:\path\to\python.exe"
.\scripts\start.ps1
```

Mở [http://localhost:8000](http://localhost:8000).

Khi phân tích video local, thanh replay hiển thị thời gian hiện tại/tổng thời
lượng và hỗ trợ pause/resume, tua ±10 giây, kéo timeline, phát lại từ đầu và
tiếp tục từ vị trí đã dừng. Các API này nằm ở backend dùng chung nên Web,
Docker/Jetson và AAOS WebView có cùng hành vi; camera live không cho phép seek.

Tài khoản demo:

| Vai trò | Username | Password | Quyền |
|---|---|---|---|
| Tài xế | `driver` | `driver123` | HUD, khởi động/dừng replay |
| Kỹ sư ADAS | `engineer` | `engineer123` | Dashboard, metrics, config có audit |

Đây là thông tin demo. Trước mọi triển khai ngoài phòng lab phải đổi `ROADWATCH_SECRET` và tài khoản mặc định.

## Kiểm thử và bằng chứng

```powershell
.\scripts\test.ps1
.\.venv\Scripts\python.exe .\scripts\benchmark.py --source test_video1.mp4 --seconds 30
.\.venv\Scripts\python.exe .\scripts\evaluate.py --scenario test-video10-speed-lane
.\.venv\Scripts\python.exe .\scripts\compare_object_models.py
.\.venv\Scripts\python.exe .\scripts\edge_preflight.py
```

Object detector mặc định là profile `baseline_coco`. Candidate fine-tune được bật
có chủ đích bằng biến `ROADWATCH_OBJECT_PROFILE=roadwatch_objects_v1` hoặc qua
cấu hình kỹ sư. Không đổi mặc định trước khi promotion gate và kiểm tra false
alert thủ công đạt. Xem [MODEL_PROMOTION.md](docs/MODEL_PROMOTION.md) và
[PHASE2_1_RESULTS.md](docs/PHASE2_1_RESULTS.md).

Luồng hazard/TTS cho biển báo, chính sách chống alert fatigue và video trace tái
lập được mô tả tại [TRAFFIC_SIGN_ALERTING.md](docs/TRAFFIC_SIGN_ALERTING.md).

Nghiệm thu gồm:

- test backend/rule engine/role đạt;
- React production build đạt;
- `/api/health` báo đủ model/provider;
- benchmark JSON có FPS, frame-drop, P50/P95 từng model và end-to-end;
- event SQLite lưu evidence và audio action;
- mất Internet không ảnh hưởng replay, inference, login hoặc UI local.

Chi tiết xem [INSTALL.md](docs/INSTALL.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [SAFETY.md](docs/SAFETY.md), [VALIDATION.md](docs/VALIDATION.md) và [VINFAST_PROFILES.md](docs/VINFAST_PROFILES.md).

## Pipeline nâng cấp và safety gates

```powershell
# Xác minh timestamp Ground Truth
.\.venv\Scripts\python.exe .\scripts\validate_ground_truth.py

# So sánh lane model và sinh ảnh review
.\.venv\Scripts\python.exe .\scripts\benchmark_lane_models.py

# Xuất checkpoint UFLDv2 chính chủ sang ONNX (không huấn luyện local)
.\.venv\Scripts\python.exe .\scripts\export_ufldv2_onnx.py

# Camera calibration; cần tối thiểu 12 ảnh chessboard thật
.\.venv\Scripts\python.exe .\scripts\calibrate_camera.py --images "calibration/*.jpg"
```

Profile lane mặc định vẫn là `yolop`. Profile thử nghiệm
`ufldv2_fusion` dùng UFLDv2 cho hai biên ego-lane và YOLOP cho drivable-area.
Có thể bật có chủ đích bằng `ROADWATCH_LANE_PROFILE=ufldv2_fusion`.
Khi UFLDv2 không đủ tin cậy (đặc biệt video đêm), hệ thống bỏ lane geometry để
không phát LDW sai nhưng vẫn giữ drivable-area cho hazard context.

Traffic Sign Phase 2 nằm trong `kaggle/train_sign_phase2`; fallen-rider Quality
Gate nằm trong `kaggle/train_fallen_rider`. Hai pipeline đều dừng trước training
cho tới khi Human Quality Gate được chấp thuận. Quy trình thử xe kín được khóa tại
[CLOSED_COURSE_VALIDATION.md](docs/CLOSED_COURSE_VALIDATION.md). Báo cáo thực thi,
metrics và các blocker hiện tại nằm tại
[IMPROVEMENT_EXECUTION_2026-08-19.md](docs/IMPROVEMENT_EXECUTION_2026-08-19.md).

## Docker CPU baseline

```powershell
docker compose build
docker compose up -d
```

Container mount `models/`, `media/`, `data/` từ máy host. Audio được tắt trong Docker baseline do chuyển tiếp thiết bị âm thanh khác nhau giữa Windows/Linux; demo TTS nên chạy native bằng `scripts/start.ps1`.

## API chính

- `GET /api/health` — health không cần đăng nhập.
- `POST /api/auth/login` — đăng nhập local.
- `POST /api/session/start|stop` — điều khiển phiên video/camera.
- `GET /api/status`, `WS /ws` — trạng thái realtime.
- `GET /api/events` — timeline/evidence.
- `GET|PATCH /api/config` — engineer only; patch tạo audit log.
- `GET /api/stream.mjpg` — video overlay local.
