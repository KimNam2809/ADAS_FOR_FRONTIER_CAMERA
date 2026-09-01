# RoadWatch Copilot
## Mô tả dự án và kỹ thuật sử dụng

> **Tài liệu gửi VinFast — trạng thái:** Technical PoC / Demo-ready, được thiết
> kế theo hướng production-shaped architecture. RoadWatch hiện chưa phải tính
> năng ADAS OEM đã tích hợp trên xe VinFast, chưa có Camera HAL/CAN thật và chưa
> được chứng nhận an toàn. Các giới hạn này được ghi rõ để tách bạch năng lực đã
> chứng minh với lộ trình cần phối hợp cùng doanh nghiệp.

## 1. Tóm tắt dự án

### Tên sản phẩm

**RoadWatch Copilot**

### Mô tả ngắn

RoadWatch Copilot là trợ lý cảnh báo hỗ trợ lái đa phương thức, phân tích camera
trước để nhận diện tác nhân giao thông, làn đường, biển báo và nguy cơ va chạm
trong môi trường giao thông hỗn hợp Việt Nam. Hệ thống hợp nhất quyết định thành
hazard banner, beep và cảnh báo Piper TTS tiếng Việt có ngữ cảnh, nhưng chỉ hỗ
trợ người lái và không tự lái, phanh hoặc đánh lái.

### Tầm nhìn sản phẩm

RoadWatch hướng tới một **Vietnamese-context, edge-first warning copilot** có
thể chạy offline trong xe, hiển thị trên HMI/AAOS, đồng thời có Engineer
Dashboard và MLOps plane để kiểm thử, HITL, quản trị model và cải tiến theo dữ
liệu được phê duyệt.

Sản phẩm không được định vị là một hệ thống cloud-only. GCP chỉ là control và
evaluation plane; đường cảnh báo quan trọng trên xe phải chạy cục bộ tại edge.

## 2. Bài toán RoadWatch giải quyết

### 2.1. Bối cảnh

Giao thông Việt Nam có các đặc điểm làm bài toán ADAS khó hơn một kịch bản đường
cao tốc được chuẩn hóa:

- Xe máy, xe đạp, ô tô, xe buýt, xe tải và người đi bộ cùng xuất hiện trong một
  vùng quan sát.
- Phương tiện có thể cắt ngang tại ngã tư, từ đường nhánh hoặc từ vùng khuất.
- Xe máy/ô tô có thể nhập làn, tạt đầu, phanh hoặc đổi hướng nhanh.
- Vạch làn có thể bị mờ, che khuất, phản chiếu khi mưa, thiếu sáng hoặc suy giảm
  bởi video nén/rung.
- Biển báo có thể nhỏ, bị che, xuất hiện nhiều biển cùng lúc hoặc nằm ở hướng
  không liên quan tới làn xe ego.
- Một cảnh báo chỉ bằng tiếng beep không cho tài xế biết đối tượng nào, ở đâu và
  cần phản ứng thế nào.

### 2.2. Khoảng trống sản phẩm

RoadWatch tập trung vào lớp cảnh báo có ngữ cảnh:

```text
Nhận diện đơn lẻ       →       Quyết định có ngữ cảnh
“Có xe máy”             →       “Xe máy phía trước bên phải, hãy chú ý”
“Thấy biển 80”          →       Chỉ thông báo sau temporal confirmation và
                                kiểm tra relevance/ambiguity
“Có vật thể”            →       Ưu tiên FCW/VRU/cut-in trước advisory sign
```

Mục tiêu là giảm hai rủi ro đối nghịch:

1. **Bỏ sót nguy cơ quan trọng** — false negative ở người đi bộ, xe máy, xe cắt
   ngang hoặc xe phía trước đang tiến gần.
2. **Cảnh báo mệt mỏi** — false positive, cảnh báo trùng lặp hoặc cảnh báo sai
   đối tượng/hướng khiến tài xế mất niềm tin.

## 3. RoadWatch hiện đang có gì?

### 3.1. Ứng dụng local trên Windows/AMD

Bản local hiện chạy bằng FastAPI backend và React HMI tại `localhost`. Nó hỗ trợ:

- Video library trong `media/` và upload video mới.
- Phát lại video với thời gian hiện tại/tổng thời lượng.
- Pause/resume, tua ±10 giây, kéo timeline và phát lại từ đầu.
- Reset session, tracking, risk, alert và cached frame khi đổi video.
- Driver HUD cho người lái.
- Engineer Console cho model health, metric, event timeline, evidence và config
  có audit.
- Login theo vai trò tài xế/kỹ sư.
- SQLite local lưu event/evidence/audit.
- Chạy offline sau khi đã có dependency, model, video và voice asset.
- Beep và Piper Vietnamese TTS chạy bất đồng bộ; critical beep không chờ TTS.

### 3.2. Perception hiện có

RoadWatch local đã có các model runtime sau:

| Head | Artifact hiện hành | Nhiệm vụ |
|---|---|---|
| Road-user detection | `yolo11n.pt` / `yolo11n.onnx` | `person`, `bicycle`, `motorcycle`, `car`, `bus`, `truck` |
| Traffic-sign detection | `roadwatch_detector_v2.pt` / `.onnx` | Phát hiện biển báo Việt Nam |
| Speed-value recognition | `roadwatch_speed_digits_v2.pt` / `.onnx` | Xác nhận giá trị biển giới hạn tốc độ |
| Lane/drivable area | `yolop_lane_detection_640.onnx` / `.pth` | Lane mask và drivable-area mask |
| Lane candidate | `ufldv2_culane_res18_320x1600.onnx` / `.pth` | Lane geometry candidate, chưa phải default |

Các video target-domain đã có gồm `dashcam_vietnam.mp4`, bản đêm, mưa/đêm,
traffic-multi và các video test cho FCW, biển báo, VRU, cut-in, cross-traffic.

### 3.3. Risk và cảnh báo hiện có

Risk Engine và Alert Governor hiện hỗ trợ logic cho:

- FCW — Forward Collision Warning.
- VRU — Vulnerable Road User.
- Cut-in và cross-traffic.
- Lead-braking heuristic dựa trên relative image-space motion.
- LDW — Lane Departure Warning khi lane quality đủ tin cậy.
- Traffic-sign alert, đặc biệt biển giới hạn tốc độ và biển cấm.
- Temporal confirmation nhiều frame.
- Tracking/history theo object ID.
- Severity priority, debounce, cooldown, deduplication, hysteresis.
- Critical beep preemption.
- Canonical alert event để banner và TTS dùng cùng message/event ID.

Mô hình quyết định khẩn cấp là deterministic rule-based. Không đưa SLM/LLM vào
critical path vì quyết định cảnh báo phải có độ trễ dự đoán được, tái lập được và
giải thích được.

### 3.4. HMI và âm thanh

Driver HUD ưu tiên:

- Cảnh báo lớn, ít thông tin phụ.
- Hazard theo severity.
- Hướng và loại đối tượng.
- FPS/health ở mức vừa đủ cho demo.
- Audio-first khi mức nguy hiểm cao.

Engineer Console hiển thị:

- Perception provider/model health.
- Lane quality và risk score.
- Event timeline.
- Track/evidence packet.
- Audio action và suppression reason.
- Config/audit dành cho kỹ sư.

TTS chính là Piper `vi_VN-vais1000-medium`, language metadata `vi_VN`, sample
rate 22.050 Hz. Browser Web Speech không còn là đường TTS chính trên public Web
vì có thể fallback sang giọng tiếng Anh tùy máy khách.

## 4. Kiến trúc kỹ thuật hướng tới xe thật

### 4.1. Một Core, ba deployment planes

RoadWatch được thiết kế theo nguyên tắc **one Core, three deployments**:

```text
                         RoadWatch Core Contract
                                  |
          ┌───────────────────────┼───────────────────────┐
          v                       v                       v
    Edge / Jetson              AAOS HMI              GCP Control Plane
  offline safety path       camera/HMI adapter      demo + HITL + MLOps
```

Tất cả runtime dùng chung các hợp đồng dữ liệu:

- `FramePacket`: frame, timestamp, sequence và session identity.
- `VehicleTelemetry`: ego speed/gear/turn signal/brake nếu OEM cho phép.
- `AlertEvent`: event ID, object, direction, severity, risk, message, evidence.
- `ModelManifest`: model version, checksum, backend, precision và promotion
  status.

Chỉ thay đổi các adapter như `VideoSource`, `CameraSource`, `VehicleAdapter`,
model provider và transport; không sao chép riêng logic safety giữa Web, AAOS và
edge.

### 4.2. Luồng xử lý end-to-end

```text
Camera/video frame
        |
        v
Perception Engine
 object + sign + speed + lane + drivable area
        |
        v
Temporal Evidence / Tracking
 track ID + history + confirmation + quality
        |
        v
Kinematics / Risk Engine
 closing trend + path conflict + lateral motion + image-space risk
        |
        v
Alert Governor
 severity + cooldown + deduplication + preemption
        |
        v
Canonical AlertEvent
        |                 |                    |
        v                 v                    v
   AAOS/HUD          Beep critical       Piper Vietnamese TTS
```

### 4.3. Edge/vehicle plane

Đây là đường chạy cần được ưu tiên khi đưa lên xe thật:

- Camera adapter nhận stream từ Camera HAL/EVS/CSI theo quyền OEM.
- ONNX Runtime hoặc TensorRT xử lý model.
- Risk Engine chạy local, không chờ Internet.
- Piper audio chạy offline.
- Evidence tối thiểu được lưu cục bộ.
- AAOS nhận state/event qua local IPC, local HTTP/WebSocket hoặc contract được
  OEM phê duyệt.

GCP không được nằm trên critical path của FCW, VRU, LDW hoặc cross-traffic.

### 4.4. AAOS plane

AAOS hiện là HMI/replay simulation:

- Import video có sẵn.
- Hiển thị Driver HUD trong Automotive Device/WebView.
- Chạy background/replay theo lifecycle mô phỏng.
- Hỗ trợ pause, seek, resume và reset.
- Có thể thay `FileReplaySource` bằng Camera2/EVS adapter khi có quyền hệ thống
  và API OEM.

AAOS hiện **chưa** đọc camera trước của VinFast và **chưa** gọi vehicle API/CAN
production. Đây là một điểm được cố ý giữ rõ để không giả mạo mức độ tích hợp.

### 4.5. GCP control/evaluation plane

GCP được sử dụng cho:

- Public Web demo.
- Video Library/custom upload.
- Replay/evaluation.
- Engineer Dashboard/HITL.
- Asset bootstrap model/media/voice qua GCS allowlist/checksum.
- Cloud Build/Artifact Registry/IAM/Secret Manager.
- Model registry, evidence và OTA candidate trong tương lai.

URL demo hiện tại:

<https://roadwatch-web-bx6lfekcba-as.a.run.app/>

Public cloud không phải bằng chứng rằng xe thật đã đạt realtime. Cloud Run là
demo/evaluation plane; edge/AAOS mới là kiến trúc mục tiêu cho sản phẩm xe.

## 5. Kỹ thuật sử dụng

### 5.1. Computer Vision và AI

| Thành phần | Kỹ thuật |
|---|---|
| Object detection | YOLO11n COCO, ONNX export, confidence/class threshold |
| Traffic sign | YOLO fine-tuned trên traffic-sign Việt Nam, temporal confirmation và sign arbitration |
| Speed recognition | Detector + speed digit classifier + visual/temporal validation |
| Lane | YOLOP segmentation; UFLDv2 ResNet-18 là candidate geometry |
| Tracking | IoU temporal tracker MVP; schema cho phép thay bằng ByteTrack/DeepSORT sau benchmark |
| Motion | Relative image-space motion, bbox expansion, lateral displacement, path conflict |
| Risk | Deterministic rule engine, không tuyên bố absolute TTC khi chưa calibration |
| TTS | Piper Vietnamese voice, WAV cache, async audio worker |

### 5.2. Backend và HMI

- Python 3.10–3.12.
- FastAPI/Uvicorn.
- WebSocket/polling cho status.
- MJPEG overlay cho replay visualization.
- SQLite local cho event/evidence/audit.
- React + TypeScript + Vite.
- Web Audio cho beep và playback control.
- Android Studio/AAOS Automotive Device cho HMI simulation.

### 5.3. Runtime acceleration

| Môi trường | Backend dự kiến |
|---|---|
| Windows AMD | ONNX Runtime DirectML nếu provider khả dụng; CPU fallback |
| NVIDIA desktop/EC2 | CUDA/ONNX Runtime GPU |
| Jetson Orin | TensorRT/ONNX Runtime CUDA, FP16; INT8 chỉ sau calibration |
| Cloud Run CPU | ONNX CPU, async optional heads, bounded threads |

Các model nặng không được commit Git. Git chỉ quản lý source/config nhẹ; runtime
asset được tải từ Drive/Kaggle/GCS theo manifest, checksum và release decision.

### 5.4. Data và MLOps

Quy trình model:

```text
Public/target-domain data
        → taxonomy normalization
        → train/val/test split khóa
        → Kaggle GPU fine-tune
        → export ONNX
        → static model metrics
        → RoadWatch event regression
        → latency/safety gate
        → promote hoặc giữ baseline
```

Các nguyên tắc đã áp dụng:

- Không train full trên laptop AMD.
- Không trộn target-domain frame vào validation/test.
- Không promote model chỉ vì mAP tăng.
- Model mới phải giữ critical-event recall và false-alert budget trong giới hạn.
- Model/video/voice dùng hash/checksum và manifest.
- Dataset không rõ license hoặc taxonomy không đạt Quality Gate bị cách ly.

## 6. Model decision và bằng chứng hiện tại

### 6.1. Traffic sign

Traffic Sign Phase 2 đã được promote sau Quality Gate:

- Detector best precision: `0,95847`.
- Detector best recall: `0,96651`.
- mAP50: `0,98741`.
- mAP50-95: `0,83217`.
- Speed classifier top-1: `0,98254`.
- `test_video10`: xác nhận biển 60 và TTS 60.
- `test_video11`: xác nhận biển 80 và TTS 80.
- Negative window `video_test` 34–67 giây: không phát false speed event trong
  locked regression.

Đây là model validation và locked replay evidence, không phải claim rằng mọi
biển báo trên mọi xe đều nhận diện đúng.

### 6.2. Object detection

Baseline COCO `yolo11n_320/yolo11n.onnx` đang được giữ làm runtime baseline vì
Object V2 candidate không vượt event-level promotion gate. Candidate V2 có static
metrics/latency chưa đủ bù cho việc locked event recall giảm và false alert tăng.

Đây là quyết định engineering quan trọng: ưu tiên hành vi cảnh báo trên scenario
thực tế hơn một con số mAP riêng lẻ.

### 6.3. Lane

YOLOP đang là lane/drivable runtime hiện hành. UFLDv2 ResNet-18 có lane geometry
tốt hơn ở một số slice nhưng bị giữ ở trạng thái candidate vì edge FPS gate chưa
đạt. Benchmark DirectML fusion ghi nhận khoảng `3,04 FPS`, lane P95 `124,68 ms`
và E2E P95 `149,37 ms`.

Khi lane quality thấp, RoadWatch khóa LDW thay vì hiển thị geometry giả chính
xác. Multi-lane counting trong mưa/đêm/video nén vẫn là workstream cần tiếp tục.

### 6.4. Alert/audio logic

- RW-11: `120` decision-policy permutations, output deterministic và các gate về
  critical preemption/sign cooldown đạt.
- RW-12: software audio queue pass; canonical HUD/TTS equality, stale-event
  dropping và critical beep preemption đạt. Cabin listening/human intelligibility
  gate vẫn còn.
- Full Python regression evidence gần nhất: `156/156` pass.
- Local benchmark Windows AMD ghi nhận E2E P95 `138,13 ms` ở một run 10 giây;
  benchmark 30 giây trước đó ghi nhận `155,25 ms`. Đây là replay benchmark, không
  phải vehicle benchmark.

## 7. Vì sao RoadWatch phù hợp với VinFast?

### 7.1. Phù hợp với bối cảnh thị trường Việt Nam

RoadWatch tập trung vào motorcycle-heavy mixed traffic, cross-traffic, cut-in,
VRU và tiếng Việt. Đây là lớp dữ liệu và HMI cần được đánh giá trong bối cảnh
địa phương, thay vì chỉ dùng benchmark giao thông tổng quát.

### 7.2. Phù hợp với hướng phát triển xe điện và cockpit software

Kiến trúc RoadWatch phù hợp với bài toán phần mềm trên xe vì:

- Core có thể chạy offline.
- HMI tách khỏi perception/risk.
- AAOS được dùng như một contract/HMI plane.
- Camera, telemetry và vehicle API được trừu tượng hóa thành adapter.
- Không phụ thuộc cloud cho cảnh báo nguy hiểm.
- Có thể benchmark theo điện năng, nhiệt độ, FPS và latency trên edge device.

### 7.3. Có lộ trình tích hợp, không chỉ là demo model

RoadWatch đã chuẩn bị các lớp cần thiết để tiến tới tích hợp:

```text
FileReplaySource
      ↓ thay bằng
CameraSource / Camera HAL / EVS adapter

MockTelemetry
      ↓ thay bằng read-only contract
CAN / vehicle signals được OEM phê duyệt

Local React/AAOS HMI
      ↓ giữ nguyên event contract
VinFast cockpit HMI theo API thực tế
```

Việc này cho phép giữ lại perception/risk/alert core khi thay đổi nguồn camera
hoặc nền tảng hiển thị.

### 7.4. Thể hiện năng lực kỹ thuật có giá trị cho OEM

RoadWatch thể hiện khả năng kết hợp:

- Computer Vision và model fine-tuning.
- Data taxonomy, HITL và quality gate.
- ONNX/DirectML/CUDA/TensorRT deployment planning.
- Realtime pipeline và async worker.
- HMI/AAOS integration contract.
- Vietnamese TTS/audio UX.
- GCP/Cloud Run/GCS/IAM/MLOps.
- Safety guardrail, metrics và rollback.

## 8. Mức độ sẵn sàng thực tế

| Hạng mục | Trạng thái | Diễn giải |
|---|---|---|
| Local video replay | **Đã có** | Chạy offline, có HUD, audio, event/evidence |
| Local object/sign/lane | **Đã có** | Model runtime và profile đã xác định |
| Vietnamese TTS/beep | **Đã có** | Piper local/public path và audio governance |
| Engineer Dashboard/HITL | **Đã có một phần** | Có console, evidence và review workflow; cần mở rộng persistence/fleet |
| Public Web | **Đã có** | GCP Cloud Run/GCS evaluation plane |
| AAOS replay HMI | **Đã có** | Android Studio Automotive Device, chưa có camera thật |
| Edge packaging | **Đã chuẩn bị** | Docker CPU/NVIDIA/ARM64/Jetson profiles |
| Jetson Orin benchmark | **Chưa nghiệm thu** | EC2 ARM64 không thay thế Orin thật |
| Camera HAL VinFast | **Chưa có** | Cần API, permission, camera stream và calibration của OEM |
| CAN/radar/depth | **Chưa có** | Hiện dùng vision-only proxy |
| TTC/khoảng cách mét | **Chưa đủ điều kiện** | Cần calibration/telemetry/sensor validation |
| Closed-course safety test | **Chưa có** | Cần xe, track, safety driver và protocol được duyệt |
| Production certification | **Chưa có** | Ngoài phạm vi claim của prototype |

## 9. An toàn và giới hạn thiết kế

RoadWatch có các guardrail sau:

- Không có API tự động phanh, đánh lái, tăng ga hoặc điều khiển actuator.
- Không đặt LLM/SLM trong critical decision path.
- Không tuyên bố absolute distance/TTC khi chưa calibration.
- Ghi rõ `estimated`, `image-space` hoặc `uncalibrated` khi dùng proxy.
- Khóa LDW khi lane quality không đủ.
- Suppress/silence khi biển báo không đủ temporal confirmation hoặc không rõ lane
  relevance.
- Beep critical có quyền preempt cảnh báo advisory.
- Không dùng cloud request để quyết định FCW/VRU critical.

Đây là cách tiếp cận phù hợp để bắt đầu một R&D pilot với OEM: chứng minh cảnh
báo trước, không phát sinh rủi ro từ việc tự ý điều khiển xe.

## 10. Lộ trình từ prototype tới pilot VinFast

### Phase 1 — Khóa dữ liệu và safety metrics

- Mở rộng ground truth cho ngày/đêm/mưa/traffic-multi/occlusion/negative.
- Có owner review và secondary review độc lập.
- Đo event recall, direction accuracy, duplicate rate, false alerts/minute và
  time-to-warning theo từng scenario.
- Hoàn thiện Fallen Rider dataset/model chỉ khi taxonomy và license đạt.

### Phase 2 — Edge performance

- Benchmark trên đúng Jetson Orin hoặc hardware được VinFast chỉ định.
- Mục tiêu đề xuất: demo edge `>=20 FPS`, release target `>=30 FPS`, critical
  pipeline P95 `<150 ms`.
- Đo RAM/VRAM, power, thermal, dropped frames, cold/warm start.
- So sánh FP32/FP16/INT8 với calibration set.

### Phase 3 — AAOS/camera integration

- Nhận Camera HAL/EVS contract từ platform owner.
- Calibrate intrinsic/extrinsic/FOV/hood mask/vanishing point.
- Tích hợp read-only telemetry trước: ego speed, turn signal, gear, brake.
- Giữ RoadWatch warning-only trong toàn bộ pilot đầu tiên.

### Phase 4 — Closed-course pilot

- Dùng safety driver và track kín.
- Kiểm tra FCW, VRU, cut-in, cross-traffic, LDW, sign relevance và audio cabin.
- Đo time-to-warning, false alert, missed event, p95 latency và fail-safe khi
  camera/telemetry mất.
- Chỉ sau giai đoạn này mới đánh giá tiếp production/certification pathway.

### Phase 5 — MLOps/fleet readiness

- Model registry với version/hash/promotion/rollback.
- OTA candidate chỉ sau regression gate.
- Fleet data có consent, anonymization, retention và cybersecurity policy.
- Vehicle profile theo từng platform, không suy luận chung từ kích thước VF5–VF9.

## 11. Đề xuất hợp tác/pilot với VinFast

RoadWatch phù hợp để bắt đầu bằng một pilot có phạm vi kiểm soát:

1. VinFast cung cấp camera/sample data hoặc cho phép sử dụng data collection
   protocol đã được phê duyệt.
2. RoadWatch chạy read-only, không nối actuator.
3. Đánh giá trước trên replay và simulator.
4. Sau khi có calibration, chạy trên closed course với safety driver.
5. Đo theo release gate đã thống nhất.
6. Chỉ sau khi đạt gate mới mở rộng sang vehicle integration hoặc fleet pilot.

Giá trị của pilot không chỉ là một model nhận diện, mà là đánh giá toàn bộ chuỗi:

```text
Vietnamese data → perception → risk → priority → Vietnamese HMI
               → edge latency → evidence → safe iteration
```

## 12. Kết luận

RoadWatch Copilot hiện đã là một prototype end-to-end có local replay, perception,
risk reasoning, alert prioritization, Vietnamese Piper TTS, Driver HUD, Engineer
Dashboard, Docker profiles, GCP evaluation deployment và AAOS replay HMI.

Điểm phù hợp nhất với VinFast là RoadWatch được thiết kế để trở thành một lớp
phần mềm cảnh báo có ngữ cảnh Việt Nam, chạy offline trên edge và có đường nối
rõ ràng tới AAOS/camera/vehicle contract. Nó không phụ thuộc vào việc ban tổ chức
phải tin một video demo; mọi thay đổi model đều được gắn với metric, evidence,
Quality Gate và rollback.

Tại thời điểm hiện tại, RoadWatch nên được giới thiệu với VinFast là:

> **Một prototype R&D production-shaped cho trợ lý cảnh báo ADAS tiếng Việt,
> đã chứng minh được pipeline phần mềm và HMI/replay, sẵn sàng bước vào giai đoạn
> OEM data, camera calibration, edge benchmark và closed-course validation.**

Không nên gọi RoadWatch là hệ thống ADAS production-certified hoặc hệ thống tự
lái cho đến khi hoàn tất các human/hardware gates nói trên.

## 13. Tài liệu kỹ thuật tham chiếu

- [`README.md`](../README.md) — cài đặt và chạy local.
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — pipeline core.
- [`UNIFIED_DEPLOYMENT_ARCHITECTURE.md`](./UNIFIED_DEPLOYMENT_ARCHITECTURE.md) —
  kiến trúc Edge + Web GCP + AAOS.
- [`VINFAST_PROFILES.md`](./VINFAST_PROFILES.md) — UI/deployment baseline VF5–VF9.
- [`CLOUD_FULL_PERCEPTION_DEPLOYMENT.md`](./CLOUD_FULL_PERCEPTION_DEPLOYMENT.md) —
  public full-perception evidence.
- [`PIPER_VI_WEB_DEPLOYMENT.md`](./PIPER_VI_WEB_DEPLOYMENT.md) — Vietnamese TTS
  deployment evidence.
- [`VINFAST_BUSINESS_REPORT.md`](./VINFAST_BUSINESS_REPORT.md) — business-facing
  product report.

