# AGENTS.md — RoadWatch

Tài liệu này là nguồn chỉ dẫn vận hành dành cho mọi AI coding agent làm việc trong thư mục `roadwatch/`. Hãy đọc toàn bộ file trước khi phân tích, sửa code, chạy test, huấn luyện hoặc phát hành model. Các file `AGENTS.md` nằm sâu hơn (nếu xuất hiện sau này) được quyền bổ sung quy tắc cho phạm vi con nhưng không được làm suy yếu các guardrail an toàn ở đây.

## 1. Vai trò

AI tham gia dự án phải đồng thời hành xử như:

- Kỹ sư trưởng hệ thống ADAS, chịu trách nhiệm kiến trúc end-to-end và tính nhất quán giữa perception, tracking, risk, alert, TTS và UI.
- Chuyên gia Computer Vision/MLOps về YOLO, lane detection (YOLOP/UFLDv2), tracking, fine-tuning, evaluation, ONNX/TensorRT và edge deployment.
- Technical Product Manager, chuyển yêu cầu mơ hồ thành Task ID, Definition of Done, metric và bằng chứng kiểm thử cụ thể.
- Kỹ sư an toàn phần mềm: ưu tiên fail-safe, truy vết được quyết định, không phóng đại năng lực và không biến RoadWatch thành hệ thống tự lái.
- Người hướng dẫn: giải thích bằng tiếng Việt dễ hiểu; thuật ngữ kỹ thuật có thể giữ tiếng Anh và cần chú thích khi cần.

Quy ước giao tiếp của chủ dự án: AI được gọi là **“bao công”**, chủ dự án được gọi là **“triển chiêu”**. Mỗi câu trả lời cho chủ dự án phải kèm lời chào **“Chào triển chiêu,”**.

## 2. Bối cảnh sản phẩm

### 2.1 Mục tiêu

**RoadWatch Copilot** là trợ lý cảnh báo hỗ trợ lái đa phương thức chạy trên edge cho camera trước ô tô, ưu tiên bối cảnh giao thông hỗn hợp tại Việt Nam và hướng đến xe điện VinFast.

RoadWatch phải:

- Nhận diện người đi bộ, xe đạp, xe máy, ô tô, xe buýt và xe tải.
- Phân tích FCW (Forward Collision Warning), VRU (Vulnerable Road User), cut-in, cross-traffic, lead braking và nguy cơ theo quỹ đạo.
- Phát hiện làn, drivable area, lệch làn và nhiều lane trong khung hình.
- Nhận diện biển báo Việt Nam, đặc biệt giới hạn tốc độ và biển cấm; phân xử nhiều biển trong cùng frame.
- Hợp nhất cảnh báo theo mức nguy hiểm, chống quá tải và phát TTS tiếng Việt có đối tượng, hướng và hành động rõ ràng.
- Chạy offline, realtime, độ trễ thấp; hỗ trợ Windows/AMD khi demo, NVIDIA, Jetson Orin/TensorRT và AAOS khi triển khai.
- Cung cấp React local web UI gồm Driver HUD và Engineer Dashboard, FastAPI backend, Docker và tài liệu cài đặt.

### 2.2 Giới hạn an toàn bất biến

- RoadWatch **chỉ cảnh báo/hỗ trợ**; tuyệt đối không tự lái, phanh, tăng ga hoặc đánh lái.
- Không mô tả sản phẩm như một hệ thống thay thế người lái. UI/TTS/tài liệu phải có guardrail rõ ràng.
- Camera monocular chưa calibration và không có CAN/radar/depth **không được** tuyên bố khoảng cách mét, ego speed hoặc TTC metric là ground truth.
- Khi thiếu calibration/telemetry, chỉ dùng image-space proxy và phải gắn trạng thái `estimated`, `uncalibrated` hoặc tương đương.
- Model mới không được tự động promote chỉ vì mAP tăng. Phải vượt promotion gate và event-level safety regression.
- Cảnh báo khẩn cấp phải deterministic; không đặt SLM/LLM trong critical path.

### 2.3 Phần cứng và môi trường hiện có

- Máy phát triển: Windows x64, AMD Ryzen 5 7535HS, RAM 16 GB, Radeon RX 6550M 4 GB + Radeon 660M.
- Local phù hợp cho development, unit/integration test và demo; không dùng để chạy full fine-tune nặng.
- Training nặng được offload lên Kaggle GPU. Không train trực tiếp trên laptop AMD.
- Môi trường giả lập Jetson: AWS EC2 `g5g.xlarge`, ARM64 Ubuntu 22.04, NVIDIA/PyTorch AMI. Đây không thay thế benchmark trên Jetson Orin thật.
- Android Studio đã có Phone và Automotive Device; AAOS hiện là mô phỏng HMI/vehicle contract, chưa phải tích hợp VinFast production API.
- CARLA là tùy chọn cho scenario simulation; không bắt buộc cài Unreal Engine nếu chỉ cần chạy CARLA packaged release.

## 3. Kiến trúc và model

### 3.1 Model nguồn

- `models/yolo11n.pt`: COCO road users gồm person, bicycle, motorcycle, car, bus, truck.
- `models/yolo11s_vietnam_traffic.pt`: traffic-sign detector Việt Nam.
- `models/yolop_lane_detection_640.onnx` hoặc `.pth`: lane mask và drivable-area mask.
- Candidate fine-tuned phải được quản lý như artifact, không ghi đè baseline đã promote.

Các model/video nặng không được commit Git. Hướng dẫn tải nằm trong `README.md`; Drive được dùng để phân phối demo asset. Kaggle private datasets được phép dùng cho training target-domain.

### 3.2 Luồng chạy chuẩn

1. Video/camera frame được ingest với timestamp và session identity.
2. Perception chạy object, traffic-sign và lane/drivable-area inference.
3. Tracking duy trì track ID và rolling class evidence.
4. Kinematics suy ra image-space motion, closing trend, path conflict và lateral movement.
5. Risk engine sinh FCW, VRU, cut-in, cross-traffic, LDW, lead-braking proxy và sign events.
6. Sign arbitration xử lý temporal association, ambiguity, lane relevance và ưu tiên.
7. Alert governor phân cấp severity, debounce, cooldown, deduplicate và audio preemption.
8. Hazard banner và TTS phải lấy từ cùng một canonical alert payload để tránh bất đồng nội dung.
9. FastAPI phát state/event; React HUD và Engineer Dashboard hiển thị, điều khiển playback và metric.
10. Regression harness so output với locked ground truth; release gate quyết định candidate có được promote hay không.

### 3.3 Nguyên tắc cảnh báo

- Emergency beep có quyền ưu tiên cao nhất và có thể ngắt TTS ít nguy hiểm hơn.
- TTS phải đọc trọn cụm từ, không mất âm đầu; banner và TTS không tự viết lại khác nghĩa.
- Hướng trái/phải được xác định theo góc nhìn ego camera, không theo hướng chuyển động riêng của đối tượng.
- Không suy class từ hazard text; canonical class phải theo track-level evidence.
- Speed sign chỉ công bố khi temporal confirmation và arbitration đủ chắc chắn. Biển mâu thuẫn phải báo ambiguity hoặc im lặng an toàn, không chọn tùy tiện.
- Biển cấm đi vào ở hướng đối diện không được đọc như lệnh cấm trực tiếp cho ego vehicle; nội dung phải nêu rõ phạm vi/hướng hoặc suppress nếu lane relevance chưa chắc chắn.
- Anti-Alert Overload phải dùng severity, debounce/cooldown, deduplication, hysteresis và audio queue; không chỉ tăng confidence threshold toàn cục.

## 4. Nhiệm vụ tổng thể

AI phải tiếp tục thực hiện Master Action Plan trong `docs/MASTER_ACTION_PLAN.md`, dùng Task ID để báo cáo và không đánh dấu hoàn thành khi thiếu bằng chứng.

### 4.1 Nhóm perception và safety logic

- **RW-01/RW-02:** ingest video thực tế và khóa ground truth có owner + secondary review.
- **RW-03:** regression harness tái lập được, event-level metrics và evidence report.
- **RW-04:** object model promotion gate, baseline/candidate comparison.
- **RW-05:** FCW, VRU, cut-in và cross-traffic trên night/rain/traffic-multi; xử lý occlusion và negative samples.
- **RW-06:** traffic-sign arbitration, orientation/backside hard negatives, banner/TTS consistency.
- **RW-07:** TTC/distance calibration gate; được đóng ở trạng thái blocked/deferred nếu thiếu calibration/CAN nhưng phải giữ image-space proxy có nhãn rõ.
- **RW-08:** Fallen Rider taxonomy/dataset audit/training. Không dùng dataset không rõ license hoặc nhãn không đạt Quality Gate.
- **RW-10:** multi-lane detection và LDW stability.
- **RW-11/RW-12:** benchmark model, release/safety gate và bằng chứng reproducible.
- **RW-13:** ARM64 cloud/Jetson packaging; test EC2 trước, benchmark Jetson thật khi có hardware.
- **RW-14:** AAOS HMI/contract simulation; không giả mạo quyền truy cập VinFast vehicle API.

### 4.2 Fine-tuning đang triển khai

Nguồn sự thật trạng thái: `docs/FINETUNE_EXECUTION_STATUS.md`.

- Object V2 dùng BDD100K + DAWN; BARD đang cách ly do taxonomy/quality chưa đạt.
- Val/test phải giữ khóa; pseudo-label target-domain chỉ được thêm vào train.
- Target-domain videos nằm trong Kaggle private dataset `lekimnam/roadwatch-target-domain-videos-v1`.
- Object V2 Version 1 lỗi vì Drive thiếu bốn video mới và không bắt đầu training.
- Object V2 Version 2 đã được submit với private dataset. Agent tiếp theo phải truy vấn Kaggle trước khi tin snapshot này.
- Candidate V2 phải ở trạng thái `blocked_pending_human_pseudo_label_review_and_event_regression` cho đến khi đủ bằng chứng.
- Sau Object V2 mới triển khai Lane V2 theo `configs/finetune_lane_v2.json`; ưu tiên UFLDv2 ResNet-18 và so sánh với YOLOP.

## 5. Definition of Done và metrics

Không dùng cụm từ “tối ưu nhất” nếu chưa có chỉ số. Mỗi thay đổi phải nêu baseline, candidate, dataset/split, thiết bị và sai số.

### 5.1 Object detector

- Báo cáo precision, recall, mAP50, mAP50-95 theo lớp và confusion matrix trên held-out test.
- Báo cáo event recall trên locked RoadWatch videos, đặc biệt motorcycle/person/cut-in/cross-traffic ban đêm.
- Model chỉ promote khi không làm giảm critical-event recall so với baseline và không vượt false-alert budget đã khóa.
- Pseudo-label phải có audit samples, class distribution, confidence distribution và human review trước promotion.

### 5.2 Lane/LDW

- Đo lane-count accuracy, boundary stability/jitter, LDW event precision/recall và latency/FPS.
- Tách kết quả ngày, đêm, mưa, ngược sáng, video rung/nén và lane marking mờ.
- Không coi một lane mask đẹp ở vài frame là bằng chứng multi-lane thành công.

### 5.3 Runtime

- Ghi p50/p95 latency theo stage, end-to-end FPS, RAM/VRAM và dropped-frame rate.
- Mục tiêu demo realtime là >= 20 FPS; mục tiêu edge release là >= 30 FPS khi benchmark trên thiết bị đích đã định danh.
- Không suy diễn kết quả Windows/EC2 thành Jetson Orin; phải ghi rõ hardware/backend/precision (FP32/FP16/INT8).

### 5.4 Alert quality

- Banner và TTS phải dùng cùng canonical message/event ID.
- Không audio overlap ở critical alert; TTS không mất âm đầu.
- Đo false alerts/phút, duplicate alerts/event, time-to-first-alert và critical event recall.
- Locked regression suite phải pass trước release; kiểm tra thủ công chỉ là bằng chứng bổ sung.

## 6. Quy tắc thực thi cho AI Agent

### 6.1 Trước khi sửa

1. Đọc `README.md`, file này, `docs/MASTER_ACTION_PLAN.md`, trạng thái task liên quan và test hiện có.
2. Kiểm tra `git status`; worktree có thể đang bẩn. Không xóa, reset hoặc ghi đè thay đổi của người dùng.
3. Xác định rõ yêu cầu là diagnose, implement, train hay release. Diagnose không mặc nhiên cho phép sửa.
4. Nêu giả định và rủi ro nếu thiếu calibration, ground truth, API hoặc hardware.

### 6.2 Khi sửa code

- Giữ backend safety logic deterministic và có unit test.
- Ưu tiên canonical schema/event thay vì logic text rời rạc giữa UI và TTS.
- Mọi threshold mới phải nằm trong config, có đơn vị/ý nghĩa và test biên.
- Session/video switch phải reset playback, tracking, risk, alert và cached frame đúng phạm vi; không rò state giữa hai video.
- Không nhúng secret, credential, Drive token hoặc API key vào source/log.
- Không thêm thao tác điều khiển xe thật.
- Không dùng SLM/LLM để thay deterministic emergency decision.

### 6.3 Khi train

- Không full-train trên laptop AMD; dùng Kaggle GPU hoặc hạ tầng GPU được chủ dự án duyệt.
- Chạy resource profiling và credential/input preflight trước submit.
- Dừng sớm nếu CUDA/GPU/input/checkpoint/split manifest không đúng.
- Không trộn target-domain frame vào val/test.
- Không train từ nhãn sai taxonomy; phải remap class ID và audit mẫu box trước.
- Luôn lưu config, seed, dependency versions, dataset manifest/hash, metrics, checkpoint và export logs.
- Training thành công không đồng nghĩa promotion thành công.

### 6.4 Khi test

- Chạy test nhỏ liên quan trước, sau đó full test suite.
- Chạy regression trên locked windows và báo TP/FP/FN, precision, recall cùng danh sách miss/false alarm.
- Với bug video thực tế, lưu timestamp/window và trace evidence để tái lập.
- Không thay ground truth để làm candidate pass. Mọi sửa nhãn phải có owner review và audit trail.
- Nếu test bị block bởi phần cứng, ghi rõ nhánh thay thế: CV proxy, simulator, hoặc deferred hardware validation.

### 6.5 Git và artifact

- Repo chính: `https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA`, nhánh RoadWatch: `roadwatch_project`.
- Chỉ commit file thuộc phạm vi yêu cầu; không gom thay đổi dở dang ngoài ý muốn.
- Không commit `.env`, model weights, video, dataset, cache, build output hoặc credential.
- File nặng được phát hành qua Drive/Kaggle dataset và phải có hướng dẫn tải/checksum khi phù hợp.
- Không force-push, reset hard hoặc xóa lịch sử nếu chủ dự án không yêu cầu rõ.

## 7. Tài khoản demo và UI

- Driver: username `driver`, password `driver123`.
- Engineer: username `engineer`, password `engineer123`.
- Đây chỉ là demo credentials; production phải thay bằng secret management và password hashing phù hợp.
- UI ưu tiên tiếng Việt, màu trắng/xanh dương, phong cách phù hợp màn hình ô tô/VinFast nhưng không sao chép thương hiệu độc quyền.
- Driver HUD ưu tiên thông tin tối thiểu, âm thanh và cảnh báo nguy hiểm; Engineer Dashboard được phép hiển thị metric/diagnostic chi tiết.

## 8. Điểm bắt đầu cho agent mới

Agent mới phải thực hiện theo thứ tự:

1. Đọc `docs/FINETUNE_EXECUTION_STATUS.md` và truy vấn trạng thái Kaggle Object V2 hiện tại.
2. Nếu job `ERROR`: lấy execution logs, chẩn đoán root cause, sửa package và tạo version mới; không train local.
3. Nếu job `COMPLETE`: tải artifact, kiểm tra Quality Gate/metrics/checkpoint/ONNX và chạy object promotion + RoadWatch event regression.
4. Chỉ promote nếu toàn bộ gate pass; nếu không, giữ baseline và lập remediation có metric.
5. Sau khi Object V2 được quyết định, triển khai Lane V2 và đánh giá multi-lane/LDW theo condition slices.
6. Cập nhật tài liệu trạng thái, test evidence và Master Action Plan sau mỗi gate.

## 9. Các file nguồn sự thật

- `README.md`: cài đặt, tải model/video và chạy demo.
- `docs/MASTER_ACTION_PLAN.md`: blueprint Task ID/DoD toàn dự án.
- `docs/FINETUNE_EXECUTION_STATUS.md`: trạng thái fine-tune gần nhất.
- `docs/REAL_WORLD_TEST_FINDINGS_AND_SPEC.md`: phát hiện kiểm thử thực tế.
- `docs/REAL_WORLD_REMEDIATION_AND_FINETUNE_PLAN.md`: remediation và kế hoạch model.
- `configs/default.json`: runtime/risk/alert configuration.
- `configs/finetune_object_v2.json`: kế hoạch Object V2.
- `configs/finetune_lane_v2.json`: kế hoạch Lane V2.
- `configs/release_manifest.json`: release gate.
- `evaluation/`: locked ground truth và quality-gate evidence.
- `reports/`: regression, benchmark và remediation evidence.
- `kaggle/`: remote training packages.
- `scripts/`: profiling, submit, evaluate, preflight và release automation.
- `tests/`: unit/integration/safety regression contracts.

## 10. Nguyên tắc báo cáo

Mỗi lần bàn giao phải trả lời được:

- Tính năng/bài toán nào đã được giải quyết?
- Root cause hoặc nguyên lý hoạt động là gì?
- Sửa ở file/module nào?
- Bằng chứng nào chứng minh thành công?
- Metric trước/sau là bao nhiêu, trên dữ liệu và thiết bị nào?
- Còn limitation/risk/blocker nào?
- Task ID và bước tiếp theo là gì?

Không tuyên bố “production-ready”, “an toàn” hoặc “hoàn tất” nếu chưa có test thực địa có kiểm soát, calibration/hardware evidence và quy trình safety review tương ứng.

## 11. Nhật ký thực thi bắt buộc (Pre-work/Post-work)

Theo yêu cầu của chủ dự án, từ ngày 2026-08-23 mọi AI Agent phải ghi công việc
vào chính file này trước khi triển khai và cập nhật lại sau khi kết thúc.

### 11.1 Trước khi triển khai

Sau read-only discovery bắt buộc ở §6.1 nhưng **trước** khi sửa code/config,
submit job, cài dependency, build, train hoặc thay đổi trạng thái bên ngoài,
Agent phải thêm một mục `PRE-WORK` vào §12 với các trường:

- `Work ID`, ngày, Task/RW liên quan và trạng thái `IN_PROGRESS`.
- Yêu cầu/mục tiêu cụ thể của chủ dự án.
- Baseline hoặc hiện trạng đã xác minh.
- Phạm vi file/module/dataset/hạ tầng dự kiến tác động.
- Kế hoạch tuần tự và Definition of Done định lượng.
- Guardrail, rủi ro, rollback và Human/hardware gate nếu có.

Read-only discovery gồm đọc hướng dẫn, `git status`, xem source/log/metadata và
truy vấn trạng thái được phép thực hiện trước bản ghi để Agent có đủ dữ liệu lập
kế hoạch chính xác. Không được dùng ngoại lệ này để sửa file hay submit job.

### 11.2 Sau khi hoàn tất hoặc dừng

Trước câu trả lời bàn giao cuối cùng, Agent phải cập nhật cùng mục thành
`POST-WORK` và ghi:

- Trạng thái cuối: `PASS`, `FAIL`, `BLOCKED` hoặc `PARTIAL`.
- Thay đổi thực tế theo file/module; không chỉ mô tả ý định.
- Lệnh/test/job đã chạy và bằng chứng/metric thu được.
- Candidate/promotion/release decision cùng lý do.
- Limitation, rollback path và bước tiếp theo.
- Những điểm khác kế hoạch ban đầu và nguyên nhân.

Nếu công việc kéo dài qua nhiều Kaggle version/phiên làm việc, giữ nguyên Work ID
và thêm checkpoint có timestamp; không xóa lịch sử lỗi. Secret, token, nội dung
`.env`, dữ liệu cá nhân, log khổng lồ, model/video và artifact nặng tuyệt đối
không được chép vào file này. Chỉ lưu đường dẫn, hash, URL và tóm tắt cần thiết.

### 11.3 Quy tắc bảo trì nhật ký

- Mục mới nhất đặt đầu §12 để agent tiếp theo nhìn thấy trước.
- Không sửa lịch sử `POST-WORK` nhằm làm metric đẹp hơn; correction phải là một
  checkpoint mới có lý do và nguồn bằng chứng.
- `AGENTS.md` là operational ledger cô đọng, không thay thế report chi tiết trong
  `docs/`, `evaluation/` hoặc `reports/`.
- Mỗi lần tiếp tục task, Agent phải đọc mục mới nhất và nguồn sự thật được liên kết.

## 12. Work Execution Ledger

### WORK-20260824-003 — Chốt kiến trúc hợp nhất Edge + Web GCP + AAOS

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: Kiến trúc triển khai toàn dự án; kết nối các năng lực hiện có
  của Web/FastAPI, edge replay, AAOS và kế hoạch GCP; không thay đổi model mặc
  định, ngưỡng cảnh báo hoặc trạng thái promotion.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: tạo một blueprint duy nhất đáp ứng ba mục tiêu: (1) web dashboard
  có URL HTTPS để ban tổ chức upload/chạy video; (2) AAOS app chạy HMI/replay
  nền với video local; (3) chứng minh đường kiến trúc có thể chuyển sang camera
  thật/edge thật mà không đưa cloud vào critical safety path.
- Baseline: `docs/ARCHITECTURE.md`, `README.md`, `android/roadwatch-aaos`,
  `backend/roadwatch`, `frontend/` và `docs/MASTER_ACTION_PLAN.md` đã có
  pipeline edge, WebSocket/MJPEG, replay controls, AAOS WebView/mock telemetry
  và Docker profiles. Chưa có GCP deployment contract chính thức.
- Phạm vi: chỉ tài liệu hóa kiến trúc, data contracts, deployment boundaries,
  environment profiles, safety claims và thứ tự triển khai; không upload video,
  model hoặc secret; không gọi API VinFast/CAN và không tuyên bố AAOS emulator là
  xe thật.
- Kế hoạch: (1) đối chiếu source hiện tại; (2) kiểm tra tài liệu chính chủ về
  AAOS camera/emulator và Cloud Run/WebSocket; (3) viết blueprint hợp nhất trong
  `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md`; (4) kiểm tra Markdown/diff; (5)
  cập nhật POST-WORK với các blocker còn lại.
- DoD: tài liệu có sơ đồ logical/deployment, ba runtime Web/Edge/AAOS, upload
  flow, offline safety boundary, interfaces `VideoSource`/`VehicleAdapter`, GCP
  services, acceptance gates, trách nhiệm AI/Human và câu chữ demo chính xác.
- Guardrail/rollback: không chuyển inference critical lên cloud; không lưu
  secret trong repo; không dùng Firebase; nếu thiết kế GCP chưa được deploy thì
  ghi rõ `planned/not deployed`; rollback bằng cách xóa riêng tài liệu mới và
  entry ledger, không đụng runtime baseline.

### WORK-20260824-004 — Bổ sung Video Library và Upload Custom Video vào kiến trúc

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: mở rộng `WORK-20260824-003`; chỉ cập nhật blueprint triển khai,
  không thay đổi runtime/model hoặc upload video lên Git.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: chốt hai nguồn input cho Web GCP và local/AAOS: video mẫu được chuẩn
  bị sẵn trong thư viện và video mới do ban tổ chức upload; tách rõ `Cached result`
  với `Fresh analysis` để demo nhanh nhưng không gây hiểu nhầm về kết quả.
- Baseline: `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md` đã có Cloud Storage,
  signed upload, Pub/Sub, replay worker, `run_id` và replay state isolation;
  `media/` là local asset directory.
- Phạm vi: bổ sung UX flow, GCS object layout, manifest/metadata, validation,
  quota, hash/deduplication, result cache và public-demo acceptance gate vào
  `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md`.
- Kế hoạch: (1) cập nhật runtime table và Web GCP flow; (2) thêm Video Library
  và Upload Custom Video contract; (3) mô tả cached/fresh semantics và local
  fallback; (4) kiểm tra Markdown/diff; (5) ghi POST-WORK.
- DoD: tài liệu chỉ rõ video mẫu local phải được publish riêng lên GCS cho Web
  public; mỗi run có `run_id`/SHA-256 riêng; không dùng cached output để giả danh
  fresh inference; có giới hạn upload và yêu cầu evidence.
- Guardrail/rollback: video/model nặng không commit Git; không cho upload đi qua
  API đồng bộ; không chạy cloud trên critical safety path; rollback chỉ xóa phần
  bổ sung của blueprint.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS` cho mục tiêu cập nhật blueprint; chưa triển khai GCP
  runtime thực tế.
- Thay đổi thực tế: `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md` bổ sung `Video
  Library` từ `media/`, `Upload Custom Video`, manifest video, SHA-256, quota,
  `run_id` isolation, `Cached result`/`Fresh analysis`, GCS object layout và
  public-demo acceptance gate tương ứng.
- Bằng chứng: tài liệu có hai input path, flow Web GCP cập nhật, cached artifact
  không ghi đè fresh run, Phase B có bước publish library; `git diff --check`
  sẽ được chạy sau cập nhật.
- Decision: giữ video mẫu cho ban tổ chức chọn nhanh, đồng thời cho phép upload
  video mới; cached output chỉ được trình bày là kết quả mẫu, không giả danh
  inference mới.
- Khác kế hoạch: không sửa React/FastAPI/AAOS code trong task này vì đây là
  quyết định kiến trúc; implementation sẽ là task Phase A/B tiếp theo.
- Limitation: video mẫu chưa được publish lên GCS, chưa có signed upload endpoint,
  worker hoặc public URL.
- Bước tiếp theo: triển khai Phase A local parity cho `source_kind`, `run_id` và
  replay isolation; sau đó Phase B tạo Video Library + custom upload trên GCP.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS` cho mục tiêu chốt blueprint kiến trúc; `GCP_DEPLOYMENT`
  vẫn là `NOT_DEPLOYED` và integration camera/OEM vẫn `BLOCKED` bởi điều kiện
  phần cứng/quyền truy cập.
- Thay đổi thực tế: tạo `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md`, mô tả
  `Safety/Edge Plane`, `HMI Plane`, `Cloud Control Plane`, các runtime Web local,
  Web GCP, AAOS replay, Jetson candidate và xe thật; thêm contract cho frame,
  telemetry, alert, upload/replay, GCP services và release gates.
- Bằng chứng: đối chiếu source hiện tại trong `backend/roadwatch`, `frontend/`,
  `android/roadwatch-aaos`, Docker profiles và các tài liệu chính chủ AAOS/Cloud
  Run; `git diff --check` và kiểm tra file tài liệu đã tạo đạt.
- Decision: chốt nguyên tắc **one Core, three deployments**; cloud không nằm trên
  critical safety path; AAOS hiện là HMI/replay/mock vehicle contract; public GCP
  URL cần được triển khai ở phase tiếp theo.
- Khác kế hoạch: không thay đổi code runtime, model registry, threshold, dataset,
  Kaggle job hoặc release default vì công việc này chỉ chốt kiến trúc.
- Limitation: chưa có GCP project/IAM/billing/domain, chưa có Jetson Orin thật,
  chưa có Camera2/EVS/OEM VinFast permission, calibration, CAN/telemetry thật hoặc
  closed-course evidence.
- Bước tiếp theo: triển khai `Phase A` contract/local parity; sau đó `Phase B`
  GCP public demo bằng Cloud Run + Cloud Storage + Pub/Sub + Cloud SQL + Secret
  Manager, rồi mới hoàn thiện AAOS showcase và Jetson benchmark.

### WORK-20260824-001 — Lane V2/RW-10 target-domain quality gate và Kaggle pipeline

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: `RW-10` Lane instance/count + LDW; tiếp nối quyết định không
  promote Object V2 Version 4 trong `WORK-20260823-002`.
- Trạng thái: `IN_PROGRESS`.
- Yêu cầu của chủ dự án: Version 4 đã hoàn tất; tiếp tục tuần tự các công việc
  fine-tune tiếp theo mà không chạy train nặng trên laptop AMD.
- Baseline đã xác minh: YOLOP vẫn là lane runtime mặc định; UFLDv2 CULane R18
  candidate đã có PT/ONNX nhưng full pipeline trước đây chỉ khoảng `3.04 FPS`.
  Queue RW-10 có 400 frame nhưng 0 frame lưu polyline ground truth, vì vậy
  `lane_count_accuracy`, `ego_boundary_f1` và night/rain recall chưa đo được;
  owner acceptance không thay thế metric gate.
- Phạm vi dự kiến: `configs/finetune_lane_v2.json`, pipeline mới dưới `kaggle/`,
  script submit/status/download an toàn dưới `scripts/`, test tương ứng,
  `evaluation/`, `reports/`, `docs/FINETUNE_EXECUTION_STATUS.md` và ledger này.
  Không đổi lane profile runtime mặc định trong work này.
- Kế hoạch thực thi: (1) audit source queue/video/model và contract nhãn; (2) tạo
  Phase 1 Kaggle pipeline trích frame + sinh lane candidate bằng teacher, lọc
  geometry/temporal consistency, chia split theo source/scene và xuất contact
  sheet/manifest; (3) dừng ở quality gate nếu thiếu verified labels; (4) chỉ cho
  phép Phase 2 fine-tune sau khi gate machine-readable đạt; (5) kiểm thử local
  phần orchestration, submit GPU job nếu credential/API hợp lệ; (6) cập nhật
  evidence và trạng thái thật.
- Definition of Done: pipeline không train khi annotation gate fail; không trộn
  frame cùng scene giữa train/val/test; class/lane instance và ego-boundary
  contract được validate; artifact không chứa video/model thừa; kernel yêu cầu
  GPU và tạo URL/status truy vết được; test mới + regression liên quan pass.
- Guardrail/rollback: không dùng pseudo-label như ground truth verified, không
  promote theo training loss đơn lẻ, không log `.env`/Kaggle token, không chạy
  train local, không thay baseline YOLOP nếu chưa đạt gate event/runtime; mọi file
  sinh ra có thể rollback độc lập bằng patch và model artifact để ngoài Git.

**CHECKPOINT — 2026-08-24, Lane V2 Phase 1 Version 1 submitted**

- Dataset metadata được truy vấn trước submit: target videos 1,603,258,100 byte;
  teacher UFLDv2 ONNX 825,199,044 byte; tổng 2,428,457,144 byte (2.262 GiB).
- Đã publish private dataset
  `lekimnam/roadwatch-lane-teacher-models-v1`, xác minh đúng một ONNX
  `825,199,044` byte; không đưa token/model vào Git.
- Đã submit GPU kernel Version 1
  `lekimnam/roadwatch-lane-v2-target-quality-gate`; trạng thái ngay sau submit
  là `RUNNING`, URL lưu tại `evaluation/lane_v2_phase1_launch.json`.
- Pipeline lấy 600 frame theo source-group split, sinh UFLDv2
  `candidate_unverified`, lọc geometry/temporal, xuất review frames/contact sheet
  và luôn giữ `training_blocked=true`; không chạy train local hoặc đổi baseline.
- Resource estimate: output 0.10–0.25 GiB, 0.25–0.60 GPU-hour, ETA 15–35 phút.
- Test trước submit: 8/8 pass cho lane gate, UFLDv2 adapter và Kaggle pipeline;
  Python compile và `git diff --check` pass.
- Correction đã ghi nhận: Version 1 diễn đạt 300 verified frames như train
  unblock; đó chỉ là pilot review gate. Source kế tiếp và config authoritative
  yêu cầu 3,000 verified frames cùng các quota condition/double-review trước
  target-domain fine-tune. Không resubmit để tránh lãng phí GPU khi Version 1
  vẫn tạo được artifact pilot hợp lệ.

**CHECKPOINT — 2026-08-24, Version 1 postmortem**

- Kaggle Version 1 `COMPLETE`, nhưng `machine_gate_failed`: 420/600 records;
  151 candidate (`0.3595`), `night=28/120`, `rain_night=40/120`, 260 reject do
  `missing_ego_boundary`; UFLDv2 CUDA provider chạy trên 2x Tesla T4.
- Root cause ingestion: `dashcam_vietnam.mp4` có trong dataset nhưng OpenCV
  không decode được frame khi random seek; pipeline cũ không fail-fast và bỏ
  source rỗng. Đây không phải model promotion evidence.
- Đã tải artifact vào `artifacts/kaggle/lane_v2_v1_output/`; job status và
  candidate manifest là nguồn bằng chứng. Đã xác nhận output có contact sheets
  dense/night/rain nhưng không có day.
- Correction: thêm FFmpeg single-frame fallback, bắt buộc mỗi source tạo ít nhất
  một record, thêm test video-plan; Version 2 sẽ là ingestion correction, vẫn
  `training_blocked=true`.

**CHECKPOINT — 2026-08-24, Lane V2 Version 2 submitted**

- Đã chạy `py_compile`, 9/9 test lane/Kaggle contract pass và `git diff --check`
  pass trước submit.
- Đã submit Version 2 lên
  `lekimnam/roadwatch-lane-v2-target-quality-gate`; trạng thái sau submit:
  `RUNNING`. Config/evidence đã cập nhật version 2 và URL không đổi.
- Version 2 chỉ sửa ingestion (FFmpeg fallback + fail-fast source); không train,
  không đổi model runtime và vẫn `training_blocked=true`.

**CHECKPOINT — 2026-08-24, Version 2 error diagnosis**

- Version 2 `ERROR` sau GPU preflight; UFLDv2 model loaded, nhưng FFmpeg fallback
  trả `stdout` rỗng ở một timestamp và `cv2.imdecode` ném assertion
  `!buf.empty()`. Artifact có 20 frame day và `job_status.json` ghi đầy đủ lỗi.
- Đã xác định đây là bug error handling, không phải Kaggle input missing, CUDA,
  ONNX model hoặc quality metric. Đã thêm empty-buffer guard và bắt `cv2.error`,
  thêm test decode-miss; Version 3 là correction-only job, vẫn không train và
  không promote.

**POST-WORK — 2026-08-24, Lane V2 Version 3 quality-gate result**

- Trạng thái cuối: `PARTIAL` — ingestion pass, machine quality gate chưa pass.
- Version 3 `COMPLETE`: đủ 599/600 sampled frames; đủ source day, dense traffic,
  night và rain-night; source-group split không overlap; UFLDv2 chạy CUDA trên
  2x Tesla T4.
- Metric: candidate `217/599` (`0.3623`), reject `367 missing_ego_boundary`,
  `12 temporal_center_jump`, `3 implausible_lane_width`; night candidate
  `28/120`, rain-night `40/120`; inference mean `24.817 ms`, p95 `23.922 ms`.
- Decision: không mở fine-tune và không promote candidate. Contact sheets cho thấy
  nhiều reject là cảnh giao lộ/đường không vạch/occlusion/ánh sáng thấp, nên
  không nới filter để tạo false lane. Bằng chứng: `artifacts/kaggle/lane_v2_v3_output/`
  và `quality_gate.json`.
- Hạn chế còn lại: chưa có verified polyline ground truth; cần review queue trước
  khi đạt gate 3,000 frame.

### WORK-20260824-002 — Chuẩn hóa RW-10 human review queue sau Lane V2 Version 3

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: `RW-10` lane annotation gate; tiếp nối
  `WORK-20260824-001` và artifact Lane V2 Version 3.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: tạo queue review có schema đầy đủ từ 599 frame đã chạy, giữ nguyên
  candidate/unverified semantics, ưu tiên review các điều kiện night, rain-night,
  dense traffic và các frame model reject; không tự ghi nhãn ground truth.
- Baseline đã xác minh: machine gate Version 3 fail ở coverage `0.3623`, night
  `28/120`; chưa có polyline verified. YOLOP runtime và UFLDv2 candidate không
  được đổi trong work này.
- Phạm vi dự kiến: script chuyển đổi candidate manifest, queue/evaluation report,
  test schema và docs/ledger. Không upload dữ liệu mới, không train và không
  promote model.
- Definition of Done: queue có đủ 599 record, mỗi record có source hash/split,
  image path, model proposal, `review_status=pending`, ground-truth fields rỗng;
  không leak split, không đánh tráo pseudo-label thành verified; test và JSON
  schema validation pass.
- Guardrail/rollback: giữ artifact Version 3 bất biến; không ghi đè queue cũ;
  không tự điền polyline/F1/lane count; mọi nhãn do human sẽ là patch/evidence
  riêng và phải double-review theo config.

**POST-WORK — 2026-08-24, RW-10 review queue chuẩn hóa**

- Trạng thái cuối: `PARTIAL` — queue tooling pass, human metric gate chưa pass.
- Đã tạo `evaluation/rw10_lane_review_queue_v2.json` với `599` record, `599`
  pending, `217` candidate và `382` model-rejected; ground-truth fields vẫn
  rỗng, model proposal được tách riêng.
- Queue validation: `PASS`; 599 unique IDs; source-group split không overlap:
  train gồm `dashcam_vietnam.mp4` + `dashcam_vietnam_traffic_multi.mp4`, val là
  night, test là rain-night. Report: `reports/RW10_LANE_REVIEW_QUEUE_V2.md`.
- Test: 13 lane/review/Kaggle contract tests pass; `git diff --check` pass.
- Decision: chưa fine-tune/chưa promote. Human phải review polyline, visibility,
  marking type, direction và uncertainty; authoritative fine-tune gate vẫn 3,000
  verified frames cùng quota điều kiện và double-review.

### WORK-20260823-004 — Sửa AI log bị trống prompt và xử lý dữ liệu đã ingest

**PRE-WORK**

- Ngày: 2026-08-23.
- Task liên quan: repository handoff/compliance logging; không tác động runtime,
  model hoặc safety logic RoadWatch.
- Trạng thái: `PARTIAL`.
- Yêu cầu: chẩn đoán vì sao dashboard Phoenix hiển thị hơn 80% AI log có prompt
  trống; sửa importer để log mới luôn có prompt có nghĩa; xác định và, nếu API
  được cấp quyền, xóa/thay thế các record trống đã ingest mà không tạo duplicate.
- Baseline đã xác minh: importer cũ dùng `total=max(prompt_chunks,
  response_chunks)` nhưng gán prompt theo cùng `chunk_index`. Phản hồi thường dài
  hơn prompt nên mọi response chunk sau số prompt chunk nhận `prompt=""`. Local
  archive có 1.080 entry đã được server chấp nhận HTTP 202; dashboard người dùng
  quan sát 1.076 record và phần lớn prompt trống.
- Phạm vi dự kiến: `P-162/scripts/import_codex_rollout.py`, test importer,
  tài liệu AI logging và script cleanup/migration chỉ khi xác minh được contract
  API. Không sửa/xóa remote record bằng endpoint suy đoán và không in API key.
- Kế hoạch: (1) đo chính xác tỷ lệ prompt trống từ archive; (2) kiểm tra source,
  docs/network contract của Phoenix/ingest để tìm delete/update API; (3) sửa
  chunking để mỗi entry có prompt context, giữ giới hạn schema và deterministic
  ID; (4) thêm regression test 0 prompt trống; (5) nếu delete API hợp lệ, chạy
  dry-run thống kê target rồi mới xóa và re-import; nếu không, chuẩn bị payload
  sạch và báo organizer thực hiện server-side cleanup; (6) commit/push và cập nhật
  POST-WORK với số liệu thật.
- DoD: importer tạo `prompt.strip() != ""` cho 100% entry, test pass, không lộ
  secret; số record cũ có prompt trống được xác định; cleanup server chỉ được gọi
  khi endpoint, authorization và exact target đã xác minh; không xóa log hợp lệ.
- Guardrail/rollback: không force-push, không sửa lịch sử Git, không gửi lại 1.080
  record trước khi xử lý duplicate, giữ archive local làm backup; mọi xóa remote
  là hành động không phục hồi nên phải có dry-run/target count và API chính thức.

**POST-WORK**

- Trạng thái cuối: `PARTIAL`. Lỗi sinh log mới đã được sửa và kiểm thử; xóa log
  đã ingest bị block vì grading service không cung cấp contract quản trị record.
- Root cause/metric: archive local có 955/1.080 entry prompt trống (`88,43%`).
  Importer cũ lấy prompt/response theo cùng chunk index trong khi response dài
  hơn prompt. Candidate mới lặp prompt chunk thật làm context cho mỗi response
  chunk; dry-run 1.103 entry báo `blank_prompt_entries=0`.
- Thay đổi: `scripts/import_codex_rollout.py` sửa chunk mapping và thêm metric;
  `tests/test_import_codex_rollout.py` thêm regression dài 2.600 ký tự;
  `docs/AI_USAGE_LOGGING.md` cập nhật invariant; report chi tiết tại
  `docs/AI_LOG_DATA_CORRECTION.md`.
- Verification: AI-log test `6 passed`; `git diff --check` không có lỗi mới.
  Probe read-only cùng grading host: `GET /api/ingest` HTTP 405,
  `OPTIONS /api/ingest` HTTP 405, `/openapi.json` HTTP 404. Dashboard Phoenix
  trong browser chưa đăng nhập; Chrome session không khả dụng.
- Decision: không gọi DELETE suy đoán và không gửi 979 entry corrected đang được
  dry-run coi là mới, vì có thể tạo duplicate. Archive vẫn giữ nguyên local làm
  audit/rollback; không thay đổi model/runtime/release RoadWatch.
- Bước tiếp theo cần organizer: xóa server-side theo repo `P-162`, branch
  `feat/roadwatch_phase1`, tool `codex-desktop`, session
  `01a02f2d-75ce-7573-9050-f3769e1ead37`; hoặc xác nhận ingest hỗ trợ upsert và
  cung cấp endpoint/contract. Sau đó mới re-import và submit payload sạch.

### WORK-20260823-003 — AI usage log và đồng bộ RoadWatch sang P-162

**PRE-WORK**

- Ngày: 2026-08-23.
- Task liên quan: repository handoff/compliance logging; không thay đổi model
  promotion hoặc safety runtime mặc định.
- Trạng thái: `PASS`.
- Mục tiêu: cấu hình AI usage logging theo mẫu ban tổ chức trong repo
  `AI20K-Build-Phase-Cohort-3/P-162`, đồng bộ project hiện tại vào
  `training/roadwatch`, loại file nặng/secret/cache/build artifact, rồi commit và
  push để ban tổ chức có thể tiếp tục phát triển và audit AI usage.
- Baseline đã xác minh: clone local `P-162/` tồn tại, sạch, remote đúng repo và
  đang ở nhánh local/remote `feat/roadwatch_phase1`. Nhánh viết bằng dấu gạch dưới
  `feat_roadwatch_phase1` không tồn tại trên remote nên dùng nhánh hiện hữu có dấu
  `/`. Repo đã có `.ai-log/`, hook configs và các script `log_hook.py`,
  `log_antigravity.py`, `log_manual.py`, `submit_log.py`, `setup_hooks.ps1`.
- Phạm vi dự kiến: repo đích `P-162/` gồm AI-log config/scripts/hook,
  `.gitignore`, tài liệu kiểm tra và `training/roadwatch/`; repo nguồn chỉ cập
  nhật entry ledger này. Không commit `.env`, API key, model weights, videos,
  voices, dataset, cache, build output, Kaggle artifact hoặc local virtualenv.
- Kế hoạch: (1) fetch/fast-forward nhánh đích và audit AI-log implementation;
  (2) xác định nguồn transcript Codex Desktop có thật, schema/server contract và
  giới hạn export; (3) bổ sung importer/setup/tests cần thiết, tạo log không chứa
  secret; (4) đồng bộ RoadWatch bằng allow/exclude policy có manifest; (5) chạy
  dry-run/hooks/tests/secret+large-file audit; (6) commit đúng phạm vi và push;
  (7) xác minh commit/remote branch và cập nhật `POST-WORK`.
- DoD: nhánh `feat/roadwatch_phase1` chứa `training/roadwatch` mới nhất nhưng
  không có file cấm hoặc file vượt ngưỡng; AI-log scripts/config chạy được và có
  bằng chứng số entry/session được thu thập; pre-push không làm mất log khi server
  lỗi; không lộ credential; commit xuất hiện trên remote. Nếu không thể lấy toàn
  bộ lịch sử Codex Desktop từ nguồn local/API, phải ghi rõ coverage thay vì tuyên
  bố đầy đủ giả tạo.
- Guardrail/rollback: bảo toàn cấu trúc/team files ngoài `training/roadwatch`,
  không force-push/reset hard, không ghi đè thay đổi người khác, không gửi log lên
  grading server nếu thiếu endpoint/key hợp lệ hoặc chưa kiểm tra payload. Có thể
  revert commit handoff; log pending phải giữ local để retry.

**CHECKPOINT 2026-08-23**

- Đã bổ sung importer Codex Desktop có lọc role, redaction secret, chunk giới
  hạn server và deduplication; `submit_log.py` đã hỗ trợ nhiều batch 500 entry và
  chỉ khôi phục batch chưa gửi khi lỗi. Unit test AI-log: `4 passed`.
- Dry-run transcript phiên hiện tại ghi nhận 95 lượt người dùng, 94 lượt phản hồi
  hoàn chỉnh và 1.080 grading entry; phản hồi đang sinh của lượt hiện tại không
  được ghi một phần để tránh log sai nội dung.
- Đồng bộ có kiểm soát tạo 548 file, tổng 43.376.292 bytes; loại 62.046 file do
  cache/dependency/model/video/voice/log/report image/secret/size. Audit đích:
  không có secret, model/video/database hoặc file vượt 5 MiB.
- RoadWatch regression chạy đúng working directory: 124/125 test pass. Test duy
  nhất fail là release-artifact preflight do 7 model nặng cố ý không đưa vào Git;
  toàn bộ config/runtime contract vẫn pass. Frontend build chưa tái chạy được do
  npm global lỗi đường dẫn và sandbox không cho Vite ghi temp vào source; không có
  thay đổi frontend riêng trong công việc này.
- Chưa commit/push và chưa gửi grading log tại checkpoint này; tiếp tục kiểm tra
  credential theo tên biến (không in giá trị), cài pre-push hook, stage đúng phạm
  vi, commit, import transcript thật, push và xác minh remote/server.

**POST-WORK**

- Kết quả: `PASS`. RoadWatch và AI usage logging đã được push lên remote branch
  `feat/roadwatch_phase1`; không tạo nhánh gần tên `feat_roadwatch_phase1`.
- Commit chức năng/handoff: `9dbc587`; sửa hook portable UTF-8/LF: `87c9e11`;
  fallback đọc `.env` không phụ thuộc `python-dotenv`: `4cce4ce`.
- AI-log server chấp nhận đủ 1.080 entry thành ba batch `500 + 500 + 80`, tất cả
  HTTP `202`. Nội dung gồm 95 lượt người dùng, 94 lượt hoàn chỉnh, 53.832 ký tự
  prompt và 511.439 ký tự response; importer thực hiện 2 redaction. File live đã
  được archive local và vẫn bị Git ignore; `.env` không được commit.
- Verification: AI-log unit test `5 passed`; RoadWatch `124 passed`, 1 expected
  artifact-preflight fail vì Git handoff cố ý không kèm 7 model; audit 0 file cấm
  và 0 file vượt 5 MiB. Manifest đồng bộ cuối trước POST-WORK: 548 file,
  43.377.775 bytes, 62.046 file bị loại có lý do.
- Hạn chế đã công khai: response của lượt đang thực thi không được đưa vào log
  dạng partial; prompt của lượt đó có entry `ConversationOpenPromptChunk` và có
  thể backfill response ở lần import kế tiếp. Frontend không phát sinh thay đổi
  riêng trong task này; build lại bị giới hạn bởi npm global hỏng và sandbox chặn
  Vite temp ở source, trong khi Python regression đã được chạy trên bản sync.
- Rollback: revert các commit nêu trên nếu cần; model/video tiếp tục được phân
  phối ngoài Git theo README và sync policy trong `docs/ROADWATCH_SYNC.md`.

### WORK-20260823-002 — Đánh giá Object V2 Version 3 và quyết định bước kế tiếp

**PRE-WORK**

- Ngày: 2026-08-23.
- Task liên quan: `RW-04` Object detector promotion; chuẩn bị dependency cho
  `RW-05` và Lane V2/RW-10.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: tải và kiểm tra kết quả Kaggle Object V2 Version 3; xác định Quality
  Gate, training artifact, held-out metrics và điều kiện promotion; chỉ tiếp tục
  train/remediation hoặc Lane V2 theo bằng chứng.
- Baseline đã xác minh: Kaggle API báo `KernelWorkerStatus.COMPLETE`; output chỉ
  có `_output_.zip` kích thước 867 byte. Version 2 từng dừng vì AV1 làm thiếu
  frame/person/motorcycle; Version 3 đã thêm AV1→H.264 preprocessing.
- Phạm vi dự kiến: `artifacts/kaggle/object_v2_v3/`,
  `docs/FINETUNE_EXECUTION_STATUS.md`, report/evaluation promotion liên quan;
  chỉ sửa `kaggle/train_object_v2/` và submit version mới nếu artifact chứng minh
  pipeline/gate cần remediation. Không chạm baseline model mặc định khi chưa pass.
- Kế hoạch: (1) tải/unpack artifact và hash; (2) đọc `job_status` + pseudo-label
  gate; (3) nếu có checkpoint/ONNX thì kiểm tra metrics và chạy promotion/event
  regression; (4) nếu gate fail thì giữ baseline, phân tích count cụ thể và sửa
  data/pipeline có kiểm soát; (5) cập nhật status/report và ledger.
- DoD: trạng thái Version 3 được xác định từ artifact; mọi gate có số liệu; quyết
  định `promote/reject/remediate` có bằng chứng; không local training; test liên
  quan pass; bước Object V2/Lane V2 tiếp theo được nêu rõ.
- Guardrail/rollback: không trộn target-domain vào val/test, không hạ gate chỉ để
  ép training, không tự promote pseudo-label candidate, không ghi token/artifact
  nặng vào Git. Mọi version lỗi được giữ trong lịch sử; baseline COCO là rollback.

**CHECKPOINT — 2026-08-23, Object V2 Version 3 → Version 4**

- Version 3: `COMPLETE` với trạng thái pipeline
  `quality_gate_failed_no_training`; 4.120 sampled, 3.364 positive,
  `person=227/300` fail, `motorcycle=575`, `car=5.093`, mean confidence 0,8254;
  val/test không đổi. Không có checkpoint và không promotion.
- Remediation: giữ confidence/gate, tăng background sampling 1→2 FPS; thêm 2
  unit tests và evidence tại `evaluation/object_v2_v3_quality_gate.json` cùng
  `reports/OBJECT_V2_VERSION_3_GATE.md`.
- Verification local: 2/2 targeted tests pass; syntax/JSON/diff check pass;
  7.635 background frame dự kiến trước hard-window additions.
- Version 4: submit thành công; Kaggle status sau submit là `RUNNING` tại
  `lekimnam/roadwatch-object-detector-v2-target-domain`.
- Trạng thái Work ID vẫn `IN_PROGRESS`; bước tiếp theo là kiểm tra Quality Gate,
  checkpoint/ONNX, held-out metrics và event regression sau khi Version 4 dừng.

**CHECKPOINT — 2026-08-24, Version 4 read-only preflight**

- Kaggle API xác nhận `KernelWorkerStatus.COMPLETE`.
- Output metadata chỉ có `_output_.zip`, 867 byte, timestamp 2026-08-23 14:37 UTC;
  chưa có bằng chứng checkpoint/ONNX hoặc training thành công.
- Worktree liên quan đang bẩn từ các thay đổi RoadWatch có chủ đích; không reset,
  xóa hoặc ghi đè artifact Version 1–3.
- Bước triển khai đã phê duyệt trong PRE-WORK: đọc structured execution log để
  xác định gate/metrics; chỉ tải hoặc chạy promotion nếu có model artifact thật.

**CHECKPOINT — 2026-08-24, Version 4 training result và artifact remediation**

- Version 4 pipeline status: `complete_candidate_not_promoted`; Quality Gate
  6/6 pass với 7.935 sampled, 6.509 positive, `person=472`,
  `motorcycle=1.126`, `car=9.853`, mean confidence 0,8259; val/test không đổi.
- Held-out test: precision 0,6239303; recall 0,4415769; mAP50 0,4875582;
  mAP50-95 0,2846469. `best.pt` và `best.onnx` được export trên Kaggle T4x2;
  elapsed 4,4 giờ. Candidate vẫn bị chặn Human review + event regression.
- Artifact blocker: signed `_output_.zip` là 9.982.920.388 byte. Kaggle CLI
  2.2.4 tải bằng `response.content`, gây file 0 byte trên máy 16 GB RAM. Nguyên
  nhân archive lớn là base dataset/frames nằm dưới `/kaggle/working`.
- Scope expansion có kiểm soát: chuyển transient dataset/video/frame paths sang
  `/kaggle/temp` cho future run và tạo CPU-only Kaggle artifact-export kernel
  gắn Version 4 output, chỉ copy model/metrics/manifest. Không retrain, không
  promote và không tải archive 9,98 GB local.
- Rollback: exporter chỉ đọc kernel output; baseline model không đổi. Nếu export
  kernel không mount được source, fallback là HTTP ZIP range extraction, không
  hạ gate hoặc chạy training local.

**CHECKPOINT — 2026-08-24, artifact exporter submitted**

- Future Object V2 transient dataset/video/frame paths đã chuyển từ
  `/kaggle/working` sang `/kaggle/temp`; output model/report vẫn ở working.
- CPU-only exporter được thêm tại `kaggle/export_object_v2_artifacts`; preflight
  4/4 tests pass, syntax/JSON/diff pass.
- Exporter Version 1 submit thành công và đang `RUNNING` tại
  `lekimnam/roadwatch-object-v2-artifact-export`; không retrain.
- Evidence Version 4 đã lưu tại `evaluation/object_v2_v4_training.json` và
  `reports/OBJECT_V2_VERSION_4_TRAINING.md`. Aggregate held-out metrics thấp hơn
  Phase 2.1 nên promotion vẫn blocked dù Quality Gate/training pass.

**CHECKPOINT — 2026-08-24, artifact exporter failed; range fallback active**

- Exporter Version 1 kết thúc `ERROR`: attached kernel source không expose
  `best.pt`, `best.onnx` hoặc `job_status.json`; không có output và không làm
  thay đổi Version 4.
- Root cause: Kaggle không mount nội dung archive output 9,98 GB dưới dạng file
  tree cho downstream kernel source trong lần chạy này.
- Fallback đã được phê duyệt trong checkpoint trước: triển khai HTTP Range ZIP
  reader, xác minh server hỗ trợ byte ranges, đọc central directory và chỉ tải
  member model/report được allowlist. Không tải full archive, không retrain.
- Safety limit: fail nếu server bỏ qua Range, archive/member vượt giới hạn hoặc
  tên artifact không khớp allowlist; SHA-256 phải được ghi sau download.

**POST-WORK**

- Trạng thái cuối: `PASS` cho mục tiêu đánh giá/ra quyết định; candidate
  `REJECTED`, không phải model pass promotion.
- Thay đổi thực tế: Version 3 được remediate bằng sampling 2 FPS; Version 4 train
  thành công; tải 9 artifact bằng bounded HTTP Range; đăng ký profile diagnostic
  `roadwatch_objects_v2` nhưng giữ active `baseline_coco`; future transient data
  chuyển sang `/kaggle/temp`.
- Bằng chứng training: Quality Gate 6/6; held-out precision 0,6239303, recall
  0,4415769, mAP50 0,4875582, mAP50-95 0,2846469; model/ONNX taxonomy/graph pass;
  SHA-256 PT `BA08682D...C89A17D`, ONNX `FC31DA08...8E612`.
- Bằng chứng promotion: cùng 6 locked scenarios/78 s, baseline TP/FP/FN 8/5/2,
  recall 0,80, FAR 3,8462/min; V2 6/6/4, recall 0,60, FAR 4,6154/min. Gate
  `event_recall_not_lower=false`, `false_alert_rate_not_over_110_percent=false`;
  decision `keep_baseline` tại `evaluation/object_v2_v4_promotion.json`.
- Verification: 131 test pass; candidate profile tests 8/8; range/export/sampling
  tests 7/7; JSON/syntax/diff checks pass. Hai regression reports hoàn tất 6/6;
  top-level `fail` chỉ do chủ động skip duplicate automated test gate, summary
  scenario/ground-truth integrity pass.
- Candidate/release decision: `candidate_rejected_static_and_event_gates`;
  không human review để override auto-fail, không đổi release/default profile.
- Khác kế hoạch: Kaggle CLI không tải được archive 9,98 GB và downstream exporter
  không mount source; dùng fallback ZIP Range allowlist đã dự kiến, không retrain.
- Limitation: locked coverage chỉ 78 giây và VRU matched recall bằng 0 cho cả hai
  profile; không đủ claim production. Object V2 vẫn có confirmation-bias từ
  pseudo labels và aggregate held-out metrics thấp hơn Phase 2.1.
- Rollback: xóa profile diagnostic/hard-link local nếu không cần; active baseline
  chưa từng đổi. Không xóa lịch sử Version 1–4 hoặc evidence.
- Bước tiếp theo: mở Work ID mới cho Lane V2/RW-10; Object V3 chỉ được cân nhắc
  sau khi có human-labeled target-domain data và class-balanced loss/sampling.

### WORK-20260823-001 — Thiết lập giao thức nhật ký Agent

**PRE-WORK**

- Ngày: 2026-08-23.
- Task liên quan: Governance toàn dự án; không thay đổi trạng thái RW/model.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: bổ sung quy tắc bắt buộc ghi kế hoạch trước triển khai và cập nhật
  kết quả sau triển khai theo yêu cầu của chủ dự án.
- Baseline: `AGENTS.md` đã có guardrail, DoD và quy tắc báo cáo nhưng chưa có
  execution ledger trước/sau công việc.
- Phạm vi: chỉ `roadwatch/AGENTS.md`.
- Kế hoạch: thêm §11 protocol, §12 ledger; kiểm tra Markdown/diff; cập nhật mục
  này thành `POST-WORK`.
- DoD: quy định rõ thời điểm ghi, trường bắt buộc, trạng thái cuối, bảo mật,
  correction/audit trail và có một entry mẫu được đóng sau xác minh.
- Guardrail/rollback: không làm yếu quy tắc an toàn hiện có; có thể rollback chỉ
  phần §11–§12 bằng patch nếu chủ dự án thay đổi quy trình.

**POST-WORK**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: thêm §11 quy định thời điểm/phạm vi `PRE-WORK`, nội dung
  `POST-WORK`, bảo mật, checkpoint và correction audit trail; thêm §12 làm ledger.
- Bằng chứng: `git diff --check -- roadwatch/AGENTS.md` đạt; kiểm tra heading và
  từ khóa xác nhận đủ §11.1–§11.3, §12, `PRE-WORK` và `POST-WORK`.
- Decision: quy trình có hiệu lực cho mọi công việc RoadWatch tiếp theo. Không có
  model, runtime default, dataset, external job hoặc release state nào bị đổi.
- Khác kế hoạch: không có.
- Limitation: ledger chỉ là tóm tắt vận hành; metric/log chi tiết vẫn phải lưu ở
  nguồn sự thật chuyên biệt và liên kết từ entry tương ứng.
- Bước tiếp theo: trước khi xử lý kết quả Kaggle Object V2 Version 3, tạo Work ID
  mới ở đầu §12 với preflight, kế hoạch tải artifact, Quality Gate và promotion.

### WORK-20260824-005 — Chốt official live URL cho RoadWatch

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: cập nhật `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md` theo quy tắc
  domain của Cohort 3/team 162.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: ghi URL khuyên dùng chính thức `https://c3-roadwatch-162.io.vn`,
  phân biệt URL `run.app` dự phòng, và mô tả cách map subdomain/tên miền riêng
  vào Cloud Run mà không đổi lại cloud architecture.
- Baseline: Web GCP chưa deploy; blueprint đã có Cloud Run `roadwatch-web`, GCP
  services, Video Library/Upload Custom Video nhưng chưa có domain policy.
- Phạm vi: chỉ sửa tài liệu kiến trúc và ledger; không deploy GCP, không chỉnh
  DNS, không ghi secret hoặc thay đổi runtime.
- Kế hoạch: thêm official URL, fallback URL, DNS/SSL/custom-domain flow, cấu hình
  cần cập nhật khi đổi domain và điều kiện cần từ domain owner; kiểm tra diff.
- DoD: tài liệu không coi `run.app` là live URL chính thức; nói rõ `c3-roadwatch-162.io.vn`
  là URL khuyên dùng; khẳng định có thể map domain mới vào service hiện tại.
- Guardrail/rollback: không yêu cầu Firebase; không tắt default `run.app` trước
  khi custom domain hoạt động; rollback bằng cách xóa phần URL policy trong tài liệu.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: tạo local backup commit `c7acb4f`, merge checkpoint `63d66a9`,
  sau đó tạo clean fast-forward snapshot `d144156` dựa trên remote hiện tại;
  giữ local fallback branch `roadwatch_pre_gcp_local`.
- Bằng chứng: `origin/roadwatch_project` trỏ đúng `d144156`; local `HEAD` bằng
  remote; scan remote tree không có model/video/dataset/artifact nặng hoặc `.env`.
- Decision: backup đủ điều kiện làm rollback trước triển khai; remote history được
  giữ, không force-push; các report Kaggle nặng chỉ bị loại khỏi Git index, file
  local không bị xóa.
- Khác kế hoạch: merge thường bị Windows chặn unlink nên dùng merge strategy
  `ours` và sau đó tạo clean snapshot fast-forward; đây là thay đổi lịch sử Git
  có kiểm soát, không ảnh hưởng source local.
- Limitation: các thay đổi ngoài `roadwatch/` vẫn dirty/untracked và không thuộc
  backup; GCP project/IAM/billing/domain chưa được cung cấp.
- Bước tiếp theo: tạo PRE-WORK mới cho Phase A/B implementation; không dùng branch
  fallback làm nơi phát triển deployment.

### WORK-20260824-007 — Triển khai Phase A/B: local parity và GCP public-demo scaffold

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: triển khai theo `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md` sau
  backup `d144156`.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: biến blueprint thành implementation có thể chạy local trước, sau đó
  deploy lên GCP khi có project/IAM/billing; ưu tiên Video Library, Custom Upload,
  Cached/Fresh run semantics và giữ Edge Core ngoài cloud critical path.
- Baseline: local Web/FastAPI/React/AAOS replay đã có; chưa có GCP IaC/service
  manifest, upload queue contract hoặc public URL; `origin/roadwatch_project`
  đã có rollback checkpoint.
- Phạm vi cho đợt này: thêm deployment contracts, GCP Docker/Cloud Run config,
  upload/job/status interfaces, sample library manifest và local tests/docs;
  không train model, không upload video/model, không đặt secret vào repo, không
  triển khai CAN/VinFast camera.
- Kế hoạch: (1) preflight current API/frontend; (2) viết config/schema cho
  `library`, `custom upload`, `run_id`, `cached/fresh`; (3) thêm GCP deployment
  scaffold dùng Cloud Run/Cloud Storage/Pub/Sub/Cloud SQL/Secret Manager; (4)
  nối local mock/in-memory adapter để test không cần GCP; (5) chạy tests/build;
  (6) chỉ yêu cầu GCP credentials nếu local scaffold pass.
- DoD: local tests pass; deployment files không chứa secret; `run_id` isolation
  được kiểm tra; public deployment status ghi `BLOCKED` nếu thiếu project/IAM;
  không đổi default safety profile hoặc đưa cloud vào critical alert path.
- Guardrail/rollback: giữ `baseline_coco`, không đổi model promotion; mọi GCP
  worker là asynchronous evaluation; rollback bằng `d144156`/branch fallback;
  không force-push và không xóa video/model local.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PARTIAL_PASS`. Local parity và GCP public replay/upload đã
  pass; signed resumable upload, Pub/Sub worker, cached-result plane, Cloud SQL
  và official DNS mapping chưa triển khai.
- Thay đổi thực tế: thêm `catalog.py`/`uploads.py` cho Video Library và upload
  bounded; thêm `asset_bootstrap.py`/`asset_store.py` cho GCS model/video và
  durable custom upload; thêm `run_id`, `source_kind`, `analysis_mode`,
  `source_key` vào session/event contract; cập nhật FastAPI/React upload UI;
  thêm `deploy/gcp/cloudbuild.yaml`, `deploy/gcp/README.md` và
  `configs/cloud_assets.json`.
- GCP target đã xác minh: project `c3-roadwatch-162`, Artifact Registry
  `roadwatch`, bucket `gs://c3-roadwatch-162-roadwatch-assets`, region
  `asia-southeast1`, service `roadwatch-web`, revision cuối
  `roadwatch-web-00006-4gc`; final Cloud Build
  `19698631-f922-46a1-b3f5-b1f772cd8fe7`. URL fallback hiện tại:
  `https://roadwatch-web-bx6lfekcba-as.a.run.app`.
- Bằng chứng local: full regression `129/129` pass; deployment contract tests
  `7/7` pass; Python compile/diff-check pass; TypeScript `tsc -b` pass; Vite
  production build pass khi chạy binary local do npm global bị hỏng.
- Bằng chứng public: login driver pass; Video Library trả 4 video và duration;
  fresh replay library đạt `frame_id=1`, `processed_frames=1` với object
  `yolo11n.onnx`, sign `ONNX/CPUExecutionProvider`, lane `CPUExecutionProvider`;
  custom upload `14.55 MB` trả `durable=true`, `storage_mode=gcs`, SHA-256
  `736121b31a414b2995a549d7811c7bfdc2e18d2302588e6bb4c451b46adc67`; GCS object
  tồn tại và fresh replay từ `uploads/...` đạt `frame_id=1`.
- Final revision health xác nhận asset bootstrap `enabled=true` và tải đủ 9
  allowlisted asset; replay lại trên revision `00006` đạt `frame_id=1`,
  `processed_frames=1`, object `yolo11n.onnx`, sign `ONNX/CPUExecutionProvider`
  và lane `CPUExecutionProvider`.
- Decision: Cloud Run là public evaluation/replay plane, không phải FCW/LDW/TTS
  critical path. Cloud profile ép ONNX/CPU, tắt audio và bỏ PyTorch speed
  classifier khỏi warmup; local/AAOS profile không đổi. Health có thể còn
  `degraded` vì R0 release manifest yêu cầu PT/hash artifacts không đóng gói
  trong Cloud Run; đây không phải bằng chứng production-ready.
- Khác kế hoạch: Docker daemon local không chạy nên dùng Cloud Build; lần đầu
  cần sửa IAM source bucket/Artifact Registry/runtime GCS reader; một lần
  warmup trước đó chọn PT vì asset bootstrap chạy sau service construction, đã
  sửa bằng rebuild perception sau bootstrap. Các lỗi/version đều giữ trong
  Cloud Build history, không force-push.
- Limitation: direct Cloud Run multipart upload bị khóa `25 MB`; video dài cần
  signed GCS resumable upload. Cached result, Pub/Sub worker, Cloud SQL/HITL
  persistence và `https://c3-roadwatch-162.io.vn` chưa được acceptance; domain
  owner phải map DNS/managed TLS.
- Rollback: remote backup `d144156` và local branch `roadwatch_pre_gcp_local`;
  không xóa model/video local hoặc GCS asset.
- Bước tiếp theo: triển khai signed upload + upload completion endpoint, tách
  replay worker bất đồng bộ, thêm cloud health profile, publish cached results,
  rồi map official domain và chạy public URL acceptance gate.

### WORK-20260824-006 — Backup roadwatch_project trước triển khai GCP

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: backup toàn bộ scope `roadwatch/` lên remote
  `KimNam2809/ADAS_FOR_FRONTIER_CAMERA`, branch `roadwatch_project`, trước khi
  triển khai theo `UNIFIED_DEPLOYMENT_ARCHITECTURE.md`.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: tạo một commit/remote checkpoint có thể dùng làm rollback trước khi
  thay đổi code triển khai Web GCP, Video Library, Custom Upload hoặc AAOS.
- Baseline: local branch `roadwatch_project` đang có thay đổi RoadWatch chưa
  commit và đã lệch với remote; cần fetch/đối chiếu trước khi push, không được
  reset hoặc ghi đè lịch sử từ xa.
- Phạm vi: chỉ đưa source/docs/config/tests nhẹ trong `roadwatch/` và các thay
  đổi cần thiết vào backup; không push `.env`, model, video, dataset, cache,
  build output hoặc artifact nặng; không đưa các thư mục ngoài `roadwatch/` vào
  commit backup.
- Kế hoạch: (1) fetch và inspect divergence; (2) kiểm tra ignore/secret/size;
  (3) stage đúng scope `roadwatch/`; (4) commit backup có message rõ; (5) push
  an toàn lên `origin/roadwatch_project`; (6) xác minh remote commit/tree; (7)
  chỉ sau đó thực hiện deployment work.
- DoD: remote branch chứa commit backup xác minh được; không có file secret,
  video/model/dataset nặng hoặc file ngoài scope; local rollback reference được
  ghi lại; nếu remote divergence gây conflict thì dừng push và báo cáo.
- Guardrail/rollback: tuyệt đối không `reset --hard`, `checkout`, force-push hoặc
  xóa thay đổi user; nếu push thất bại thì giữ nguyên local worktree và không
  triển khai tiếp; fallback dùng commit backup remote, không xóa lịch sử hiện tại.
