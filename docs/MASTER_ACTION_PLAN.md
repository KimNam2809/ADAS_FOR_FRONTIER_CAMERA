# RoadWatch — Master Action Plan

## Trạng thái thực thi

| Task | Trạng thái | Bằng chứng gần nhất |
|---|---|---|
| RW-00 | **COMPLETE** | Release preflight 24/24; 7 artifact SHA-256; health gate; xem `RW-00_RELEASE_BASELINE.md`. |
| RW-01 | **SOFTWARE COMPLETE / DATA COVERAGE PARTIAL** | 70.610/70.610 frame decode; 4.708 mẫu 2 FPS; 600 frame; 24 contact sheet; video không có night/rain coverage. |
| RW-02 | **COMPLETE — QUALITY GATE PASS** | 600 giây verified, gồm 440 giây negative; 16 event (`cross_traffic=7`, `cut_in=8`, `speed_sign=1`); 7/7 critical windows independently reviewed; disagreement 0%; schema integrity pass. Xem `reports/rw02_final_gate.json`. |
| RW-03 | **COMPLETE — HARNESS PASS / BASELINE QUALITY FAIL** | 37/37 scenario completed; hashes/config/taxonomy/ground truth/tests pass; seed 162. Baseline recall 0,7083, precision 0,0335, 491 FP nên không đủ điều kiện promote. Xem `evaluation/rw03_baseline_evidence.json`. |
| RW-04 | **COMPLETE — V3 Full candidate rejected / baseline retained** | Kaggle full artifact hợp lệ; locked regression `6/5/4`, event recall `0,6000` < baseline `0,8000`; xem `reports/RW04_OBJECT_V3_FULL_KAGGLE_REVIEW_20260828.md`. |
| RW-05…RW-16 | **PENDING** | Tiếp tục remediation VRU/cut-in/cross-traffic và các dependency theo DoD; không coi V3 Full là production model. |

Trạng thái trên là execution ledger. Definition of Done và thứ tự phụ thuộc bên
dưới vẫn là nguồn chuẩn để triển khai.

> Phiên bản: 2026-08-21 · Trạng thái: blueprint thực thi · Phạm vi: hệ thống
> cảnh báo hỗ trợ lái **warning-only**. RoadWatch không được điều khiển ga,
> phanh hoặc đánh lái trong mọi task của kế hoạch này.

Tài liệu này là backlog kỹ thuật có thể thực thi. Khi nhận lệnh `thực hiện
RW-XX`, AI Agent phải dùng đúng Definition of Done (DoD), dependency, phạm vi
quyền hạn và cách đo nêu tại đây; không tự promote model hay bật tính năng
critical chỉ vì inference chạy được.

## 1. Tổng quan chiến lược & tính khả thi

### 1.1. Hiện trạng đã xác minh

| Năng lực | Trạng thái | Bằng chứng/giới hạn quyết định |
|---|---|---|
| Pipeline offline | Có FastAPI, React HUD/Engineer Console, SQLite evidence, ONNX Runtime DirectML và Piper tiếng Việt. | Có test backend, replay video và health/provider status. |
| Object detection | `baseline_coco` là mặc định; candidate `roadwatch_objects_v1_1` có mAP50 `0.5124`. | Candidate giảm timestamp event recall từ `0.5000` xuống `0.3750`; **không được promote**. |
| Biển báo/tốc độ | `roadwatch_detector_v2` + classifier tốc độ đã qua locked regression. | Detector mAP50 `0.9874`; classifier top-1 `0.9825`; speed 40/50/60/80 cần tiếp tục regression. |
| FCW/VRU/cut-in/cross-traffic/lead braking | Đã có rule engine, tracking, temporal confirmation, near-field fallback và alert governor. | Hiện là image-space risk, không phải TTC theo mét hoặc vận tốc vật lý. |
| LDW/lane | YOLOP là mặc định; UFLDv2 fusion là candidate. | UFLDv2 đạt coverage `0.8571` trên 21 frame nhưng full pipeline chỉ `3.04 FPS`, chưa đạt gate `>=12 FPS`. |
| Ground truth | Có schema/scorer và khoảng 52 giây cửa sổ verified. | Quá ít để công bố false-alert rate hoặc recall production. |
| Fallen rider | Có quality gate và annotation queue. | Chưa có dataset dashcam target đạt gate; chưa có checkpoint được phép dùng. |
| Camera/TTC/CAN/Jetson | Có calibration, telemetry và TensorRT benchmark scripts. | Chưa có camera calibration, CAN read-only, Jetson Orin hoặc closed-course evidence. |

`media/dashcam_vietnam.mp4` đã có local, dài 39 phút 16 giây và khoảng 892 MB.
Nó là dữ liệu đánh giá/annotation riêng, không được commit vào Git hoặc dùng để
claim metric trước khi Human Quality Gate xác nhận nhãn.

### 1.2. Định nghĩa các mức sẵn sàng

| Mức | Ý nghĩa | Điều kiện tối thiểu |
|---|---|---|
| R0 — Research demo | Demo video offline có guardrail và evidence. | Test tự động pass, model/provider health pass; không tuyên bố an toàn xe thật. |
| R1 — Edge candidate | Có thể chạy liên tục trên target edge với cấu hình bị khóa. | `>=12 processed FPS`, E2E P95 `<=150 ms`, no pipeline error trong replay 30 phút. |
| R2 — Closed-course candidate | Được phép thử tại khu vực kín, warning-only, có safety driver. | Gate event/latency/audio ở §1.3 và protocol `CLOSED_COURSE_VALIDATION.md` pass. |
| R3 — Vehicle integration/certification | Tích hợp đọc dữ liệu xe với OEM approval. | Không đạt chỉ bằng code. Cần OEM interface, hardware, đánh giá an toàn độc lập và thẩm quyền pháp lý. |

RoadWatch hiện ở R0. Một task chỉ có thể nâng mức khi toàn bộ gate của mức đó
đều đạt; không có ngoại lệ dựa trên mAP đơn lẻ.

### 1.3. Release gates định lượng

| Nhóm | Gate R1/R2 | Cách đo |
|---|---|---|
| Runtime | R1: `>=12 FPS`, E2E P95 `<=150 ms`, pipeline error `=0` trên replay 30 phút. | `scripts/benchmark.py`, JSON report có model/version/hash. |
| Critical event | R2: FCW/VRU recall `>=0.95`, semantic class/direction accuracy `>=0.95`. | Ground truth video-grouped, closed-course repetition, 95% CI. |
| False alert | R2: false critical `<=0.1/min`; all-alert `<=1/min` trong negative driving. | Cửa sổ negative được review exhaustively. |
| Timing | Critical warning không trễ hơn deadline scenario; báo cáo median/P95 time-to-warning. | Timestamp event log đồng bộ source video. |
| TTS/HMI | `display_message == spoken_message` 100%; audio completed `>=99%`; stale/dropped `<2%`; cached TTS start P95 `<=750 ms`. | Lifecycle SQLite + audio integration test trên thiết bị đích. |
| Speed sign | Accuracy giá trị 40/50/60/80 `>=0.98`; accepted false speed event `=0` trong locked negative window. | `trace_traffic_signs.py` + ground truth. |
| Lane | Ego-boundary F1 `>=0.90`, lane-count accuracy `>=0.95` trên bộ đánh nhãn day/night; LDW false alert `<=1/min`. | Lane annotation + per-condition report. |
| Metric TTC | Distance median error `<=10%`, P95 `<=20%`; TTC median absolute error `<=0.5 s`. | Measured-distance closed-course; trước đó telemetry-only. |

### 1.4. Phân nhánh khả thi khi thiếu phần cứng

| Hạng mục bị thiếu | (A) Software/CV thay thế | (B) Giả lập | (C) Điều kiện bắt buộc phải gác lại |
|---|---|---|---|
| Khoảng cách/TTC | Dùng relative proximity, bbox expansion, optical flow và track history; chỉ tạo `relative_risk`, không ghi mét/giây hoặc TTC critical. | CARLA render camera có depth/pose GT để kiểm thử sai số thuật toán. | Metric TTC dùng cho FCW cần chessboard calibration cùng camera/mount và khoảng cách đo thật. |
| Lead braking | Fuse paired-red-lamp score, bbox expansion, relative closing trend; cần 3 frame confirmation, advisory/warning theo risk. | CARLA phát ego speed, lead speed/brake state và video đồng bộ. | Phanh gấp theo khoảng cách/vận tốc tuyệt đối cần ego speed + distance/depth đã kiểm chứng. |
| Jetson Orin | Export ONNX, profiling script, static input profile và test regression có thể chuẩn bị trên Windows. | Docker/CI chỉ kiểm tra compatibility, không được gọi là benchmark Orin. | FPS, thermal, power, TensorRT engine và DLA phải đo trên Jetson/JetPack thật. |
| Vehicle/VinFast | Giữ `VehicleAdapter` read-only, mock telemetry JSON và HMI local. | Android Automotive OS (AAOS) emulator/VHAL giả lập speed, gear, day/night; CARLA giả lập scenario. | CAN/OBD/OEM API thật, quyền truy cập và signal definition bắt buộc từ OEM; không reverse-engineer hay gửi CAN write. |
| Chứng nhận an toàn | Tạo ODD, hazard log, traceability, versioned evidence và safety case nội bộ. | CARLA + closed-course rehearsal. | ISO 26262/SOTIF/certification chính thức cần OEM, cơ quan/đơn vị đánh giá độc lập và xe thật. |

AAOS emulator có thể mô phỏng Vehicle HAL properties, gồm speed và gear; nó chỉ
phù hợp test HMI/telemetry adapter, không chứng minh tương thích VinFast.
CARLA phù hợp sinh camera/ground truth có kiểm soát. Xem §4 để biết nguồn kỹ
thuật chính chủ.

## 2. Master Action Plan

### Quy ước trách nhiệm

- **AI 100%**: Agent có thể code, tạo script, chạy test local, tạo report và
  commit khi được yêu cầu.
- **AI + Human gate**: Agent tự động hóa pipeline, nhưng Human phải xác minh
  annotation, quality gate hoặc kết quả có ý nghĩa an toàn.
- **Human/hardware bắt buộc**: Không được giả định đã hoàn tất nếu thiếu thiết
  bị, quyền OEM, permission địa điểm hoặc dữ liệu thực.

| ID | Hạng mục & phụ thuộc | Definition of Done (đo được) | AI Agent Action | Trách nhiệm |
|---|---|---|---|---|
| **RW-00** | Release manifest & runtime synchronization. Không phụ thuộc. | `default.json`, `runtime.json`, model registry và `/api/health` cùng model filename/SHA-256; preflight fail khi khác nhau; 100% test pass. | Viết `release_preflight.py`; đọc provider/model thực tế, compare manifest, thêm CI/local test và hướng dẫn rollback. | AI 100%; Human chọn profile phát hành. |
| **RW-01** | Ingest `dashcam_vietnam.mp4`; phụ thuộc RW-00. | Inventory JSON có duration/FPS/resolution/hash; scene cuts; 2 FPS contact-sheet index; tối thiểu 600 frame stratified từ day/night/rain/intersection/dense traffic; không copy video vào Git. | Code extractor, perceptual-hash dedupe, blur/quality score, scene sampler và contact sheet. | AI 100% cho tooling; Human xác nhận quyền dùng/che thông tin riêng tư khi chia sẻ. |
| **RW-02** | Ground truth event-level; dùng output RW-01. | Tăng từ 52 giây lên ít nhất **600 giây verified exhaustive coverage**, gồm `>=150 giây` negative; mỗi FCW/VRU/cut-in/cross/LDW/lead-braking/sign có `>=20` event hoặc được ghi rõ là chưa đủ dữ liệu. Hai người review độc lập cho critical windows; disagreement log `<=10%` trước adjudication. | Mở rộng schema, queue annotation, contact sheets, scorer precision/recall/FAR/min/TtW; chặn promotion nếu coverage/second-review thiếu. | AI + Human gate: Human gán nhãn và adjudicate. |
| **RW-03** | Regression harness và test taxonomy; phụ thuộc RW-02. | Mỗi release chạy full regression trên locked media + dashcam sample; artifact JSON có hash/config; no unexpected event type; 100% automated tests pass. | Code scenario manifest, deterministic replay seed, golden-event comparison và markdown report generator. | AI 100%; Human duyệt thay đổi golden truth. |
| **RW-04** | Object detector promotion; RW-02/RW-03. | Candidate chỉ thay `baseline_coco` nếu event recall không giảm, VRU recall không giảm, P95 object latency `<=125%` baseline, FAR/min không tăng >10%, và Human review 50 FP/FN mẫu. | Train/evaluate Kaggle pipeline, class-aware threshold sweep, NMS/confidence calibration, temporal label voting; cập nhật registry chỉ khi gate pass. | AI + Human gate; Human duyệt sample/compute credential. |
| **RW-05** | VRU, cut-in, cross-traffic; RW-01/RW-02. | Recall `>=0.90` cho verified VRU/cut-in/cross subset; left/right semantic accuracy `>=0.95`; duplicate event rate `<=5%`; false critical `<=0.1/min`. | Add velocity smoothing/Kalman state, ego-path polygon, track association rider↔motorcycle, occlusion recovery và counterfactual regression tests. | AI + Human gate cho labels. |
| **RW-06** | FCW & lead braking without telemetry; RW-02. | Relative FCW/lead-brake event recall `>=0.90` trên verified video; no single-frame trigger; brake cue needs `>=3` frames; output evidence labels every metric as `image_space`/`relative`. | Fuse bbox scale derivative, track depth proxy, optical flow, paired brake-lamp score, hysteresis; expose confidence/reason in SQLite/HUD. Không dùng YOLOP mask để tuyên bố vận tốc tuyệt đối. | AI 100% code; Human gate cho safety thresholds. |
| **RW-07** | Metric distance/TTC; RW-06. | Trước calibration: only telemetry, no TTC-trigger. Sau calibration + closed course: đạt gate §1.3 trên 5/10/15/20/30/40 m, day+night. | Implement calibration artifact validation, monocular projection/depth experiment, TTC error evaluator, CARLA camera benchmark. | AI code/simulation; Human/hardware bắt buộc cho chessboard, measured distance và safety driver. |
| **RW-08** | Fallen-rider dataset gate; RW-01. | Public candidate report có license, viewpoint, box/temporal label type, duplicate hash, negative ratio và video-group split. Training block nếu không đạt: `>=250` instance/lớp, negatives:positives `>=2:1`, adverse/night `>=20%`. | Search/audit public sources; use D²-City for dashcam hard negatives/tracking only, A3D/accident datasets for temporal candidate discovery only; generate contact sheets and quarantine invalid sources. | AI 100% tooling/research; Human phải chấp thuận license và annotation policy. |
| **RW-09** | Fallen-rider detector/event; RW-08 + RW-02. | Advisory fallen event recall `>=0.90`, precision `>=0.75`, FAR `<=0.5/min` on held-out forward-dashcam videos; no promotion from CCTV-only data. | First implement temporal heuristic: prior rider track → person/motorcycle separation → stationary persistence in drivable area; then train specialist `fallen_person/fallen_rider`; require temporal confirmation before alert. | AI + Human data/annotation gate. |
| **RW-10** | Lane instance/count + LDW; RW-01/RW-02. | Lane-count accuracy `>=0.95`, ego-boundary F1 `>=0.90`, LDW FAR `<=1/min`; R1 runtime remains `>=12 FPS`, P95 `<=150 ms`. | Benchmark YOLOP vs UFLDv2 at 320×1600/optimized resolutions; infer lane every N frames, propagate curves with tracker, reject invalid geometry, optionally train lightweight lane-instance head. | AI code/benchmark; Human supplies target-lane labels and Jetson for final gate. |
| **RW-11** | Traffic-sign arbitration; RW-03. | At most one spoken sign prompt per audio window; critical road-user/FCW always preempts sign; same speed limit is not re-spoken for 20 s; 100% deterministic output on a permutation suite of `>=30` multi-sign frames. | Implement rule table by sign class/severity/road relevance, NMS by sign family, stable track/ROI confirmation, active-speed state and TTS priority queue tests. | AI 100%; Human reviews Vietnamese policy wording. |
| **RW-12** | TTS/HMI anti-alert overload; RW-03/RW-05. | Canonical HUD/TTS equality 100%; critical beep preempts advisory; audio completion `>=99%`, stale `<2%`, P95 start `<=750 ms`; max 1 advisory utterance/2.5 s and max 3/min per semantic key unless severity escalates. | Persist queue lifecycle, semantic debounce `(event_type, track/family, direction)`, token-bucket audio budget, cache warm-up, provider failure telemetry and audio integration tests. | AI 100%; Human checks intelligibility/volume in cabin. |
| **RW-13** | Jetson Orin TensorRT deployment; RW-00/RW-03/RW-10. | Engine build reproducible on exact JetPack; FP16 passes output regression; target reaches R1 runtime gate; thermal/power/memory logged for 30 min; INT8 only adopted if event recall/semantic accuracy drop `<=1 pp`. | Export static ONNX, build `trtexec` FP16 engines first, add per-engine/output parity test, collect latency/VRAM/temperature/power; use calibration set only after data gate. | AI code; Human/hardware mandatory for Orin/JetPack access. |
| **RW-14** | AAOS/CARLA simulation & vehicle adapter; RW-00/RW-06. | AAOS demo renders RoadWatch HMI at 1024×768 and 1080×600, consumes mock VHAL speed/gear read-only; CARLA suite has `>=50` scripted scenarios with synchronized video/event GT; no CAN write code. | Build localhost/WebSocket bridge or Android WebView client, mock VHAL telemetry schema, CARLA scenario/evaluation adapter and replay fixtures. | AI can code; Human needs Android SDK/GPU only to execute emulator/CARLA. OEM/VinFast integration remains blocked. |
| **RW-15** | Closed-course execution; RW-07/RW-10/RW-12/RW-13. | Execute every scenario in `CLOSED_COURSE_VALIDATION.md`: 10 repetitions per side/condition, SIGN 20/value, NEG 30 min; all R2 gates pass with synchronized artifacts. | Create run sheet, recorder, artifact hash collector, pass/fail report and automatic metric aggregation. | Human/hardware/site permission mandatory; AI assists only. |
| **RW-16** | Safety case & handover; RW-15. | Versioned ODD, hazard log, known limitations, traceability matrix task→test→metric, rollback plan and signed R0/R1/R2 status. No claim of ISO certification. | Generate documentation templates, release checklist, SBOM/dependency lock and evidence index. | AI 100% documentation; Human/OEM/assessor mandatory for any formal certification. |

### Execution ledger (2026-08-21)

- RW-04: complete; candidate rejected, active model remains `baseline_coco`.
- RW-05: partial; 3/4 gates pass, maneuver Recall `0.4444` remains model/data-blocked.
- RW-06: R0 software gate pass; 2/2 verified events và FAR `0.9278/min`, nhưng sample nhỏ.
- RW-07: software validator/evaluator complete; camera calibration and closed-course
  validation remain hardware/Human-blocked.
- Detailed evidence: `docs/RW-04_TO_RW-07_EXECUTION_REPORT.md`.
- RW-05 expansion: 790 seconds from three adverse/mixed-traffic videos are queued for Human review.
- RW-08: source/taxonomy gate implemented; training remains data/license-blocked.
- RW-10: 400-frame lane queue built; UFLDv2 candidate benchmarked but not promoted.
- RW-13: ARM64 cloud package ready; G5g execution deferred to avoid AWS cost.
- RW-14-AAOS: warning-only Android Automotive shell implemented; emulator sync/run pending.
- RW-11: deterministic traffic-sign arbitration implemented; 120 input permutations produce one output signature, one spoken sign per window, and critical road-user alerts preempt signs. Evidence: `evaluation/rw11_quality_gate.json`.
- RW-12: software queue gate pass; canonical HUD/TTS payload, critical preemption, 2.5-second global gap, semantic budget 3/minute, stale/failed/completed telemetry and start-latency measurement implemented. Vietnamese cabin intelligibility remains a Human gate. Evidence: `evaluation/rw12_quality_gate.json`.
- RW-05/RW-10 owner acceptance is recorded in `evaluation/rw05_rw10_owner_attestation.json`; metric gates are not overridden because per-record ground truth was not retained.
- Detailed evidence: `docs/RW-05_08_10_13_14_EXECUTION_REPORT.md`.

## 3. Thứ tự thực thi bắt buộc

```text
RW-00 → RW-01 → RW-02 → RW-03
                      ├→ RW-04 → RW-05 → RW-06 → RW-07
                      ├→ RW-08 → RW-09
                      ├→ RW-10
                      └→ RW-11 → RW-12
RW-00 + RW-03 + (RW-10) → RW-13 → RW-14 → RW-15 → RW-16
```

Không bắt đầu fine-tune/promotion RW-04 hoặc RW-09 trước RW-02. Không bắt đầu
metric TTC RW-07 hoặc closed-course RW-15 trước khi có calibration/hardware.
RW-13 có thể chuẩn bị source trước, nhưng benchmark target không được mô phỏng
bằng laptop AMD.

### Milestone gần nhất được khuyến nghị

1. **M0 — Evidence baseline:** hoàn thành RW-00, RW-01, RW-02. Đây là điều kiện
   để mọi metric phía sau có ý nghĩa.
2. **M1 — Video safety regression:** RW-03, RW-05, RW-06, RW-11, RW-12. Mục tiêu
   là giảm miss/overload trên dashcam Việt Nam trước khi thay model.
3. **M2 — Perception upgrade:** RW-04, RW-08, RW-09, RW-10. Chỉ promote bằng
   event-level gates, không bằng training mAP riêng lẻ.
4. **M3 — Edge + simulation:** RW-13, RW-14. Bản AAOS/CARLA là demo tích hợp,
   không phải VinFast integration.
5. **M4 — Physical safety evidence:** RW-07, RW-15, RW-16. Bắt buộc Human,
   hardware và điều kiện test kín.

## 4. Nguồn R&D và chính sách dataset

### 4.1. Fallen rider / incident data

Không có nguồn public nào được coi là dataset fallen-rider dashcam đạt chuẩn chỉ
vì có chữ “accident”. Mọi nguồn phải qua RW-08.

- [D²-City](https://arxiv.org/abs/1904.01975) là dashcam đa dạng với detection/
  tracking, phù hợp hard-negative, rider trajectory và domain adaptation; không
  tự động trở thành nhãn `fallen_rider`.
- [A3D / AnAn Accident Detection](https://arxiv.org/abs/1903.00618) và các
  dataset accident scene-level chỉ có thể hỗ trợ temporal candidate mining;
  không dùng làm bbox supervision nếu không có localization license/label.
- [CADP](https://arxiv.org/abs/1809.05782) có bối cảnh CCTV, nên chỉ nghiên cứu
  pretraining/negative; không promote cho forward dashcam.
- Kaggle/Roboflow chỉ là kênh discovery. AI Agent phải ghi source URL, license,
  checksum, viewpoint, class mapping và split-audit vào report trước download/
  training.

### 4.2. Target edge & simulation

- TensorRT/Jetson: bắt đầu FP16, sau đó mới INT8 có calibration set đại diện;
  NVIDIA yêu cầu đo trực tiếp accuracy/performance trên model và hardware đích.
  Không giả định DLA luôn nhanh hơn GPU.
- AAOS: [Android Automotive emulator](https://developer.android.com/training/cars/testing/emulator)
  có Automotive AVD và VHAL/vehicle-property simulation; dùng để test HMI/read-only
  telemetry, không thay thế VinFast API.
- CARLA: dùng [camera sensors](https://carla.readthedocs.io/en/latest/ref_sensors/)
  và scenario scripting để tạo video + GT có kiểm soát; tất cả kết quả phải được
  gắn nhãn `simulation`, không trộn với metric real-world.

## 5. Giao thức thực thi cho AI Agent

Khi triển khai một task `RW-XX`, Agent phải trả về và lưu report theo khuôn sau:

1. **Preflight:** git status, model/config versions, asset availability,
   dependency/hardware gate.
2. **Scope:** file được phép sửa, file/data không được commit, rollback path.
3. **Implementation:** code/script/config bằng patch có test kèm theo.
4. **Verification:** lệnh chạy, output metrics, so sánh DoD từng dòng.
5. **Decision:** `pass`, `fail`, hoặc `blocked`; không đổi default/promotion khi
   fail hoặc coverage không đủ.
6. **Human request:** chỉ hỏi đúng dữ liệu, nhãn, quyền hoặc hardware còn thiếu.

### Trạng thái ban đầu để gọi task

| Gọi | Agent được phép làm ngay | Cần từ Human trước khi kết thúc |
|---|---|---|
| `RW-00` | Có thể bắt đầu ngay. | Xác nhận profile release nếu có nhiều lựa chọn. |
| `RW-01` | Có thể ingest `dashcam_vietnam.mp4` local ngay. | Xác nhận quyền sử dụng/chia sẻ nếu tạo sample export. |
| `RW-02` | Có thể tạo queue, schema, contact sheets. | Nhãn và second-review. |
| `RW-04/RW-09` | Có thể chuẩn bị Kaggle package/audit. | Dataset license + Human Quality Gate + GPU job approval. |
| `RW-07/RW-13/RW-15` | Có thể chuẩn bị scripts/protocol. | Camera/Jetson/site/measurement/safety driver. |
| `RW-14` | Có thể scaffold adapter/simulator integration. | Android Studio/CARLA execution environment, OEM docs nếu có. |

## 6. Tài liệu liên quan trong repo

- `docs/IMPROVEMENT_EXECUTION_2026-08-19.md` — bằng chứng và blocker đã biết.
- `docs/MODEL_PROMOTION.md` — promotion gate object detector.
- `docs/TRAFFIC_SIGN_ALERTING.md` — policy sign/HUD/TTS.
- `docs/CLOSED_COURSE_VALIDATION.md` — protocol R2.
- `configs/model_registry.json` — version, hash, metric và promotion state.
- `configs/fallen_rider_sources.json` — quality gate dataset fallen rider.
