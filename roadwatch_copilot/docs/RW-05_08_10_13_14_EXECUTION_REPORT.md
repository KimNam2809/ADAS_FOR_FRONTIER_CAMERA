# RoadWatch RW-05/RW-08/RW-10/RW-13/RW-14 Execution Report

Ngày thực thi: 2026-08-22. Release level giữ nguyên **R0 — Research demo**.

## Kết luận

| Task | Trạng thái | Kết luận |
|---|---|---|
| RW-05 expansion | Tooling/data ready; Human gate pending | 3 video mới đã ingest, storyboard và tạo 790 giây annotation queue không chồng lặp. |
| RW-08 | Audit implementation complete; dataset blocked | Taxonomy được khóa; source/data gate chặn training chưa đủ bằng chứng. |
| RW-10 | Candidate benchmark complete; annotation gate pending | UFLDv2 tốt hơn YOLOP trên sample CPU nhưng chưa được promote. |
| RW-07 | Deferred hardware | Metric TTC bị khóa; không chặn RW-08/RW-10/RW-13/RW-14-AAOS. |
| RW-13 | ARM64 cloud package ready; remote test pending | Không khởi chạy AWS và không phát sinh chi phí. |
| RW-14 AAOS | Source/contract ready; Android sync/run pending | Warning-only WebView shell + mock VHAL read-only, không có vehicle control. |

## RW-05 — Ba video mới

| Source | Duration | Indexed 2 FPS | Selected | Queue coverage |
|---|---:|---:|---:|---:|
| `dashcam_vietnam_night.mp4` | 180.033 s | 361 | 180 | 180 s |
| `dashcam_vietnam_rain+night.mp4` | 111.667 s | 224 | 112 | 110 s |
| `dashcam_vietnam_traffic_multi.mp4` | 689.189 s | 1377 | 500 | 500 s |

Queue builder đã được sửa để không tạo nhiều cửa sổ 10 giây hơn thời lượng cho phép;
vì vậy `planned_coverage_seconds` không còn bị tính khống do overlap. Tổng cộng có
79 storyboard/cửa sổ và 790 giây candidate coverage. Tất cả vẫn là
`pending_human_review`, chưa đi vào release metric.

Smoke test 20 giây/video trên laptop AMD DirectML:

| Source | FPS | E2E P95 | Lane coverage | Pipeline error |
|---|---:|---:|---:|---|
| night | 3.47 | 167.15 ms | 5.63% | none |
| rain+night | 5.73 | 137.64 ms | 0% | none |
| traffic multi | 5.51 | 162.44 ms | 3.54% | none |

Các event smoke chỉ là prediction, không phải true positive. Không tính Recall/FAR cho
ba video trước khi queue được review exhaustive.

## RW-08 — Fallen Rider dataset gate

Taxonomy được chốt:

- specialist image classes: `fallen_person`, `fallen_two_wheeler`;
- temporal event: `fallen_rider`;
- states: normal → unstable → transition → persistent → recovered/left;
- hard negatives được định nghĩa riêng.

Source policy:

- D²-City: hard negatives/candidate mining only;
- A3D: quarantined đến khi license/schema chính thức được xác minh;
- CADP: CCTV temporal pretraining only;
- CARLA: synthetic supplement only;
- CCTV laying dataset cũ: pretraining only và vẫn fail duplicate/negative gate.

`evaluation/rw08_source_audit.json` xác nhận catalog pass nhưng training bị block cho
đến khi mỗi lớp có ít nhất 250 instance, negatives:positives >=2:1, adverse >=20%,
video-group split không leakage, license approved và có forward-dashcam test set.

## RW-10 — Lane instance/count

Đã tạo queue 400 frame:

- 100 night;
- 100 rain+night;
- 200 day/dense traffic.

Mỗi record có lane count, ego-boundary polylines, uncertain flag và model evidence
fields. Gate yêu cầu 300 verified frame, lane-count accuracy >=0.95, ego-boundary F1
>=0.90 và LDW FAR <=1/min.

Benchmark 41 timestamp trên CPU:

| Model | Usable coverage | Mean quality | P50 | P95 |
|---|---:|---:|---:|---:|
| YOLOP | 43.90% | 0.4772 | 196.82 ms | 241.03 ms |
| UFLDv2 | 63.41% | 0.4974 | 130.19 ms | 144.62 ms |

UFLDv2 chưa được promote vì chưa có ground truth và full-pipeline R1 benchmark. Lane
geometry đảo biên/negative width hiện bị reject hoàn toàn thay vì đưa sang LDW.

## RW-07 — Deferred hardware

`evaluation/rw07_status.json` đóng task cho milestone phần mềm hiện tại với
`metric_ttc_alerting_allowed=false`. RW-07 chỉ được mở lại khi có calibration từ camera
và mount cuối, measured-distance day/night và closed-course TTC evidence.

## RW-13 — ARM64 cloud candidate

Đã thêm:

- `Dockerfile.arm64-cloud`;
- `docker-compose.arm64-cloud.yml`;
- `configs/arm64_cloud_manifest.json`;
- `scripts/arm64_preflight.py`;
- `scripts/build_arm64_cloud.ps1`.

Compose schema parse thành công. Local preflight trả `not_on_target` vì laptop là AMD64
và không có T4G; đây là expected result. Chưa build/push/run EC2 nên không phát sinh
AWS cost. G5g chỉ được dùng làm ARM64 CUDA parity evidence, không làm Jetson FPS,
thermal, power, DLA hoặc JetPack evidence.

## RW-14 — Android Automotive

Project nằm tại `android/roadwatch-aaos`:

- Automotive-only manifest;
- landscape WebView tới `http://10.0.2.2:8000`;
- mock speed/gear telemetry read-only;
- `distractionOptimized=false`;
- không có quyền Bluetooth/CAN/vehicle control;
- cleartext chỉ là development policy cho emulator localhost.

Android Studio 2026.1 đã được phát hiện tại `D:/Android/Android Studio`. SDK folder hiện
chưa cung cấp platform/build-tools cho terminal và project chưa có generated wrapper
JAR, nên APK build/run cần Android Studio Sync. Frontend TypeScript compile pass và Vite
build pass bằng out-dir kiểm tra; `frontend/dist` chính đang bị tiến trình khác khóa nên
không bị ghi đè.

## CARLA / Unreal Engine

Không cần cài Unreal Engine để chạy CARLA packaged. Chỉ cài Unreal khi cần build CARLA
từ source hoặc tạo map/asset riêng. Với RX 6550M 4 GB, ưu tiên packaged CARLA low-quality
hoặc EC2 x86-64 sau này. G5g ARM64 không phải CARLA host mặc định phù hợp.

## Bước còn cần Human

1. Review 79 cửa sổ RW-05 mới; critical window cần reviewer thứ hai.
2. Annotate tối thiểu 300/400 lane frames hoặc chấp thuận AI-provisional rồi audit.
3. Cung cấp/duyệt license và positive Fallen Rider data trước khi RW-08 cho phép train.
4. Mở AAOS project trong Android Studio, Sync SDK/Gradle và chạy Automotive emulator.
5. Khi sẵn sàng trả chi phí AWS, chạy RW-13 preflight/build/regression trên G5g.
