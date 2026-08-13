# RoadWatch Copilot

RoadWatch là ứng dụng cảnh báo hỗ trợ lái chạy offline trên edge: camera/video → perception → bằng chứng theo thời gian → risk engine → Alert Governor → HUD/TTS tiếng Việt. Giao diện web được phục vụ tại `localhost`; đường cảnh báo vẫn chạy khi trình duyệt đóng.

> **Safety guardrail:** RoadWatch chỉ hỗ trợ cảnh báo. Project không có API điều khiển ga, phanh hoặc đánh lái; không được dùng như một hệ thống tự lái hay thiết bị an toàn đã chứng nhận.

## Điểm khác biệt

- Cảnh báo có `evidence packet`: track ID, số frame xác nhận, lane/drivable context, risk và confidence.
- “Biết im lặng”: temporal confirmation, lane-quality gate, cooldown, hysteresis và audio budget giảm alert fatigue.
- Giao thông hỗn hợp Việt Nam: ưu tiên xe máy, xe đạp và người đi bộ trong drivable/ego path.
- Edge-first: model, rule engine, SQLite, Piper Vietnamese TTS và UI đều local.
- Multi-runtime: AMD dùng YOLOP DirectML + YOLO CPU; NVIDIA/Jetson dùng CUDA/TensorRT theo profile triển khai.

## Tài sản model local

Đặt các file sau trong `models/` (đã bị `.gitignore` loại khỏi Git):

```text
models/
├── yolo11n.pt
├── yolo11s_vietnam_traffic.pt
├── yolop_lane_detection_640.onnx
└── yolop_lane_detection.pth
```

Video demo đặt trong `media/`. Voice Piper đặt trong `voices/`. Không commit các thư mục nặng này.

## Chạy nhanh trên Windows

Yêu cầu Python 3.10–3.12, Node.js 20+, npm và PowerShell:

```powershell
cd roadwatch
.\scripts\setup.ps1 -PythonExe "C:\path\to\python.exe"
.\scripts\start.ps1
```

Mở [http://localhost:8000](http://localhost:8000).

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
```

Nghiệm thu gồm:

- test backend/rule engine/role đạt;
- React production build đạt;
- `/api/health` báo đủ model/provider;
- benchmark JSON có FPS, frame-drop, P50/P95 từng model và end-to-end;
- event SQLite lưu evidence và audio action;
- mất Internet không ảnh hưởng replay, inference, login hoặc UI local.

Chi tiết xem [INSTALL.md](docs/INSTALL.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [SAFETY.md](docs/SAFETY.md), [VALIDATION.md](docs/VALIDATION.md) và [VINFAST_PROFILES.md](docs/VINFAST_PROFILES.md).

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
