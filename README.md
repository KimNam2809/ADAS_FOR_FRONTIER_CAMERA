# RoadWatch Copilot

RoadWatch là ứng dụng cảnh báo hỗ trợ lái chạy offline trên edge: camera/video → perception → bằng chứng theo thời gian → risk engine → Alert Governor → HUD/TTS tiếng Việt. Giao diện web được phục vụ tại `localhost`; đường cảnh báo vẫn chạy khi trình duyệt đóng.

> **Safety guardrail:** RoadWatch chỉ hỗ trợ cảnh báo. Project không có API điều khiển ga, phanh hoặc đánh lái; không được dùng như một hệ thống tự lái hay thiết bị an toàn đã chứng nhận.

## Gói bàn giao `roadwatch_copilot`

Đây là bản hợp nhất giữa RoadWatch end-to-end hiện tại và landing page mới nhất
từ `P-162/main` (commit `83c5654`). Một entrypoint frontend duy nhất phục vụ:

- `/` — landing page giới thiệu sản phẩm, kiến trúc, bằng chứng và lối vào demo.
- `/app/` — Web Driver HUD hoặc Engineer Dashboard; sau đăng nhập, pipeline vẫn
  chạy đầy đủ `perception → tracking → risk → Alert Governor → TTS/beep → UI`.

Landing page chỉ là lớp giới thiệu tĩnh; nó không tự chạy inference. Dashboard
mới là nơi phân tích video thật bằng FastAPI. Video giữ đúng tỷ lệ 16:9, còn
RoadWatch vẫn là hệ thống warning-only và không điều khiển xe.

### Cài đặt nhanh trên Windows

Yêu cầu: Python 3.10–3.12, Node.js 20+, npm và PowerShell.

```powershell
cd roadwatch_copilot
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\scripts\start.ps1 -Port 8013
```

Mở `http://127.0.0.1:8013/`. Chọn `MỞ DASHBOARD` hoặc truy cập trực tiếp
`http://127.0.0.1:8013/app/`, rồi đăng nhập bằng tài khoản bên dưới.

`setup.ps1` có tính lặp lại: nó tạo `.venv`, cài dependency, tự tìm/tải
model runtime và video từ hai thư mục Drive công khai, tải Piper tiếng Việt,
và build frontend release. Nếu assets đã có sẵn thì không tải lại.

Để chỉ build code khi chưa muốn tải asset lớn:

```powershell
.\scripts\setup.ps1 -SkipDriveAssets -SkipVoice
```

## Tải model và media từ Google Drive

Các link phân phối chính thức của bản demo:

- [Thư mục model trên Google Drive](https://drive.google.com/drive/folders/1m_u6KELkCru8DLh46iuTFmXKioMfS_KT?usp=sharing)
- [Thư mục media trên Google Drive](https://drive.google.com/drive/folders/1dFb_SLqwN98hXSTLxEqPu_RgZ1PyjVPM?usp=sharing)

Khi clone sạch, lệnh `setup.ps1` tự cài `gdown` từ
`requirements-assets.txt`, đọc `configs/external_assets.json`, rồi tải:

```text
models/    ← model từ Drive
media/     ← video replay từ Drive
voices/    ← Piper voice (tải bởi piper.download_voices)
```

Có thể xem trước kế hoạch mà không tải:

```powershell
.\.venv\Scripts\python.exe .\scripts\download_drive_assets.py --dry-run
```

Nếu folder Drive đổi nội dung, dùng `-ForceDriveAssets` để yêu cầu tải lại:

```powershell
.\scripts\setup.ps1 -ForceDriveAssets
```

Script không xóa file local. Khi local đã có model bắt buộc hoặc có video,
script sẽ giữ lại và báo rõ trong log. Nếu Drive tạm thời không truy cập được,
có thể dùng cách thủ công sau.

### Cách 2 — dùng assets của người dùng

Không cần chỉnh code. Chạy setup bỏ qua Drive:

```powershell
.\scripts\setup.ps1 -SkipDriveAssets
```

Sau đó đặt file vào đúng vị trí:

```text
roadwatch_copilot/
├── models/
│   ├── yolo11n.onnx
│   ├── roadwatch_detector_v2.onnx
│   ├── roadwatch_speed_digits_v2.onnx
│   └── yolop_lane_detection_640.onnx
├── media/
│   └── *.mp4, *.mov, *.mkv
└── voices/
    ├── vi_VN-vais1000-medium.onnx
    └── vi_VN-vais1000-medium.onnx.json
```

Các file `.pt` tương ứng có thể giữ trong `models/` để fallback CPU hoặc
benchmark, nhưng release demo ưu tiên ONNX. SLM Qwen là tùy chọn Engineer
Console; nếu muốn bật, đặt artifact Qwen theo `docs/SLM_INTEGRATION.md` và
bật rõ `ROADWATCH_SLM_ENABLED=1`. Thiếu SLM không làm mất cảnh báo chính.

Sau khi đặt assets, chạy kiểm tra:

```powershell
.\.venv\Scripts\python.exe .\scripts\download_drive_assets.py --skip-models --skip-media --dry-run
.\scripts\start.ps1 -Port 8013
```

Không commit các file model, video, voice, dataset, `.env`, database, cache
hoặc build output vào Git. `.gitignore` chỉ ngăn commit; runtime local/cloud
vẫn phải được bootstrap đúng artifact theo allowlist/checksum riêng.

## Model và runtime đang sử dụng

| Thành phần | Artifact release | Vai trò | Fallback/candidate |
|---|---|---|---|
| Object detection | `yolo11n.onnx` / `yolo11n.pt` | person, bicycle, motorcycle, car, bus, truck | Object fine-tune và YOLO26 chỉ benchmark/candidate |
| Traffic sign | `roadwatch_detector_v2.onnx` | detector 82 lớp biển Việt Nam | giữ profile `roadwatch_sign_phase2` |
| Speed value | `roadwatch_speed_digits_v2.onnx` | đọc giá trị tốc độ sau sign arbitration | chỉ phát khi temporal/lane gate đạt |
| Lane + drivable area | `yolop_lane_detection_640.onnx` | lane mask, drivable-area mask, LDW | TwinLiteNet+ là candidate, YOLOP fallback |
| TTS | `vi_VN-vais1000-medium` | Piper tiếng Việt offline, display name `Trúc Ly` | không dùng browser voice tiếng Anh |
| Context | `Traffic Context v1` | dense-traffic selective audio | `off`/`shadow` là rollback |
| Explanation | Qwen2.5-0.5B ONNX, optional | giải thích event cho Engineer, không quyết định alert | deterministic fallback |

Các model candidate chưa được tự động promote chỉ vì FPS/mAP. Quyết định release
phải dựa trên event recall, false-alert rate, semantic/direction accuracy,
latency và test trên cùng data split; xem `configs/model_registry.json` và
`docs/MODEL_PROMOTION.md`.

## Sử dụng và kiểm tra

1. Chạy setup và start như ở trên.
2. Đăng nhập `driver` để xem HUD tối giản, video replay, hazard và TTS.
3. Đăng nhập `engineer` để xem metrics, Event History, Model Health, Traffic
   Context v1, SLM status và HITL threshold.
4. Chọn video mẫu trong Video Library hoặc upload video riêng; phiên mới có
   `session_id` riêng, hỗ trợ pause/resume, tua và đổi video không giữ frame cũ.
5. Kiểm tra `/api/health` và `/api/status` khi cần xác minh model, provider,
   audio owner, context mode và lỗi pipeline.

Rollback nhanh:

```powershell
# UI fallback
.\scripts\start.ps1 -FrontendDist .\frontend\dist-ui-v3

# Tắt selective audio, giữ lại engine để benchmark
.\scripts\start.ps1 -TrafficContextMode off

# Native/AAOS speaker owner (chỉ dùng khi môi trường có loa server)
.\scripts\start.ps1 -AudioOwner server
```

Các lệnh trên không thay model và không xóa assets. `Piper` là provider mặc
định; `VieNeu` chỉ bật có chủ đích bằng `-TtsProvider vieneu` để benchmark.

## Phạm vi triển khai thực tế

- Local Windows/AMD: development và demo replay; DirectML/ONNX được ưu tiên.
- NVIDIA/Jetson Orin: dùng Docker/NVIDIA/TensorRT profile sau khi benchmark
  trên thiết bị thật; EC2 ARM64 chỉ là môi trường giả lập.
- AAOS: app HMI/WebView và video local mô phỏng camera; Camera HAL/EVS, CAN,
  calibration và VinFast vehicle API vẫn là integration gate cần OEM/hardware.
- GCP: public replay/evaluation plane và landing; không đặt FCW critical path
  lên cloud và không dùng cloud latency để tuyên bố xe thật realtime.

### Tài khoản demo

| Vai trò | Username | Password |
|---|---|---|
| Tài xế | `driver` | `driver123` |
| Kỹ sư ADAS | `engineer` | `engineer123` |

Đây là credentials cho demo; khi triển khai ngoài phòng lab phải thay secret,
password hashing và cơ chế quản lý danh tính.

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
├── yolo26n.pt / yolo26n.onnx         # pretrained public candidate, benchmark-only
├── yolo26s.pt / yolo26s.onnx         # pretrained public candidate, benchmark-only
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

## Catalog cảnh báo vNext và fallback

Runtime hiện khởi động với catalog `vnext` theo tài liệu
[`ALERT_COPY_EVIDENCE_BASED_RECOMMENDATIONS.md`](docs/ALERT_COPY_EVIDENCE_BASED_RECOMMENDATIONS.md).
Catalog này ưu tiên câu theo mức nguy hiểm và vùng xung đột; không dùng lại câu
TTS/ banner khác nhau. Profile `legacy` vẫn giữ catalog 7 từ trước đó để
rollback nhanh khi chạy thử không phù hợp.

```powershell
# Chạy thử catalog mới
.\scripts\start.ps1 -AlertCopyProfile vnext

# Fallback về catalog trước đó; cần restart backend
.\scripts\start.ps1 -AlertCopyProfile legacy
```

Profile đang chạy được trả về trong `GET /api/health` và `GET /api/status` ở
trường `alert_copy_profile`. Việc đổi profile chỉ thay nội dung cảnh báo; không
thay model, ngưỡng risk, tracking hoặc đường chạy inference.

Piper `vi_VN-vais1000-medium` là TTS release chính thức của bản demo. Trong
RoadWatch, voice này được định danh là **Trúc Ly** để hiển thị nhất quán trên
HUD/status. Model Piper hiện có một speaker và metadata không chứa `speaker_id_map`,
vì vậy tên “Trúc Ly” là tên release của sản phẩm, không phải một speaker ID do
model tự khai báo. VieNeu-TTS v3 Turbo chỉ là candidate A/B và mặc định không
được bật:

```powershell
# Cấu hình an toàn mặc định
$env:ROADWATCH_TTS_PROVIDER = "piper"
$env:ROADWATCH_TTS_VOICE = "voices/vi_VN-vais1000-medium.onnx"
$env:ROADWATCH_TTS_VOICE_NAME = "Trúc Ly"

# Candidate local (chỉ bật rõ ràng để benchmark, không phải release)
pip install -r requirements-tts-vieneu.txt
$env:ROADWATCH_TTS_PROVIDER = "vieneu"
$env:ROADWATCH_TTS_BACKEND = "onnx"
$env:ROADWATCH_TTS_PRECISION = "int8"
$env:ROADWATCH_TTS_VOICE_NAME = "Minh Triết"
```

`.\scripts\setup.ps1` tự tải hai file Piper vào `voices/` bằng lệnh:

```powershell
& ".\.venv\Scripts\python.exe" -m piper.download_voices vi_VN-vais1000-medium --data-dir voices
```

Sau đó setup build bundle `frontend/dist-ui-v4`. Lệnh chạy demo bình thường sẽ
tự chọn bundle này, khóa Piper/Trúc Ly, bật `Traffic Context v1` ở chế độ
`enforce` và dùng Browser Web Audio làm audio owner:

```powershell
.\scripts\start.ps1 -Port 8013
```

Không cần đặt biến môi trường cho bản demo. Để kiểm tra fallback của chính sách
traffic context, dùng `scripts/start.ps1 -TrafficContextMode off`; để chỉ
ghi telemetry mà chưa đổi audio, dùng `-TrafficContextMode shadow`.

Nếu cần kiểm tra provider candidate một cách có chủ đích, dùng
`.\scripts\start.ps1 -TtsProvider vieneu`; quay lại bản release bằng
`.\scripts\start.ps1 -TtsProvider piper`. Nếu thiếu voice, entrypoint dừng
với lỗi rõ ràng thay vì âm thầm rơi xuống giọng hệ thống có thể đọc tiếng Việt
như tiếng Anh.

Chạy A/B trên toàn bộ corpus canonical của profile đang bật và lưu report local:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_tts_ab.py --provider all
```

Candidate chưa được promote nếu chưa đạt static/performance gate và human listening
gate. Nếu VieNeu lỗi, gateway fallback về Piper và ghi nguyên nhân trong health/status.
Chi tiết xem [TTS_PROVIDER_AB.md](docs/TTS_PROVIDER_AB.md).

## SLM giải thích kỹ thuật (tùy chọn)

RoadWatch có thêm worker ONNX Qwen2.5-0.5B-Instruct để giải thích các event đã
được `AlertGovernor` chấp nhận cho Engineer Console. Worker chạy bất đồng bộ,
không quyết định cảnh báo, không thay đổi `RoadWatch Alert Context v1`, không
điều khiển audio/TTS và tự fallback khi thiếu model hoặc xảy ra lỗi.

Mặc định SLM đang **tắt** để giữ nguyên latency của bản demo. Tài liệu tích hợp
và cấu hình xem tại [`docs/SLM_INTEGRATION.md`](docs/SLM_INTEGRATION.md). Nếu đã
chuẩn bị đủ asset trong `models/qwen2.5-0.5b/`, có thể bật cho local test:

```powershell
$env:ROADWATCH_SLM_ENABLED = "1"
.\scripts\start.ps1
```

`device=auto` ưu tiên CUDA rồi CPU. DirectML chỉ là lựa chọn thử nghiệm có chủ
đích cho SLM Q4F16 trên AMD Windows; cần kiểm tra output trước khi sử dụng.

Các model lớn không được commit Git. Nếu SLM không sẵn sàng, event vẫn được
phát cảnh báo bằng pipeline deterministic và ghi `slm_status=fallback` hoặc
`disabled` để Engineer Console phân biệt rõ.

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

YOLO26n/YOLO26s là pretrained public candidates dùng cho benchmark nhanh, chưa
được promote vào release. Có thể chạy thử profile tương ứng sau khi đặt weights
vào `models/`:

```powershell
$env:ROADWATCH_RUNTIME = "directml"
$env:ROADWATCH_OBJECT_PROFILE = "yolo26s_public"
.\scripts\start.ps1
```

Rollback tức thì về baseline bằng cách mở terminal mới hoặc chạy:

```powershell
$env:ROADWATCH_OBJECT_PROFILE = "baseline_coco"
.\scripts\start.ps1
```

Tải public weights bằng Hugging Face Hub:

```powershell
.\.venv\Scripts\python.exe -c "from huggingface_hub import hf_hub_download; from pathlib import Path; root=Path('models'); [hf_hub_download('Ultralytics/YOLO26', f'yolo26{x}.pt', local_dir=str(root)) for x in ('n','s')]"
```

Sau đó export ONNX bằng Ultralytics hoặc dùng sẵn các file `.onnx` đã export.
YOLO26 dùng license AGPL-3.0; cần review license/commercial terms trước khi
đưa vào sản phẩm doanh nghiệp.

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

### Thử TwinLiteNet+ với YOLOP fallback

TwinLiteNet+ Medium ONNX là candidate lane/drivable nhanh hơn trên máy AMD.
Profile này không thay đổi mặc định production. Khi bật, RoadWatch load cả hai
model: TwinLiteNet+ chạy chính; YOLOP tự động nhận xử lý nếu candidate không có
file, không load được, inference lỗi hoặc trả lane mask rỗng. Kết quả có các cờ
`source`, `fallback_used` và `fallback_reason` để audit.

Mở một PowerShell tại thư mục `roadwatch` và chạy:

```powershell
$env:ROADWATCH_RUNTIME = "directml"
$env:ROADWATCH_LANE_PROFILE = "twinlitenetplus"
.\scripts\start.ps1
```

Sau đó mở [http://localhost:8000](http://localhost:8000), đăng nhập bằng
`driver/driver123`, chọn video mẫu và bấm **Bắt đầu phân tích**. Để kiểm tra
model/fallback bằng log hoặc API status, dùng Engineer Dashboard và tìm:

```text
lane.model = TwinLiteNet+ primary -> YOLOP fallback
lane.active_model = twinlitenetplus
lane.primary_loaded = true
lane.fallback_loaded = true
lane.primary.provider = DmlExecutionProvider
lane.fallback.provider = DmlExecutionProvider
lane.fallback_count = 0       # phiên bình thường dùng TwinLiteNet+
lane.fallback_count > 0       # đã có frame quay về YOLOP
```

Smoke test ép fallback an toàn mà không đổi tên hoặc xóa model thật:

```powershell
$env:ROADWATCH_TWINLITENETPLUS_MODEL = "__missing_twinlitenetplus_test__.onnx"
.\scripts\start.ps1
```

Sau khi bắt đầu phân tích một video, `lane.primary.available` sẽ là `false` và
`lane.active_model` sẽ là `yolop_fallback`, `lane.fallback_loaded` là `true` và
`lane.fallback_count` sẽ tăng; đó là bằng chứng YOLOP đã tiếp quản. Muốn quay
lại TwinLiteNet+ hoặc quay lại YOLOP ngay lập tức, dừng server rồi chạy:

```powershell
Remove-Item Env:ROADWATCH_LANE_PROFILE -ErrorAction SilentlyContinue
Remove-Item Env:ROADWATCH_TWINLITENETPLUS_MODEL -ErrorAction SilentlyContinue
$env:ROADWATCH_LANE_PROFILE = "yolop"
.\scripts\start.ps1
```

Khi đóng PowerShell, các biến môi trường phiên này cũng mất; `runtime.json`,
release manifest và YOLOP production không bị sửa.

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
