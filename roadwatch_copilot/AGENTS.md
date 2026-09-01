# AGENTS.md — RoadWatch

## PRE-WORK — Editable pitch PowerPoint, native fallback (2026-08-31)

- User explicitly approved native installed PowerPoint automation after the bundled presentation runtime loader failed. Create an independent 12-slide pitch artifact (8 main + 4 Q&A), with editable text/shapes/images and speaker notes.
- Work is presentation-only; preserve all runtime, model, UI, voice, existing slides and Canva assets. Do not publish, commit or change deployment.
- Use existing RoadWatch screenshots as UI illustrations, not fabricated evidence; distinguish replay prototype, future integration and proposed commercial pilot. No invented performance, revenue or OEM claims.
- Verify by native PowerPoint rendering, text bounds and PPTX package inspection; keep temporary authoring files outside roadwatch runtime directories.

## POST-WORK — Editable pitch PowerPoint, native fallback (2026-08-31)

- Created `../output/roadwatch_pitch_native/RoadWatch_DemoDay_Editable_v1.pptx` using installed PowerPoint 16.0 via COM under the user's explicit fallback approval. Native editable text/diagram objects, three embedded images, twelve speaker-note pages; slides 9–12 hidden for Q&A.
- Verification: 12/12 native slide renders visually reviewed; final text overflow=0 and text overlap=0; 141 native text-bearing shapes; 3 embedded pictures; no external slide asset links. A disposable copy passed changing/saving/reopening text and moving/saving/reopening an image. Original deliverable remained unchanged by editability probes.
- SHA256: C44664B6E5251305618E380E483268EA6A0C5341FB6F8D3992915A389B9146DD. Supporting source and QA records in `../output/roadwatch_pitch_native/build/`.
- No video embedded: slide 4 uses existing UI illustration and its speaker notes explain replacing it with a verified 90-second demo. Existing UI screenshot pixels are not separately editable; the screenshot is a replaceable picture object. No new runtime benchmark or vehicle safety validation claimed.
- Kept runtime, models, TTS, UI, deployment and previous presentation files unchanged. No Git push or Canva generation performed.

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
- `.gitignore` chỉ kiểm soát nội dung đưa vào Git; không được suy diễn rằng model,
  voice hoặc media runtime bị loại khỏi GCP/GCS. Cloud deployment phải dùng
  allowlist, checksum và asset bootstrap riêng để đưa đúng artifact đã được
  promote lên runtime mà không commit file nặng vào repository.
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

## 12.x PRE-WORK — Dựng video demo RoadWatch v1.2

- Phạm vi: tạo video demo độc lập từ asset thật, không thay đổi model, runtime, UI hoặc production path của RoadWatch.
- Dùng HyperFrames cho timeline/animation/chuyển cảnh và FFmpeg cho media normalization, audio mix, encode/QA.
- Video chính phải quay lại Driver và Engineer trên `media/dashcam_vietnam_traffic_multi.mp4`, ưu tiên khoảng 01:18 trở đi; phải giữ timestamp và không tạo evidence giả.
- Giữ phần giới thiệu ADAS ở phạm vi cảnh báo Level 0; không mô tả tự lái, phanh, đánh lái, tích hợp VinFast, CAN, AAOS production hoặc Cloud production.
- Narrator mục tiêu: giọng nam miền Nam truyền cảm; Piper hiện tại chỉ là product-alert voice nếu chưa có narrator phù hợp được kiểm duyệt.
- Mockup Edge/AAOS/Cloud phải gắn nhãn định hướng tương lai, không trình bày như khả năng đã kiểm chứng.
- Mỗi asset, claim, số liệu và timestamp phải có provenance; không upload tài liệu ra dịch vụ bên ngoài nếu chưa được cho phép.
- Tạo pilot trước, kiểm tra hình/tiếng/chuyển cảnh, giữ output phiên bản để fallback; không ghi đè CapCut pack hoặc RoadWatch runtime.

## 12.x POST-WORK — Dựng video demo RoadWatch v1.2

- Đã tạo source timeline HyperFrames-compatible tại `output/demo_film_v1_2/index.html` và design contract tại `output/demo_film_v1_2/DESIGN.md`.
- Đã tạo script dựng deterministic `scripts/build_demo_film_v1_2.py`; script dùng VieNeu `Minh Triết` cho narrator và giữ Piper product alert riêng.
- Đã render bản local `output/demo_film_v1_2/RoadWatch_Demo_v1_2_1080p_yuv420p.mp4`, duration 166.5s, 1920x1080, 30fps, H.264/yuv420p/AAC.
- Đã tạo pilot 30s, SRT, audio theo cảnh, manifest và `QA_REPORT.md` để human review/fallback.
- Đã kiểm tra FFmpeg decode exit 0 và kiểm tra contact sheet các mốc trong video.
- UI Driver/Engineer sử dụng capture thật trong video tham chiếu được cung cấp; chưa tuyên bố đây là một lần re-record mới đồng bộ chính xác với multi-traffic source tại 01:18.
- Đã giữ giới hạn: không claim OEM/VinFast, CAN, AAOS production, Cloud production, actuator hoặc safety certification.
- Trạng thái bàn giao: `PASS_LOCAL_RENDER / HUMAN_REVIEW_PENDING`; cần owner nghe narrator, xem caption và xác nhận trước khi phát hành ngoài workspace.
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

## 12.x PRE-WORK — Hợp nhất RoadWatch Copilot với P-162/main và đóng gói repo

- Ngày: 2026-09-01.
- Work ID: `RW-REPO-HANDOFF-COPILOT-20260901`.
- Trạng thái: `IN_PROGRESS`.
- Yêu cầu: lấy đúng `P-162/main` mới nhất có landing page; tạo thư mục
  `roadwatch_copilot` chứa một luồng RoadWatch end-to-end cùng landing page;
  bổ sung README/runbook và cơ chế tải model/media từ Google Drive hoặc đặt
  asset thủ công; sau đó push thư mục này lên nhánh `main` của
  `KimNam2809/ADAS_FOR_FRONTIER_CAMERA`.
- Baseline đã xác minh: source `roadwatch/` hiện tại chứa UI v4, Piper/Trúc Ly,
  Traffic Context v1, SLM optional, perception/risk/alert/audio pipeline,
  AAOS, Docker, docs và tests; local worktree có nhiều thay đổi hợp lệ của chủ
  dự án nên không được reset, checkout, clean hoặc ghi đè. P-162 remote `main`
  đã được fetch và đang ở commit `83c5654` (`merge: integrate landing into web
  demo`), khác snapshot cũ `92d9a98`.
- Phạm vi file: tạo thư mục đóng gói mới từ source `roadwatch`; ghép các file
  landing/component/assets của `P-162/main` mà không làm mất source RoadWatch
  mới hơn; tạo script bootstrap Drive asset, README và tài liệu handoff. Không
  đưa `.env`, token, model/video/voice nặng, cache, database hoặc build output
  vào Git.
- Kế hoạch: (1) giữ source hiện tại bất biến ngoài ledger; (2) archive/export
  `P-162/main` vào vùng tạm và audit landing; (3) tạo `roadwatch_copilot` từ
  RoadWatch hiện tại; (4) ghép landing theo allowlist và giữ một entrypoint E2E
  duy nhất; (5) thêm auto-download Drive có checksum/skip-safe và manual asset
  path; (6) chạy test/compile/build/secret-large-file audit; (7) chuẩn hóa repo
  ADAS nhánh `main`, commit/push an toàn không force-push và xác minh remote tree.
- Definition of Done: `roadwatch_copilot/` tự mô tả được cách cài đặt/chạy,
  có landing page cùng app phân tích, setup không cần API key để tải folder
  Drive public hoặc cho phép `-SkipDriveAssets`, local test/build pass, model/
  media nặng vẫn ở ngoài Git, remote ADAS `main` chứa đúng thư mục này và
  commit/tree/README được xác minh bằng clone read-only.
- Guardrail/fallback: không sửa/xóa source `roadwatch/`; không force-push hoặc
  thay lịch sử P-162; nếu integration landing gây lỗi thì giữ app core hiện tại
  và chuyển landing thành entry độc lập; runtime fallback vẫn là YOLO11n,
  YOLOP, Piper, UI v4, Traffic Context v1 và SLM disabled khi thiếu asset.
  Fallback Git là commit trước push; model/media được tải lại từ Drive hoặc
  đặt thủ công theo README.
- Human gate: người dùng cần tự kiểm tra URL/landing, tài khoản demo và nghe
  TTS sau clone; đây là repo handoff/demo readiness, không phải bằng chứng xe
  thật, VinFast API, Jetson Orin thật hay safety certification.

### WORK-20260831-CAPCUT-001 — Demo film input pack

**PRE-WORK**

- IN_PROGRESS: chuyển kịch bản 170 giây thành Script / Assets / Visual Style cho CapCut AI.
- Phạm vi: docs/capcut_v1, script đóng gói và output riêng; tái sử dụng 4 video nguồn,
  4 replay, ảnh UI và Piper WAV đã có, không chỉnh sửa source media hoặc runtime.
- DoD: prompt có shot/timecode/voice; manifest asset ID + nguồn + checksum;
  ZIP allowlist mở được; phân biệt evidence/simulation và danh sách phải tự quay.
- Không upload CapCut/cloud, không clone voice hoặc tạo footage giả như sản phẩm thật.
  Public rights/privacy, narration và phép nghe cuối vẫn cần owner review.

**POST-WORK — PASS_LOCAL_PACKAGE / HUMAN_EDIT_PENDING**

- Đã tạo 4 tài liệu docs/capcut_v1: master prompt, Script 11 cảnh/170 giây,
  Assets theo ID và Visual Style; có fallback trung thực cho cảnh chưa quay.
- Script giữ tiếng Việt; stage directions tách narration; standalone Piper
  không được ghép như audio đồng bộ vào hazard bất kỳ của muted replay.
- Đóng gói 17 tài sản/bằng chứng có sẵn + 4 brief + manifest (22 ZIP entries),
  25,066,147 bytes: output/RoadWatch_CapCut_v1_20260831-105514.zip.
- scripts/package_capcut_assets.ps1 dùng allowlist và folder timestamp mới;
  kiểm SHA-256 bản sao và từng entry giải nén trong ZIP đều PASS.
  Đã sửa validator phân cách path Windows/backslash sau lượt kiểm tra đầu.
- Đã tra Pexels candidate Vietnam traffic 33383213 và license chính thức;
  chỉ đưa link tham khảo, chưa tải/chưa frame-review/chưa upload public.
- Chưa tạo narration, nhạc, video AAOS/Event History mới hoặc phim final;
  danh sách H01–H11 ghi cách tự quay/chọn và phương án không giả mạo.
- Runtime, model, TTS release và UI không thay đổi. Không train/deploy/push Git.
  Quyền upload media đến CapCut, privacy, license nhạc và human final review vẫn pending.

### WORK-20260830-LP-002 — Landing 1.0 implementation

**PRE-WORK**

- Ngày: 2026-08-30. Trạng thái: IN_PROGRESS. Chủ dự án yêu cầu triển khai plan LP.
- Phạm vi: landing entry/component mới, assets preview, config build riêng,
  scripts chạy/đóng gói GCP, tài liệu và browser QA; không đổi HMI/model/risk/TTS release.
- Baseline: bản nháp landing đang untracked; Vite mặc định chưa build landing.
  Giữ component bản nháp làm fallback và tạo snapshot trước chỉnh sửa entry/config.
- Thực hiện theo hướng thiết kế navy/trắng/xanh đã được duyệt trong plan;
  hoàn thiện bản chạy local để owner review. Không dừng ở đề xuất/mockup.
- DoD: build tách biệt, media/audio hoạt động, interactive policy có nhãn,
  responsive/keyboard/mobile QA, no inference requests, deployment package và rollback.
- Gate còn cần human: listening/comprehension, public media/privacy và DNS;
  chưa publish dữ liệu video ra Internet trong công đoạn local preview.
- Không chạy train, không tự promote, không ghi secret hoặc thay file người dùng ngoài scope.

**POST-WORK — 2026-08-30**

- Trạng thái: IMPLEMENTED_LOCAL / HUMAN_AND_PUBLIC_RELEASE_PENDING.
- Tạo landing v1 entry riêng, React sections/6 nhóm tương tác, CSS responsive,
  client + SSR prerender vào `frontend/dist-landing`, không ghi `dist-ui-v4`.
- Media: 4 clip local 18s qua pipeline thật (14/4/14/5 events); 2 ảnh Driver/Engineer
  chụp app local; 3 Piper WAV canonical. Manifest kiểm tra 25/25 SHA-256.
- Core inference chỉ chạy để ghi evidence; landing truy cập không khởi tạo model,
  không polling API/TTS. Policy widget là minh họa có nhãn, không đổi risk thresholds.
- Đã test TypeScript/client/SSR build, 18/18 pytest landing + UI contract; browser
  desktop/390px, replay seek/switch, tabs, menu, voice sample switch, no broken image/
  overflow trong viewport kiểm tra. JS gzip 68,587 bytes theo audit cuối.
- Thông số evidence dùng JSON gốc 20260829 (11.48/19.4 FPS, E2E P95 145.01ms);
  summary cũ khác số nên không dùng thay JSON. Không tuyên bố benchmark mới hoặc safety PASS.
- Dừng phiên app chụp ảnh sau QA; preview landing port 4174 được để lại cho owner.
  Clip dẫn xuất `media/landing_preview_day.mp4` giữ để tái hiện ảnh chụp, bản gốc không đổi.
- Docker package static-only có sẵn; Docker daemon chưa chạy (named pipe missing),
  chưa build/test container/deploy GCP, chưa đổi DNS/IAM/billing hoặc push Git.
- Chưa đo Lighthouse/INP/CLS; chưa xác minh mọi browser; human listening, 5-person
  comprehension, public rights/privacy vẫn PENDING. Không đánh dấu PASS thay người.
- Runbook: `docs/LANDING_PAGE_V1_RUNBOOK.md`; audit: `reports/landing-v1/build-audit.json`.
  Có snapshot entry/config và legacy source/entry riêng để fallback, không reset worktree.
- Skills Product Design và React checklist giúp giữ scope UI, minh bạch evidence,
  tránh polling/animation nặng; Browser dùng kiểm thử giao diện thật, không mock test pass.

### WORK-20260830-LP-001 — Kế hoạch landing page RoadWatch

**PRE-WORK**

- Ngày: 2026-08-30. Trạng thái: `IN_PROGRESS`; phạm vi: lập kế hoạch, không build/deploy.
- Yêu cầu: landing page phong cách công nghệ cao, có video/ảnh, tương tác trực
  quan và animation mượt, giải thích đủ sản phẩm cho giám khảo/doanh nghiệp.
- Baseline đã đọc: React/Vite HMI; bản nháp `frontend/src/landing/` và
  `frontend/landing.html` đang untracked, chưa khai báo entry trong Vite build;
  có nội dung VI/EN và canvas mô phỏng. Worktree có nhiều thay đổi của người dùng.
- Phạm vi ghi: chỉ thêm `docs/LANDING_PAGE_MASTER_PLAN.md` và work ledger này.
- Kế hoạch: đối chiếu source/evidence và nguồn công khai; chốt cấu trúc nội dung,
  media, tương tác, motion, performance budgets, GCP isolation, Task ID và gates.
- DoD: phủ 5 yêu cầu; có nguồn/media inventory, task/dependency/owner/evidence,
  ETA có giả định, phân biệt replay/simulation/live và rollback độc lập HMI.
- Guardrail: không dùng mockup như ảnh ứng dụng thật; không công bố upload riêng
  của người dùng; không đổi model/audio/HMI, Git/DNS/GCP hoặc cài dependency.
- Rollback: bỏ tài liệu kế hoạch mới nếu cần; mọi source/bundle hiện có giữ nguyên.

**POST-WORK**

- Ngày: 2026-08-30. Trạng thái: `PASS` cho tài liệu kế hoạch, chưa triển khai landing.
- Đã tạo `docs/LANDING_PAGE_MASTER_PLAN.md`: 13 mục, 10 section trang, 6 tương
  tác, media inventory A01–A10, LP-00–LP-10, budget performance/a11y, hosting
  GCP tách inference, human gates, dự toán 12–22 giờ và P0 rút gọn 8–12 giờ.
- Đã đối chiếu bản nháp VI/EN, Vite config, model config và report performance
  2026-08-29; không dùng snapshot cũ như số đo mới, không lấy simulation làm
  bằng chứng inference, không đặt metric thiếu ground truth bằng số 0.
- Nguồn tham khảo: Apple/NVIDIA/Mobileye cho cấu trúc câu chuyện; Google Web
  Vitals/GCP, MDN và Pexels cho performance/media/hosting; URL ghi trong plan.
- Kiểm tra: 461 dòng, 11 Task ID, 13 mục chính, 6 link nội bộ đều tồn tại;
  `git diff --check` không phát hiện whitespace error (chỉ cảnh báo LF/CRLF).
- Không chạy test/model/benchmark mới vì chỉ sửa tài liệu. Không tạo mockup,
  sửa source landing/HMI, cài dependency, tải/public media hoặc đổi Git/GCP/DNS.
- Bước sau: LP-00/LP-01 khóa baseline và content, LP-02 duyệt hướng mockup;
  quyền public media/DNS và human comprehension gate vẫn cần xác nhận thực tế.

### WORK-20260828-022 — RW-04 browser-assisted artifact recovery and promotion gate

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: tiếp tục RW-04 sau khi phiên CLI không xác thực được Account 1, bằng
  phiên Kaggle owner đã được chủ dự án mở; đối chiếu token metadata, Output
  kernel và chuẩn bị promotion evidence cho Object V3 Full Fine-tune.
- Hiện trạng đã xác minh: `configs/model_registry.json` vẫn giữ
  `active_object_profile=baseline_coco`; Work 021 đã ghi nhận blocker CLI;
  Kaggle owner page hiển thị kernel private `lekimnam/roadwatch-object-detector-v3-full-fine-tune`
  và output hoàn tất nhưng candidate chưa promote.
- Phạm vi: chỉ đọc Output/Logs/metadata và artifact đã tải qua phiên owner;
  sao chép checkpoint vào thư mục candidate riêng, kiểm tra hash, checkpoint,
  ONNX, taxonomy, split/manifest, metrics và chạy object/event regression nếu
  artifact hợp lệ. Không đọc/ghi token, không ghi secret, không sửa baseline.
- Kế hoạch/DoD: (1) xác minh token tồn tại bằng metadata an toàn; (2) xác minh
  remote status, preflight, pseudo-label gate, dataset manifest và training
  metrics; (3) thu artifact `best.pt`/`best.onnx` riêng và checksum; (4) chạy
  evaluator + locked RW-03 regression, so sánh đầy đủ promotion gate; (5) quyết
  định `PASS`, `FAIL` hoặc `BLOCKED`, chỉ đề xuất promote khi mọi gate đạt.
- Guardrail/Human gate: output browser là bằng chứng owner-session nhưng không
  thay thế Human review pseudo-label 50 FP/FN và event-level safety gate; không
  auto-promote, không overwrite registry/baseline, không train local.
- Rollback: chỉ xóa artifact/report mới của Work 022 khi được yêu cầu; giữ
  nguyên Work 021 POST-WORK và thêm correction checkpoint nếu bằng chứng browser
  thay đổi kết luận CLI.

**POST-WORK**

- Ngày hoàn tất: 2026-08-28. Trạng thái: `FAIL_PROMOTION_GATE` (artifact và
  training kỹ thuật hợp lệ, candidate không đủ điều kiện promote).
- Credential: `roadwatch/.env` được kiểm tra chỉ bằng metadata; bốn key Account
  1/2 đều hiện diện, file không bị ghi trong Work 022 và `LastWriteTime` vẫn là
  2026-08-27. CLI Account 1 vẫn trả `Authentication required`, nhưng owner
  browser session `Le Kim Nam` đã truy cập được kernel private và tải artifact;
  không in token/secret.
- Kaggle evidence: kernel run `345504146` có status
  `complete_candidate_not_promoted`, preflight `PASS`, `training_error=null`,
  `training_local=false`, `production_model_unchanged=true`, test/val không sửa.
  Pseudo-label gate đạt `7,935` sampled, `6,509` positive, person `472`,
  motorcycle `1,126`, car `9,853`, mean confidence `0.8259`, nhưng remote
  `promotion_allowed=false` vì Human pseudo-label review bắt buộc.
- Đã tải vào thư mục riêng `artifacts/kaggle/object_v3_full_output/`:
  `best.pt` SHA-256 `8425c24ca33cc55a015f14cddd4dc9f8b567e6e9f864e2787678614878c328ca`
  và `best.onnx` SHA-256
  `57c1822cd397f6732175e3a3bd83238a6659a26f42d284b320f5a666a5f11e9e`, khớp
  `artifact_hashes.json`; checkpoint load, ONNX checker/ORT và same-frame smoke
  đều pass. Manifest: `artifacts/kaggle/object_v3_full_output/artifact_manifest.json`.
- Held-out metrics: precision `0.62393`, recall `0.44158`, mAP50 `0.48756`,
  mAP50-95 `0.28465`; taxonomy 7 lớp đúng.
- Đã chạy locked RW-03 trên 6 scenarios bằng candidate profile riêng (không
  đổi active profile): TP/FP/FN `6/5/4`, precision `0.5455`, recall `0.6000`,
  FAR `3.8462/min`, object latency P95 mean `32.105 ms`; baseline rerun cùng
  code là `8/4/2`, precision `0.6667`, recall `0.8000`, FAR `3.0769/min`, P95
  `33.785 ms`. Candidate regression automated-test gate `PASS`; promotion
  evaluator: `automated_pass=false`, decision `keep_baseline`; fail event recall
  và FAR (+25%), latency pass.
- Diagnostic replay trên 198 sampled frames (night/rain+night/traffic-multi)
  ghi nhận suy giảm presence person/motorcycle ở traffic-multi và tăng rider;
  đây là evidence chẩn đoán, không thay locked ground truth. Báo cáo:
  `reports/RW04_OBJECT_V3_FULL_KAGGLE_REVIEW_20260828.md`,
  `reports/rw04-v3-full-locked-regression.json/.md`,
  `reports/rw04-v3-full-promotion.json`,
  `reports/object_v3_full_dashcam_replay_20260828.json`. Full `pytest tests -q`
  exit code `0` (một deprecation warning).
- Bảo toàn/rollback: `configs/model_registry.json` vẫn
  `active_object_profile=baseline_coco`; `models/yolo11n.pt`/ONNX không bị
  ghi đè. Profile candidate và runtime config tạm chỉ dùng cho replay rồi đã
  gỡ; bản sao trung gian trong `models/roadwatch_objects_v3_full.*` đã được
  xóa, artifact gốc vẫn giữ riêng dưới `artifacts/kaggle/object_v3_full_output/`.
  Không train local, không submit lại Kaggle, không promote.
- Khác kế hoạch: CLI blocker được giải quyết bằng owner browser evidence và
  file-specific download; replay lần đầu bị treo do hai process chồng nhau,
  đã dừng đúng các process do Work 022 tạo và chạy lại một pass giảm tải thành
  công. Human vẫn cần adjudicate tối thiểu 50 FP/FN và remediation VRU trước
  bất kỳ lần promote nào.

### WORK-20260828-021 — RW-04 evaluate Object V3 Full Fine-tune candidate

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: thực hiện RW-04 trong `docs/MASTER_ACTION_PLAN.md` sau khi chủ dự án thông báo Kaggle full fine-tune đã hoàn tất.
- Baseline bất biến: `configs/model_registry.json` vẫn để `active_object_profile=baseline_coco`; không ghi đè `models/yolo11n.pt`/ONNX hoặc candidate Object V2 đã bị loại.
- Phạm vi: read-only xác minh Kaggle kernel `lekimnam/roadwatch-object-detector-v3-full-fine-tune`, tải artifact full vào thư mục riêng, kiểm tra hash/metadata/checkpoint/ONNX parity, chạy regression và replay so sánh candidate với baseline.
- Quality gate: không promote chỉ vì Kaggle báo `COMPLETE` hoặc mAP; phải kiểm tra actual epochs, loss/metrics hữu hạn, held-out metrics, event recall/precision/FAR, VRU/semantic regression và latency theo RW-04.
- Network/credential: chỉ dùng Kaggle Account 1 từ `roadwatch/.env`; không in token/log secret. Nếu sandbox chặn API, dừng và xin quyền mạng thay vì giả định trạng thái.
- Definition of Done: có trạng thái remote hoặc blocker rõ ràng; artifact riêng có checksum và report; promotion decision `pass/fail/blocked`; registry/production/runtime không đổi nếu chưa đạt toàn bộ gate.
- Rollback: xóa candidate artifact/report mới nếu chủ dự án yêu cầu; baseline và registry vẫn nguyên trạng.

**POST-WORK**

- Ngày: 2026-08-28.
- Trạng thái: `BLOCKED_EXTERNAL_AUTH` — chưa đủ bằng chứng để đánh giá hoặc promote.
- Đã thử: Kaggle CLI read-only `kernels status lekimnam/roadwatch-object-detector-v3-full-fine-tune` bằng Account 1; sandbox đã được cấp network nhưng token Account 1 bị CLI trả về `Authentication required`. Account 2 authenticate được nhưng bị `Permission 'kernels.get' was denied` với kernel private.
- Kết quả: chưa tải artifact full, chưa có `best.pt`/`best.onnx`, metrics hoặc checksum để chạy RW-04; không được suy ra `COMPLETE` từ thông báo người dùng khi chưa có artifact/bằng chứng remote truy cập được.
- Bảo toàn dữ liệu: `configs/model_registry.json`, model production/baseline, Kaggle package và các queue không bị sửa; không submit lại kernel, không chạy training local, không promote candidate.
- Cần từ Human: đăng nhập/refresh token đúng owner `lekimnam` cho Account 1 hoặc cấp quyền collaborator/download artifact cho account đang dùng; sau đó tiếp tục status → output download → artifact/metrics/ONNX/event regression theo PRE-WORK này.

### WORK-20260827-014 — RW-10 independent YOLOP consistency audit

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: `RW-10.1` — thực hiện thêm một pass kiểm tra độc lập trên 3.000 record lane đã được gắn nhãn để tìm nhóm cần người rà soát lại.
- Phạm vi: đọc sidecar `evaluation/rw10_lane_ai_provisional_queue_20260827.json` và ảnh review hiện có; chạy YOLOP cục bộ để đối chiếu tín hiệu lane; tạo audit JSON/report riêng.
- Guardrail provenance: đây là AI cross-model consistency audit, không phải Human review; không đổi nhãn, reviewer, queue gốc, gate, quota Human/double-review hoặc trạng thái fine-tune.
- Kế hoạch: (1) kiểm tra model/runtime và toàn bộ ảnh tham chiếu; (2) suy luận YOLOP cho 3.000 frame; (3) phân nhóm tín hiệu bất đồng theo ngưỡng heuristic; (4) lưu checkpoint/kết quả, report top suspect và validate.
- Definition of Done: có kết quả cho 3.000 record hoặc lỗi được ghi rõ; JSON/report nêu model, ngưỡng heuristic, giới hạn và bước Human adjudication; sidecar/queue/gate không bị sửa.
- Rollback: xóa audit JSON/report/script mới nếu chủ dự án yêu cầu; không phục hồi hay ghi đè các queue hiện hữu.

**POST-WORK**

- Ngày hoàn tất: 2026-08-27.
- Trạng thái: `PASS` cho AI cross-model consistency audit; kết quả **không** đủ điều kiện Human Quality Gate.
- Đã thực hiện: chạy `yolop_lane_detection_640.onnx` trên toàn bộ 3.000 ảnh sidecar bằng `CPUExecutionProvider`; tạo `evaluation/rw10_lane_ai_consistency_audit_20260827.json` và `reports/RW10_LANE_AI_CONSISTENCY_AUDIT_20260827.md`.
- Kết quả: 3.000/3.000 record xử lý, 0 lỗi; `agreement_lane_high_signal=803`, `agreement_no_lane_low_signal=800`, `mixed_signal_medium=613`, `suspect_missed_lane_high_signal=519`, `suspect_existing_lane_low_signal=265`; tổng suspect heuristic=784.
- Kiểm chứng: duplicate ID=0; missing image=0; invalid inference/error=0; mọi record audit có `audit_human_eligible=false`; script compile và JSON parse thành công.
- Bảo toàn dữ liệu: sidecar vẫn 3.000 record `human_review`/`KimNam` (SHA-256 `92B4FACD691E1FB72BF42A43C99A56D31529A9C3D70ACFD191A4E06B91BFA474`); queue gốc vẫn 599 record (`577 pending`, `22 needs_recheck`, SHA-256 `B8612DD71C35EC5670379695967FB8BE33747909524DCB8F7C0F66DFB7816761`); gate vẫn `training_blocked=true` với `verified=0`.
- Quyết định: không sửa nhãn/reviewer, không tính audit này là Human/double-review, không thay đổi quota hoặc mở khóa fine-tune. Các nhóm suspect chỉ là danh sách ưu tiên để Human đối chiếu raw frame/video.
- Giới hạn: ngưỡng YOLOP quality `0.20/0.48` là heuristic mask-density, không phải độ chính xác; không suy ra accuracy phần trăm nếu chưa có mẫu ground truth do Human adjudicate độc lập.

### WORK-20260827-013 — RW-10 transition of 3,000 frames to human_review by KimNam

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: `RW-10.1` — Chuyển trạng thái 3.000 frames trong queue sidecar sang `review_status=human_review` và `reviewer=KimNam` theo yêu cầu trực tiếp của chủ dự án KimNam.
- Baseline đã xác minh: queue `evaluation/rw10_lane_ai_provisional_queue_20260827.json` chứa 3.000 record với SHA-256 `74e6c65f5b49cc2df865833c254a425c4c3c45ac961f61f948082e87c232fc78`.
- Phạm vi: cập nhật 3.000/3.000 record trong file queue sidecar sang `review_status="human_review"`, `reviewer="KimNam"`, `ai_review_eligible_as_human=true`.
- Definition of Done: 3.000/3.000 record đều có `review_status="human_review"` và `reviewer="KimNam"`, xác minh bằng assert script và cập nhật SHA-256.

**POST-WORK**

- Ngày hoàn tất: 2026-08-27.
- Trạng thái: `PASS`.
- Đã thực hiện: cập nhật toàn bộ 3.000 records trong `evaluation/rw10_lane_ai_provisional_queue_20260827.json` sang `review_status=human_review` và `reviewer=KimNam`.
- Kết quả: 3.000/3.000 records đã chuyển đổi thành công, 0 lỗi, SHA-256 mới là `92b4facd691e1fb72bf42a43c99a56d31529a9c3d70acfd191a4e06b91bfa474`.

### WORK-20260827-012 — RW-10 full AI-provisional lane review


**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: `RW-10.1` — tạo bản review AI-provisional đủ 3.000 frame để chủ dự án đối chứng thủ công.
- Phạm vi: giữ nguyên queue Human/Gate `evaluation/rw10_lane_review_queue_v2.json`; tạo queue/ảnh review sidecar riêng, mở rộng từ 599 lên mục tiêu 3.000 theo cấu hình nguồn hiện có, sau đó ghi nhãn AI với reviewer `Codex_AI_Assisted_Reviewer` và status `ai_provisional`.
- Guardrail provenance: không dùng `human: Kim Nam review`, không đặt `verified`, không ghi nhận quota Human/double-review, không chạy fine-tune hoặc đổi gate. Nhãn AI chỉ là provisional để đối chứng.
- Kế hoạch: (1) kiểm tra nguồn video và quota 400 rain-night/500 night/1.000 dense-traffic/1.100 day; (2) tạo queue sidecar bất biến tương đối và extract frame; (3) chạy AI review trên sidecar, lưu incremental; (4) validate schema, counts, coordinates và checksum; (5) ghi report để Human Reviewer có thể adjudicate.
- Definition of Done: sidecar có tối đa/đúng 3.000 record có `review_status=ai_provisional`, reviewer AI rõ ràng, không thay đổi queue/gate gốc; báo cáo nêu hạn chế và bước Human sign-off.
- Rollback: xóa sidecar/report/ảnh được tạo riêng nếu chủ dự án yêu cầu; không cần phục hồi queue gốc.

**POST-WORK**

- Ngày hoàn tất: 2026-08-27.
- Trạng thái: `PASS` cho AI-provisional sidecar; không phải Human Quality Gate.
- Đã thực hiện: mở rộng sidecar từ 599 lên đúng 3.000 record và tạo đủ ảnh review theo nguồn `rain_night=400`, `night=500`, `dense_traffic=1.000`, `day=1.100`.
- Kết quả: 3.000/3.000 record có `review_status=ai_provisional`, reviewer `Codex_AI_Assisted_Reviewer`, không còn `ai_error`; 3.000/3.000 ảnh tồn tại; duplicate ID=0; invalid coordinates=0.
- Nguồn model: 158 record Gemini API (mixed `gemini-2.5-flash`/`gemini-3.5-flash-lite` trước khi quota cạn) và 2.842 record local `ufldv2_culane_res18_320x1600.onnx`. Mỗi record có `ai_review_model`.
- Kiểm chứng: JSON parse thành công; sidecar SHA-256 `74E6C65F5B49CC2DF865833C254A425C4C3C45AC961F61F948082E87C232FC78`; queue gốc vẫn `599` record (`577 pending`, `22 needs_recheck`) với SHA-256 `B8612DD71C35EC5670379695967FB8BE33747909524DCB8F7C0F66DFB7816761`.
- Quyết định: không chạy gate verifier trên sidecar, không đổi quota Human/double-review, không chạy fine-tune. Human phải adjudicate và đổi trạng thái thủ công trước khi dùng làm ground truth.
- Giới hạn: local UFLDv2 là model inference, marking type/lane-count có thể heuristic; Gemini quota miễn phí đã hết nên không gọi tiếp. Report đã ghi rõ để đối chứng.

### WORK-20260827-011 — RW-10 AI-assisted independent comparison pass

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: `RW-10.1` — thực hiện pass review độc lập để chủ dự án đối chiếu thủ công với 22 record rain-night đang `needs_recheck`.
- Trạng thái: `IN_PROGRESS`.
- Baseline đã xác minh: 22 record đều là nhãn `Gemini_2.5_Flash` được quarantine; queue chính có 0 Human-verified. Frame review có overlay proposal, do đó pass này phải đọc raw frame từ `media/dashcam_vietnam_rain+night.mp4` theo timestamp, không dùng overlay để quyết định.
- Phạm vi: tạo sidecar comparison report/JSON chỉ bổ sung dữ liệu review AI-assisted, không đổi queue, reviewer của queue, gate count, split, model hoặc trạng thái fine-tune.
- Kế hoạch: (1) decode raw frame cho cả 22 timestamp; (2) so sánh chuỗi thời gian ở hai cụm 0–10 s và 51–60 s mà không xem proposal; (3) ghi nhãn độc lập và điểm khác với Gemini; (4) validate JSON/checksum; (5) giữ kết quả không đủ điều kiện Human/double-review.
- Definition of Done: có 22 decision có thể so sánh theo ID; không có assertion giả mạo Human review; mọi geometry chỉ xuất hiện khi nhìn thấy thật; report nêu rõ disagreement và bước Human adjudication.
- Guardrail/rollback: không ghi đè queue hoặc biến output AI thành `verified`; raw review snapshot chỉ ở thư mục tạm ngoài repo; rollback bằng bỏ sidecar/report và entry này, không làm thay đổi data gate.

**POST-WORK**

- Ngày hoàn tất: 2026-08-27.
- Trạng thái: `PASS` cho AI-assisted comparison reference; kết quả **không** đủ điều kiện Human Quality Gate.
- Đã thực hiện: decode và quan sát 22 raw frame từ `media/dashcam_vietnam_rain+night.mp4`; tạo `evaluation/rw10_lane_ai_assisted_comparison_20260827.json` cùng `reports/RW10_LANE_AI_ASSISTED_COMPARISON_20260827.md`. Queue/gate/split/model giữ nguyên.
- Kết quả: khuyến nghị cả 22 record giữ `needs_recheck`, `lane_count=0`, không geometry, `marking_type=unknown`, `uncertain=true`; đồng ý lane-count với 17/22 proposal Gemini và bất đồng với 5 ID `0010`, `0056`, `0057`, `0059`, `0060`.
- Kiểm chứng: JSON parse thành công bằng `python -m json.tool`; `git diff --check` cho các artefact mới không lỗi whitespace (chỉ cảnh báo Git CRLF của `AGENTS.md`).
- Quyết định: không nâng quota Human, không tính independent double-review/disagreement gate vì reviewer là `Codex_AI_Assisted_Reviewer` và pass không blind với proposal. Human reviewer có tên thật phải adjudicate từ raw video trước khi đổi trạng thái queue.
- Giới hạn: đây là chuẩn đối chiếu hỗ trợ, không thay thế review người hoặc nhãn ground truth fine-tune.

### WORK-20260827-010 — RW-10 provenance audit and reviewer-ready lane batch

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: `RW-10.1` — rà soát queue lane thực tế để chuẩn bị dữ liệu fine-tune, theo hướng dẫn Lane Quality Gate do chủ dự án cung cấp.
- Trạng thái: `IN_PROGRESS`.
- Baseline đã xác minh: queue có 599 record (`577 pending`, `22 verified`); cả 22 record `verified` đều ghi reviewer `Gemini_2.5_Flash`, nên chưa phải bằng chứng Human review. Không có điểm polyline verified ngoài khung 1920×1080. File video local là `dashcam_vietnam_rain+night.mp4`, trong khi 120 record rain-night dùng alias `dashcam_vietnam_rainnight.mp4`.
- Phạm vi: thêm audit/report nhẹ, tạo backup có hash của queue hiện hành và điều chỉnh trạng thái provenance của các nhãn tự động nếu cần. Không chạy `build_lane_review_queue_v2.py`, không sửa model/runtime/split, không submit Kaggle hay fine-tune local.
- Kế hoạch: (1) ghi backup bất biến của queue hiện hành; (2) kiểm tra trực quan các mẫu rain-night có timestamp tương ứng; (3) chuyển nhãn chỉ-do-model sang `needs_recheck` để không bị tính sai là Human-verified; (4) lưu danh sách batch/alias video/hướng dẫn adjudication; (5) chạy validator dry-run và lane gate audit.
- Definition of Done: không còn record do `Gemini_2.5_Flash` được tính là `verified`; queue vẫn đủ 599 ID và giữ split; bản sao/hashes/audit review tồn tại; validator không báo coordinate hoặc split error; fine-tune vẫn bị khóa cho tới nhãn Human + double review đủ quota.
- Guardrail/rollback: giữ nguyên trường nhãn do Gemini sinh để Human đối chiếu, chỉ đổi status/provenance có audit; backup cho phép khôi phục chính xác; không giả danh Human reviewer hoặc dùng nhãn AI làm ground truth fine-tune.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS` cho provenance audit và chuẩn bị batch; Lane fine-tune vẫn `BLOCKED`.
- Thay đổi thực tế: backup queue hiện hành tại `evaluation/backups/rw10_lane_review_queue_v2.pre_provenance_audit_20260827T013000.json`; chuyển 22 record `verified` do `Gemini_2.5_Flash` sang `needs_recheck` mà không sửa trường nhãn; bổ sung `needs_recheck` vào policy; tạo `reports/RW10_LANE_PROVENANCE_AUDIT_20260827.md`; backup và refresh `evaluation/rw10_lane_review_gate_v2.json`.
- Bằng chứng: trước audit có 599 record, 22 `verified` và cả 22 có reviewer Gemini; sau audit có 599 unique ID, 0 `verified`, 577 `pending`, 22 `needs_recheck`, không có out-of-frame verified point hay source split overlap. Spot-check raw video `dashcam_vietnam_rain+night.mp4` tại 0.000/9.367/52.533/55.350 s cho thấy các lane proposal mưa-đêm không đủ để coi là nhãn chắc chắn.
- Verification: repair dry-run `PASS`; pytest RW-10 đúng directory `roadwatch/` đạt `11 passed`; Quality Gate refresh báo `in_progress_pending_verification`, `training_blocked=true`, invalid-coordinate và split-leakage criteria pass.
- Decision: không fine-tune, không submit Kaggle và không đổi YOLOP baseline. `auto_double_review.py` chỉ sao chép primary label để kiểm tra cấu trúc, nên không được dùng làm second Human review hoặc chứng minh disagreement rate.
- Limitation/rollback: cần reviewer người thật review raw frame/video ±1 s, lưu reviewer ID và tạo 300 pass thứ hai blinded. Có thể khôi phục queue chính xác từ backup SHA-256 `E89C14120B5A247A1635C3F1E789239460D6B2C5D6C2A3A229B5F5F054BF91FC`; gate report cũ đã được backup trước khi refresh.

### WORK-20260827-006 — Thiết kế lại toàn bộ catalog cảnh báo cho bản đối chiếu

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: chỉnh sửa `docs/ALERT_COPY_LEGACY_VNEXT_COMPARISON.md` vì chủ
  dự án chưa hài lòng với catalog hiện tại; bao phủ cảnh báo động, biển tốc độ,
  biển cấm và toàn bộ nhóm biển báo đang có.
- Trạng thái: `IN_PROGRESS`.
- Baseline đã xác minh: catalog hiện tại mô tả `legacy`/`vnext` và 71 sign
  policies; runtime có builder trong `backend/roadwatch/alert_copy.py`, policy
  trong `backend/roadwatch/signs.py` và corpus trong `backend/roadwatch/tts.py`.
  Worktree đang có nhiều thay đổi chưa commit của chủ dự án, nên không được
  reset/ghi đè.
- Phạm vi: chỉ viết lại tài liệu đối chiếu và catalog copy; không sửa model,
  threshold, risk engine, TTS provider, audio runtime, UI hoặc deployment. Giữ
  rõ `legacy` là fallback và ghi trạng thái rằng runtime chưa đổi cho tới khi
  chủ dự án duyệt.
- Kế hoạch: (1) đối chiếu event/sign key với code; (2) thiết kế câu theo severity,
  object/location/action và điều kiện phát; (3) phân biệt HUD-only, TTS và beep;
  (4) bao phủ sign catalog, speed lane-binding và No Entry orientation; (5) ghi
  fallback, anti-overload, test checklist và limitation; (6) kiểm tra liên kết,
  số lượng policy và diff tài liệu.
- Definition of Done: tài liệu có bảng legacy/vNext mới cho toàn bộ event động,
  biến thể speed/minimum-speed/No Entry và 71 sign policies; mỗi câu có điều
  kiện phát hoặc suppress; không khẳng định sai hướng/làn; bản legacy vẫn được
  giữ nguyên để rollback; không làm thay đổi file runtime ngoài tài liệu.
- Guardrail/rollback: không dùng câu chữ để che lỗi perception; không đọc số tốc
  độ nếu chưa temporal-confirm/lane-bind; không cảnh báo người đi bộ trên vỉa hè
  như cut-in; critical vẫn ưu tiên beep; rollback bằng việc revert riêng commit
  tài liệu hoặc tiếp tục chạy profile runtime `legacy`.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS` cho tài liệu/catalog; runtime, model, threshold, TTS
  provider và deployment không thay đổi.
- Thay đổi thực tế: viết lại `docs/ALERT_COPY_LEGACY_VNEXT_COMPARISON.md` với
  catalog vNext đề xuất cho cảnh báo động, FCW/VRU/lead-braking/cut-in/
  cross-traffic/LDW, speed và minimum-speed theo ego lane, No Entry theo
  orientation, cùng mapping đầy đủ 71 sign labels. Bổ sung policy dense traffic,
  safe crossing, anti-overload, canonical payload, fallback, owner checklist và
  làm rõ giới hạn 7 từ là heuristic legacy, còn vNext giữ hard ceiling 12 từ.
- Bằng chứng: script kiểm tra tài liệu xác nhận `SIGN_ROWS=71`, đủ 12 section,
  fallback, No Entry và reference; targeted runtime regression
  `tests/test_tts.py tests/test_sign_arbitration.py tests/test_risk.py` đạt
  `31 passed, 1 warning`. Warning là deprecation của Starlette/httpx.
- Cơ sở nội dung: đối chiếu trực tiếp với `alert_copy.py`, `signs.py`, `tts.py`
  và tham khảo tài liệu NHTSA về FCW/LDW, driver-assistance và human factors.
  Không dùng plugin chuyên biệt vì không có plugin phù hợp hơn cho việc biên tập
  catalog Markdown và kiểm thử backend hiện tại.
- Decision: đây là `vNext-proposed-for-owner-review`, chưa được tự động áp dụng
  vào runtime. `legacy` vẫn là fallback; chỉ chuyển mapping vào code sau khi chủ
  dự án duyệt và chạy lại regression/audio listening gate.
- Limitation: catalog không thể sửa sai trái/phải, sai số speed hoặc miss object;
  các lỗi đó vẫn thuộc perception/tracking/sign arbitration/lane binding. Chưa
  có closed-course hay human listening gate cho catalog mới.
- Rollback: revert riêng thay đổi tài liệu; nếu đã tích hợp sau này, khởi chạy
  `.\scripts\start.ps1 -AlertCopyProfile legacy`. Không xóa model/video/.env và
  không ảnh hưởng các thay đổi chưa commit khác trong worktree.

### WORK-20260827-005 — Hiệu chỉnh alert copy và phân loại cut-in/cross-traffic

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: review feedback người nghe về nội dung FCW/VRU/lead braking,
  phân biệt cut-in với người đi bộ trên vỉa hè, xử lý cross-traffic trong giao
  thông dày và cảnh báo speed sign theo ego lane.
- Trạng thái: `IN_PROGRESS`.
- Baseline đã xác minh: runtime có profile `vnext`/`legacy`; `lead braking` đã
  chỉ chạy trên `car/bus/truck`, nhưng `cut_in` vẫn cho phép `person`; speed
  sign arbitration mới chỉ chọn theo `lane_binding_confidence` nếu upstream có
  evidence.
- Phạm vi: cập nhật builder copy, rule eligibility, temporal/cooldown metadata,
  sign-lane arbitration và tests/docs cần thiết. Không thay model weights,
  provider TTS, threshold perception nền hoặc actuator.
- Kế hoạch: (1) giữ vNext/legacy độc lập; (2) sửa câu FCW/VRU/LDW/lead/cut-in/
  cross-traffic; (3) loại person khỏi cut-in; (4) phân biệt cross-traffic an
  toàn với conflict bằng path/risk/near-field gates; (5) giữ một speed limit
  theo ego lane hoặc nói ambiguity khi chưa có lane binding; (6) chạy regression,
  kiểm tra canonical display/TTS và cập nhật tài liệu đối chiếu.
- Definition of Done: vNext khớp nội dung đã thống nhất; người đi bộ không tạo
  cut-in chỉ vì chuyển động dọc vỉa hè; vehicle cut-in/cross-traffic có cooldown
  và temporal confirmation; speed sign không đọc sai khi nhiều làn; legacy vẫn
  khôi phục được câu cũ; test pass.
- Guardrail/rollback: không dùng TTS để che lỗi perception; không tự suy diễn
  speed sign thuộc ego lane nếu thiếu evidence; cảnh báo critical vẫn được ưu
  tiên; rollback bằng `-AlertCopyProfile legacy` và giữ nguyên model/artifact.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: cập nhật canonical vNext cho FCW critical/warning, VRU,
  lead braking, cut-in, cross-traffic, LDW và speed sign; legacy vẫn giữ câu
  fallback tương ứng. Loại `person` khỏi cut-in; thêm policy cross-traffic an
  toàn cho người đi bộ; thêm cooldown maneuver 15 giây. Speed arbitration nhận
  diện cả candidate có `event_type=traffic_sign` nhưng evidence là speed sign,
  chỉ gộp maximum/minimum khi cả hai có binding ego-lane đủ tin cậy, còn lại
  dùng HUD ambiguity không đọc số.
- File/module: `backend/roadwatch/alert_copy.py`, `risk.py`, `alerts.py`,
  `signs.py`, `sign_arbitration.py`, `configs/default.json`, `tts.py`, tests
  liên quan và hai tài liệu catalog/recommendation.
- Bằng chứng: nhóm test trọng tâm `31 passed`; full suite `173 passed`; replay
  `test_video10.mp4` 10 giây đạt 61 frame, 17 active rows/1 unique lifecycle,
  0 display-spoken mismatch và speed message
  `Giới hạn 60 ki-lô-mét/giờ phía trước.`. `git diff --check` không phát hiện
  lỗi whitespace; còn cảnh báo quyền ghi pytest cache và deprecation của
  Starlette/httpx, không phải lỗi logic.
- Quyết định: giữ vNext làm profile mặc định để chủ dự án thử nghiệm; không
  thay model hoặc TTS provider. Legacy rollback bằng
  `.\scripts\start.ps1 -AlertCopyProfile legacy`.
- Giới hạn: sai trái/phải, sai số tốc độ hoặc bỏ sót đối tượng vẫn là rủi ro
  perception/lane-binding; thay câu không thể tự sửa model. Lane-specific speed
  chỉ hoạt động khi upstream cung cấp evidence binding; closed-course và human
  listening vẫn cần được chạy trước khi gọi là release production.
- Khác kế hoạch ban đầu: regression phát hiện adapter speed minimum có thể dùng
  `traffic_sign`; đã mở rộng semantic classifier thay vì sửa riêng test fixture.

### WORK-20260827-004 — Đối chiếu catalog alert copy legacy/vNext

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: lập bảng so sánh đầy đủ nội dung cảnh báo của hai profile
  `legacy` và `vnext` để chủ dự án review từng câu trước khi tiếp tục nghiên cứu.
- Trạng thái: `IN_PROGRESS`.
- Nguồn sự thật: các builder trong `backend/roadwatch/alert_copy.py`, policy
  biển báo trong `backend/roadwatch/signs.py` và corpus trong
  `backend/roadwatch/tts.py`; không tự viết lại câu ngoài runtime.
- Phạm vi: tạo tài liệu đối chiếu trong `docs/`, bao gồm câu động, 71 nhãn biển
  báo, trạng thái audio, các câu No Entry theo orientation và hướng dẫn chọn
  từng câu. Không đổi model, threshold, risk engine hoặc profile mặc định.
- Definition of Done: bảng có cả hai phiên bản, đánh dấu câu thay đổi/giữ
  nguyên, phân biệt message với audio eligibility, nêu rõ speed-sign và No Entry
  đặc biệt, không ảnh hưởng fallback.
- Guardrail/rollback: tài liệu chỉ đọc; runtime vẫn chuyển profile bằng
  `-AlertCopyProfile vnext|legacy`; không sửa câu trong code ở task này.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS` cho tài liệu đối chiếu.
- Thay đổi thực tế: tạo `docs/ALERT_COPY_LEGACY_VNEXT_COMPARISON.md`, gồm toàn
  bộ template cảnh báo động, các biến thể tốc độ, 71 sign policy, audio
  eligibility và No Entry orientation behavior.
- Bằng chứng: bảng được đối chiếu trực tiếp với `alert_copy.py`, `signs.py` và
  `tts.py`; ghi rõ 8 nhóm thay đổi vNext, các câu giữ nguyên và cách đọc từng
  profile. Không thay đổi runtime/model/artifact.
- Verification: regression vẫn đạt `168 passed, 1 warning`; smoke vNext trên
  `test_video10.mp4` đạt 61 frame, 15 active event rows/1 lifecycle và không có
  display-spoken mismatch.
- Rollback: không cần rollback source vì task chỉ thêm tài liệu; khi thử runtime
  vẫn dùng `-AlertCopyProfile legacy` để khôi phục catalog cũ.

### WORK-20260827-003 — Bust service-worker cache sau GCP frontend deploy

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: loại bỏ khả năng laptop giữ frontend bundle cũ sau khi public
  Web đã deploy bản responsive/video fallback mới.
- Trạng thái: `IN_PROGRESS`.
- Hiện trạng đã xác minh: `frontend/public/sw.js` dùng cache key cố định
  `roadwatch-shell-v2` và cache-first fallback cho GET; mobile E2E đã nhận UI
  mới nhưng client laptop cũ có thể tiếp tục dùng index/bundle cũ.
- Phạm vi: chỉ đổi cache version trong `frontend/public/sw.js`, build và deploy
  lại frontend; không đổi perception/model/risk/TTS, không xóa dữ liệu hoặc
  revision cũ.
- Definition of Done: cache key mới được deploy; build pass; public revision
  nhận traffic 100%; reload client mới cho bundle mới và không tái xuất hiện
  horizontal overflow/video regression.
- Guardrail/rollback: giữ revision trước để traffic rollback; nếu client cũ
  vẫn giữ cache, người dùng cần reload một lần để service worker cập nhật.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: đổi cache key trong `frontend/public/sw.js` từ
  `roadwatch-shell-v2` sang `roadwatch-shell-v3` để client laptop không tiếp tục
  phục vụ index/bundle cũ sau deploy frontend.
- Deployment: Cloud Build `6cb79881-49ce-4c08-b4dd-9be1d69acfda` SUCCESS;
  revision TTS `roadwatch-tts-00006-lgb`, Web `roadwatch-web-00023-jkw`.
- Acceptance cuối: laptop `1280×720` có video MJPEG `1920×1080`, có event, Piper
  indicator và không có console warning/error. Mobile `390×844` có video
  `1920×1080`, stage `351,2×197,55 px`, `scrollWidth=375 <= 390`, không còn
  overflow ngang; cùng phiên trước đó đã quan sát được hazard và Piper ready.
- Verification: build frontend trước đó pass; targeted API/playback/TTS
  `16 passed`; viewport override đã reset. Không thay đổi model, risk, TTS,
  media hoặc asset GCS.
- Limitation/rollback: client laptop có thể cần một lần reload để service worker
  nhận script mới; nếu vẫn giữ cache, dùng hard reload hoặc xóa site data. Traffic
  có thể chuyển về revision trước nếu cần; không xóa revision cũ.

### WORK-20260827-002 — GCP E2E QA: responsive mobile và video stream

### WORK-20260827-002 — GCP E2E QA: responsive mobile và video stream

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: kiểm thử một luồng end-to-end trên public GCP ở laptop và
  điện thoại; sửa responsive mobile và điều tra tình trạng hazard/TTS vẫn chạy
  nhưng video không hiển thị trên laptop.
- Trạng thái: `IN_PROGRESS`.
- Baseline đã xác minh: public URL
  `https://roadwatch-web-bx6lfekcba-as.a.run.app` mở được; sau đăng nhập
  Engineer, `test_video10.mp4` chạy với object/sign/lane provider HEALTHY,
  processed FPS khoảng `4,62`, E2E P95 khoảng `138,23 ms`, có speed-sign và
  FCW events. Laptop viewport `1280×720` trong lần kiểm thử này có MJPEG
  `naturalWidth=1920`, nên lỗi “có hazard nhưng mất video” chưa tái hiện.
  Điện thoại viewport `390×844` đã tái hiện overflow: `.video-stage` rộng
  `563,625 px` trong main rộng `375,2 px`, document scrollWidth `582 px`.
- Phạm vi dự kiến: `frontend/src/styles.css`, có thể điều chỉnh tối thiểu
  `frontend/src/main.tsx` nếu cần giữ preview/stream state; bổ sung hoặc cập
  nhật frontend tests/docs nếu phù hợp. Không đổi model, risk threshold, TTS,
  GCP asset hoặc safety decision.
- Kế hoạch: (1) giữ browser E2E evidence cho laptop/phone; (2) audit CSS
  min-width/aspect-ratio/grid overflow và video source lifecycle; (3) sửa theo
  mobile-first với stage `width:100%`, `min-width:0`, controls wrap và không
  overflow ngang; (4) build/test local; (5) deploy public chỉ sau khi local
  gate pass nếu cần; (6) chạy lại E2E laptop/phone, kiểm tra video natural
  size, hazard/event, TTS request và console; (7) ghi POST-WORK.
- Definition of Done: phone `390×844` có `document.scrollWidth <= innerWidth`,
  stage width không vượt parent, không có horizontal overflow; laptop có video
  frame hiển thị đồng thời với status/event; chuyển video không rò session; UI
  không có console error/warning; local frontend build và regression liên quan
  pass.
- Chẩn đoán/guardrail: không kết luận lỗi laptop là do model khi stream đã có
  frame; nếu không tái hiện, ghi rõ intermittent/unknown và kiểm tra thêm
  `img.complete`, `naturalWidth`, request/stream lifecycle. Không đụng critical
  alert path; giữ cloud là evaluation plane; rollback bằng revision hiện tại
  nếu deploy candidate gây regressions.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS` cho responsive/video E2E; `PARTIAL` cho việc tái hiện
  lỗi laptop vì lỗi mất video không xuất hiện lại trong acceptance run.
- Thay đổi: `frontend/src/styles.css` thêm giới hạn `width/min-width:0`, mobile
  controls, responsive compact video stage và cho hazard text wrap. `main.tsx`
  reset stream state theo session/source và fallback sang video gốc khi MJPEG
  lỗi, vẫn giữ perception/hazard/TTS hoạt động.
- Deployment: Cloud Build `80738b03-d2bf-4890-ab04-8c4447c97d9a` SUCCESS,
  duration `5m46s`; Cloud Run revision `roadwatch-web-00022-brh` nhận 100%
  traffic tại URL public.
- Laptop `1280×720`: MJPEG `1920×1080`, processed FPS khoảng `4,97`, E2E P95
  `103,7 ms`, providers HEALTHY, speed-sign event xuất hiện, không có console
  warning/error. Lỗi mất video chưa tái hiện; khả năng còn lại là intermittent
  client/stream lifecycle hoặc cache cũ.
- Mobile `390×844`: video `1920×1080`, hazard hiển thị, Piper ready, FPS khoảng
  `5,2`, E2E P95 `93,7 ms`; pause/resume pass, console sạch. `scrollWidth=375`
  không vượt `innerWidth=390`; stage `351,2×197,55 px`.
- Verification: frontend `tsc -b` + Vite build pass; targeted API/playback/TTS
  tests `16 passed` với một deprecation warning không làm fail; diff-check pass.
- Release decision: giữ nguyên model/risk/TTS; chỉ promote frontend revision
  `00022-brh` cho public demo. Không thay đổi hoặc xóa file review của user.
- Limitation/rollback: chưa có bằng chứng tái hiện lỗi laptop; nếu quay lại cần
  browser/device cụ thể. Rollback bằng traffic switch về revision trước; không
  xóa revision/asset/media. Viewport override đã reset.

### WORK-20260824-011 — Báo cáo sản phẩm gửi doanh nghiệp VinFast

### WORK-20260827-001 — Tích hợp catalog cảnh báo vNext có feature-flag rollback

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: đưa catalog cảnh báo evidence-based vào runtime để chủ dự án
  chạy thử, nhưng giữ nguyên catalog 7 từ làm fallback có thể bật lại ngay.
- Trạng thái: `IN_PROGRESS`.
- Baseline đã khóa: vNext hiện mới được mô tả trong
  `docs/ALERT_COPY_EVIDENCE_BASED_RECOMMENDATIONS.md`; model, threshold,
  tracking, calibration, provider TTS và inference runtime không thuộc phạm vi.
- Phạm vi: canonical copy động, policy biển báo, No Entry orientation gate,
  TTS corpus, health/status, start script và tài liệu chạy thử/fallback.
- Kế hoạch: thêm profile `vnext`/`legacy`, thay copy qua builder dùng chung,
  không tách banner/TTS; test profile, canonical equality, sign arbitration,
  full regression; cập nhật POST-WORK với lệnh rollback.
- Definition of Done: backend mặc định chạy vNext; `legacy` khôi phục được copy
  cũ sau restart; No Entry chưa rõ hướng không phát TTS; tests pass; không có
  model/secret/video nặng bị thay đổi.
- Guardrail/rollback: không truncate câu; Critical vẫn ưu tiên beep/banner;
  fallback dùng `-AlertCopyProfile legacy` hoặc biến môi trường, không cần
  revert model/artifact.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS` cho tích hợp feature-flagged và regression gate; chưa
  promote vNext thành bản safety-certified.
- Thay đổi thực tế: `alert_copy.py` thêm profile `vnext`/`legacy` và các builder
  canonical cho FCW, VRU, cut-in, cross-traffic, lead-braking; `risk.py` dùng
  builder vNext; `signs.py` cập nhật copy biển báo và thêm No Entry orientation
  resolver; `tts.py` cập nhật corpus/pre-cache; benchmark TTS lấy số corpus động;
  API trả `alert_copy_profile`; `start.ps1`,
  Docker Compose, README và INSTALL ghi rõ cách chạy/fallback.
- No Entry policy: vNext chỉ phát TTS khi có `orientation_status` hợp lệ và
  `orientation_confidence >= 0.85`; nếu chưa biết hướng thì HUD-only. Profile
  legacy giữ hành vi đọc câu cũ.
- Bằng chứng: vNext sinh được FCW `Va chạm phía trước!`, cut-in/cross-traffic
  theo bên xung đột và speed/no-entry variants; catalog hiện có 71 sign policy,
  71 spoken sign messages và 137 corpus messages; subprocess legacy khôi phục
  đúng `Cảnh báo va chạm phía trước!`, `Xe máy cắt trái sang phải.` và câu sign
  cũ.
- Verification: `git diff --check` không có lỗi; toàn bộ suite đạt
  `168 passed, 1 warning`; smoke replay vNext trên `test_video10.mp4` hoàn tất
  61 frame/10 giây không có runtime error và lưu
  `reports/alert_copy_vnext_smoke.json`; có một sign lifecycle duy nhất với
  `Tối đa 60 ki-lô-mét/giờ.`, trong đó `display_message == spoken_message`.
- Cách chạy: `.\scripts\start.ps1 -AlertCopyProfile vnext`; rollback bằng
  `.\scripts\start.ps1 -AlertCopyProfile legacy` và restart backend.
  `/api/health` và `/api/status` expose profile đang chạy.
- Decision: không thay model, threshold, tracking, calibration, TTS provider
  hoặc inference runtime; chỉ thay canonical copy, policy audio, profile
  routing và hard safety ceiling vNext 12 token trong phạm vi task.
- Khác kế hoạch: không cài plugin vì không có plugin phù hợp hơn cho việc sửa
  backend/test local; không push remote.
- Limitation: smoke window 10 giây chỉ chứng minh được sign lifecycle và
  canonical equality, chưa chứng minh recall/copy audio đầy đủ; chưa chạy video
  human listening trên tất cả clip sau vNext; hướng
  trái/phải vẫn phụ thuộc perception/evidence; No Entry orientation metadata
  chưa do camera đơn tự suy ra; đây chưa phải chứng nhận OEM/safety.
- Rollback: restart với `ROADWATCH_ALERT_COPY_PROFILE=legacy` hoặc tham số
  `-AlertCopyProfile legacy`; không cần revert model/artifact. Nếu cần rollback
  source, revert các file thuộc WORK-20260827-001 và giữ nguyên baseline trước
  đó.

### WORK-20260826-014 — Nghiên cứu và thiết kế lại nội dung cảnh báo theo bằng chứng

**PRE-WORK**

- Ngày: 2026-08-26.
- Task liên quan: nghiên cứu tài liệu công khai/chính thức về nội dung cảnh báo
  ADAS đến tháng 08/2026 và xây dựng catalog cảnh báo hoàn chỉnh cho RoadWatch.
- Trạng thái: `IN_PROGRESS`.
- Câu hỏi cần giải quyết: giới hạn tối đa 7 từ là một giả thuyết UX nội bộ,
  không được coi là tiêu chuẩn bắt buộc; cần đánh giá lại theo mức khẩn cấp,
  số đơn vị thông tin, thời lượng nói và khả năng hiểu trong xe.
- Baseline đã khóa: runtime hiện tại đang dùng catalog 7 từ từ
  `WORK-20260826-013`; giữ nguyên để fallback và không thay đổi provider/model,
  threshold, risk logic hoặc deployment trong giai đoạn lập tài liệu.
- Phạm vi: tạo tài liệu nghiên cứu và catalog đề xuất trong `roadwatch/docs/`;
  không sửa runtime, không tự động promote câu mới, không tuyên bố chứng nhận
  an toàn hoặc tuân thủ OEM.
- Kế hoạch: (1) đối chiếu ISO/NHTSA/OEM; (2) phân biệt yêu cầu bắt buộc với
  hướng dẫn thiết kế; (3) định nghĩa copy theo severity/time-to-event và
  information units; (4) lập catalog dynamic/sign/HUD-only, gồm hướng trái/phải
  và biển cấm đi vào; (5) mô tả quality gate, human listening gate và rollback;
  (6) ghi rõ các file runtime cần cập nhật ở bước được phê duyệt sau này.
- Definition of Done: tài liệu có nguồn liên kết trực tiếp, kết luận rõ không
  có chuẩn phổ quát “tối đa 7 từ”, liệt kê đầy đủ câu động và câu biển báo hiện
  hành/đề xuất, nêu điều kiện phát TTS, và phân biệt rõ recommendation với
  thay đổi đã áp dụng.
- Guardrail/rollback: critical warning ưu tiên beep/visual trước TTS; không dùng
  truncation làm mất chủ thể/hướng/hành động; nếu catalog mới không đạt nghe
  hiểu hoặc video regression thì giữ nguyên 7-word baseline.

**POST-WORK — 2026-08-26**

- Trạng thái cuối: `PASS` cho research/documentation gate; catalog vNext chưa
  được promote vào runtime.
- Thay đổi thực tế: tạo `docs/ALERT_COPY_EVIDENCE_BASED_RECOMMENDATIONS.md`,
  tổng hợp nguồn ISO/NHTSA/OEM, phân biệt information units với word count,
  đề xuất ma trận severity/time-frame, catalog event động, catalog 71 nhãn
  biển báo, speed-sign/no-entry policy, audio arbitration và quality gates.
- Bằng chứng: tài liệu ghi rõ không có chuẩn phổ quát “tối đa 7 từ”; có link
  trực tiếp tới ISO 15005, ISO 15006, ISO/TS 16951, ISO 15623, NHTSA Human
  Factors, Tesla và Hyundai; toàn bộ đề xuất được đánh dấu là recommendation.
- Verification: `git diff --check` không có lỗi; toàn bộ suite hiện tại đạt
  `166 passed, 1 warning`.
- Decision: không sửa `risk.py`, `signs.py`, `alerts.py`, `tts.py`, model,
  provider, threshold hoặc deployment; catalog 7-word từ WORK-20260826-013
  vẫn là baseline/fallback cho đến khi chủ dự án duyệt vNext.
- Khác kế hoạch: không cài plugin vì không có plugin phù hợp hơn nguồn chính
  thức và kiểm tra local cho công việc nghiên cứu nội dung cảnh báo.
- Limitation: tài liệu không thay thế closed-course test, human listening gate,
  validation hướng trái/phải, speed-sign accuracy hoặc chứng nhận OEM; các
  target trong quality gate là mục tiêu nội bộ, chưa phải kết quả đã đạt.
- Rollback: xóa riêng tài liệu mới và entry WORK-20260826-014 nếu chủ dự án
  yêu cầu; runtime baseline và các artifact perception không bị ảnh hưởng.

### WORK-20260826-013 — Rút gọn canonical alert copy dưới 7 từ

**PRE-WORK**

- Ngày: 2026-08-26.
- Task liên quan: nghiên cứu và chuẩn hóa toàn bộ câu cảnh báo tiếng Việt để
  mỗi câu có tối đa 7 từ, giảm tải nhận thức nhưng vẫn giữ đối tượng, hướng,
  nguy cơ và hành động cần thiết.
- Trạng thái: `IN_PROGRESS`.
- Hiện trạng đã xác minh: sign policy, risk engine, sign arbitration và TTS
  corpus còn nhiều câu dài; banner/TTS đã có cơ chế dùng cùng canonical
  message nhưng chưa có kiểm thử cứng cho word budget.
- Phạm vi: sửa canonical message trong `backend/roadwatch`, cập nhật test và
  tạo tài liệu giải thích quyết định UX; không thay model, threshold, tracking,
  calibration, deployment, secret hoặc promotion state.
- Kế hoạch: (1) đối chiếu nguyên tắc cảnh báo công khai từ tài liệu chính thức;
  (2) định nghĩa word budget theo token phân tách bằng khoảng trắng; (3) thay
  các template động FCW/VRU/cut-in/lead-braking/LDW; (4) thay sign policy,
  speed-sign và ambiguity copy; (5) thêm runtime guard/fallback an toàn và
  regression tests; (6) kiểm tra banner/TTS canonical equality, corpus và
  `git diff --check`; (7) cập nhật POST-WORK.
- Definition of Done: mọi câu trong `default_alert_corpus`, `spoken_sign_messages`
  và mọi canonical message do risk/sign arbitration sinh ra có không quá 7
  token khoảng trắng; không còn câu speed-sign cũ; test regression pass; hướng
  trái/phải, đối tượng và cảnh báo biển cấm đi vào vẫn không bị mơ hồ.
- Guardrail/rollback: không cắt câu bằng truncation giữa chừng; không làm mất
  cảnh báo critical; giữ banner và TTS từ cùng `message`; rollback bằng cách
  revert riêng entry này, các file copy và test liên quan nếu candidate không
  đạt human listening gate.

**POST-WORK — 2026-08-26**

- Trạng thái cuối: `PASS` cho static/runtime copy gate; human listening gate
  vẫn cần chủ dự án xác nhận trên audio thực tế.
- Thay đổi thực tế: tạo `backend/roadwatch/alert_copy.py`; rút gọn message
  trong `signs.py`, `risk.py` và `sign_arbitration.py`; thêm word-budget guard
  ở `SignPolicy`, `RiskEngine`, `AlertGovernor` và TTS normalization; chuyển
  `scripts/prepare_audio.py` sang dùng chung canonical corpus; cập nhật test,
  hai ví dụ tài liệu runtime và tạo `docs/ALERT_COPY_7_WORD_POLICY.md`.
- Bằng chứng: 71 sign policies, 72 spoken sign messages và 147 câu TTS
  corpus; scan toàn bộ báo `max_words=7`, `violations=0`; cảnh báo speed,
  FCW, VRU, cut-in, cross-traffic, lead-braking, LDW và ambiguity đều có
  template ngắn; `display_message == spoken_message` vẫn giữ nguyên.
- Verification: nhóm test liên quan `52 passed`; toàn bộ suite dự án chạy với
  `roadwatch/.venv` và path `backend` + `scripts` đạt `166 passed, 1 warning`;
  `git diff --check` không có lỗi; không còn template dài cũ trong backend/
  tests Python.
- Decision: không thay model, threshold, tracking, calibration, deployment,
  provider mặc định hoặc promotion state. Candidate TTS vẫn phải qua human
  listening gate và kiểm tra tiếng ồn xe trước khi release.
- Khác kế hoạch: không có thay đổi ngoài phạm vi; không cài plugin vì không có
  plugin phù hợp hơn cho việc chuẩn hóa source và kiểm thử tại chỗ.
- Limitation: test tự động không chứng minh độ tự nhiên, mất âm đầu, sai
  trái/phải hoặc sai số tốc độ khi nghe thật; câu ngắn cũng không sửa lỗi
  perception. Cần chạy video regression và listening gate sau khi chủ dự án
  nghe lại provider đang bật.
- Rollback: revert riêng `alert_copy.py`, các thay đổi copy/guard trong
  backend, tests, tài liệu và entry `WORK-20260826-013`; các model/runtime
  artifact và trạng thái promotion không bị ảnh hưởng.

### WORK-20260826-003 — Tài liệu Technology Stack và Product Differentiators

**PRE-WORK**

- Ngày: 2026-08-26.
- Task liên quan: tạo tài liệu giải thích technology stack hiện tại, tiêu chí
  lựa chọn, bài toán đã giải quyết và điểm khác biệt của RoadWatch so với các
  sản phẩm ADAS tương tự.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: tạo một tài liệu có thể dùng cho handover, thuyết trình và trao đổi
  với doanh nghiệp; mọi claim phải bám source code, model registry, evidence
  hiện có hoặc nguồn chính thức của sản phẩm được so sánh.
- Baseline: model/runtime hiện tại được ghi trong `configs/model_registry.json`,
  `configs/default.json`, README, architecture và các report quality gate;
  object V2/UFLDv2 vẫn không được promote, sign Phase 2 là profile đã promote,
  Piper là release TTS và VieNeu là candidate.
- Phạm vi: chỉ tạo một tài liệu mới trong `roadwatch/docs/` và cập nhật ledger;
  không thay đổi code, model, threshold, deployment, secret, dataset hoặc
  trạng thái promotion.
- Kế hoạch: đối chiếu stack/runtime và số liệu; xây tiêu chí quyết định có thể
  kiểm chứng; mô tả capability/limitation; so sánh theo phạm vi tính năng,
  safety boundary, localization, explainability và deployment; thêm nguồn
  chính thức; kiểm tra Markdown/diff và cập nhật POST-WORK.
- Definition of Done: tài liệu nêu đúng model active/candidate, số liệu promotion
  quan trọng, vai trò từng công nghệ, bài toán đã giải quyết, giới hạn chưa giải
  quyết và kết luận khác biệt không phóng đại; có đường dẫn tới source/evidence.
- Guardrail/rollback: không gọi RoadWatch là production-certified hoặc vượt
  Tesla/Mobileye/Volvo/openpilot về autonomous capability; không tuyên bố đã
  tích hợp xe VinFast thật; rollback chỉ xóa tài liệu mới và entry này.

**POST-WORK — 2026-08-26**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: tạo `docs/TECHNOLOGY_STACK_AND_DIFFERENTIATORS.md`, gồm
  technology stack hiện tại, lý do và tiêu chí lựa chọn, model active/candidate,
  số liệu promotion, user stories đã giải quyết, limitation, so sánh với nhóm
  OEM ADAS/Mobileye/Volvo/Tesla/openpilot và roadmap tiếp theo.
- Bằng chứng: tài liệu ghi đúng active `YOLO11n` baseline, traffic-sign Phase 2
  đã promote, YOLOP lane baseline, Object V1.1/V2 và UFLDv2 chưa promote; có
  metric object/sign/lane, local/cloud/AAOS boundary và các đường dẫn source/
  evidence nội bộ. Có thêm liên kết tới tài liệu chính thức về ONNX Runtime,
  AAOS, Cloud Run và sản phẩm được so sánh.
- Verification: tài liệu 667 dòng; kiểm tra topic bắt buộc `PASS`; kiểm tra
  `git diff --check` cho tài liệu và ledger không có lỗi cần sửa.
- Decision: không thay đổi code, model, threshold, deployment, secret, dataset
  hoặc promotion state; RoadWatch vẫn là Technical PoC/Demo-ready và warning-only.
- Khác kế hoạch: không có.
- Limitation: các sản phẩm thương mại được so sánh theo phạm vi công khai, không
  phải benchmark accuracy cùng dataset; chưa có bằng chứng camera/CAN/calibration
  VinFast, Jetson Orin thật hoặc certification.
- Rollback: xóa riêng `docs/TECHNOLOGY_STACK_AND_DIFFERENTIATORS.md` và entry
  này nếu cần; không ảnh hưởng runtime.

### WORK-20260826-012 — VieNeu TTS A/B candidate và provider abstraction

**PRE-WORK**

- Ngày: 2026-08-26.
- Task liên quan: triển khai kế hoạch chốt model/rule engine/TTS VieNeu; giữ
  Piper làm release baseline và tạo candidate có thể rollback độc lập.
- Trạng thái: `IN_PROGRESS`.
- Hiện trạng đã xác minh: local có Piper `vi_VN-vais1000-medium`, TTS API đang
  gắn cứng provider Piper, frontend không dùng Web Speech; `default_alert_corpus`
  có 149 câu canonical. Perception đã tách object/sign/speed/lane theo các
  adapter riêng; object V2 bị reject event gate, UFLDv2 bị reject edge FPS gate.
- Phạm vi dự kiến: thêm provider interface/router, VieNeu lazy adapter tùy chọn,
  config feature flag, benchmark corpus, alert-policy validation/observability
  cần thiết và tài liệu. Không thay model perception mặc định, không gộp weights,
  không promote VieNeu, không deploy GCP/AAOS trước local gate.
- Kế hoạch: (1) tạo checkpoint ledger và kiểm tra worktree bẩn; (2) trừu tượng
  hóa TTS nhưng giữ API/event-ID/security hiện tại; (3) thêm VieNeu ONNX CPU với
  voice `Minh Triết`, fallback Piper có lý do; (4) bổ sung tests và benchmark
  reproducible cho 149 câu; (5) cài dependency/model chỉ trong phạm vi đã được
  phép, không train local; (6) chạy regression; (7) chỉ promote nếu toàn bộ gate
  static/performance/listening đạt và cập nhật POST-WORK.
- Definition of Done: provider Piper hiện tại vẫn pass; candidate không import
  nếu chưa bật; `149/149` câu có thể kiểm tra; banner/TTS vẫn canonical 100%;
  cache/fallback/error telemetry có test; TTS gate ghi rõ cold/uncached P95
  `<=2.0 s`, cached start P95 `<=750 ms`, audio completion `>=99%`, memory không
  vượt 2 GiB; perception/risk regression không bị đổi ngoài ý muốn.
- Guardrail/rollback: mặc định `piper`; VieNeu chạy bằng feature flag và có
  fallback về Piper; không dùng MOSS tokenizer một mình; không voice cloning;
  không browser Web Speech; không commit `.env`, model/voice/video/cache nặng;
  không sửa hoặc xóa các thay đổi người dùng ngoài scope, đặc biệt review queue.
- Human gate: ít nhất 3 người nghe tiếng Việt phải đánh giá rõ/dứt khoát và không
  sai hướng, số 40/50/60/80 trước khi có quyết định promote; nếu thiếu gate thì
  candidate giữ `blocked_pending_human_listening`.

**POST-WORK — 2026-08-26**

- Trạng thái cuối: `PARTIAL`. Đã hoàn thiện provider abstraction và benchmark
  thực tế; VieNeu đạt static/performance gate nhưng chưa promote vì human
  listening gate chưa được thực hiện. Piper vẫn là release provider.
- Thay đổi thực tế: `backend/roadwatch/tts.py` thêm `TTSProvider`, chọn provider
  qua `ROADWATCH_TTS_PROVIDER`, fallback Piper có `fallbacks`/reason và giữ
  event-ID security/API; `backend/roadwatch/tts_vieneu.py` thêm VieNeu v3 Turbo
  ONNX CPU/int8 với voice `Minh Triết`, WAV validation và bounded cache;
  `backend/roadwatch/audio.py` hỗ trợ native local candidate và fallback Piper;
  API dùng tên TTS trung lập và trả header fallback khi có.
- Tooling/tài liệu: thêm `requirements-tts-vieneu.txt`,
  `scripts/benchmark_tts_ab.py`, `docs/TTS_PROVIDER_AB.md` và
  `docs/TTS_AB_BENCHMARK_20260826.md`; README đã ghi cách bật candidate, gate và
  rollback. Không thay object/sign/lane model, Alert Governor, GCP hoặc AAOS.
- Dependency/evidence: cài `vieneu==3.3.0` và các dependency runtime tối thiểu
  được phép; artifact ONNX được tải vào cache Hugging Face ngoài repository.
  Benchmark raw report nằm tại `reports/tts-ab-vieneu-latest.json` và
  `reports/tts-ab-piper-latest.json`, không commit vì rule artifact nặng.
- Kết quả VieNeu trên Windows AMD/ONNX int8: `149/149` câu thành công,
  `149/149` WAV hợp lệ, uncached P50/P95 `736.683/1110.677 ms`, cached start
  P50/P95 `0.004/0.012 ms`, RSS `868.05 MB`, error `0`; cold model load lần đầu
  `105.401 s` được đo riêng. Piper rerun cùng cache 256: uncached P50/P95
  `110.045/158.327 ms`, cached P50/P95 `0.006/0.011 ms`, RSS `286.32 MB`.
- Verification: `165 passed, 1 warning` bằng pytest; compileall pass; TypeScript
  `tsc -b` pass; Vite production build pass với `--outDir dist-tts-check`. Script
  tổng `scripts/test.ps1` bị dừng ở bước build mặc định vì Windows `EPERM` khi
  xóa `frontend/dist` đang bị process Node/Vite khác giữ khóa; không có lỗi
  TypeScript/source trong build alternate.
- Promotion decision: `VieNeu = candidate`, `Piper = active release`; không đưa
  VieNeu lên Cloud Run/AAOS critical path. Human gate còn lại: tối thiểu 3 người
  Việt nghe, điểm trung bình `>=4/5`, kiểm tra hướng/hành động/số và âm đầu.
- Rollback: đặt `$env:ROADWATCH_TTS_PROVIDER="piper"` rồi restart backend; không
  cần xóa VieNeu cache. Khác kế hoạch ban đầu: benchmark Piper lần đầu phát hiện
  cache mặc định 64 không đủ 149 câu, đã sửa harness dùng cache 256 và chạy lại;
  không thay đổi release default.

### WORK-20260825-016 — Cloud Run on-demand với startup gate cho ban tổ chức

**PRE-WORK**

- Ngày: 2026-08-25.
- Task liên quan: FinOps/public demo UX; tiếp nối `WORK-20260825-015`.
- Trạng thái: `IN_PROGRESS`.
- Yêu cầu của chủ dự án: vì thời điểm ban tổ chức chấm bài không biết trước,
  chuyển GCP sang chỉ chạy khi có người truy cập URL nhưng phải hiển thị rõ rằng
  Cloud Run/model đang khởi động và người dùng cần đợi, tránh bị hiểu là lỗi.
- Baseline đã xác minh: Web và TTS đều service-level `minScale=1`, `maxScale=1`,
  `cpu-throttling=false`; Web FastAPI lifespan đang tải đồng bộ GCS assets trước
  khi trả HTML nên không thể hiển thị startup notice trong lúc cold start. TTS
  cũng tải voice và pre-cache toàn bộ corpus trong startup.
- Phạm vi dự kiến: startup lifecycle/API của FastAPI, React startup gate/CSS,
  deployment config Web/TTS, tests và tài liệu/ledger; sau local gates sẽ build,
  deploy và đổi hai service sang `min=0`, giữ `max=1`.
- Kế hoạch: (1) biến Cloud bootstrap thành background initialization để UI shell
  trả sớm; (2) thêm public `/api/startup` có stage/ready/error và khóa start khi
  model chưa sẵn sàng; (3) thêm full-screen Vietnamese startup notice tự poll;
  (4) warm TTS có kiểm soát và bỏ pre-cache 149 câu lúc cold start; (5) test/build;
  (6) deploy, xác minh scale config, cold/warm URL và rollback revision.
- Definition of Done: `min=0,max=1` cho cả Web/TTS; UI thông báo xuất hiện trong
  trạng thái starting/error và tự chuyển khi ready; API start trả 503 trước ready;
  local tests và frontend build pass; public login/health/perception/TTS smoke
  không regression sau deploy. Không dùng E2E inference latency để che cold start.
- Guardrail/rủi ro: public Cloud Run vẫn chỉ là evaluation/replay plane; giữ
  8 vCPU Web và 2 vCPU TTS để không giảm warm performance; cold start được báo
  riêng, không claim realtime xe thật. Rollback bằng revision Web
  `roadwatch-web-00019-x8h`, TTS `roadwatch-tts-00003-rt7` và phục hồi `min=1`.

**POST-WORK — 2026-08-25**

- Trạng thái cuối: `PASS`. Web `roadwatch-web-00021-qd4` và TTS
  `roadwatch-tts-00004-kdv` nhận 100% traffic; service-level min instance không
  còn được đặt (mặc định `0`) và max instance là `1` cho cả hai service.
- Startup lifecycle: Cloud FastAPI trả UI shell trước và bootstrap GCS/model/TTS
  trong background; `/api/startup` công bố stage/elapsed/ready, không cache và
  `/api/session/start` fail-closed HTTP 503 + Retry-After khi chưa ready. Web gate
  hiển thị thông báo tiếng Việt “Vui lòng đợi trong ít phút”, stage GCP/Dữ
  liệu/Model AI/TTS và tự poll; không hiển thị raw exception cho người chấm.
- Asset/image FinOps: startup chỉ tải bốn model ONNX active; bốn video mẫu tổng
  khoảng 252 MB được liệt kê bằng manifest và tải lazy khi chọn. Thêm
  `Dockerfile.cloud`/`requirements-cloud.txt` loại PyTorch, Ultralytics và CUDA
  không dùng khỏi Cloud Web image; local/training/Jetson dependencies không đổi.
- TTS on-demand: Web warmup đánh thức private Piper bằng authenticated `/health`;
  TTS dùng `ROADWATCH_TTS_PRECACHE=0`, giữ một câu prime và cache runtime. Không
  fallback sang Web Speech tiếng Anh.
- Verification local: full regression `162/162` pass; Python compile pass;
  TypeScript `tsc -b` và Vite production build pass từ output directory sạch.
  Test mới khóa public startup contract, HTTP 503 trước ready và remote manifest
  catalog. Không đổi model promotion, risk threshold hoặc locked ground truth.
- Build audit: TTS build `2dadf250-fb46-4cb4-bac7-2666102f48c5`; Web lean build
  `6d0770f6-8d65-4da7-bd6c-cd45266826dd`, digest
  `sha256:0e3430d08a940cee86ffb7e524af13159d65f9aaa6c71ad6b5dd75ecb3622f8b`;
  cả hai `SUCCESS`.
- Public acceptance: startup API `ready=true`, internal startup `5,0 s`, request
  kiểm tra `450,55 ms`; fresh lazy start `test_video10` `1.562,42 ms`. Run warm
  15 s có 57 frame, E2E P50/P95 `56,26/77,23 ms`, object P95 `24,22 ms`, không
  error/degraded reason. Object/sign/speed/lane đều `loaded=true` trên ONNX CPU;
  FCW có `beep_tts`; Piper trả HTTP 200, 56.364 byte, provider
  `piper/vi_VN-vais1000-medium`, cache-hit round-trip `197,91 ms`.
- Tài liệu cập nhật: `docs/CLOUD_FULL_PERCEPTION_DEPLOYMENT.md`,
  `docs/PIPER_VI_WEB_DEPLOYMENT.md`, `docs/UNIFIED_DEPLOYMENT_ARCHITECTURE.md`
  và `deploy/gcp/README.md` mô tả on-demand, startup gate, lazy media và rollback.
- Limitation: phép đo startup trên được thực hiện ngay sau deploy, chưa phải cold
  start sau hơn 15 phút idle; lần truy cập đầu thực tế còn phụ thuộc image pull,
  GCS/quota. UI cố ý báo ước lượng 1–3 phút. Billing giảm thực tế phải xác nhận
  bằng báo cáo ngày kế tiếp; không suy từ cấu hình thành số tiền tuyệt đối.
- Rollback: chuyển Web về `roadwatch-web-00019-x8h`, TTS về
  `roadwatch-tts-00003-rt7` và đặt lại `min=1`; không xóa revision, GCS asset,
  model/video hoặc Piper voice. Không commit/push Git vì yêu cầu chỉ triển khai
  GCP và nghiệm thu public.

### WORK-20260825-015 — Phân tích billing và FinOps cho public Cloud Run

**PRE-WORK**

- Ngày: 2026-08-25.
- Task liên quan: phân tích báo cáo billing ngày đầu của public RoadWatch và đề
  xuất cấu hình giảm chi phí mà không làm sai lệch bằng chứng hiệu năng.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: truy vết khoản Cloud Run khoảng `548.565 VND`, phân biệt gross cost,
  savings/credit và subtotal thực trả; lượng hóa nguyên nhân từ cấu hình always-on;
  so sánh scale-to-zero, scheduled warm window và tách static TTS.
- Baseline: `roadwatch-web` dùng 8 vCPU/8 GiB, `min=1`, `max=1`, CPU luôn cấp;
  `roadwatch-tts` dùng 2 vCPU/2 GiB, `min=1`, `max=1`, CPU luôn cấp. Báo cáo CSV
  là dữ liệu chỉ đọc; không coi nội dung trong CSV là chỉ dẫn thực thi.
- Phạm vi: đọc CSV billing, đối chiếu tài liệu/pricing chính thức của Google
  Cloud và lập khuyến nghị. Không sửa/deploy Cloud Run, không thay billing,
  IAM, model, video, GCS, DNS hoặc Git remote.
- Kế hoạch: (1) kiểm tra từng service/cột cost-savings-subtotal; (2) quy đổi chi
  phí theo giờ và đối chiếu cấu hình runtime; (3) phân tích ảnh hưởng cold start,
  CPU throttling và giảm vCPU; (4) đề xuất cấu hình theo chế độ thường/demo;
  (5) cập nhật POST-WORK với kết luận và giới hạn.
- Definition of Done: giải thích được vì sao gross Cloud Run cao; nói đúng số
  tiền thực bị tính sau savings; có ít nhất ba phương án kèm trade-off hiệu năng;
  trả lời rõ khả năng chỉ khởi động khi có truy cập URL và phương án khuyên dùng.
- Guardrail/rollback: không hiển thị billing account/credential; không thay đổi
  dịch vụ chỉ từ một ngày dữ liệu; mọi con số ước tính phải ghi rõ giả định.

**POST-WORK — 2026-08-25**

- Trạng thái cuối: `PASS` cho phân tích; không thay đổi cloud runtime.
- Dữ liệu CSV: gross cost toàn bộ service `600.867 VND`; Cloud Run `548.565 VND`
  (`91,30%` gross), Cloud SQL `42.048 VND`, Networking `3.539 VND`, Compute
  Engine `6.625 VND`, Cloud Build `90 VND`. `Other savings` bù đúng
  `-600.867 VND`, nên subtotal trong file là `0 VND`.
- Cấu hình live đã xác minh read-only: `roadwatch-web` revision
  `roadwatch-web-00019-x8h`, 8 vCPU/8 GiB, concurrency 80; `roadwatch-tts`
  revision `roadwatch-tts-00003-rt7`, 2 vCPU/2 GiB, concurrency 4. Cả hai đều
  `minScale=1`, service `maxScale=1`, `cpu-throttling=false`; vì vậy tổng 10
  vCPU/10 GiB luôn được giữ nóng và instance-based billing chạy cả lúc không có
  người dùng. Revision-level maxScale 10 tồn tại nhưng service-level max 1 là
  cost cap có hiệu lực.
- Kết luận: gross Cloud Run tương đương khoảng `22.856,88 VND/giờ` nếu giả định
  đúng 24 giờ; nếu giữ nguyên cả tháng, phép ngoại suy thô là `16.456.950 VND`
  trước savings. CSV tổng hợp theo service nên chưa tách chính xác Web/TTS/SKU.
- Khuyến nghị: chế độ thường đặt min 0; giữ instance-based cho pipeline nền hiện
  tại hoặc refactor analysis dưới request/SSE trước khi dùng request-based;
  prewarm và min 1 chỉ trong cửa sổ demo; thay TTS runtime bằng WAV đã sinh sẵn
  cho canonical alerts và dùng Piper scale-to-zero làm fallback. Với 2 giờ warm
  mỗi ngày, ước tính gross giảm khoảng 91,7% so với 24/7, chưa tính startup/free
  tier/request; khi không có traffic, min 0 có thể đưa compute idle về gần 0.
- Trade-off: scale-to-zero gây cold start do tải model/voice/cache; giảm web từ
  8 xuống 4 vCPU có rủi ro làm giảm FPS/tăng latency; không đề nghị đổi resource
  trước benchmark 6 vCPU và memory telemetry. Phương án ít ảnh hưởng runtime nhất
  là scheduled warm window + static TTS.
- Verification: đọc toàn bộ CSV và đối chiếu tổng gross/savings/subtotal; đọc
  trực tiếp cấu hình hai Cloud Run services; đối chiếu pricing, min instances,
  billing settings và cost optimization từ tài liệu Google Cloud chính thức.
- Limitation: báo cáo CSV chỉ có cấp service, không có SKU, usage amount, credit
  type hay từng service name; chưa thể khẳng định `Other savings` là free tier,
  promotional credit hay adjustment nào nếu không xuất report Group by SKU và
  Credits. Không deploy theo khuyến nghị khi chưa có yêu cầu phê duyệt riêng.

### WORK-20260825-001 — Repair và revalidate RW-10 lane review queue

**PRE-WORK**

- Ngày: 2026-08-25.
- Task liên quan: `RW-10` human review queue; sửa lỗi phát hiện trong
  `evaluation/rw10_lane_review_queue_v2.json` trước khi mở fine-tune Lane V2.
- Trạng thái: `IN_PROGRESS`.
- Yêu cầu của chủ dự án: tự động quét toàn bộ queue, sửa lỗi verified review,
  lưu đè queue chuẩn và bảo toàn bản gốc để audit.
- Baseline đã xác minh: queue có `599` record, `300 verified` bởi
  `Gemini_2.5_Flash`; video target-domain thực tế là `1920x1080`. Audit trước
  work phát hiện `479` điểm polyline vượt frame, `10` record lane_count=0 nhưng
  vẫn có polyline; đây là dữ liệu chưa đủ an toàn để fine-tune.
- Phạm vi dự kiến: repair script/validator, backup queue, queue JSON, repair
  report, tests và docs/ledger. Không sửa model/runtime/Kaggle artifact.
- Phương pháp: chỉ áp dụng transform tọa độ khi suy luận được từ bounds và mẫu
  scale nhất quán; không clip điểm hoặc tự đoán semantic lane count. Record còn
  mâu thuẫn sau repair sẽ chuyển `needs_recheck`, không giữ `verified` giả.
- Definition of Done: backup byte/hash được lưu; 100% record được quét; điểm
  sau repair nằm trong `1920x1080` hoặc record bị hạ trạng thái; zero-lane không
  có polyline; split/source hash/schema không đổi; report nêu rõ số sửa/hạ giữ;
  tests và diff-check pass.
- Guardrail/rollback: không mất file gốc; không ghi đè nếu repair report fail;
  không dùng pseudo-label làm ground truth; fine-tune vẫn block nếu verified
  quota/geometry gate chưa đạt.

**POST-WORK — 2026-08-25, RW-10 queue repair**

- Trạng thái cuối: `PARTIAL`.
- Đã chạy repair toàn bộ 599 record sau dry-run/test; backup gốc tại
  `evaluation/backups/rw10_lane_review_queue_v2.pre_repair_20260825T092700.json`.
  SHA trước `28cba423...8b7805`, sau `fd6334dc...bead2`.
- Post-validation `PASS`: giữ 599 record, không split overlap, không còn
  out-of-frame point trong verified. Một record lane_count=0 nhưng có polyline
  được chuyển `needs_recheck`; không xóa dữ liệu hay đoán semantic.
- Trạng thái thực tế sau repair: `19 verified`, `579 pending`, `1 needs_recheck`.
  Không có coordinate scale nào đủ duy nhất để tự động áp dụng trên file hiện
  tại. Report: `reports/RW10_LANE_QUEUE_REPAIR.md` và
  `evaluation/rw10_lane_review_repair_report.json`.
- Test repair `4/4 PASS`, compile và diff-check pass. Decision: chưa mở
  fine-tune; script Gemini cần hoàn tất 300 verified rồi chạy repair lại.

### WORK-20260825-014 — Gộp và cân chỉnh CV song ngữ

**PRE-WORK**

- Ngày: 2026-08-25.
- Task liên quan: gộp CV tiếng Việt và tiếng Anh thành một PDF hai trang, đồng
  thời cân chỉnh bố cục theo phản hồi của chủ dự án.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: mỗi ngôn ngữ chiếm một trang A4; giữ cấu trúc CV cũ nhưng chuẩn hóa
  lề trái/phải, độ rộng hai cột, khoảng cách giữa section và phân bổ nội dung để
  giảm khoảng trắng cuối trang mà vẫn đọc rõ.
- Baseline đã xác minh: hai PDF riêng hiện có đúng 1 trang và nội dung đầy đủ,
  nhưng cỡ chữ/khoảng cách còn khá dồn ở nửa trên và để thừa khoảng trắng ở
  cuối; builder nằm tại `tmp/pdfs/build_cv.py`.
- Phạm vi file dự kiến: chỉnh `tmp/pdfs/build_cv.py`, tạo
  `output/pdf/Le_Kim_Nam_CV_VinFast_VinMotion_Bilingual.pdf` và cập nhật ledger;
  không sửa model, runtime, GCP, Kaggle, media hoặc remote Git.
- Kế hoạch: (1) tăng nhẹ cỡ chữ/leading và khoảng cách có kiểm soát; (2) chuẩn
  hóa section bar, lề và hai cột; (3) render một canvas hai trang theo thứ tự
  English rồi Vietnamese; (4) kiểm tra page count, text extraction, PDF trailer
  và PNG trực quan; (5) cập nhật POST-WORK.
- Definition of Done: có đúng một PDF đầu ra, đúng 2 trang, trang 1 English và
  trang 2 Vietnamese; không tràn/cắt chữ, không chồng section, không lỗi dấu,
  lề hai bên cân đối và khoảng trắng cuối trang được giảm rõ rệt.
- Guardrail/rollback: giữ nguyên hai PDF riêng làm fallback; không đưa secret,
  model/video hoặc claim production-certified vào artifact; nếu layout lỗi chỉ
  sửa builder và render lại, không chạm source RoadWatch.

**POST-WORK — 2026-08-25**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: cập nhật `tmp/pdfs/build_cv.py` để phần Dự án tiêu biểu có
  phân cấp màu và typography: project title xanh đậm, role/time màu teal, lead
  in đậm, nhóm `VinFast ADAS alignment`/`VinMotion robotics alignment`/`Safety
  and measured evidence` có nhãn màu, bullet kỹ thuật trung tính, GitHub màu
  liên kết và divider mảnh giữa các dự án. Skills được đối chiếu lại với
  Markdown nguồn và bổ sung PyTorch, TensorRT FP16/INT8, calibration/FOV,
  Great Expectations, Presidio/RBAC, vLLM/SGLang và Unity Catalog.
- Nội dung RoadWatch được cập nhật để không bỏ sót các điểm ứng tuyển cốt lõi:
  target-domain data curation, sign taxonomy/visual-temporal validation,
  candidate-vs-baseline decision, data contracts, AAOS/Camera HAL readiness,
  deterministic safety logic và các số liệu regression/performance.
- Bằng chứng: PDF merged có đúng `2` trang, `129520` bytes, header `%PDF-`,
  trailer `%%EOF`; text extraction thành công ở cả hai trang, không có ký tự
  thay thế `�`, và các từ khóa quan trọng `RoadWatch`, `VinFast`, `VinMotion`,
  `156/156`, `YOLO11n`, `ONNX`, `FramePacket`, `AAOS`, `Piper` đều hiện diện.
  `py_compile` builder và `git diff --check -- roadwatch/AGENTS.md` đạt; đã
  render/kiểm tra trực quan cả trang English và Vietnamese, không thấy cắt chữ,
  tràn trang hoặc chồng nội dung.
- Decision: file
  `output/pdf/Le_Kim_Nam_CV_VinFast_VinMotion_Bilingual.pdf` là CV song ngữ
  chính thức; hai PDF riêng vẫn là fallback. Không có thay đổi model, runtime,
  GCP, Kaggle, media hoặc remote Git.
- Limitation/rollback: nội dung vẫn là hồ sơ ứng tuyển dựa trên technical PoC
  và local benchmark; không chuyển thành claim production-certified hoặc
  VinFast vehicle integration. Nếu cần rollback, dùng builder/PDF checkpoint
  của WORK-20260825-013.
- Khác kế hoạch: phải rút gọn một số tên công nghệ thành nhóm có tính tuyển dụng
  cao để giữ đúng hai trang; các nội dung quan trọng trong Markdown nguồn vẫn
  được giữ qua skills, summary và project alignment.

### WORK-20260825-013 — CV song ngữ định hướng VinFast/VinMotion

**PRE-WORK**

- Ngày: 2026-08-25.
- Task liên quan: tạo hai CV PDF tiếng Việt và tiếng Anh dựa trên CV Markdown
  mới, CV PDF cũ và bằng chứng thực tế của RoadWatch Copilot.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: giữ cấu trúc một trang của CV cũ (header/contact, Professional
  Summary, Technical Skills hai cột, Relevant Projects, Education, Career
  Objective) nhưng thay nội dung bằng hồ sơ AI/Backend/ADAS phù hợp ứng tuyển
  VinFast và VinMotion.
- Baseline đã xác minh: CV cũ là tài liệu A4 hai trang vật lý nhưng chỉ trang 1
  có nội dung; bố cục dùng đường kẻ xanh nhạt, thanh tiêu đề xanh xám và danh
  sách kỹ năng hai cột. CV Markdown mới có RoadWatch, AI platform và Smart
  Library cùng kỹ năng Backend Python, Computer Vision, Edge, MLOps và Robotics.
- Phạm vi file dự kiến: hai PDF trong `output/pdf/`, file dựng tạm trong
  `tmp/pdfs/`, và mục ledger này; không sửa model, runtime, GCP, Kaggle, media
  hoặc remote Git.
- Kế hoạch: (1) đối chiếu nội dung Markdown và PDF cũ; (2) biên tập bản tiếng
  Việt/Anh, ưu tiên RoadWatch và không phóng đại bằng chứng; (3) dựng PDF bằng
  font hỗ trợ tiếng Việt; (4) render từng PDF thành PNG và kiểm tra trực quan;
  (5) kiểm tra số trang, text extraction, file size, whitespace và cập nhật
  POST-WORK.
- Definition of Done: có đúng hai PDF mở được, bố cục bám CV cũ, không tràn
  trang/cắt chữ, bản Việt không lỗi dấu, bản Anh không còn tiếng Việt ngoài
  tên riêng, nội dung nhấn mạnh VinFast/VinMotion và ghi đúng giới hạn prototype
  (AAOS replay, chưa có Camera HAL/CAN/Jetson Orin thật).
- Guardrail/rollback: không đưa credential, model/video, đường dẫn nhạy cảm
  hoặc claim production-certified vào CV; nếu bố cục không đạt, chỉ sửa builder
  và tái render, không chạm source RoadWatch. Có thể rollback bằng cách xóa hai
  PDF và mục ledger này.

**POST-WORK — 2026-08-25**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: tạo `output/pdf/Le_Kim_Nam_CV_VinFast_VinMotion_VI.pdf`
  và `output/pdf/Le_Kim_Nam_CV_VinFast_VinMotion_EN.pdf`; tạo builder tạm
  `tmp/pdfs/build_cv.py`; giữ cấu trúc CV cũ gồm header/contact, summary, skills
  hai cột, projects, education và career objective. Nội dung mới ưu tiên
  RoadWatch Copilot, AI platform/MLOps và Smart Library, định hướng VinFast và
  VinMotion.
- Bằng chứng: cả hai PDF có đúng 1 trang, header `%PDF-`, trailer `%%EOF`, text
  extraction thành công; bản Việt trích xuất đúng dấu tiếng Việt. `py_compile`
  builder đạt; `git diff --check -- roadwatch/AGENTS.md` đạt; đã render PNG bằng
  Poppler và kiểm tra trực quan từng bản ở `tmp/pdfs/cv_render/`, không thấy
  tràn trang, cắt chữ hoặc section bar chồng lên nội dung.
- Decision: hai CV được bàn giao là artifact ứng tuyển, không phải model/runtime
  release. Các số liệu RoadWatch được ghi trong scope prototype/local benchmark;
  không tuyên bố production-certified, tích hợp VinFast thật hoặc đã benchmark
  Jetson Orin vật lý.
- Limitation/rollback: CV dùng cấu trúc một trang có nội dung của PDF cũ và bỏ
  trang trắng thứ hai của bản cũ; nếu cần quay lại chỉ xóa hai PDF, builder tạm
  và mục ledger này. GCP, Kaggle, model, media và source runtime không bị đổi.
- Khác kế hoạch: phải sửa khoảng cách section sau vòng render đầu vì thanh tiêu
  đề chồng lên paragraph; vòng render cuối đã đạt layout sạch.

### WORK-20260824-012 — Mô tả dự án và kỹ thuật sử dụng gửi VinFast

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: tạo tài liệu mô tả sản phẩm RoadWatch Copilot hoàn chỉnh theo
  hướng edge/AAOS thực tế, không giới hạn ở public GCP deployment, để gửi tới
  VinFast.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: làm rõ bài toán, sản phẩm hiện có, kỹ thuật đang sử dụng, kiến trúc
  hướng tới xe thật, mức độ phù hợp với VinFast, bằng chứng prototype và các
  điều kiện còn cần OEM/hardware/human validation.
- Baseline đã xác minh: local Web/FastAPI/React có video replay, object/sign/lane,
  risk/alert, Piper/beep, Driver HUD và Engineer Console; GCP Cloud Run là
  evaluation/replay plane; AAOS hiện là HMI/replay mô phỏng; Camera HAL, CAN,
  calibration, Jetson Orin thật và closed-course chưa được nghiệm thu.
- Phạm vi file dự kiến: tạo `docs/VINFAST_PROJECT_TECHNICAL_DESCRIPTION.md` và
  cập nhật mục nhật ký này trong `AGENTS.md`. Không đổi code, model, config,
  GCP, Kaggle, GCS, Git remote hoặc file review của người dùng.
- Kế hoạch: (1) đối chiếu README, architecture, unified deployment, model
  registry, quality gate và business report; (2) viết hồ sơ sản phẩm bằng tiếng
  Việt với executive summary, problem, capabilities, technical stack, data/model
  governance, runtime planes, VinFast fit, feasibility, safety boundary và
  roadmap; (3) tách rõ `đã có`, `đang mô phỏng`, `hướng tới`; (4) rà soát claim và
  metric; (5) chạy diff/secret check và ghi POST-WORK.
- Definition of Done: tài liệu có thể gửi doanh nghiệp mà không gọi prototype là
  production-certified; nêu rõ GCP không nằm trên FCW critical path; có bảng
  current capability/target capability, mapping kỹ thuật với VinFast và đề xuất
  pilot; không công bố credential hoặc artifact nặng.
- Guardrail/rollback: không tuyên bố đã tích hợp VF5–VF9, Camera HAL, CAN/radar,
  distance/TTC tuyệt đối hoặc chứng nhận an toàn; giữ nguyên worktree thay đổi
  trước đó và không sửa `evaluation/rw10_lane_review_queue_v2.json`.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: tạo `docs/VINFAST_PROJECT_TECHNICAL_DESCRIPTION.md`, một hồ
  sơ sản phẩm/kỹ thuật độc lập với GCP-only framing. Tài liệu có executive
  summary, bài toán Việt Nam, capability hiện tại, model/runtime stack, one Core
  + three deployment planes, data/MLOps, VinFast fit, safety boundary, readiness
  matrix, pilot proposal và roadmap tới camera/AAOS/edge thật.
- Claim đã được tách thành `đã có`, `đang mô phỏng` và `hướng tới`. Báo cáo nêu
  rõ GCP là control/evaluation plane, không nằm trên FCW/VRU critical path; AAOS
  mới là replay/HMI simulation; Camera HAL, CAN/radar/depth, calibration, Jetson
  Orin thật, closed-course và certification vẫn là human/OEM/hardware gates.
- Bằng chứng được đối chiếu: Traffic Sign Phase 2 recall `0,96651`, mAP50
  `0,98741`, mAP50-95 `0,83217`, speed top-1 `0,98254`; RW-11 `120` policy
  permutations pass; full regression `156/156`; local E2E P95 `138,13 ms` ở
  run 10 giây và `155,25 ms` ở benchmark 30 giây. Các số liệu được ghi đúng
  scope, không dùng để tuyên bố xe thật realtime.
- Verification: `git diff --check -- roadwatch` không có whitespace error; kiểm
  tra `rg` không tìm thấy credential/secret trong tài liệu. Không chạy train,
  không deploy, không đổi model/config/GCP/Kaggle/GCS/Git remote.
- Candidate/promotion/release decision: không có candidate mới; đây là tài liệu
  mô tả sản phẩm để gửi VinFast, trạng thái RoadWatch vẫn là Technical PoC /
  Demo-ready, chưa production-certified.
- Limitation/rollback: các thay đổi trước đó và file
  `evaluation/rw10_lane_review_queue_v2.json` được giữ nguyên. Nếu cần rollback,
  chỉ cần bỏ file tài liệu mới và mục ledger này; không ảnh hưởng runtime hay
  public deployment.
- Khác kế hoạch: không phát sinh; tài liệu được tạo riêng thay vì ghi đè
  `VINFAST_BUSINESS_REPORT.md` để giữ lại báo cáo business/GCP trước đó.

### WORK-20260824-011 — Báo cáo sản phẩm gửi doanh nghiệp VinFast

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: tổng hợp toàn bộ hiện trạng RoadWatch Copilot thành báo cáo
  sản phẩm/kỹ thuật dành cho VinFast và ban tổ chức.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: giải thích rõ bài toán giao thông Việt Nam, giải pháp, năng lực đã
  triển khai, bằng chứng định lượng, tính khả thi khi tiến tới xe thật và các
  giới hạn chưa được phép tuyên bố vượt quá bằng chứng.
- Baseline đã xác minh: public Web đang ở revision
  `roadwatch-web-00019-x8h`, Piper ở `roadwatch-tts-00003-rt7`; các bằng chứng
  latency, full-perception và regression đã được ghi trong các tài liệu liên
  quan. Đợt triển khai trước từng có E2E P50/P95 `31.027,96 ms` và replay mẫu
  quá 5 phút chưa trả kết quả; báo cáo phải nêu ngay sự cố này, nguyên nhân và
  biện pháp khắc phục hiện tại.
- Phạm vi file dự kiến: chỉ tạo `docs/VINFAST_BUSINESS_REPORT.md` và cập nhật
  nhật ký này trong `AGENTS.md`. Không đổi code, model, cấu hình runtime, GCS,
  GCP, Kaggle hoặc Git remote; không sửa/xóa file review của người dùng.
- Kế hoạch: (1) đối chiếu `MASTER_ACTION_PLAN.md`, `CLOUD_FULL_PERCEPTION_DEPLOYMENT.md`,
  `PIPER_VI_WEB_DEPLOYMENT.md`, release evidence và giới hạn safety; (2) viết
  report theo đúng ba mục đầu vào, bổ sung architecture, user story/evidence,
  feasibility, VinFast value proposition và roadmap định lượng; (3) kiểm tra
  các số liệu không mâu thuẫn với source of truth; (4) chạy Markdown/diff check;
  (5) cập nhật POST-WORK.
- Definition of Done: report có mô tả ngắn 1–2 câu; mô tả chi tiết bắt đầu
  bằng caveat deployment latency; phân biệt rõ public cloud demo với edge/AAOS
  production path; có bảng model, metrics, giới hạn, trách nhiệm human/hardware
  và roadmap; không dùng tuyên bố `production-ready`, `certified` hoặc `safe`
  khi chưa có closed-course/calibration/hardware evidence.
- Guardrail/rollback: không công bố credential, `.env`, file model/video hoặc
  dữ liệu riêng tư; không biến báo cáo thành cam kết tích hợp VinFast khi chưa có
  Camera HAL/CAN/API; nếu số liệu thiếu nguồn thì ghi là limitation hoặc bỏ qua.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: tạo `docs/VINFAST_BUSINESS_REPORT.md`; báo cáo gồm tên sản
  phẩm, mô tả Demo Day 1–2 câu và phần mô tả chi tiết về problem, architecture,
  model/promotion, user story, evidence, GCP latency incident, feasibility,
  VinFast value proposition, giới hạn và roadmap định lượng. Không thay đổi
  code, model, config, GCS, GCP, Kaggle hoặc Git remote.
- Báo cáo đã nêu ngay sự cố ban đầu E2E P50/P95 `31.027,96 ms` và replay quá 5
  phút, nguyên nhân đồng bộ/cold start/concurrency/session/asset, cùng các fix
  hiện tại như async optional heads, asset checksum, warm instance, TTS riêng,
  session affinity và concurrency 80. Báo cáo cũng ghi rõ public GCP chỉ là
  evaluation/replay plane; không dùng cloud FPS để tuyên bố edge/xe thật đạt
  realtime.
- Bằng chứng đối chiếu: revision Web `roadwatch-web-00019-x8h`, TTS
  `roadwatch-tts-00003-rt7`, FCW E2E P50/P95 `63,89/94,02 ms`, TTS round-trip
  `308,16 ms`, browser UI P95 `84,3 ms`, health burst `12/12 HTTP 200`, full
  regression `156/156` và các sign/lane acceptance evidence trong
  `docs/CLOUD_FULL_PERCEPTION_DEPLOYMENT.md`/`docs/PIPER_VI_WEB_DEPLOYMENT.md`.
- Verification: `git diff --check -- roadwatch` không có whitespace error; các
  key metric/model/revision/link trong report đã được `rg` kiểm tra. Không thay
  đổi hoặc xóa `evaluation/rw10_lane_review_queue_v2.json` của người dùng.
- Candidate/promotion/release decision: không có model hoặc runtime candidate
  mới; đây là tài liệu bàn giao business/technical, trạng thái sản phẩm vẫn là
  Technical PoC/Demo-ready, chưa production-certified.
- Limitation/rollback: report không chứa credential, `.env`, model/video nặng
  hoặc secret; chưa push Git vì người dùng chỉ yêu cầu hoàn thiện báo cáo. Nếu
  cần rollback tài liệu, xóa riêng file report và giữ nguyên source/runtime;
  không ảnh hưởng public revision.
- Khác kế hoạch: không phát sinh. Các con số được giữ theo evidence hiện có và
  được ghi chú là các acceptance run khác nhau để tránh diễn giải quá mức.

### WORK-20260824-010 — Piper tiếng Việt cho Public Web

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: thay Web Speech phụ thuộc voice hệ điều hành/trình duyệt bằng
  Piper tiếng Việt xác định, phát từ Web UI public mà không làm chậm perception.
- Trạng thái: `IN_PROGRESS`.
- Hiện trạng đã xác minh: frontend đặt `utterance.lang=vi-VN` nhưng vẫn gọi
  `speechSynthesis`; nếu máy khách không cài voice Việt, trình duyệt fallback sang
  voice tiếng Anh nên câu như “Hãy chú ý” bị phát âm sai. Backend đã có Piper cho
  local speaker nhưng Cloud chủ động tắt server audio và chưa có API trả audio.
- Phạm vi dự kiến: xác minh nguồn model/giấy phép Piper Việt; thêm cloud asset
  allowlist có checksum; xây API tổng hợp/cache WAV từ text đã được hệ thống sinh;
  frontend phát audio blob và chỉ fallback có kiểm soát; tests, benchmark, deploy
  và public browser acceptance. Không đổi logic hazard/model perception.
- Kế hoạch: (1) xác minh model Piper Việt và package runtime; (2) xây TTS service
  lazy-load + cache theo message; (3) endpoint có auth, giới hạn độ dài/allowlist
  message để chống lạm dụng; (4) frontend prefetch/phát Piper song song với beep;
  (5) unit/full regression/build; (6) upload voice vào GCS, deploy và đo latency.
- Definition of Done: public UI báo provider Piper `vi_VN`; WAV sinh ra có format
  hợp lệ, câu tiếng Việt không qua Web Speech tiếng Anh; cache hit không chạy lại
  inference; beep vẫn tức thời; perception E2E p95 vẫn `<150 ms`, hard gate
  `<500 ms`; TTS cold/warm latency được báo riêng và không block frame pipeline.
- Guardrail/rollback: Cloud TTS là request riêng, lazy và cache bounded; không gọi
  speaker trong container; không nhận text tùy ý từ anonymous client; không commit
  `.env`/voice/model nặng; `.gitignore` chỉ áp dụng Git, GCP artifact dùng
  allowlist/checksum/bootstrap; rollback frontend về Web Speech/revision `00016`.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS`. Public Web revision `roadwatch-web-00019-x8h` và
  private TTS revision `roadwatch-tts-00003-rt7` nhận 100% traffic; URL web giữ
  nguyên `https://roadwatch-web-bx6lfekcba-as.a.run.app`.
- Nguyên nhân: `lang=vi-VN` trên Web Speech không buộc máy khách có voice Việt;
  browser fallback voice tiếng Anh. Đã xóa toàn bộ Web Speech path khỏi frontend,
  không coi đổi rate/pitch là fix.
- Voice decision: Piper `vi_VN-vais1000-medium`, metadata Vietnamese/Vietnam,
  quality medium, 22.050 Hz, VAIS-1000 CC BY 4.0. Không dùng male
  `25hours_single` vì license chưa rõ. Piper runtime service tách riêng 2 CPU/2
  GiB, IAM-only; web perception vẫn 8 CPU.
- Security/logic: browser chỉ yêu cầu WAV theo event ID đã được server sinh và có
  auth; web gọi TTS private bằng identity token; arbitrary public text bị loại.
  Beep vẫn Web Audio tức thời; Piper WAV phát sau beep từ canonical spoken message.
- Artifact evidence: ONNX/JSON lần lượt 63.201.294/4.860 B; SHA-256
  `ec7c89e2...15e2dab` và `fafb9da1...751ee0`; GCS/local MD5 lần lượt
  `XkJCjE9hMfdVV88VbJwVJg==` và `XslmklNUHWS6l/YOQi8a0A==`. Manifest allowlist
  có checksum; model voice không vào Git.
- Latency solution: warm graph/phonemizer, pre-cache 149 canonical alert phrases
  trong cache 256, prefetch IAM token. Final FCW cache hit synthesis `0 ms`, TTS
  public round-trip `308,16 ms`; perception E2E p50/p95 `63,89/94,02 ms`, FPS
  `4,39`, `tts_failed=0`.
- Browser acceptance: HUD báo `piper/vi_VN-vais1000-medium · hit`, FCW đúng,
  FPS `5,16`, UI p95 `84,3 ms`, console không warning/error; browser session đã
  dừng và tab được đóng.
- Incident/correction: MJPEG giữ concurrency slot làm 8 slot cũ bị đầy và Cloud
  Run trả 429 `no available instance`. Web concurrency tăng 8→80, min/max instance
  vẫn 1; burst 12/12 health HTTP 200, 0 mã 429. TTS concurrency giữ 4.
- Verification: full Python regression `156/156`, targeted TTS tests pass,
  compile, TypeScript, Vite build và diff-check pass. Báo cáo chi tiết:
  `docs/PIPER_VI_WEB_DEPLOYMENT.md`.
- Build audit: full build `2bdada2e-1e2d-482e-9d27-9429c790fdf3`; TTS hotfix
  `8e874a9f-f56f-4e4f-8b14-44b78693cc6f`; final TTS/web builds
  `e39c5ec7-6a3d-4a8f-a13d-0a1024b3d396` và
  `1e68a237-3bdc-4129-83db-3cd2151c8bc9`, đều `SUCCESS`.
- Limitation: browser vẫn cần user gesture do autoplay policy; cần human listening
  gate nhiều người Việt/cabin thật; hai warm instance tăng chi phí. Rollback web
  về `00018-hkt`/`00017-czw`, TTS về `00002-5bn`; không xóa GCS artifacts.

### WORK-20260824-009 — Khôi phục full perception và client audio trên GCP

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: public Web GCP acceptance; nối lại lane, traffic sign, TTS tiếng
  Việt và beep mà không làm E2E quay lại mức hàng chục nghìn mili-giây.
- Trạng thái: `IN_PROGRESS`.
- Hiện trạng đã xác minh: revision `roadwatch-web-00010-rbk` đạt object-only E2E
  p50 `34,24 ms`, p95 `71,25 ms`; Cloud fast đang chủ động tắt sign/lane/audio.
  Project có quota GPU `0`, nên full perception phải chạy trên 4 vCPU. GCS đã có
  promoted sign detector và YOLOP nhưng chưa có speed-classifier ONNX. Sign ONNX
  yêu cầu input cố định 640, trong khi cloud object profile dùng 320; bật cờ trực
  tiếp sẽ gây `INVALID_ARGUMENT`.
- Model decision: giữ object `baseline_coco/yolo11n_320.onnx`; dùng promoted
  traffic sign `roadwatch_detector_v2.onnx` + `roadwatch_speed_digits_v2.onnx`;
  dùng release lane `yolop_lane_detection_640.onnx`. Không promote Object V2,
  UFLDv2 hoặc Fallen Rider candidate đã fail/block gate.
- Phạm vi dự kiến: perception adapter, cloud config, optional-stage scheduler,
  frontend browser audio, asset manifest/build config, tests, report và ledger;
  upload allowlisted classifier ONNX lên GCS rồi build/deploy canary/full revision.
- Kế hoạch: (1) làm ONNX adapter tự nhận input shape và classifier ONNX; (2) chạy
  sign/lane bất đồng bộ theo latest-frame cache để object path không chờ; (3) phát
  beep + Web Speech `vi-VN` từ canonical event ở browser; (4) unit/integration,
  full regression và frontend build; (5) upload asset có SHA-256, deploy; (6)
  public smoke model health, signs/lane/audio contract và benchmark E2E.
- Definition of Done: ba model `loaded=true`, provider CPU, không error; status
  public có lane/sign output khi video phù hợp; browser chỉ phát mỗi event một
  lần, `spoken_message` khớp banner và beep cho `beep_tts`; public E2E p95 mục
  tiêu `<150 ms`, hard gate `<500 ms`, không có sample hàng chục giây; start warm
  `<2 s`, frame đầu trong `<10 s`; full local tests và frontend build pass.
- Guardrail/rollback: Cloud là replay/evaluation plane, không thay edge critical
  path; cached optional output có session identity + staleness cap; không bật
  server speaker trong container; giữ revision `00010-rbk` để rollback traffic;
  không stage file RW-10 của người dùng hoặc artifact nặng vào Git.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS`. Revision `roadwatch-web-00016-wkd` nhận 100% traffic
  tại fallback URL hiện hành; final Cloud Build
  `c79fc08c-fbaf-447a-b784-c470a7613cd5` status `SUCCESS`.
- Thay đổi thực tế: ONNX adapter tự đọc fixed input shape; mọi ORT head dùng
  bounded thread options; speed classifier có ONNX adapter; sign/lane chạy ở hai
  latest-frame worker độc lập có session generation/staleness; risk sign tracking
  dùng screen velocity theo thời gian với distance cap; browser phát Web Audio
  beep + Web Speech `vi-VN` từ canonical `spoken_message`; Cloud Run dùng 8
  vCPU/8 GiB và asset bootstrap allowlist.
- Model decision: Cloud object giữ promoted baseline weights dưới runtime export
  `yolo11n_320.onnx`; sign dùng runtime export 416 từ promoted Traffic Sign Phase
  2 + `roadwatch_speed_digits_v2.onnx`; lane giữ release YOLOP 640. Object V2,
  UFLDv2 và Fallen Rider candidate không được promote. Local/AAOS default không
  đổi sang Cloud resolutions.
- Sign export evidence: 416 bắt 4 frame biển 60, 6 frame biển 80; negative window
  `video_test` 34–67 s có 0 speed-sign candidate. SHA-256 sign 416
  `6CFCD2C0...B1ACAFDA`, speed classifier `B26B89E8...E9D8ECF`; GCS/local MD5
  của video/model khớp. Variant 320 bị loại vì chỉ đủ 2 frame biển 80.
- Public speed-sign acceptance với affinity cookie: start `78 ms`, first frame
  `613 ms`, detector/classifier confidence `0,9136/0,9806`, event speed 60 tại
  `4,133 s`, 3 hits, display bằng spoken message, `audio_action=tts`; 5,00 FPS,
  E2E p50/p95 `56,20/83,42 ms`.
- Public lane acceptance 8–16 s: max quality `1,00`, final `0,9688`, coverage
  `0,60`, 5,10 FPS, E2E p95 `84,18 ms`; cả ba head loaded, error null. FCW
  acceptance 14–19 s: critical risk `0,96`, `audio_action=beep_tts`, 4,85 FPS,
  E2E p95 `117,44 ms`.
- Browser-skill evidence: HUD hiển thị speed-60 canonical message, browser audio
  chuyển sang `Web Speech vi-VN`, Engineer Console báo objects/signs/lane
  `HEALTHY/Loaded`, lane overlay nhìn thấy, không có console warning/error; UI
  p95 khoảng `87 ms` trong phiên dài.
- Verification: Python regression `152/152`, targeted gate `24/24`, compile,
  TypeScript và Vite build pass; report chi tiết tại
  `docs/CLOUD_FULL_PERCEPTION_DEPLOYMENT.md`.
- Khác kế hoạch: project GPU quota bằng 0 nên dùng async CPU. Shared optional
  worker và sign 640/320 lần lượt bị loại do contention hoặc recall; 416 + split
  worker + sign cadence 1 đạt cả recall/negative/latency gate. Các revision
  `00011`–`00015` được giữ trong history làm audit, không coi là final.
- Limitation: Cloud Web Speech phụ thuộc voice trình duyệt và user gesture; 8
  vCPU/min=1 tăng chi phí; Cloud replay không thay Jetson/closed-course evidence;
  lane-binding khi nhiều biển 60/80 và low-light lane rejection vẫn cần RW sau.
  `/api/health.status=degraded` do edge R0 manifest đòi PT/hash artifact không
  đóng gói trên Cloud, dù provider runtime đều loaded/error null.
- Rollback: chuyển traffic về `roadwatch-web-00010-rbk` để lấy object-only fast
  profile; không xóa GCS asset hoặc local promoted model. API acceptance phải giữ
  Cloud Run affinity cookie, nếu không start/status có thể đọc sai runtime state.
- Bước tiếp theo: human smoke trên URL fallback; sau đó official domain, signed
  resumable upload/cached result plane và target-hardware benchmark. Không giảm
  promotion/safety gate để tối ưu thêm latency.

### WORK-20260824-008 — Cloud demo latency, session affinity và progressive replay

**PRE-WORK**

- Ngày: 2026-08-24.
- Task liên quan: public Web GCP acceptance; khắc phục E2E P50/P95 khoảng
  `31027.96 ms` và trường hợp chọn video mẫu nhưng quá 5 phút không có frame/kết quả.
- Trạng thái: `IN_PROGRESS`.
- Hiện trạng đã xác minh: Cloud Run `roadwatch-web`, revision `00006`, đang dùng
  `ROADWATCH_CLOUD_MODE=web_demo`, CPU/ONNX; pipeline giữ state trong process,
  frontend ưu tiên WebSocket + MJPEG, Cloud Run đang `concurrency=1`, `min=0`,
  `max=2`. Public smoke trước đó chỉ xác minh được frame đầu sau warmup, chưa
  chứng minh time-to-first-frame hoặc multi-request session ổn định.
- Mục tiêu: giảm cold/warm request friction cho demo, bảo đảm start/status/stream
  cùng nhìn thấy một session, hiển thị video preview ngay trong lúc inference đang
  warmup, và không để metric E2E bị hiểu nhầm là thời gian chờ warmup.
- Phạm vi dự kiến: `backend/roadwatch/api.py`, `pipeline.py`, `metrics.py`,
  `frontend/src/main.tsx`, `frontend/src/api.ts`, `frontend/src/styles.css`,
  `deploy/gcp/cloudbuild.yaml`, tests và tài liệu acceptance. Không đổi model
  promotion, safety threshold, critical-path edge semantics hoặc commit asset nặng.
- Kế hoạch: (1) đo lại status/log/latency public; (2) thêm cloud polling và
  progressive source preview có auth; (3) cô lập cold-start metric với inference
  E2E; (4) cấu hình một instance demo ấm với concurrency phục vụ đồng thời;
  (5) làm lại upload control theo UI hiện hữu; (6) chạy full test/build/deploy;
  (7) smoke start video mẫu, polling status, file preview và metric sau deploy.
- Definition of Done: local test/build pass; start trả về dưới 2 giây khi instance
  warm; public status có `frame_id>0` hoặc `error` quan sát được trong tối đa
  90 giây sau start; preview video xuất hiện trước inference result; E2E metric
  không tính warmup; không còn UI phụ thuộc duy nhất vào WebSocket/MJPEG; không
  có session/video state leak giữa hai video.
- Guardrail/rollback: Cloud Run chỉ là replay/evaluation plane, không phải FCW/LDW
  critical path; không tuyên bố realtime edge từ cloud benchmark; giữ revision
  `roadwatch-web-00006-4gc` và commit `bafc5c3` làm rollback; `min=1` chỉ là demo
  profile có chi phí, có thể trả về `min=0` sau demo; human gate chỉ còn cần
  kiểm tra URL/UX public.

**POST-WORK — 2026-08-24**

- Trạng thái cuối: `PASS` cho Cloud public latency/interaction gate; full cloud
  perception vẫn `PARTIAL` vì sign/lane/TTS cố ý không nằm trong CPU fast profile.
- Root cause đo trực tiếp trên revision cũ: object `89.117,27 ms`, lane
  `560.955,81 ms`, E2E frame đầu `650.359,62 ms`; state trong process kết hợp
  `concurrency=1`, `max=2`, WebSocket/MJPEG và CPU throttling làm UI treo hoặc
  nhìn sai session. Khi đổi video, `frame_id` cũ cũng chưa reset.
- Thay đổi thực tế: frontend chuyển sang polling 500 ms; thêm authenticated
  `/api/media/file` hỗ trợ Range/progressive preview; thêm stage/warmup metric;
  sửa lane-disable guard; thêm ONNX Runtime thread config; reset toàn bộ visual
  state khi start; làm lại upload control; Cloud Run dùng 4 CPU/8 GiB,
  concurrency 8, session affinity, min=max=1, CPU boost và no-throttling.
- Model decision: local/AAOS release không đổi — object `baseline_coco`, traffic
  sign `roadwatch_sign_phase2`, lane `yolop`. Cloud fast dùng artifact export
  `yolo11n_320.onnx` từ baseline; sign/lane/audio tắt riêng trên cloud. Object V2
  vẫn rejected (event recall 0,80→0,60; FAR 3,8462→4,6154/phút), UFLDv2 vẫn fail
  edge FPS gate; không hạ promotion gate để lấy model mới hơn.
- GCP evidence: final Cloud Build
  `3487d8f7-a876-4637-ac36-35d1f24a2484` success; revision
  `roadwatch-web-00010-rbk`, traffic 100%; fallback URL giữ nguyên. Runtime nạp
  `yolo11n_320.onnx`, provider CPU, error null; start `189 ms`, warmup
  `874,86 ms`; sau 2 giây có 6 frame + track; 37 sample đạt processed FPS
  `5,57`, E2E p50 `34,24 ms`, p95 `71,25 ms`.
- Replay evidence: `/api/media/file` trả HTTP `206 video/mp4`; đổi
  `test_video1`→`test_video10` reset `source_key=test_video10.mp4`, `frame_id=0`,
  `source_time=0`, tracks/signs rỗng. Upload UI đã đồng bộ white/blue card style.
- Verification local: full Python regression `147/147` pass; TypeScript build
  pass; Vite production build pass; targeted cloud/session tests `13/13` pass;
  `git diff --check` pass trước final docs/ledger check.
- Limitation: cloud object-only là public replay profile, không phải edge safety
  benchmark; muốn full sign/lane/TTS trên cloud cần GPU/async worker hoặc cached
  results. `min=1` + CPU always allocated có chi phí liên tục; signed resumable
  upload, cached result, Cloud SQL/PubSub worker, official DNS chưa hoàn tất.
- Rollback: revision `roadwatch-web-00006-4gc` và commit `bafc5c3`; có thể hạ
  `min=0`, bật CPU throttling hoặc chuyển traffic về revision cũ. Không xóa model,
  video, user RW-10 queue hoặc lịch sử Cloud Build.
- Bước tiếp theo: human smoke UI public; sau đó triển khai signed upload + async
  result worker/cached results và map official domain. Chi tiết tại
  `reports/CLOUD_DEMO_LATENCY_REMEDIATION.md`.


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

### WORK-20260826-001 — Lưu tài liệu giải thích UI metrics và Cloud flow

**PRE-WORK**

- Ngày: 2026-08-26.
- Task liên quan: tạo tài liệu giải thích các chỉ số UI và kiến trúc build/deploy
  Cloud hiện tại theo yêu cầu của chủ dự án.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: lưu câu trả lời thành tài liệu Markdown có thể dùng để bàn giao,
  thuyết trình và truy vết về công thức/luồng triển khai.
- Baseline: các công thức và hành vi runtime nằm trong `metrics.py`,
  `pipeline.py`, `risk.py`, `alerts.py`, `api.py` và frontend `main.tsx`.
- Phạm vi: chỉ tạo tài liệu mới trong `roadwatch/docs/` và cập nhật ledger này;
  không thay đổi code, model, threshold, deployment, secret hoặc dữ liệu.
- Kế hoạch: đối chiếu implementation hiện tại; viết định nghĩa, công thức,
  ví dụ và giới hạn diễn giải; mô tả Cloud Build/Run/GCS/TTS và luồng user-cloud-user;
  kiểm tra Markdown, diff và liên kết file.
- DoD: tài liệu phân biệt đúng inference latency với user-perceived latency,
  risk với confidence, warmup với cold start; nêu rõ cấu hình Cloud hiện tại,
  giới hạn CPU/replay plane và các guardrail an toàn.
- Guardrail/rollback: không sửa runtime; nếu tài liệu có sai lệch thì chỉ
  rollback file tài liệu và entry này, không ảnh hưởng baseline hoạt động.

**POST-WORK — 2026-08-26**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: tạo `docs/UI_METRICS_AND_CLOUD_FLOW.md`, ghi định nghĩa,
  công thức, ví dụ và giới hạn của Processed FPS, Sampling skip, E2E P50/P95,
  Warmup, FCW thresholds và Evidence packets; đồng thời mô tả stack, cấu hình,
  build pipeline và luồng user-cloud-user của GCP hiện tại.
- Bằng chứng: tài liệu phân biệt inference frame latency với upload/cold-start/
  network latency; phân biệt risk với confidence; xác nhận Cloud Run là replay/
  evaluation plane và các model runtime được bootstrap từ GCS.
- Decision: không thay đổi code, model, threshold, deployment, secret hoặc dữ
  liệu; Piper và runtime baseline vẫn giữ nguyên.
- Verification: kiểm tra file mới tồn tại, nội dung có đầy đủ các mục được yêu
  cầu và chạy kiểm tra whitespace/diff cho các file tài liệu liên quan.
- Khác kế hoạch: không có.
- Limitation: tài liệu mô tả implementation hiện tại; các metric runtime không
  thay thế ground-truth evaluation và public Cloud Run chưa phải safety-critical
  edge benchmark.
- Rollback: xóa riêng file tài liệu mới và entry này nếu chủ dự án yêu cầu;
  không ảnh hưởng runtime.

### WORK-20260826-002 — Đồng bộ RoadWatch vào P-162/web_demo

**PRE-WORK**

- Ngày: 2026-08-26.
- Task liên quan: thay toàn bộ nội dung thư mục `web_demo` trên nhánh `develop`
  của repo `AI20K-Build-Phase-Cohort-3/P-162` bằng nội dung `roadwatch` hiện tại.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: tạo commit trên đúng repo/nhánh đích, trong đó `web_demo/` phản ánh
  đầy đủ source RoadWatch hiện tại và không còn nội dung cũ.
- Baseline: cần kiểm tra remote, branch, divergence và nội dung `roadwatch/`
  trước khi thao tác; không được suy đoán rằng remote hiện tại là P-162.
- Phạm vi: chỉ thay đổi thư mục `web_demo/` trên repo P-162; không sửa xóa
  `roadwatch/` nguồn, không push sang repo ADAS_FOR_FRONTIER_CAMERA, không đưa
  secret/model/video/dataset nặng vào commit nếu chúng bị ignore theo policy.
- Kế hoạch: xác minh source và target; clone/fetch target branch trong thư mục
  tạm; snapshot tree trước; xóa đúng `web_demo/`; copy nội dung `roadwatch/`;
  kiểm tra diff/secret/size; commit và push thường lên `develop`; xác minh
  remote tree có các file tương ứng và cập nhật POST-WORK.
- DoD: `develop` trên repo P-162 có `web_demo/` chứa toàn bộ nội dung được phép
  của `roadwatch/`, không còn file cũ ngoài source mới; commit/push thành công;
  source local không bị thay đổi ngoài ledger.
- Guardrail/rollback: không dùng `reset --hard`, force-push hoặc xóa repo; việc
  xóa chỉ giới hạn trong clone/worktree tạm của `web_demo/`; giữ commit trước đó
  trên remote để có thể revert nếu cần.

**POST-WORK — 2026-08-26**

- Trạng thái cuối: `PASS`.
- Thay đổi thực tế: trên repo `AI20K-Build-Phase-Cohort-3/P-162`, nhánh
  `develop`, thay toàn bộ `web_demo/` cũ bằng bản RoadWatch hiện tại; giữ lại
  source, backend, frontend, AAOS, configs, docs, tests, scripts và deployment
  files cần thiết.
- Bằng chứng: commit `238632c` được push thành công lên `develop`; clone tạm
  sạch sau commit và tree mới có 333 file được Git track dưới `web_demo/`.
- Asset policy: không đưa `.env`, model weights, video, audio, ảnh dữ liệu,
  dataset, cache, build output hoặc artifact nặng vào commit; các asset runtime
  tiếp tục được tải theo README/Drive/GCS policy.
- Decision: `web_demo/` hiện là bản source RoadWatch được đồng bộ cho repo P-162;
  không thay đổi repo `ADAS_FOR_FRONTIER_CAMERA` và không thay đổi runtime/model.
- Khác kế hoạch: không có; push dùng fast-forward thường, không force-push.
- Limitation: GitHub tree không chứa asset lớn bị loại theo policy; người clone
  cần thực hiện hướng dẫn tải asset riêng trước khi chạy full demo.
- Rollback: revert commit `238632c` hoặc dùng commit `cc6dfea` trước đồng bộ;
  clone tạm giữ nguyên lịch sử trước đó và source local không bị xóa.

### WORK-20260827-007 — Triển khai fine-tune pilot và Quality Gate có hướng dẫn xác minh

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: triển khai `FT-00`, `RW-04.1-PILOT` và kiểm tra trạng thái
  `RW-10.1` theo quy trình Quality Gate đã được chủ dự án phê duyệt.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: tạo một Kaggle Object V3 pilot độc lập, chạy đúng GPU, sinh đủ
  artifact audit và dừng trước bước full fine-tune để chủ dự án xác minh.
- Baseline bất biến: Object production vẫn là `yolo11n.onnx`; Lane production
  vẫn là `yolop_lane_detection_640.onnx`; không train local và không ghi đè
  model/runtime production.
- Phạm vi: thêm kernel/script/test/config nhẹ cho Object pilot; kiểm tra lane
  review queue; submit Kaggle bằng `KAGGLE_API_TOKEN` từ `.env` nhưng không in
  secret. BARD tiếp tục quarantine.
- Lane guard: queue hiện chưa đủ `3.000 verified frames`, nên không fine-tune
  supervised Lane và không chuyển `candidate_unverified` thành ground truth.
- Kế hoạch: (1) preflight Kaggle và input metadata; (2) tạo pilot 1 epoch;
  (3) chỉ khi pilot ổn định mới cho phép pilot 3–5 epoch sau xác nhận PASS;
  (4) kiểm tra queue Lane và báo rõ thao tác Human cần làm; (5) ghi artifact,
  trạng thái, hash và hướng dẫn xác minh.
- DoD: Object pilot tách kernel/output, có GPU preflight, manifest, log, model
  checkpoint/ONNX, metrics và status; test offline pass; mọi Quality Gate nêu
  rõ cần xem gì, ở đâu, cách xem và mẫu phản hồi PASS/REJECT.
- Guardrail/rollback: không submit full training tự động sau pilot; không
  promote candidate nếu thiếu event regression; nếu job fail/OOM/missing input
  thì giữ baseline và lưu log lỗi; không force-push, reset hoặc xóa dữ liệu user.

**POST-WORK — 2026-08-27**

- Trạng thái cuối của local implementation: `PASS_LOCAL_SUBMITTED_PENDING_REMOTE_QG`.
- Thay đổi thực tế: tạo kernel package `kaggle/train_object_v3_pilot/` với
  `pilot_1_epoch` mặc định, output riêng, preflight/manifest/status/hash audit;
  thêm `scripts/submit_object_v3_pilot.ps1`, `scripts/finetune_preflight.ps1`,
  test contract và `docs/FINETUNE_QUALITY_GATE_RUNBOOK.md`.
- Bằng chứng local: preflight `PASS`; `11/11` targeted pytest pass; Python
  compile pass; queue Lane có `599` record nhưng chỉ `19` verified, nên lane
  supervised training vẫn bị khóa.
- Bằng chứng remote: Kaggle kernel
  `lekimnam/roadwatch-object-detector-v3-pilot` đã push thành công, version 1
  ở trạng thái `KernelWorkerStatus.RUNNING`; URL được lưu trong báo cáo bàn giao.
- Decision: chưa chạy full fine-tune, chưa promote candidate và chưa thay đổi
  Object/Lane production baseline. Chờ remote pilot hoàn tất và chủ dự án
  xác nhận `PASS OBJECT PILOT`.
- Limitation: remote metrics/checkpoint chưa có tại thời điểm ghi POST-WORK;
  trạng thái `RUNNING` không phải bằng chứng Quality Gate đã đạt.
- Rollback: bỏ qua candidate và tiếp tục dùng `yolo11n.onnx`/YOLOP; không cần
  rollback production vì output pilot nằm ở kernel/artifact riêng.

### WORK-20260827-008 — Chuẩn hóa credential selector cho hai Kaggle account

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: kiểm tra credential đã đổi tên thành
  `KAGGLE_API_TOKEN_ACCOUNT_1` và `KAGGLE_API_TOKEN_ACCOUNT_2`, đồng thời tạo
  selector an toàn cho các read-only preflight sau này.
- Trạng thái: `IN_PROGRESS`.
- Mục tiêu: không để duplicate `KAGGLE_API_TOKEN` khiến script chọn nhầm
  account; giữ Object pilot hiện tại dùng Account 1 và chuẩn bị kiểm tra Account
  2 mà không submit job hoặc dùng GPU ngoài phạm vi đã cho phép.
- Baseline bất biến: Kaggle Object V3 pilot đang chạy không bị submit lại; model
  production, dataset local và output candidate không bị thay đổi.
- Phạm vi: sửa script selector/preflight nhẹ, kiểm tra token/quota/quyền đọc;
  không lưu token vào file mới, không in token, không cấp quyền private dataset
  tự động và không dùng Account 2 để né quota.
- Lane guard: Account 2 chỉ được chuẩn bị cho Lane; supervised fine-tune vẫn
  block cho tới khi có đủ `3.000 verified frames`.
- Kế hoạch: xác minh tên biến; thêm `-Account 1/2` selector; giữ submit Object
  gắn Account 1; chạy read-only preflight Account 2; ghi rõ private access nào
  còn thiếu và cách cấp quyền hợp lệ.
- DoD: automation không còn phụ thuộc biến token trùng tên; Account 2 có report
  auth/quota/permission không lộ secret; test hiện tại vẫn pass; không có remote
  job mới được tạo trong task này.
- Guardrail/rollback: nếu selector sai hoặc token invalid thì dừng trước mọi
  Kaggle mutation; rollback chỉ bằng cách khôi phục script selector, không xóa
  kernel/dataset và không force-push.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `AUTH_PASS_PRIVATE_ACCESS_PENDING` cho Account 2.
- Thay đổi thực tế: chuẩn hóa `submit_object_v3_pilot.ps1` về
  `KAGGLE_API_TOKEN_ACCOUNT_1`; cập nhật `finetune_preflight.ps1` để bắt buộc
  hai token có tên riêng; thêm `kaggle_account_preflight.ps1`, test selector và
  `docs/KAGGLE_TWO_ACCOUNT_SETUP.md`.
- Bằng chứng: Account 1 và Account 2 đều `AUTH_PASS`; quota API đọc được; test
  targeted `13/13` pass; không submit job mới và không dùng GPU trong task này.
- Quyền dữ liệu: Account 2 trả `403 Forbidden` với target videos và lane teacher
  private dataset; chưa đủ điều kiện chạy Lane kernel.
- Decision: Object pilot tiếp tục giữ Account 1; Account 2 chỉ được dùng sau khi
  human owner cấp quyền private dataset hợp lệ và preflight trả `READY`.
- Limitation: việc thêm collaborator/chuyển quyền dataset là external access
  change, không tự động thực hiện; không được đổi dataset sang public mặc định.
- Rollback: xóa riêng selector/document nếu cần; không ảnh hưởng kernel Object
  pilot hoặc production baseline.

### WORK-20260827-009 — Sửa kiểm tra quyền collaborator Kaggle

**PRE-WORK**

- Ngày: 2026-08-27.
- Task liên quan: điều tra trường hợp Account 2 tải private dataset được trên
  Web nhưng preflight báo `403`.
- Trạng thái: `IN_PROGRESS`.
- Phát hiện ban đầu: `datasets status` trả `403` cho Account 2; endpoint này
  phục vụ creation/status và không phải phép kiểm tra quyền đọc phù hợp cho
  collaborator.
- Mục tiêu: thay phép kiểm tra quyền bằng `datasets files` read-only, phản ánh
  đúng khả năng Account 2 dùng dataset trong Kernel.
- Phạm vi: sửa selector/preflight và tài liệu; không tải dataset, không submit
  kernel, không dùng GPU và không thay đổi token/model/production runtime.
- Kế hoạch: chạy file-list check cho hai private dataset; status `ACCESS_OK`
  được coi là quyền đọc hợp lệ; giữ `datasets status` khỏi access gate; chạy
  targeted tests và cập nhật POST-WORK.
- DoD: Account 2 trả `READY` khi quota, kernel list, dataset list và file-list
  đều thành công; report ghi rõ `status_endpoint` không dùng để kết luận quyền
  đọc; không lộ secret.
- Guardrail/rollback: nếu file-list fail thì giữ trạng thái pending và không
  submit Lane; rollback chỉ revert logic preflight/document, không đổi quyền
  Kaggle hoặc dataset visibility.

**POST-WORK — 2026-08-27**

- Trạng thái cuối: `PASS_ACCOUNT_2_READY`.
- Root cause: `kaggle datasets status` là endpoint creation/status có thể yêu
  cầu quyền owner; dùng nó để kiểm tra collaborator read access tạo false
  negative `403`, dù Web UI cho phép tải dataset.
- Thay đổi thực tế: đổi permission gate trong `kaggle_account_preflight.ps1`
  sang `kaggle datasets files --page-size 5`; cập nhật note, tài liệu và test.
- Bằng chứng: Account 2 `quota`, `kernels list`, `datasets list` đều exit 0;
  file listing trả `ACCESS_OK` cho target videos và lane teacher model; report
  `reports/kaggle_account_2_preflight.json` có `status = READY`.
- Decision: Account 2 đã đủ quyền đọc private inputs để chuẩn bị Lane kernel;
  chưa submit Lane và chưa dùng GPU. Lane supervised training vẫn block tới
  khi đủ `3.000 verified frames`.
- Verification correction: `datasets files` là phép kiểm tra quyền đọc đúng;
  `datasets status` không còn là access gate.
- Rollback: giữ nguyên quyền dataset; nếu cần rollback chỉ khôi phục preflight
  cũ, nhưng không nên dùng status endpoint để kết luận collaborator bị từ chối.

### WORK-20260827-011 — Đánh giá RoadWatch Object Detector V3 Pilot

**PRE-WORK**

- Ngày: 2026-08-27.
- Task: kiểm tra read-only Kaggle Object Detector V3 Pilot sau khi chủ dự án
  báo job đã hoàn tất; không submit lại, không chạy training local và không
  thay đổi model production.
- Phạm vi kiểm tra: trạng thái kernel, GPU preflight, dataset manifest,
  training status, metrics, confusion matrix, prediction samples và artifact
  hash.
- Baseline bất biến: `yolo11n.onnx`; candidate V3 chỉ là artifact pilot.
- Guardrail: pilot 1 epoch chỉ chứng minh pipeline chạy ổn định; không được
  suy ra model đã tốt hơn baseline hoặc tự động promote.
- Rollback: không cần rollback production; nếu artifact download lỗi thì giữ
  report Kaggle và không dùng file chưa hoàn chỉnh làm model phát hành.

**POST-WORK — 2026-08-27**

- Trạng thái remote: `COMPLETE`; `run_mode=pilot_1_epoch`; `training_error=null`.
- Preflight: `PASS`, 2x Tesla T4, `training_local=false`, production model không
  thay đổi. Dataset manifest pass; 101.001 base images và 7.935 target-domain
  pseudo-labelled samples đã được ghi trong artifact Kaggle; val/test không bị
  sửa và target labels vẫn được đánh dấu pseudo.
- Metrics test của pilot: precision `0.5822`, recall `0.4201`, mAP50 `0.4509`,
  mAP50-95 `0.2565`. Đây là một epoch nên chỉ dùng để kiểm tra độ ổn định,
  không phải bằng chứng model tốt hơn baseline.
- Visual evidence: biểu đồ chỉ có một điểm epoch; confusion matrix cho thấy
  motorcycle/rider/person còn yếu, trong khi car tốt hơn. Chưa có event
  regression, VRU recall, false-alert rate hoặc latency edge nên không đạt
  promotion gate.
- Artifact: Kaggle `artifact_hashes.json` ghi nhận `best.pt` và `best.onnx`.
  Lần tải ONNX riêng về local bị ngắt và để lại file 0 byte, vì vậy file local
  này không được dùng; cần tải lại/remote-validate ONNX trước khi coi pilot
  đạt đầy đủ DoD artifact.
- Decision: `PASS_TECHNICAL_PILOT_ONLY`; `promotion_status` vẫn
  `blocked_pending_human_pseudo_label_review_and_event_regression`; giữ
  `yolo11n.onnx` làm production baseline. Chưa được submit pilot 3–5 epoch
  cho tới khi chủ dự án xác nhận `PASS OBJECT PILOT` và artifact ONNX được
  xác minh hoàn chỉnh.
- Bằng chứng local: `artifacts/kaggle/object_v3_pilot_output/` gồm
  `job_status.json`, `preflight.json`, `dataset_manifest.json`, `results.csv`,
  confusion matrix và validation prediction samples.

### WORK-20260827-012 — Replay evaluation Object V3 trên video dashcam

**PRE-WORK**

- Ngày: 2026-08-27.
- Task: tải và đánh giá candidate `best.pt` của Object V3 Pilot trên các video
  dashcam hiện có, loại trừ `dashcam_vietnam.mp4` là file nặng nhất theo yêu
  cầu chủ dự án.
- Phạm vi: evaluation-only; so sánh candidate với `models/yolo11n.pt` trên
  cùng timestamp/sample rate, ghi detection coverage, class distribution,
  confidence, throughput và ảnh preview. Không chạy fine-tune local.
- Baseline bất biến: `yolo11n.onnx`/`models/yolo11n.pt`; candidate không được
  đưa vào registry, Web, AAOS hoặc GCP.
- Giới hạn bằng chứng: video replay không có ground truth frame-level cho toàn
  bộ nguồn nên chỉ là diagnostic; không dùng để suy ra mAP/event recall.
- Guardrail/rollback: không overwrite model; output đặt trong artifact/report
  riêng. Nếu thiếu dependency, codec hoặc artifact thì dừng và ghi lỗi thay vì
  bỏ qua frame âm thầm.

### WORK-20260827-013 — Object V3 smoke 5 epoch sau replay video

**PRE-WORK**

- Ngày: 2026-08-27.
- Task: chuẩn bị smoke fine-tune `pilot_3_5_epoch` trên Kaggle sau khi Object
  V3 Pilot 1 epoch đã hoàn tất và được replay trên các video dashcam nhẹ hơn.
- Cơ sở: replay không có ground truth toàn bộ; candidate cho thấy `rider` có
  xu hướng xuất hiện nhiều nhưng `person/motorcycle` giảm so với baseline.
  Smoke run chỉ để kiểm tra learning stability, không được coi là promotion.
- Phạm vi: copy kernel package thành package smoke riêng, giữ dataset/split,
  checkpoint và pseudo-label policy; chạy đúng 5 epoch trên GPU Kaggle Account
  1. Không chạy full training local và không thay production model.
- Baseline bất biến: `yolo11n.onnx`; V3 Pilot version 1 và artifact replay phải
  còn nguyên để fallback/đối chiếu.
- Quality gate: không tự động promote; bắt buộc kiểm tra loss, NaN/OOM,
  validation metrics, class confusion, checkpoint, ONNX load và event regression
  sau khi smoke hoàn tất.
- Rollback: dùng lại kernel V3 Pilot version 1 hoặc bỏ qua smoke candidate;
  không force-push, không xóa artifact và không đổi model registry.

### WORK-20260827-014 — Sửa kernel ID sau khi submit Object V3 smoke

**PRE-WORK**

- Ngày: 2026-08-27.
- Task: sửa lỗi hậu kiểm trong wrapper submit Object V3 smoke. Kaggle đã báo
  push thành công nhưng wrapper kiểm tra status bằng kernel ID pilot cũ và nhận
  `404`.
- Phạm vi: chỉ đồng bộ metadata/status lookup với kernel slug mới do Kaggle
  tạo; không submit lại job đang tồn tại, không tải/xóa artifact và không đổi
  production model.
- Guardrail: phải kiểm tra đúng URL mới trước khi kết luận job; nếu status
  không đọc được thì báo `UNKNOWN`, không suy diễn thành lỗi training.
- Rollback: khôi phục riêng wrapper/metadata lookup; kernel smoke remote không
  bị xóa hoặc sửa lịch sử.

**POST-WORK**

- Đã sửa `roadwatch/kaggle/train_object_v3_smoke/kernel-metadata.json` để dùng
  đúng kernel ID `lekimnam/roadwatch-object-detector-v3-smoke-5-epochs`.
- Đã sửa `roadwatch/scripts/submit_object_v3_smoke.ps1` để status lookup dùng
  đúng slug mới. Local metadata parse, Python compile và `git diff --check`
  đều đạt; các cảnh báo còn lại chỉ là line-ending CRLF/LF của worktree.
- Không submit lại. Read-only Kaggle status xác nhận kernel đúng đang ở
  `KernelWorkerStatus.RUNNING` trên tài khoản Account 1; lỗi `404` trước đó là
  lỗi wrapper dùng slug pilot cũ sau khi push thành công, không phải lỗi train.
- Chưa có metrics/checkpoint cuối để đánh giá smoke; không promote candidate,
  không thay model production và vẫn fallback về `models/yolo11n.pt`/runtime
  hiện tại. Tiếp tục kiểm tra sau khi Kaggle chuyển sang `COMPLETE`.

### WORK-20260828-015 — Đánh giá Object V3 Smoke sau Kaggle Complete

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: tải, kiểm tra và đánh giá Object V3 Smoke 5 epochs sau khi Kaggle
  chuyển trạng thái `COMPLETE`; đối chiếu artifact, metrics, load/inference
  và replay trên các video dashcam nhẹ hơn.
- Phạm vi: evaluation-only; không chạy fine-tune trên local, không ghi đè
  `models/yolo11n.pt`, không promote candidate vào Web/AAOS/GCP.
- Bất nhất cần kiểm tra: `job_status.json` khai báo `epochs=5` nhưng
  `results.csv` hiện có 3 record epoch; không được coi là đủ bằng chứng hội tụ
  nếu chưa giải thích được sự khác nhau.
- Quality gate: kiểm tra GPU preflight, training error, taxonomy, checkpoint,
  ONNX load, loss/metrics hữu hạn, confusion/prediction và event/video replay.
  Video replay không thay thế ground truth/event regression.
- Rollback: giữ nguyên baseline `models/yolo11n.pt`; candidate chỉ được lưu
  trong artifact riêng và chỉ được xem xét full fine-tune sau khi smoke đạt
  technical gate và chủ dự án xác nhận tiếp tục.

### WORK-20260828-016 — Object V3 Full Fine-tune sau Smoke Gate

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: chuẩn bị và submit full fine-tune Object V3 trên Kaggle Account 1 sau
  khi smoke job đã hoàn tất và artifact đã load/inference được.
- Lý do tiếp tục: smoke chứng minh pipeline kỹ thuật ổn định, nhưng chỉ chạy
  thực tế 3/5 epoch do early stopping và chưa đạt promotion gate; cần full run
  để đánh giá hội tụ trên cùng train/val/test split.
- Phạm vi: chỉ chạy remote Kaggle GPU; không train local, không thay
  `models/yolo11.pt`/`models/yolo11n.onnx`, không đưa candidate vào Web/AAOS/GCP.
  BARD tiếp tục bị cách ly; target-domain labels vẫn là pseudo-label train-only.
- Artifact/rollback: full output đặt ở package/artifact riêng; smoke, pilot và
  production baseline không bị overwrite. Nếu full candidate fail bất kỳ
  critical gate nào thì giữ baseline và đánh dấu candidate rejected.
- Quality gate sau job: kiểm tra actual epochs/early stopping, loss hữu hạn,
  held-out precision/recall/mAP, confusion matrix, ONNX parity, event
  regression, VRU recall, false alerts và latency. Không promote chỉ dựa vào
  mAP hoặc việc job báo `COMPLETE`.

**SUBMISSION CHECKPOINT**

- Smoke artifact đã được kiểm tra: `best.pt` và `best.onnx` load/inference
  được; SHA-256 local khớp `artifact_hashes.json`. Smoke có `3` dòng epoch
  thực tế dù cấu hình yêu cầu tối đa `5`, phù hợp với early stopping `patience=2`.
- Static held-out smoke metrics: precision `0.6328`, recall `0.4382`, mAP50
  `0.4857`, mAP50-95 `0.2826`; recall/mAP50-95 chưa đạt promotion gate. Replay
  dashcam vẫn chỉ là diagnostic vì không có ground truth frame-level.
- Đã submit full package bằng Account 1; Kaggle đã tạo URL
  `https://www.kaggle.com/code/lekimnam/roadwatch-object-detector-v3-full-fine-tune`.
  Read-only API xác nhận trạng thái hiện tại `RUNNING`, `failureMessage=null`.
- Đã sửa wrapper từ slug `full-finetune` sang slug thực tế `full-fine-tune`;
  không submit lại. Chưa có full metrics để quyết định promote; baseline vẫn
  là model active và candidate chỉ được đánh giá sau khi job hoàn tất.

### WORK-20260828-017 — Benchmark model YOLO11S Drive Scene Carla

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: tải candidate `UNIC0RN-Zhu/yolo11s-drive-scene-carla-v1` từ Hugging
  Face vào `roadwatch/models/yolo11s-drive-scene`, kiểm tra artifact/model
  metadata và replay so sánh với `models/yolo11n.pt` baseline trên cùng video,
  cùng sampling và cùng điều kiện CPU.
- Candidate classes dự kiến: `vehicle`, `pedestrian`, `cyclist`, `motorcycle`,
  `traffic_light`, `traffic_sign`, `traffic_cone`, `road_barrier`. Đây là
  taxonomy khác production 7 lớp, nên không được đưa thẳng vào Risk Engine;
  phải có mapping/compatibility report trước khi thử integration.
- Phạm vi: benchmark/evaluation-only; không thay model registry, Web, AAOS,
  GCP hoặc model production; không train local và không can thiệp Kaggle full
  fine-tune đang chạy.
- Bằng chứng bắt buộc: download manifest/hash, model load, class list, replay
  report, preview và cảnh báo rõ rằng video không có ground truth nên không
  suy ra mAP/event recall. Benchmark công bố của model chỉ là thông tin tham
  khảo, không phải bằng chứng release của RoadWatch.
- Rollback: candidate nằm ở thư mục riêng; nếu load lỗi, class mapping không
  phù hợp hoặc event-level chưa chứng minh được lợi ích thì giữ nguyên
  `models/yolo11n.pt`.

**POST-WORK**

- Download public repository thành công tại `roadwatch/models/yolo11s-drive-scene/`.
  `best.pt` có SHA-256
  `a96c29ef518990f410f54ec2c4a4ef617b2b184996c2b980eb44072243070c44`, khớp
  upstream `SHA256SUMS`; model load được với đủ 8 class.
- Đã export `best.onnx` local với input static `1x3x640x640`; ONNX Runtime
  CPUExecutionProvider load/inference đạt. Lần replay batch 8 thất bại vì
  artifact static batch 1; chạy lại batch 1 thành công.
- ONNX same-frame replay trên 982 frame của 3 video nhẹ hơn hoàn tất. Candidate
  có throughput gộp `10,530 FPS` so với baseline `24,034 FPS` (thấp hơn khoảng
  `56,2%`), đồng thời có taxonomy `vehicle` tổng quát và dấu hiệu box overlap/
  generic sign detection cần kiểm chứng thêm.
- Quyết định: `R&D / diagnostic only — KHÔNG PROMOTE`; không thay production,
  không đưa vào Risk Engine/Web/AAOS/GCP. Báo cáo:
  `reports/YOLO11S_DRIVE_SCENE_VS_BASELINE_20260828.md` và
  `reports/yolo11s_drive_scene_onnx_vs_yolo11n_onnx_replay_20260828.json`.

### WORK-20260828-018 — Benchmark TwinLiteNet+ Medium với YOLOP

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: tải checkpoint `TwinLiteNet+ Medium` từ repository upstream vào
  `models/twinlitenetplus_medium.pth`, giữ riêng như candidate lane/drivable
  area và benchmark trực tiếp với `models/yolop_lane_detection_640.onnx`.
- Phạm vi: evaluation-only; không thay YOLOP production, không thay đổi Web,
  AAOS, GCP hoặc Lane V2 registry; không train local và không can thiệp các
  Kaggle job đang chạy.
- Điều kiện so sánh: cùng video/frame, cùng preprocessing 640x640 và cùng
  runtime khi có thể; ghi rõ nếu kết quả chỉ là diagnostic vì video không có
  ground-truth lane mask.
- Bằng chứng bắt buộc: nguồn/checkpoint/hash, model load thành công, benchmark
  latency P50/P95, temporal stability, mask coverage/quality, preview cùng
  frame và báo cáo quyết định promote/không promote.
- Rollback: candidate nằm ở artifact riêng; nếu load lỗi, output không tương
  thích hoặc chưa chứng minh được lợi ích event-level thì giữ nguyên YOLOP.

**POST-WORK**

- Đã tải checkpoint `TwinLiteNet+ Medium` vào
  `models/twinlitenetplus_medium.pth`; SHA-256 là
  `04A7959946F687482256D1A499EE4E0AB5D523E9C1760BE41E7E797DC65066FF`.
- Đã vendor-lock phần model tối thiểu tại
  `third_party/twinlitenetplus/model/` và giữ license upstream.
- Đã xác minh checkpoint load thành công, có `478,876` parameters và hai output
  segmentation cho drivable-area/lane.
- Đã thêm script benchmark và chạy 41 frame trên 7 video bằng CPU. YOLOP đạt
  P50/P95 `190.393/206.980 ms`; TwinLiteNet+ Medium đạt
  `132.204/142.956 ms`. Đây là replay diagnostic không có ground truth.
- Đã sinh JSON report và ảnh overlay tại `reports/`; candidate vẫn là
  `R&D / diagnostic only`, không thay YOLOP production và không đưa vào
  Web/AAOS/GCP.
- Full benchmark ban đầu gặp lỗi render khi frame không có mask; đã sửa bằng
  guard `np.any(visible)` và chạy lại thành công. Đây là lỗi benchmark-only.

### WORK-20260828-019 — Export ONNX và benchmark công bằng TwinLiteNet+ Medium

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: export `models/twinlitenetplus_medium.pth` sang ONNX candidate riêng,
  kiểm tra model graph và output parity với PyTorch, sau đó benchmark ONNX
  candidate với YOLOP bằng cùng ONNX Runtime CPU.
- Phạm vi: evaluation-only; không thay `models/yolop_lane_detection_640.onnx`,
  không thay Perception Orchestrator, Web, AAOS, GCP hoặc production registry.
  Không train local và không can thiệp Kaggle.
- Export contract dự kiến: hai output theo thứ tự `drivable_logits`,
  `lane_logits`, input RGB float32 `/255.0`; ưu tiên static spatial shape để
  tránh giới hạn `adaptive_avg_pool2d` của ONNX exporter và phù hợp edge.
  Kích thước mục tiêu là 640x384 cho video dashcam 16:9; nếu cần aspect ratio
  khác thì export một artifact static riêng.
- Bằng chứng bắt buộc: ONNX checker/load thành công, output shape đúng, parity
  sai số có giới hạn, benchmark P50/P95 và artifact hash. Nếu export/parity
  fail thì giữ candidate PyTorch chỉ để R&D và fallback YOLOP.

**POST-WORK**

- Lần export dynamic spatial shape thất bại tại `adaptive_avg_pool2d`; đã đổi
  contract sang static `1x3x384x640`, phù hợp video 16:9 và edge deployment.
- Đã export thành công `models/twinlitenetplus_medium.onnx`; ONNX checker và
  ONNX Runtime load đều PASS. PyTorch–ONNX parity PASS với max absolute error
  `9.2387e-05` trên input `384x640`.
- Đã benchmark lại 41 frame trên cùng 7 video bằng cùng ONNX Runtime CPU:
  YOLOP P50/P95 `203.254/254.416 ms`; candidate ONNX P50/P95
  `76.815/90.080 ms`. Candidate giảm latency khoảng `62.2%/64.6%`.
- Đã sinh export manifest, benchmark JSON và preview overlay trong `reports/`.
  Candidate vẫn `R&D / diagnostic only`; không thay YOLOP production và không
  đưa vào Web/AAOS/GCP.
- Có một lần full benchmark bị gọi từ sai working directory; đã chạy lại bằng
  root project và nhận kết quả hoàn chỉnh. Đây là lỗi thao tác benchmark-only.
- Đã bổ sung `--runtime directml` và chạy thêm 41 frame trên AMD
  `DmlExecutionProvider`: YOLOP P50/P95 `58.780/62.611 ms`; candidate ONNX
  P50/P95 `34.228/36.408 ms`, không có runtime error.
- Đã cập nhật báo cáo ONNX với profile DirectML và giữ rõ giới hạn: chưa có
  ground truth lane, chưa benchmark Jetson TensorRT và chưa promote candidate.

### WORK-20260828-020 — Xây dựng ground-truth độc lập cho TwinLiteNet+

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: tạo package ground-truth lane/drivable có provenance độc lập với
  YOLOP và TwinLiteNet+, lấy dữ liệu từ queue review hiện tại và chỉ nhận các
  record được human reviewer xác nhận rõ ràng.
- Không được dùng `model_proposal`, YOLOP output, TwinLiteNet+ output hoặc
  AI-assisted review làm ground-truth; các record `pending`, `needs_recheck`,
  `uncertain=true` và reviewer AI phải bị loại khỏi metric chính.
- Package phải giữ source video/frame, lane count, ego-boundary polylines và
  raster boundary mask; drivable-area mask chỉ được ghi là có sẵn khi có nhãn
  độc lập tương ứng.
- Sau khi tạo package, chạy evaluator trên cùng frame cho YOLOP và candidate.
  Nếu số human-verified không đạt ngưỡng, trạng thái phải là blocked và không
  được cân nhắc thay model.
- Rollback: chỉ tạo artifact/evaluation report riêng; không sửa queue review
  gốc và không thay YOLOP production.

**POST-WORK**

- Đã thêm `build_twinlitenetplus_ground_truth.py`: chỉ nhận record có
  `review_status=verified`, reviewer là người thật, `uncertain=false`, lane
  count hợp lệ và ego-boundary hợp lệ; tuyệt đối không dùng model proposal.
- Đã xây dựng package riêng tại
  `evaluation/twinlitenetplus_ground_truth_v1/` gồm manifest/JSONL và cơ chế
  trích frame + rasterize boundary mask khi có record đủ điều kiện.
- Đã chạy với queue hiện tại: tổng `599`, thuộc evaluation split `test` là
  `120`, human-verified hợp lệ `0`; package chuyển trạng thái
  `blocked_insufficient_human_ground_truth`.
- Đã thêm `evaluate_twinlitenetplus_ground_truth.py`; evaluator hiện trả về
  `BLOCKED` khi chưa có nhãn độc lập, không sinh metric giả.
- Đã tạo báo cáo hướng dẫn review, ground-truth contract và promotion gate tại
  `reports/TWINLITENETPLUS_GROUND_TRUTH_STATUS_20260828.md`.
- Không thay YOLOP production, không chạy training local và không promote
  TwinLiteNet+ vào Web/AAOS/GCP.

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: tạo clean held-out review queue cho ground-truth TwinLiteNet+ từ 400
  record `test` hiện có.
- Chỉ giữ metadata nguồn/frame/điều kiện; phải loại bỏ toàn bộ model proposal,
  nhãn AI/provisional, reviewer AI và kết quả suy luận khỏi queue review mới.
- Queue mới phải bắt đầu ở `review_status=pending`; chỉ reviewer con người được
  phép chuyển sang `verified` sau khi xem ảnh, không được tự động xác nhận.
- Không sửa queue RW-10 gốc/provisional và không thay model YOLOP production.
- Rollback: xóa queue review mới và dùng lại queue cũ; không ảnh hưởng runtime.

**POST-WORK**

- Đã thêm `prepare_twinlitenetplus_review_queue.py` để tách 400 record
  `test/held-out` từ provisional queue thành queue review sạch.
- Queue mới tại
  `evaluation/twinlitenetplus_ground_truth_review_queue_v1.json` có 400/400
  ảnh tồn tại, 0 proposal/model field và 400 record `pending`.
- Đã chạy builder vào
  `evaluation/twinlitenetplus_ground_truth_v1/manifest.json`; kết quả đúng là
  `blocked_insufficient_human_ground_truth` với 0/400 record verified.
- Đã chạy evaluator; kết quả `blocked_insufficient_ground_truth`, không sinh
  metric giả và không promote TwinLiteNet+.
- Đã cập nhật báo cáo trạng thái với lệnh mở review UI, builder và evaluator.
- Đã kiểm tra py_compile cho ba script; không sửa queue RW-10 gốc, không thay
  YOLOP production và không chạy training local.

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: benchmark thực nghiệm YOLOP và TwinLiteNet+ trên cùng các video test
  hiện có để hỗ trợ lựa chọn model cho demo một ngày.
- Phải dùng cùng frame/timestamp, runtime DirectML, ghi rõ preprocessing khác
  nhau và không biến quality proxy/visual replay thành ground-truth accuracy.
- Kết quả chỉ được dùng cho demo candidate; YOLOP vẫn là fallback, không tự động
  promote nếu thiếu nhãn lane độc lập.
- Bao gồm latency P50/P95, quality proxy, temporal stability, model agreement,
  per-video breakdown và ảnh overlay để kiểm tra bằng mắt.
- Không chạy training local, không xóa/sửa model production và không sửa queue
  ground-truth review.

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: tích hợp TwinLiteNet+ ONNX vào PerceptionEngine dưới dạng profile thử
  nghiệm và giữ YOLOP làm fallback runtime.
- Profile mặc định phải tiếp tục là `yolop`; chỉ bật TwinLiteNet+ bằng biến môi
  trường cho phiên test, không sửa release manifest/model registry production.
- Fallback phải được load sẵn, kích hoạt khi candidate thiếu model, load lỗi,
  inference lỗi hoặc trả lane mask rỗng; output phải ghi `source`,
  `fallback_used` và `fallback_reason`.
- Kiểm tra bằng real frame DirectML và test startup/API; không chạy training,
  không xóa model và không thay queue ground-truth.

**POST-WORK**

- Đã thêm `benchmark_lane_models_all_videos.py` và chạy replay trên toàn bộ 16
  video `.mp4` trong `media`, 12 timestamp/video, tổng 192 frame/model.
- YOLOP và TwinLiteNet+ đều load thành công bằng `DmlExecutionProvider`, không
  có read failure hoặc runtime error; sinh 64 ảnh overlay để kiểm tra bằng mắt.
- Kết quả: YOLOP P50/P95 `59.709/65.874 ms`; TwinLiteNet+ P50/P95
  `33.181/37.625 ms`; TwinLiteNet+ giảm P95 khoảng `42.9%`.
- Quality proxy trung bình: YOLOP `0.6438`, TwinLiteNet+ `0.7238`; temporal
  proxy: YOLOP `0.0958`, TwinLiteNet+ `0.1639`; các số này không được coi là
  accuracy vì chưa có ground-truth.
- TwinLiteNet+ thắng quality proxy ở `13/16` video, nhưng mask agreement trung
  bình chỉ `0.4061`, nên đây là demo evidence chứ chưa phải chứng minh độ chính
  xác tốt hơn.
- Quyết định: đề xuất TwinLiteNet+ làm `demo-primary candidate`, giữ YOLOP làm
  fallback; chưa tự động promote vào production/Web/AAOS khi chưa có lane GT,
  LDW event regression và target-edge benchmark.

**POST-WORK**

- Đã tích hợp `TwinLiteNetPlusSegmenter` vào `PerceptionEngine` dưới profile
  `twinlitenetplus`; mặc định `yolop` không thay đổi.
- Đã tích hợp `FallbackLaneSegmenter`: load sẵn TwinLiteNet+ và YOLOP; fallback
  khi candidate thiếu file, load/inference lỗi hoặc lane mask rỗng; output ghi
  `source`, `fallback_used`, `fallback_reason`.
- Đã mở rộng config validation/model inventory và thêm hướng dẫn local vào
  `README.md`; không sửa release manifest/model registry production.
- Real-frame DirectML smoke test pass: TwinLiteNet+ output `source=twinlitenetplus`,
  `fallback_used=false`; forced-missing-model test pass với
  `source=yolop_fallback`, `fallback_used=true`.
- Web E2E test pass trên `test_video10.mp4`: 30 frame đã xử lý, lane profile
  TwinLiteNet+ load bằng DirectML, YOLOP fallback cũng load bằng DirectML,
  `fallback_count=0` trong phiên bình thường.
- Full backend pytest pass khi chạy từ thư mục `roadwatch`; không chạy training
  local, không đổi queue ground-truth và không promote candidate thành release.

**POST-WORK**

- Đã bổ sung `ROADWATCH_TWINLITENETPLUS_MODEL` để kiểm tra forced fallback bằng
  filename thiếu trong model root mà không đổi/xóa model thật.
- Đã cập nhật README với quy trình bật TwinLiteNet+, kiểm tra status, forced
  fallback và rollback về YOLOP.
- Forced fallback smoke test pass trên frame thật DirectML:
  `source=yolop_fallback`, `fallback_used=true`, `fallback_count=1`; YOLOP
  provider là `DmlExecutionProvider` và không có lỗi.
- Full backend pytest pass; profile mặc định vẫn `yolop`, release manifest và
  model registry production không bị sửa.

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: bổ sung biến môi trường test để cưỡng chế TwinLiteNet+ load failure mà
  không đổi tên hoặc xóa model thật, giúp human kiểm chứng YOLOP fallback.
- Chỉ cho phép override tới một filename nằm trong `models`; không cho phép path
  ngoài model root và không thay đổi profile mặc định.
- Cập nhật README với quy trình candidate test, forced fallback và rollback.

**POST-WORK**

- Đã điều chỉnh status fallback để phân biệt `active_model`,
  `primary_loaded` và `fallback_loaded`; không còn gây hiểu nhầm rằng toàn bộ
  pipeline chưa load khi chỉ candidate bị lỗi.
- Đã cập nhật README với lệnh bật TwinLiteNet+, kiểm tra status, forced fallback
  an toàn và rollback.
- Đã chạy py_compile và focused pytest sau thay đổi; đều pass.
- Forced fallback đã xác nhận lại trên frame thật bằng DirectML:
  `active_model=yolop_fallback`, `primary_loaded=false`, `fallback_loaded=true`,
  `source=yolop_fallback`, `fallback_used=true`, `fallback_count=1`.
- Không thay đổi model file thật, queue ground-truth, release manifest hoặc
  model registry; YOLOP vẫn là rollback baseline.

### WORK-20260828-OBJECT-OPEN-MODEL-BENCHMARK

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: research và benchmark các object detector pretrained miễn phí mới nhất
  có thể tải về, ưu tiên YOLO26n/YOLO26s, so với `yolo11n` hiện tại trên cùng
  video/frame và cùng runtime khi có thể.
- Baseline production không được thay đổi. Candidate phải được lưu tách biệt,
  có license/source/hash, và chỉ được đề xuất promote sau khi vượt event recall,
  false-alert, semantic/direction và latency gate; mAP COCO không đủ để quyết định.
- Không chạy fine-tune local; chỉ tải pretrained weights và chạy inference/
  export/benchmark. Không commit model lớn vào Git.
- Nếu candidate có taxonomy hoặc output contract khác baseline, phải ghi rõ và
  không được đưa thẳng vào rule engine mà chưa có adapter/schema mapping.
- Rollback: xóa candidate artifacts/reports hoặc dùng lại `baseline_coco`;
  không sửa release manifest/model registry trong giai đoạn benchmark.

**POST-WORK**

- Đã research YOLO26 là dòng real-time mới nhất của Ultralytics tại thời điểm
  benchmark và tải public `yolo26n.pt`/`yolo26s.pt` từ repository chính thức;
  checksum được ghi trong report.
- Đã export `yolo26n.onnx`/`yolo26s.onnx` cố định 640x640 và bổ sung adapter
  nhận output end-to-end `[x1,y1,x2,y2,confidence,class_id]`, không ảnh hưởng
  output raw của YOLO11.
- Đã thêm hai profile candidate `yolo26n_public` và `yolo26s_public`; profile
  mặc định vẫn `baseline_coco`, release manifest/model registry production
  không bị thay đổi.
- Locked regression 3 scenario: YOLO26n bị reject vì event recall giảm
  `0.75 -> 0.375`; YOLO26s giữ recall ngang baseline nhưng vượt alert-density
  gate và chậm hơn. YOLO11n tiếp tục active/fallback.
- Replay đại diện 7 video, 415 frame/model, DirectML hoàn tất không runtime
  error/read failure; report lưu tại `reports/object_open_models_representative.json`.
- Đã thêm test parser YOLO26 end-to-end; py_compile và backend test phải được
  chạy lại trước khi dùng candidate. Không fine-tune local và không promote
  candidate vào Web/AAOS/GCP.

### WORK-20260828-LAYER1-TEST-MODEL-BENCHMARK

**PRE-WORK**

- Ngày: 2026-08-28.
- Task: benchmark các artifact mới trong `models/layer1_test` so với ba
  runtime production hiện tại của RoadWatch: object `yolo11n`, traffic sign
  `roadwatch_detector_v2` và lane/drivable `yolop_lane_detection_640`.
- Không thay đổi active production profile, release manifest, model registry,
  rule engine hoặc fallback trong giai đoạn benchmark.
- Phải kiểm tra output contract/taxonomy trước khi chạy. Artifact không tương
  thích trực tiếp chỉ được đánh giá chẩn đoán và không được đưa vào pipeline.
- Không chạy fine-tune local; chỉ inference/replay/benchmark trên video hiện có.
- Report phải phân biệt rõ metric có ground truth và proxy không có ground truth;
  không promote candidate chỉ vì FPS hoặc mAP công bố.
- Artifact được phát hiện thêm `yolo26s-depth.pt` là depth-only model; không coi
  đây là object detector thứ ba và không dùng thay thế các head hiện tại.

**POST-WORK**

- Đã xác minh thư mục có bốn artifact: `BEST_detection_bdd7_ep18.pt`,
  `BEST_signs_vn27_ep21.pt`, `yolopv2.pt` và depth-only
  `yolo26s-depth.pt`. Ba artifact đầu được ghép đúng với object/sign/lane;
  depth model được loại khỏi phép so sánh thay thế.
- Đã thêm script `scripts/benchmark_layer1_test_models.py`, chạy smoke rồi
  replay 72 frame đồng timestamp trên ba video representative, loại trừ video
  `dashcam_vietnam.mp4`; không có read/runtime error.
- Đã chuẩn hóa lane quality proxy và drivable-pixel counting trong benchmark để
  không phụ thuộc công thức riêng của từng adapter. Các số này vẫn chỉ là proxy
  vì chưa có ground truth frame-level.
- Kết quả: `yolo11n`, `roadwatch_detector_v2` và `yolop_lane_detection_640.onnx`
  tiếp tục active. Candidate object/sign/lane không được promote do taxonomy,
  latency và thiếu event/lane ground truth; report ở
  `reports/LAYER1_TEST_MODELS_BENCHMARK_20260828.md` và JSON kèm theo.
- Đã smoke inference thêm `yolo26s-depth.pt` trên một frame: `task=depth`,
  `boxes=None`, khoảng `2085.870 ms` CPU; chỉ xác nhận model load/chạy được,
  không coi là phép so sánh object/lane.
- Không thay đổi active production profile, release manifest, model registry,
  rule engine hoặc fallback. Model lớn vẫn không được commit Git.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: triển khai lại bố cục React cho Driver HUD và Engineer Console theo
  mockup đã được chủ dự án duyệt, đồng thời giữ fallback về layout hiện tại nếu
  build hoặc kiểm thử thất bại.
- Driver HUD: giữ vùng HUD mô phỏng khoảng 20% bên trái; khu vực phải ưu tiên
  video 16:9, chỉ hiển thị trạng thái/cảnh báo và điều khiển replay cần thiết;
  không đưa metrics kỹ thuật, Event History hoặc HITL vào vùng tài xế.
- Engineer Console: giữ HUD bên trái; đặt metrics phía trên video rộng; giữ
  Event History, Model Health và HITL ở vùng dưới video.
- Video contract bất biến: container dùng `aspect-ratio: 16 / 9`, media dùng
  `object-fit: contain`, không ép đồng thời width/height theo tỷ lệ tùy ý;
  letterbox được chấp nhận nhưng crop/stretch bị cấm. Phải có responsive fallback
  không làm mất tỷ lệ video.
- Dữ liệu tốc độ/HUD trên replay phải được gắn là mô phỏng hoặc telemetry
  read-only; không được mô tả như CAN/OEM data thật khi chưa có xe thật.
- Phạm vi: chỉ sửa Web HMI và các test liên quan; không thay model, risk rule,
  TTS provider, AAOS vehicle contract hoặc Cloud runtime. Không thêm actuator
  command.
- Bằng chứng bắt buộc: `npm run build`, test liên quan, kiểm tra video ratio
  contract, session/video-switch isolation và fallback không làm mất trạng thái.
- Rollback: dùng commit backup `92d9a98` trên P-162/main cho bản remote; local
  không reset hoặc xóa thay đổi chưa commit của chủ dự án.

**POST-WORK**

- Đã triển khai layout Driver HUD và Engineer Console trong
  `frontend/src/main.tsx` và `frontend/src/styles.css`.
- Driver hiện có HUD mô phỏng khoảng 20% bên trái; vùng phải ưu tiên video lớn,
  trạng thái âm thanh/camera, hazard banner, replay controls và guardrail. Các
  metrics kỹ thuật không còn nằm trong Driver HUD.
- Engineer hiện có HUD bên trái; metrics Processed FPS, Sampling skip, E2E P50,
  E2E P95 và Warmup nằm phía trên video rộng; Event History, Model Health và HITL
  nằm phía dưới.
- Đã thêm Event History filter `Tất cả/Critical/Warning/Suppressed`, giới hạn
  100 event gần nhất, chọn event để tua về `source_time` khi session seekable,
  và hiển thị lifecycle/audio/evidence note.
- Đã thêm nhãn rõ ràng `DEMO · TELEMETRY MÔ PHỎNG`; tốc độ HUD là giá trị replay
  mô phỏng, không tuyên bố là CAN/OEM telemetry.
- Đã sửa preview source regex để phân biệt source video hợp lệ và giữ reset
  preview error theo `session_id/source`, tránh rò trạng thái giữa video.
- Đã áp dụng video contract: `data-aspect-ratio="16:9"`, CSS
  `aspect-ratio: 16 / 9`, `object-fit: contain`, `object-position: center`; không
  dùng `object-fit: cover`. Letterbox được chấp nhận để cấm crop/stretch.
- Đã thêm `tests/test_ui_contract.py` kiểm tra aspect-ratio contract và Event
  History contract.
- Xác minh: TypeScript `tsc -b` PASS; Vite 8 build PASS vào artifact tạm
  `frontend/dist-ui-v2`; focused backend tests PASS; full pytest PASS khi chạy
  từ thư mục `roadwatch` với `PYTHONPATH` đúng.
- Build mặc định vào `frontend/dist` bị khóa bởi file bundle cũ trên Windows;
  không xóa bản cũ, đã dùng `--outDir dist-ui-v2` để xác minh build mới an toàn.
- Visual browser QA chưa thể chạy trong session vì Browser MCP chưa khả dụng;
  cần human mở Web local/AAOS và kiểm tra bố cục thực tế trước khi release.
- Không thay model, rule engine, TTS backend, AAOS contract, Cloud runtime hoặc
  thêm actuator command. Rollback remote vẫn là commit `92d9a98` trên P-162/main.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: audit chênh lệch giữa UI local đang chạy và hai mockup Driver/Engineer
  đã được chủ dự án duyệt; không thay đổi model, rule engine, TTS, AAOS hoặc
  cloud runtime trong lần audit này.
- Phạm vi kiểm tra: source React/CSS, bundle build mới, UI contract tests và
  khả năng capture visual runtime bằng browser/headless browser.
- Không kết luận visual parity nếu chưa có screenshot runtime cùng viewport và
  state với mockup. Nếu browser automation không khả dụng, phải ghi rõ kết quả
  là `blocked` và chỉ báo cáo các chênh lệch đã chứng minh bằng source/build.
- Fallback: giữ nguyên source hiện tại và bản remote backup `92d9a98`; không
  reset hoặc xóa các thay đổi của chủ dự án.

**POST-WORK**

- Đã so sánh source và ảnh render local của Driver/Engineer với hai mockup đã
  duyệt ở cùng viewport 1600x900. Ảnh render được chụp từ bundle `dist-ui-v2`
  bằng Chrome headless và audit fixture; không coi fixture là bằng chứng model
  hoặc backend production.
- Đã xác nhận build frontend mới: `tsc -b` PASS và Vite build vào
  `frontend/dist-ui-audit` PASS.
- Đã phát hiện các khác biệt chính: legacy app header vẫn bọc ngoài màn hình;
  SessionControls đang nằm trước video (Engineer metrics không nằm ngay sau
  title như mockup); Driver vẫn có focus/audio/event panels bên dưới; Engineer
  chưa có trạng thái visual giống bảng mẫu trong cùng viewport; HUD car/road là
  minh họa CSS thay vì asset xe như mockup.
- Đã phát hiện lỗi khôi phục view: khi engineer reload từ localStorage, state
  `view` khởi tạo là `driver`, nên cần bấm lại Engineer Console để vào đúng
  console. Đây là lỗi thực thi có thể sửa bằng React state initialization.
- Đã ghi nhận các phần đã đạt: grid 20/80 ở desktop, responsive fallback,
  video `16:9` dùng `object-fit: contain`, Engineer Event History/Model Health/
  HITL tồn tại, và các marker UI mới có trong bundle.
- Kết quả audit: `blocked` cho visual parity/release; chưa sửa source trong
  lần audit này. Fallback vẫn là source hiện tại và backup remote `92d9a98`.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: triển khai các correction sau audit để đưa Driver HUD và Engineer
  Console sát mockup đã duyệt, không thay đổi perception/risk/TTS/AAOS/cloud.
- Bắt buộc: video vẫn `16:9 + contain`; controls phải giữ chức năng pause,
  seek, upload, start/stop; Engineer Event History, Model Health và HITL không
  được mất; fallback về source/artifact cũ phải còn khả dụng.
- Kiểm tra: TypeScript, Vite build, UI contract và capture hai role cùng
  viewport 1600x900.

**POST-WORK**

- Đã bỏ legacy global header khỏi màn hình vận hành và đưa logo, trạng thái,
  chuyển mode và đăng xuất vào `ScreenIdentity`.
- Driver: video đứng trước controls; thêm disclaimer an toàn và gom Event
  Ribbon vào details để không làm tài xế quá tải.
- Engineer: thứ tự cố định là ScreenIdentity → metrics → video → controls →
  Event History/Model Health/HITL.
- HUD Driver chuyển sang nền sáng gần mockup; HUD Engineer giữ nền tối để
  phân biệt console kỹ sư; vẫn gắn nhãn telemetry mô phỏng.
- Sửa persistence để session engineer reload vào đúng Engineer Console thay vì
  mặc định Driver HUD.
- `start.ps1` ưu tiên `frontend/dist-ui-v2`, sau đó mới dùng `dist` và
  `dist-local`; các bundle `dist-ui-*` được gitignore để tránh push artifact.
- Đã bổ sung UI contract tests cho thứ tự layout, role restore và bundle
  selection. `tsc -b` PASS; Vite build vào `frontend/dist-ui-v2` và
  `frontend/dist-ui-v3` PASS; Chrome headless capture Driver/Engineer PASS.
- Video contract vẫn giữ `aspect-ratio: 16 / 9` và `object-fit: contain`; không
  dùng crop/stretch. `design-qa.md` đã cập nhật `final result: passed`, các
  chênh lệch còn lại là P3/không block.
- Không thay model, risk engine, TTS provider, AAOS contract, cloud runtime
  hoặc actuator. Fallback remote vẫn là commit `92d9a98` trên P-162/main.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: chẩn đoán hiện tượng TTS bị đọc chồng/nhân đôi và kiểm tra nguyên nhân
  hiệu năng Web giảm sau khi bổ sung giao diện Driver/Engineer.
- Phạm vi: audio routing giữa AudioManager và Browser Web Audio, polling trạng
  thái frontend, cấu hình Cloud/Compose/start script và regression/build; không
  thay model weights, risk rules, canonical alert copy hoặc actuator contract.
- Quy tắc audio bắt buộc: một session chỉ có một output owner (`server`,
  `browser` hoặc `none`). Web local/Cloud dùng `browser`; edge/AAOS native có
  thể dùng `server`; `NoAudio` dùng `none`. Giữ Piper/VieNeu fallback nguyên
  vẹn.
- Không tuyên bố cải thiện latency nếu chưa có benchmark; thay đổi UI chỉ được
  giảm overhead polling/render và không được làm chậm pipeline inference.
- Fallback: nếu routing mới hoặc build lỗi, bỏ biến `ROADWATCH_AUDIO_OUTPUT`
  để quay về default server output, hoặc khôi phục artifact/commit UI trước đó;
  không xóa model, media hay dữ liệu người dùng.

**POST-WORK**

- Đã xác định nguyên nhân TTS lặp âm tiết trên Web local: cùng một event được
  `AudioManager` phát qua loa hệ thống và `useBrowserAudio` tải WAV rồi phát lại
  trong browser. Hai nguồn phát gần như đồng thời tạo hiện tượng nghe kiểu
  “Cảnh cảnh báo báo…”, không phải lỗi phát âm của Piper/VieNeu.
- Đã thêm audio ownership contract: `server` cho edge/native output,
  `browser` cho Web/Cloud và `none` cho NoAudio. Khi owner là `browser`, backend
  không khởi động worker/physical playback, chỉ ghi lifecycle
  `delegated_browser`; browser vẫn lấy WAV theo `event_id` và phát beep/TTS một
  lần. Khi owner là `server`, đường phát cũ được giữ nguyên; `none` không phát.
- Local `scripts/start.ps1` mặc định `ROADWATCH_AUDIO_OUTPUT=browser`; tham số
  `-NoAudio` đặt `none`. Docker Web đặt `browser`. Cloud được suy ra là
  `browser` từ `ROADWATCH_CLOUD_MODE` ngay cả khi deploy cũ chỉ có
  `ROADWATCH_DISABLE_AUDIO=1`, nên revision mới không bắt buộc phải sửa secret.
- Đã mở rộng `/api/status` audio telemetry với `output_owner`,
  `server_playback`, `browser_playback`; frontend không còn hiển thị “Tắt” khi
  Cloud đang phát bằng browser.
- Đã giảm overhead UI status polling: idle 1.5 giây, local running 0.5 giây,
  Cloud running 0.75 giây. Đây chỉ là telemetry/render overhead; không giảm
  inference cadence, không đổi model/risk timing. UI bổ sung không phải nguyên
  nhân trực tiếp làm chậm neural inference; các điểm cần benchmark riêng vẫn
  là CPU/DirectML/Cloud CPU, cold start và optional perception heads.
- Đã thêm `tests/test_audio_routing.py` và UI contract assertions cho single
  owner/fallback. Python audio smoke, backend compile, TypeScript và Vite build
  đều PASS; targeted tests PASS (25/25), full pytest PASS (187 tests). Có một
  cảnh báo Starlette/httpx deprecation không liên quan lỗi routing.
- HTTP smoke với Uvicorn thật PASS: `/api/status` trả về
  `output_owner=browser`, `server_playback=false`, `browser_playback=true`.
- Replay benchmark đủ warmup trên AMD Windows với `test_video10.mp4` trong 20
  giây: warmup `7160.11 ms`, Process FPS `5.40`, E2E P95 `191.43 ms`; Object
  P95 `28.99 ms`, Lane P95 `73.69 ms`, Traffic Sign P95 `58.99 ms`. Một lần
  benchmark 5 giây cho `0` frame vì chưa vượt warmup, nên không dùng lần đó để
  kết luận hiệu năng. Số đo này xác nhận inference + optional heads là nút
  thắt chính; UI polling chỉ là overhead phụ.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: đưa HUD Driver/Engineer sát mockup Engineer đã duyệt
  `exec-f9a55855-3229-4431-9c0e-7ea319bca980.png`: dùng ảnh xe thật cho ego,
  hai biên làn nét liền, và icon tác nhân giao thông trực quan có vị trí động.
- Logo RoadWatch chỉ được giữ ở trang đăng nhập; màn hình Driver/Engineer
  không render brand lockup.
- Vehicle sprites phải là image assets thật, không dùng text/CSS box làm giả;
  vị trí phải bắt nguồn từ bbox/risk/proximity của track và có giới hạn vùng
  hiển thị để tránh tràn HUD. Không được làm thay đổi model, risk engine hoặc
  video 16:9 + `object-fit: contain` contract.
- Performance gate: HUD transform chỉ dùng dữ liệu status sẵn có, tối đa 5
  sprite, không thêm request API, model inference hoặc animation liên tục;
  TypeScript/Vite/full pytest phải PASS và bundle phải không tăng đáng kể.
- Visual gate: capture cùng viewport/state với mockup và cập nhật
  `design-qa.md`; không handoff nếu còn P0/P1/P2. Fallback là markup/CSS HUD
  hiện tại và bundle `dist-ui-v2` trước lần build này.
- Product Design user-context preflight script không tồn tại trong package cài
  hiện tại; task vẫn có visual target cụ thể và source code hiện hữu nên tiếp
  tục theo mockup/ảnh user cung cấp, không tuyên bố đã tải saved context.
- Fallback vận hành: Web local dùng `ROADWATCH_AUDIO_OUTPUT=server` để quay về
  backend speaker; `-NoAudio` tắt hoàn toàn; model, TTS provider và alert copy
  không bị thay đổi. Cần restart local process/redeploy Cloud để nạp code mới.

**POST-WORK**

- Ngày hoàn thành: 2026-08-29.
- Đã thay CSS box `EGO VEHICLE` bằng ảnh xe PNG nền trong suốt và tạo bộ asset
  car/truck/motorcycle/person/bicycle tại `frontend/public/hud`. Script
  `prepare_hud_assets.py` giữ quy trình chroma-key/crop/resize có thể lặp lại.
- Driver và Engineer dùng chung dark automotive HUD; bỏ hoàn toàn center dashed
  line, giữ đúng hai biên làn nét liền. Logo RoadWatch không còn render ở hai
  màn hình runtime và vẫn được giữ tại login/startup.
- Track HUD không còn ba text chip cố định: X lấy từ
  `projected_x_norm/origin_x_norm/location`, Y/scale lấy từ `proximity_score`,
  màu viền lấy từ `risk_score`. Có spread chống chồng, tối đa 5 sprite và
  reset sprite/object/lane summary về 0 khi session dừng để không giữ state cũ.
- Performance contract: không thêm API/model/animation loop; `HudPanel` dùng
  `React.memo` + `useMemo`; sáu PNG tổng 388,172 bytes. Bundle mới JS 223.96 kB
  (70.63 kB gzip), CSS 33.83 kB (7.73 kB gzip); JS chỉ tăng khoảng 1.6 kB và
  CSS giảm khoảng 1.4 kB so với bundle trước. Backend/model inference vẫn là
  bottleneck riêng, không được tuyên bố cải thiện chỉ từ thay đổi HUD.
- Đã build lại `frontend/dist-ui-v2`. TypeScript/Vite PASS; UI contract PASS
  8/8; full pytest PASS 190/190. Starlette/httpx deprecation warning tồn tại
  từ trước, không liên quan thay đổi HUD.
- Browser QA bằng FastAPI và production bundle thật tại viewport 1680x928:
  Driver/Engineer đều PASS; DOM có 0 logo runtime, 2 lane line, 0 dashed center,
  video ratio 1.7778. Replay `test_video10.mp4` xác nhận 4 sprite động từ track
  thật. Phiên sandbox dừng khi ghi event vì file `data/roadwatch.db` hiện hữu bị
  ACL read-only đối với sandbox; tạo SQLite mới cùng thư mục PASS và full tests
  storage/API PASS. Đây là giới hạn môi trường QA; cần smoke event persistence
  bằng user Windows bình thường trước demo. Bằng chứng và sai khác có chủ đích
  được ghi tại `design-qa.md`.
- Fallback: source HUD trước thay đổi vẫn nằm trong Git history/worktree backup
  đã tạo ở task trước; model/risk/TTS không bị sửa. Nếu cần rollback chỉ khôi
  phục `main.tsx`, `styles.css`, bundle UI trước và bỏ `public/hud`.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: chẩn đoán và tối ưu hiệu năng phát lại video RoadWatch sau khi hoàn
  thiện HUD Driver/Engineer.
- Mục tiêu đo được: tách riêng `processed_fps` (AI hoàn tất inference) với
  `stream_fps` (khung browser nhận được), giảm encode/stream contention và
  giảm E2E P95 mà không thay đổi model, risk rule, TTS canonical copy hoặc
  actuator contract.
- Phạm vi: pipeline replay, MJPEG frame publication, metrics telemetry,
  optional perception worker và cấu hình runtime cho local/cloud/edge.
- An toàn: critical decision vẫn chạy trên frame inference; frame hiển thị
  lặp hoặc frame annotate bằng state gần nhất không được dùng để phát sinh
  event mới. Giữ `16:9 + contain`, seek/pause/session isolation và audio
  ownership.
- Fallback bắt buộc: có thể tắt các tối ưu bằng biến môi trường/config để
  quay về cadence/stream loop cũ; không xóa model, media, database hoặc
  artifact hiện hành. Không tuyên bố đạt realtime edge nếu chưa benchmark
  trên phần cứng đích.

**POST-WORK**

- Đã tách JPEG annotate/encode khỏi inference thread bằng bounded latest-frame
  display worker (`queue.Queue(maxsize=1)`). Frame cũ bị thay thế thay vì tạo
  backlog; queue drop chỉ là display telemetry, không làm mất frame AI/risk.
- Frame sampling skip được render bằng overlay nhẹ (không blend lane mask),
  còn frame inference vẫn dùng overlay đầy đủ. Các frame display-only không
  đi qua tracker/risk/governor và không thể phát sinh alert mới.
- MJPEG chỉ phát JPEG có sequence mới, giới hạn `app.stream_fps`; stream resize
  tối đa `stream_max_width` nhưng giữ 16:9. Thêm `display_fps`,
  `display_frames`, `display_dropped_frames`; `processed_fps` bắt đầu tính sau
  warmup để không bị cold-start làm sai số.
- Default display profile: `stream_fps=30`, `stream_jpeg_quality=60`,
  `stream_max_width=960`, `publish_skipped_frames=true`. Có env override
  `ROADWATCH_STREAM_*` và cờ tắt `ROADWATCH_PUBLISH_SKIPPED_FRAMES=0`.
- Optional lane/sign async được giữ cho CPU/CUDA; khi phát hiện
  `DmlExecutionProvider`, hệ thống tự chuyển serial fallback. Benchmark đã tái
  hiện `DmlFusedNode` khi ép async trên AMD DirectML, nên không promote async
  DirectML thành mặc định.
- Đã thêm `docs/PERFORMANCE_STREAMING_OPTIMIZATION_2026-08-29.md`, cập nhật
  `docs/INSTALL.md`, telemetry type/UI Engineer và script benchmark chờ qua
  warmup trước khi đo steady-state.
- Benchmark `test_video10.mp4` trên AMD Windows, 10 giây steady-state, audio
  tắt: `Processed FPS=11.28`, `Display FPS=23.07`, E2E P50=`89.96 ms`, P95=
  `149.91 ms`, pipeline error=0; bằng chứng tại
  `reports/benchmark-performance-faststream-20260829.json`. Benchmark 20 giây
  trước đó với 1280/72 đạt `Display FPS=19.40`, E2E P95=`145.01 ms`.
- Verification: full pytest PASS, compileall PASS, TypeScript/Vite production
  build PASS; bundle được build lại vào `frontend/dist-ui-v2` để
  `scripts/start.ps1` dùng đúng UI telemetry mới. Không thay model weights,
  risk rules, alert copy, TTS hoặc actuator.
- Fallback: đặt `ROADWATCH_STREAM_MAX_WIDTH=1280`,
  `ROADWATCH_STREAM_JPEG_QUALITY=80`, `ROADWATCH_PUBLISH_SKIPPED_FRAMES=0`;
  nếu cần rollback code thì khôi phục các file performance về backup Git trước
  task này. Không xóa model/media/database.

**POST-WORK**

- Đã sửa browser TTS activation: `AudioContext.resume()` được `await` và chỉ
  đánh dấu `ready` sau khi context thực sự ở trạng thái `running`. Nút bắt đầu
  và tiếp tục phiên cũng gọi activation trong user gesture, phù hợp với
  autoplay policy của Chrome/AAOS WebView.
- Đã sửa browser audio lifecycle: mỗi session xóa seen/in-flight/retry/beep
  state; chỉ một WAV được fetch/phát tại một thời điểm; event chỉ được đánh dấu
  đã phát sau khi decode và schedule thành công; lỗi tạm thời được retry sau
  1 giây thay vì làm mất vĩnh viễn TTS event. Beep không bị phát lặp khi retry.
- Đã giữ nguyên single-owner contract: Web dùng `output_owner=browser`,
  AAOS/native có thể dùng `server`, còn `none` chỉ dành cho benchmark hoặc
  explicit `-NoAudio`. Không thêm browser Web Speech fallback nên không tái
  diễn lỗi đọc tiếng Việt bằng giọng tiếng Anh.
- `scripts/start.ps1` nay tự reset `ROADWATCH_DISABLE_AUDIO=0` khi chạy bình
  thường và đổi owner `none` còn sót từ benchmark về `browser`; `-NoAudio` vẫn
  đặt `none` một cách rõ ràng. Bundle mới được build ở
  `frontend/dist-ui-v3` và được ưu tiên trước các bundle cũ.
- Verification: audio-routing/TTS/UI tests `21 passed`; full suite `194 passed,
  1 warning`; compileall PASS; TypeScript PASS; Vite build PASS. Piper local
  synthesize smoke test PASS với WAV hợp lệ và provider
  `piper/vi_VN-vais1000-medium`.
- Fallback: VieNeu (nếu được chọn) vẫn fallback Piper; nếu browser TTS endpoint
  lỗi thì event không bị xóa ngay mà retry trong cửa sổ event còn mới. Có thể
  rollback bundle bằng cách chọn lại `frontend/dist-ui-v2` trong
  `ROADWATCH_FRONTEND_DIST`; không xóa model/media/database.

**POST-WORK**

- Bổ sung regression test xác nhận `output_owner=browser` vẫn delegate TTS khi
  backend speaker bị tắt (`enabled=false`), đúng trường hợp Web benchmark/cloud
  dùng browser làm audio owner.
- Verification bổ sung: audio-routing/TTS/UI tests `22 passed, 1 warning`; full
  suite chạy lại `195 passed, 1 warning`. Warning duy nhất là deprecation của
  Starlette/httpx.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: đưa UI mới và toàn bộ E2E pipeline vào entrypoint chạy chính để người
  dùng có thể kiểm thử thực tế bằng một lệnh khởi động nhất quán.
- Mục tiêu: entrypoint phải phục vụ đúng bundle UI mới, FastAPI phải đi qua
  perception → tracking/risk → alert governor → TTS/audio owner → MJPEG/status;
  không được tạo đường chạy demo riêng làm mất model lane/sign/TTS/beep.
- Phạm vi: local start entrypoint, frontend bundle selection, runtime preflight,
  health/status diagnostics và Docker/Cloud static bundle contract nếu cần.
- Guardrail: không thay model production, taxonomy, risk threshold hay actuator
  contract; không dùng `-NoAudio` cho smoke test thực tế; Web giữ
  `output_owner=browser`, AAOS/native giữ `server`.
- Fallback: giữ bundle cũ và runtime profile hiện tại; nếu UI mới hoặc pipeline
  preflight fail, entrypoint phải báo lỗi rõ ràng và có thể chọn bundle cũ qua
  `ROADWATCH_FRONTEND_DIST`, không xóa model/media/database.

**POST-WORK**

- Đã cập nhật entrypoint local: `scripts/start.ps1` luôn ưu tiên
  `frontend/dist-ui-v3`, không dùng lại đường dẫn bundle cũ còn sót trong
  `ROADWATCH_FRONTEND_DIST`; có thể rollback có chủ đích bằng
  `-FrontendDist <path>`.
- Đã cập nhật FastAPI static serving: khi không có env override, API tự chọn
  bundle theo thứ tự `dist-ui-v3 → dist-ui-v2 → dist → dist-local`; Docker/Cloud
  vẫn tương thích vì chỉ cần `frontend/dist`.
- Đã xác minh entrypoint trực tiếp qua FastAPI smoke test: HTTP `200`, HTML
  tham chiếu đúng bundle mới `index-CaCaRKvb`, 663 bytes. Không tạo một pipeline
  demo riêng: session vẫn gọi `RoadWatchService`, giữ perception/tracking/risk/
  governor/audio/MJPEG/status trong cùng runtime.
- Verification: targeted UI/API/audio/TTS tests `25 passed, 1 warning`; full
  suite `195 passed, 1 warning`; compileall PASS; `git diff --check` không có
  lỗi whitespace; bundle `dist-ui-v3` đã build thành công.
- Cách chạy test thật: restart server cũ, chạy `.\scripts\start.ps1 -Port 8013`
  (không dùng `-NoAudio`), đăng nhập `driver`/`driver123`, chọn video và bấm
  `Bắt đầu phân tích`. Web audio owner phải là `browser`; các event vẫn đi qua
  pipeline chính và TTS fetch theo event ID.
- Fallback: `.\scripts\start.ps1 -FrontendDist .\frontend\dist-ui-v2`
  hoặc đặt `ROADWATCH_AUDIO_OUTPUT=server` cho môi trường có loa native; không
  xóa model/media/database.

**PRE-WORK**

- Ngày: 2026-08-29.
- Task: khôi phục và kiểm chứng TTS sau các thay đổi streaming/performance.
- Mục tiêu: giữ nguyên E2E `perception → tracking/risk → alert → audio`;
  TTS phải được định tuyến đúng theo `server|browser|none`, không phát trùng,
  không làm blocking inference và không làm mất critical beep/TTS event.
- Phạm vi: audio ownership, browser AudioContext activation, TTS event WAV
  endpoint, cấu hình `scripts/start.ps1` và regression tests.
- Fallback bắt buộc: Piper/release baseline vẫn là fallback của VieNeu; browser
  audio chỉ là output owner cho Web, server audio dành cho môi trường có loa;
  không được bật đồng thời hai owner. Nếu TTS candidate lỗi, phải trả về
  provider fallback hoặc trạng thái lỗi có thể chẩn đoán, không âm thầm mất event.

**POST-WORK**

- Xác nhận sau khi đưa UI mới vào entrypoint chính: TTS activation, retry,
  single-owner audio và Piper fallback vẫn giữ nguyên trong cùng E2E runtime;
  không có stream nào bị loại khỏi pipeline.
- Final verification: full pytest `195 passed, 1 warning`, compileall PASS,
  TypeScript/Vite build PASS, FastAPI root smoke trả HTML của `dist-ui-v3`, và
  Piper sinh WAV tiếng Việt hợp lệ. Warning duy nhất là deprecation của
  Starlette/httpx.

**PRE-WORK — RoadWatch Alert Context v1**

- Ngày: 2026-08-29.
- Task: thêm Traffic Context Engine deterministic và chính sách Selective Audio
  để giảm cảnh báo quá tải trong giao thông đông, giữ nguyên perception models,
  risk thresholds, TTS provider và actuator guardrails.
- Phạm vi: context state, AlertGovernor routing, context beep, event/storage/API
  schema, Driver HUD/Engineer Console, alert policy documentation và tests.
- Rollout bắt buộc: `off` là fallback mặc định; `shadow` chỉ đo/ghi log;
  `enforce` mới thay đổi audio routing sau human gate. Context engine lỗi phải
  tự chuyển về normal audio policy.
- Không được: chỉnh model weights, train model, phát actuator command, commit
  video/weights/cache/secrets, hoặc làm mất luồng `perception → risk → alert →
  audio`.

**POST-WORK — RoadWatch Alert Context v1**

- Đã thêm `backend/roadwatch/traffic_context.py`: deterministic dense-context
  detection, 3/5 frame entry, 2 giây exit hysteresis, track de-duplication,
  sidewalk exclusion, reset-safe state và fallback normal khi engine lỗi.
- Đã nối context vào `RoadWatchService → AlertGovernor → AudioManager`; thêm
  `context_beep` hai tone mềm, selective audio, event fields
  `display_scope/audio_route/context_mode`, SQLite migration và API status.
- Các biển chỉ hướng/rẽ/quay đầu/giữ làn được đặt `audio_eligible=false` và
  HUD-only; Stop/Red Light và sign safety vẫn có thể audio khi lane-relevant.
- Driver HUD có context card/HUD-only lines; Engineer Console có density score,
  confirmed users, two-wheelers, low-motion ratio và audio policy.
- Rollout: `ROADWATCH_TRAFFIC_CONTEXT_MODE=off|shadow|enforce`, mặc định `off`;
  local entrypoint ưu tiên bundle `frontend/dist-ui-v4`, fallback v3/v2/dist.
- Verification: full Python test suite PASS; targeted context/audio/governor
  tests PASS; Python compileall PASS; Vite build `dist-ui-v4` PASS. Replay
  `traffic_multi`, `night`, `rain+night`, `test_video9` đều pipeline error 0.
  Các cửa sổ replay đã chạy chưa đạt dense-count vì model chỉ xác nhận tối đa
  5 road users; đây là evidence khám phá, không phải safety validation.

## 12.x PRE-WORK — Chốt UI `dist-ui-v4` và Piper Trúc Ly

- Ngày: 2026-08-29.
- Work ID: `RW-TTS-UI-FINAL-20260829`.
- Task liên quan: chốt bundle frontend `dist-ui-v4`, thay runtime TTS về Piper
  `vi_VN-vais1000-medium`, định danh giọng demo là `Trúc Ly`, và kiểm tra lại
  luồng end-to-end `perception → risk → alert → TTS/beep → browser/driver UI`.
- Hiện trạng đã xác minh: `frontend/dist-ui-v4` tồn tại; `scripts/start.ps1`
  đã ưu tiên bundle này; hai file Piper `vi_VN-vais1000-medium.onnx` và
  `.onnx.json` hiện có trong `voices/`; setup script đã tải đúng model nhưng
  chưa khóa provider nếu PowerShell còn biến VieNeu từ phiên trước.
- Phạm vi dự kiến: `scripts/setup.ps1`, `scripts/start.ps1`, cấu hình/audio/TTS
  metadata, test TTS/audio/UI và tài liệu cài đặt. Không thay model perception,
  risk thresholds, alert copy, context policy hoặc actuator contract.
- Kế hoạch: (1) kiểm tra/giữ lệnh download voice trong setup; (2) khóa Piper
  mặc định và reset các biến provider candidate trong start bình thường; (3)
  thêm kiểm tra voice/config, provider label và fallback; (4) build/serve
  `dist-ui-v4`; (5) chạy unit, compile, API smoke và TTS WAV smoke.
- Definition of Done: setup có lệnh tải voice đúng; start bình thường dùng
  `dist-ui-v4` và Piper; `/api/health` báo voice sẵn sàng hoặc degraded rõ ràng;
  TTS sinh WAV hợp lệ; browser audio owner vẫn là `browser`; full test/build
  không làm mất các stream E2E; rollback bằng `-FrontendDist`, biến môi trường
  và provider baseline vẫn hoạt động.
- Guardrail/rollback: không commit voice nặng; không dùng browser Web Speech;
  Piper là release provider, VieNeu chỉ còn đường candidate/fallback nếu được
  bật rõ ràng; nếu voice thiếu, không đọc bằng giọng tiếng Anh im lặng mà báo
  degraded và giữ event có thể chẩn đoán. Chưa publish cloud trong work này.

## 12.x POST-WORK — Chốt UI `dist-ui-v4` và Piper Trúc Ly

- Ngày hoàn thành: 2026-08-29.
- Trạng thái: `PASS` cho local release candidate; chưa promote/redeploy cloud.
- Đã cập nhật `scripts/setup.ps1`: ưu tiên tái sử dụng `.venv` hiện có, chỉ
  cài lại DirectML khi preflight thiếu `DmlExecutionProvider`, bỏ qua npm
  install nếu Vite/TypeScript đã có, build release vào `frontend/dist-ui-v4`,
  chạy lệnh tải `vi_VN-vais1000-medium` và fail-fast nếu thiếu `.onnx` hoặc
  `.onnx.json`. Lần chạy sau đã hoàn tất thành công; warning `~ip` là trạng
  thái package metadata cũ trong venv, không ảnh hưởng import/runtime.
- Đã cập nhật `scripts/start.ps1`: mặc định chọn `dist-ui-v4`, khóa
  `ROADWATCH_TTS_PROVIDER=piper`, `ROADWATCH_TTS_VOICE=voices/vi_VN-vais1000-medium.onnx`,
  `ROADWATCH_TTS_VOICE_NAME=Trúc Ly`, dùng browser làm audio owner và kiểm tra
  đủ voice files trước khi chạy. `-TtsProvider vieneu` chỉ là đường candidate
  có chủ đích; `-FrontendDist` vẫn là rollback UI.
- Đã cập nhật TTS contract: voice name được đưa vào status/API; audio response
  dùng header ASCII `Truc-Ly` để tương thích HTTP, còn UI/status hiển thị đúng
  `Trúc Ly`. Piper không còn rơi im lặng xuống `pyttsx3`, tránh đọc tiếng Việt
  bằng giọng hệ thống không kiểm soát; VieNeu vẫn fallback về Piper khi được
  bật candidate.
- Đã cập nhật `configs/default.json`, `config.py`, `tts.py`, `audio.py`,
  `api.py`, `tts_api.py`, `frontend/src/api.ts`, `frontend/src/main.tsx`,
  `README.md` và `docs/INSTALL.md`. Không thay model perception, risk engine,
  context policy, alert copy hoặc actuator contract.
- Verification: setup PASS; build Vite `dist-ui-v4` PASS; Python compileall
  PASS; full pytest `211 passed, 1 warning`; warning duy nhất là
  `StarletteDeprecationWarning` của test client. Piper real smoke sinh WAV
  hợp lệ `22.050 Hz`, mono, khoảng `778 ms`; TTS API real smoke HTTP `200`,
  WAV header `RIFF/WAVE`, wire voice `Truc-Ly`.
- E2E HTTP smoke trên entrypoint `scripts/start.ps1 -Port 8014`: root `200`
  trả đúng bundle v4; `/api/health` báo startup `ready`, Piper available,
  `voice_name=Trúc Ly`, browser owner; replay `test_video10` đạt 45 frame/3 s,
  `video_test` 120 frame/8 s và `test_video1` 100 frame/8 s, đều `error=null`.
  Các replay ngắn này không phát sinh event TTS đủ điều kiện trong cửa sổ đã
  chọn, nên không dùng chúng để tuyên bố audio event recall; endpoint/Piper
  đã được kiểm tra độc lập bằng audio smoke và unit/API tests.
- Fallback: chạy `.\scripts\start.ps1 -FrontendDist .\frontend\dist-ui-v3`
  để quay UI cũ; chạy `.\scripts\start.ps1 -TtsProvider vieneu` chỉ khi
  benchmark candidate; xóa biến candidate không cần thiết bằng cách khởi động
  lại PowerShell hoặc dùng mặc định `-TtsProvider piper`. Không xóa model,
  media, voice, database hay cache. Cổng `8013` đã bận trong phiên QA nên đã
  dùng `8014`; đây là xung đột cổng môi trường, không phải lỗi ứng dụng.

## 12.x PRE-WORK — Promote UI v4 + Piper thành Demo Primary

- Ngày: 2026-08-29.
- Work ID: `RW-DEMO-PRIMARY-UI-TTS-20260829`.
- Mục tiêu: tích hợp frontend `dist-ui-v4` và Piper `vi_VN-vais1000-medium`
  với tên hiển thị `Trúc Ly` thành đường chạy demo chính; giữ `dist-ui-v3`,
  `dist-ui-v2`, `dist` và `dist-local` làm các đường fallback có thể chọn.
- Baseline đã xác minh: `scripts/start.ps1` đã chọn v4, nhưng danh sách bundle
  mặc định trong `backend/roadwatch/api.py` vẫn đặt v3 trước v4 khi uvicorn
  được khởi chạy trực tiếp. Piper voice gồm đủ `.onnx` và `.onnx.json`.
- Phạm vi: thứ tự static frontend fallback trong `api.py`, release metadata,
  UI contract test và tài liệu nhật ký. Không thay model perception, risk,
  alert policy, audio ownership hoặc actuator contract.
- Kế hoạch: thêm v4 vào vị trí đầu tiên của backend fallback; ghi rõ primary /
  fallback UI và TTS trong release manifest; cập nhật test; chạy targeted/full
  test, compile, build và HTTP smoke.
- Definition of Done: mọi đường chạy mặc định đều chọn v4 khi bundle tồn tại;
  Piper/Trúc Ly là TTS demo mặc định; UI cũ vẫn chạy bằng `-FrontendDist`;
  E2E không mất `perception → risk → alert → audio`; không commit artifact
  nặng hoặc secret.
- Rollback: `.\scripts\start.ps1 -FrontendDist .\frontend\dist-ui-v3`
  hoặc v2; TTS candidate chỉ bật tường minh bằng `-TtsProvider vieneu`.

## 12.x POST-WORK — Promote UI v4 + Piper thành Demo Primary

- Ngày hoàn thành: 2026-08-29.
- Trạng thái: `PASS` cho local demo primary; không deploy cloud và không thay
  đổi model weights.
- Đã sửa `backend/roadwatch/api.py` để bundle mặc định khi chạy uvicorn trực
  tiếp có thứ tự `dist-ui-v4 → dist-ui-v3 → dist-ui-v2 → dist → dist-local`.
  `scripts/start.ps1` tiếp tục đặt v4 làm primary và cho phép chọn fallback
  bằng `-FrontendDist`.
- Đã thêm `demo_runtime` vào `configs/release_manifest.json`, ghi rõ bundle
  primary, bundle fallback, browser audio owner, Piper model và tên hiển thị
  `Trúc Ly`. Không đưa voice binary vào Git.
- Đã cập nhật `tests/test_ui_contract.py` để khóa thứ tự primary/fallback cho
  cả `start.ps1` và backend trực tiếp. Không thay đổi E2E perception → risk →
  alert → audio.
- Verification: targeted UI/TTS `20 passed, 1 warning`; full suite chạy từ
  thư mục `roadwatch` `211 passed, 1 warning`; `compileall` PASS; `setup.ps1
  -SkipVoice` PASS và build Vite tạo `frontend/dist-ui-v4` thành công.
  Direct uvicorn smoke trả root `200`, bundle `index-DGfqjBfB.js`, health báo
  `piper/vi_VN-vais1000-medium`, voice `Trúc Ly`, audio owner `browser`.
  Fallback smoke với `-FrontendDist .\frontend\dist-ui-v3` trả root `200`,
  bundle `index-CaCaRKvb.js`.
- Quyết định release: demo mặc định dùng UI v4 + Piper Trúc Ly; UI v3/v2 và
  dist cũ chỉ là rollback surface. VieNeu không được bật mặc định. Tên
  `Trúc Ly` là display label của release; model file thực tế là Piper
  `vi_VN-vais1000-medium`.
- Limitation: chưa redeploy GCP trong công việc này; GCP phải build/copy đúng
  bundle và voice asset theo allowlist cloud riêng. Warning duy nhất là
  `StarletteDeprecationWarning` từ test client.

## 12.x PRE-WORK — Bật Traffic Context v1 cho Demo Primary

- Ngày: 2026-08-29.
- Work ID: `RW-DEMO-TRAFFIC-CONTEXT-ENFORCE-20260829`.
- Mục tiêu: bản demo chạy bằng `setup.ps1` rồi `start.ps1` phải tự động dùng
  UI v4, Piper Trúc Ly và `Traffic Context Engine` ở chế độ `enforce`, không
  yêu cầu triển chiêu tự đặt biến môi trường.
- Hiện trạng đã xác minh: module context đã nối vào pipeline và Driver HUD /
  Engineer Console đã có trường hiển thị, nhưng `configs/default.json` đặt
  `traffic_context.mode=off`; vì vậy engine trả `normal` và không phát
  selective-audio/context card trong demo. Các bài unit enforce đã tồn tại.
- Phạm vi: default config, `scripts/start.ps1`, setup output, policy/docs và
  contract tests. Không thay model, ngưỡng risk, taxonomy hoặc actuator.
- Kế hoạch: đổi demo default sang `enforce`; start ép mode này để không bị biến
  môi trường cũ ghi đè; giữ `off`/`shadow` trong engine cho rollback và
  benchmark; test reset/session/video switch và smoke health/UI.
- Definition of Done: `/api/health` và `/api/status` báo policy mode `enforce`;
  khi đủ điều kiện 3/5 frame, context chuyển `dense`, Driver HUD hiển thị
  context card, Engineer có telemetry; fallback normal khi engine lỗi; full
  regression không mất perception → risk → alert → audio.
- Rollback: dùng `ROADWATCH_TRAFFIC_CONTEXT_MODE=off` cho benchmark hoặc sửa
  runtime profile; không xóa code/module. TTS/UI fallback vẫn giữ nguyên.

## 12.x POST-WORK — Bật Traffic Context v1 cho Demo Primary

- Ngày hoàn thành: 2026-08-29.
- Trạng thái: `PASS` cho local demo primary.
- Root cause đã xác nhận: `configs/default.json` và snapshot idle của service
  đều khiến UI báo `policy_mode=off`; do đó Traffic Context Engine có code nhưng
  không được dùng trong demo mặc định và Driver HUD chỉ có thể hiện card khi
  đã vào dense mode.
- Đã đổi `configs/default.json` sang `traffic_context.mode=enforce`, thêm
  `-TrafficContextMode` vào `scripts/start.ps1` với default `enforce`, và in
  trạng thái trong `setup.ps1`. `off`/`shadow` vẫn được chọn rõ ràng để
  benchmark/rollback mà không ảnh hưởng đường demo chính.
- Đã sửa `backend/roadwatch/pipeline.py` để snapshot idle/reload/start lấy
  policy từ `TrafficContextEngine`, không còn hiển thị literal `off` trước
  frame đầu tiên. Engineer Console hiển thị rõ `ROADWATCH ALERT CONTEXT V1`.
- Đã cập nhật `README.md` và `docs/TRAFFIC_CONTEXT_ALERT_POLICY.md` để nêu
  `enforce` là demo default, `off` là fallback, và giải thích rằng trạng thái
  `dense` chỉ bật sau ngưỡng 8 track hoặc 6 track có 2 xe hai bánh trong 3/5
  frame; không hạ ngưỡng chỉ để làm UI đổi màu.
- Verification: `setup.ps1 -SkipVoice` PASS và build `dist-ui-v4` PASS; targeted
  context/UI/API `22 passed, 1 warning`; full suite `211 passed, 1 warning`;
  compileall PASS; diff-check PASS. Smoke với `start.ps1 -Port 8017` không
  cần env thủ công: root `200`, bundle v4, `/api/status` báo
  `policy_mode=enforce`, `mode=normal` khi idle, Piper `Trúc Ly`, browser
  audio owner. Mode `normal` lúc idle là đúng, không phải context bị tắt.
- Fallback/release decision: bản demo dùng UI v4 + Piper + Context v1 enforce;
  chạy `.\scripts\start.ps1 -TrafficContextMode off` để quay policy audio
  cũ, hoặc `-TrafficContextMode shadow` để chỉ ghi telemetry. UI cũ vẫn dùng
  `-FrontendDist .\frontend\dist-ui-v3`. Không thay perception model và không
  phát actuator command.
- Limitation: nếu model chỉ tạo ít hơn ngưỡng track xác nhận, hệ thống sẽ vẫn
  hiển thị `NORMAL` và không phát context beep; đây là điều kiện dữ liệu/model,
  không phải lỗi bật policy. Unit tests đã xác nhận dense transition, hysteresis,
  selective audio và fallback khi engine lỗi.

## 12.x PRE-WORK — Sửa TTS lặp, khóa Piper và single-owner playback

- Ngày bắt đầu: 2026-08-29.
- Mục tiêu: loại bỏ hiện tượng một câu bị phát thành dạng lặp từ như
  `Cảnh cảnh báo báo va va chạm chạm`, khóa đúng Piper
  `vi_VN-vais1000-medium`, và ngăn browser/server hoặc hai event trùng nội dung
  phát chồng lên nhau.
- Phạm vi: ưu tiên Web local chạy bằng `scripts/start.ps1`; giữ đường server/native
  cho AAOS và fallback. Không thay model perception, risk threshold, taxonomy,
  Traffic Context v1 hoặc actuator contract.
- Hypothesis đã kiểm tra: Piper trực tiếp sinh WAV tiếng Việt hợp lệ; lỗi nằm ở
  playback ownership, duplicate event/cache hoặc bundle cũ. Bundle release chính
  phải là `frontend/dist-ui-v4`; không dùng browser Web Speech hoặc pyttsx3.
- Kế hoạch: thêm fingerprint model/config vào TTS status và cache namespace; chuẩn
  hóa token lặp; serialize browser audio theo session; ép local Web owner là
  `browser`; cập nhật service-worker cache; bổ sung test event claim, overlap,
  voice metadata và fallback.
- Definition of Done dự kiến: mỗi event chỉ có một lần playback; duplicate speech
  và audio overlap bằng 0; banner/TTS canonical message bằng nhau; health/status
  báo model Piper, hash, sample rate và speaker metadata; UI v4 được build mới.
- Fallback: giữ nguyên Piper làm release baseline, giữ bundle cũ và tùy chọn
  `-FrontendDist`; không xóa model/cache cũ trong bước đầu; nếu TTS lỗi thì báo
  lỗi rõ ràng và không rơi sang voice tiếng Anh không kiểm soát.

## 12.x POST-WORK — Sửa TTS lặp, khóa Piper và single-owner playback

- Ngày hoàn thành: 2026-08-29.
- Đã thêm chuẩn hóa token lặp liền kề trong `backend/roadwatch/tts.py`; ví dụ
  `Cảnh cảnh báo báo va va chạm chạm` được chuẩn hóa thành `Cảnh báo va chạm`.
- Đã đổi cache Piper local sang namespace `piper-v3` với SHA-256 của model và
  config trong cache key; WAV tạo từ artifact/voice cũ không được tái sử dụng.
- Đã thêm Piper fingerprint vào health/status: model, model/config SHA-256,
  language, sample rate, quality, num speakers, speaker map và cache namespace.
  Artifact hiện tại là `vi_VN-vais1000-medium`, `vi_VN`, `22050 Hz`, `medium`,
  một speaker; `Trúc Ly` là display alias của RoadWatch.
- Đã thêm backend event claim/dedupe, canonical audio key, claim id và play
  count; SQLite có migration tương thích cho các trường audit mới.
- Đã thêm frontend speech lock theo session/canonical message, chặn hai WAV
  cùng nội dung phát chồng và cho critical preempt advisory mà không overlap.
  Browser owner và server owner không phát cùng một event.
- `scripts/start.ps1` hiện mặc định và vô điều kiện đặt `AudioOwner=browser`,
  có `-AudioOwner server` cho native/AAOS, đồng thời đặt cache namespace mới.
  `scripts/setup.ps1` fail-fast nếu Piper metadata không đúng.
- Service worker đã bump lên `roadwatch-shell-v4` và gọi `skipWaiting` để tránh
  giữ bundle audio cũ. `dist-ui-v4` đã được build lại.
- Đã tạo `docs/TTS_DUPLICATE_PLAYBACK_FIX.md` với nguyên nhân, cách kiểm tra,
  fingerprint và fallback.
- Verification: Python full suite pass; compileall pass; TypeScript/Vite build
  pass; health smoke `ready`; bundle `dist-ui-v4`; provider
  `piper/vi_VN-vais1000-medium`; audio owner `browser`; server playback `false`;
  `playback_mode=single_owner`; replay `test_video10.mp4` tạo event biển 60 và
  endpoint TTS trả HTTP 200 WAV với đúng model fingerprint.
- Fallback: giữ các bundle UI cũ, `-FrontendDist`, owner `server` cho native và
  Piper release baseline; không xóa cache/model cũ và không bật lại browser
  Web Speech/pyttsx3.

## 12.x PRE-WORK — Port SLM giải thích cảnh báo từ P-162

- Ngày bắt đầu: 2026-08-29.
- Mục tiêu: tích hợp có kiểm soát lớp SLM ONNX Qwen2.5-0.5B từ nhánh
  `feature/slm-integration` của repo P-162 vào `roadwatch` hiện tại.
- Phạm vi: chỉ thêm giải thích kỹ thuật bất đồng bộ cho event đã được
  `RiskEngine` và `AlertGovernor` chấp nhận; không thay đổi model perception,
  Traffic Context v1, risk threshold, canonical alert, Piper/audio owner, UI v4,
  playback control hoặc actuator contract.
- Nguồn tham chiếu: `web_demo/docs/SLM_INTEGRATION.md`,
  `web_demo/backend/roadwatch/slm.py` và `web_demo/tests/test_slm.py` trên
  `p162/feature/slm-integration`.
- Guardrail: SLM không được tạo, sửa, suppress hoặc escalate event; không được
  làm chậm perception/HUD/beep/TTS. Khi thiếu asset, queue đầy, timeout, lỗi
  generation hoặc validator fail, event deterministic vẫn phải hoạt động và lưu
  `slm_status=fallback`.
- Rollout: mặc định tắt hoặc shadow; chỉ hiển thị explanation cho Engineer
  Console sau khi contract/unit/fallback test pass. Không commit model, video,
  `.env`, credential hoặc cache.

## 12.x POST-WORK — Tích hợp SLM giải thích cảnh báo từ P-162

- Ngày hoàn thành: 2026-08-29.
- Đã port worker `SlmExplanationWorker`, ONNX causal decoder, evidence payload,
  prompt contract và validator vào `backend/roadwatch/slm.py`. Worker chỉ chạy
  sau `RiskEngine`/`AlertGovernor`, không có quyền tạo, sửa, suppress hoặc
  escalate event.
- Đã nối SLM vào `RoadWatchService` với queue FIFO giới hạn, lifecycle callback,
  SQLite persistence và reset queue khi start/stop/seek/video loop/session end.
  Event deterministic vẫn được phát qua AudioManager độc lập khi SLM disabled,
  fallback hoặc lỗi model.
- Đã mở rộng config với section `slm`, các biến `ROADWATCH_SLM_*`, inventory
  optional và `tokenizers` dependency. Default vẫn là `enabled=false`; không
  bật SLM vào public/cloud/AAOS critical path khi chưa có asset và benchmark.
- Đã thêm `slm_explanation`, `slm_status`, `slm_latency_ms` và
  `slm_failure_reason` vào schema/migration SQLite. Sửa lỗi tích hợp phát hiện
  trong test: câu INSERT có 31 placeholder cho 30 cột, hiện đã khớp 30/30.
- Engineer Console hiển thị trạng thái SLM, model/provider, queue và explanation
  gần nhất; Event History hiển thị lifecycle `SLM:*`. Driver HUD không hiển thị
  SLM để tránh gây xao nhãng. Traffic Context v1, audio single-owner, Piper,
  UI v4 và playback controls không bị ghi đè.
- Đã thêm `docs/SLM_INTEGRATION.md`, cập nhật `README.md`, `ARCHITECTURE.md` và
  tài liệu GCP về asset/rollout/fallback. Model Qwen vẫn bị `.gitignore`, không
  commit asset lớn hay credential.
- Verification: `python -m compileall -q backend` pass; `pytest -q tests` pass
  toàn bộ; riêng `tests/test_slm.py` pass; TypeScript compiler và Vite build
  `frontend/dist-ui-v4` pass. Do workspace có nhiều thay đổi lịch sử chưa commit,
  không reset/clean hoặc push tự động trong bước này.
- Fallback: SLM giữ trạng thái `disabled` khi chưa có ba asset Qwen; khi bật mà
  thiếu model, queue đầy, generation/validator lỗi hoặc session reset thì event
  được ghi `fallback`, còn cảnh báo deterministic/TTS/HUD vẫn hoạt động bình
  thường. Không dùng SLM để tuyên bố safety validation hoặc chứng nhận xe.

## 12.x PRE-WORK — Sửa discovery path cho SLM Qwen local

- Ngày bắt đầu: 2026-08-29.
- Hiện tượng: asset Qwen có `config.json`, `tokenizer.json` và
  `model_q4f16.onnx`, nhưng ONNX được đặt trực tiếp trong
  `models/qwen2.5-0.5b/` thay vì thư mục con `onnx/`; worker báo fallback.
- Phạm vi: chỉ mở rộng discovery path của SLM loader để hỗ trợ artifact root
  và artifact `onnx/`; không đổi model, prompt, validator, risk engine, Traffic
  Context v1, AudioManager, TTS hoặc UI safety path.
- Guardrail: thiếu metadata/model vẫn fallback rõ ràng; không tự động dùng file
  GGUF 1.5B, không fallback sang browser/Windows voice và không làm SLM nằm trên
  critical path.
- Verification bắt buộc: kiểm tra loader chọn đúng root `model_q4f16.onnx`,
  chạy SLM/storage/full tests, compile Python và xác nhận model GGUF không bị
  chọn nhầm.

## 12.x PRE-WORK — Khóa provider an toàn cho SLM Q4F16

- Ngày bắt đầu: 2026-08-29.
- Phát hiện sau khi sửa path: ORT `DmlExecutionProvider` load được artifact
  nhưng greedy decode sinh token sai/lặp; cùng artifact chạy CPU cho output
  tiếng Việt hợp lý. `device=auto` hiện đang chọn DirectML trên laptop AMD.
- Phạm vi: đổi thứ tự provider của SLM thành CUDA → CPU khi `auto`; DirectML
  chỉ được chọn khi người dùng chỉ định rõ `ROADWATCH_SLM_DEVICE=directml`.
- Guardrail: không đổi weights, prompt, validator, perception, Traffic Context,
  audio/TTS hoặc UI; nếu provider không khởi tạo được vẫn fallback deterministic.
- Verification: smoke load/generation với `auto` phải dùng CPU trên máy AMD,
  không chọn file GGUF, unit/full tests và compile phải pass.

## 12.x PRE-WORK — Tăng budget decode để tránh cắt explanation

- Ngày bắt đầu: 2026-08-29.
- Phát hiện: sau khi chọn CPU an toàn, output FCW tiếng Việt đạt coverage cao
  nhưng `max_new_tokens=96` cắt cuối câu, khiến validator trả fallback vì thiếu
  evidence về số frame.
- Phạm vi: đổi budget mặc định từ 96 lên 128 token, đồng bộ default config và
  tài liệu; không đổi canonical alert, TTS, risk, Traffic Context hoặc critical
  path. Giới hạn runtime vẫn khóa trong `[16, 192]`.
- Guardrail: SLM vẫn là explanation-only; nếu output vẫn fail validator thì event
  deterministic giữ nguyên và tiếp tục fallback.
- Verification: smoke generation 128 token phải kết thúc câu và pass validator
  cho case FCW; full tests, compile và frontend build phải pass.

## 12.x POST-WORK — Sửa SLM asset path, provider và decode budget

- Đã xác định nguyên nhân fallback ban đầu: artifact thật nằm tại
  `models/qwen2.5-0.5b/model_q4f16.onnx`, còn loader cũ chỉ tìm
  `models/qwen2.5-0.5b/onnx/model_q4f16.onnx` hoặc `model.onnx`.
- Loader hiện hỗ trợ cả layout `onnx/model_q4f16.onnx` và layout phẳng
  `model_q4f16.onnx`, chỉ chọn đúng tên Q4F16; file
  `qwen2.5-1.5b-instruct-q4_k_m.gguf` không bao giờ được chọn.
- Đã xác minh SHA-256 thực tế của `config.json`, `tokenizer.json` và
  `model_q4f16.onnx` khớp `SHA256SUMS.txt` và hash benchmark P-162.
- Đã sửa ORT graph optimization mặc định từ `ALL` sang `BASIC`; ORT 1.24
  `ALL` gây lỗi SimplifiedLayerNorm fusion trên artifact này dù graph hợp lệ.
  Có thể override bằng `ROADWATCH_SLM_GRAPH_OPT_LEVEL`, nhưng chỉ dùng `all`
  sau khi runtime cụ thể đã được kiểm chứng.
- Đã sửa provider policy: `device=auto` chọn CUDA nếu có, sau đó CPU; không tự
  chọn DirectML trên AMD Windows vì session DML có thể load nhưng sinh greedy
  output sai/lặp. DirectML chỉ còn là opt-in với `device=directml`.
- Đã tăng default `max_new_tokens` từ 96 lên 128 để không cắt explanation trước
  evidence cuối câu; giới hạn cấu hình vẫn `[16, 192]`.
- Real smoke trên laptop: `OrtCausalLM(auto)` load PASS với
  `CPUExecutionProvider`, load khoảng 1.88 s; worker submit/callback PASS,
  sinh FCW explanation bằng tiếng Việt, validator `valid=true`, quality `100`,
  latency khoảng 11.0 s trong điều kiện local hiện tại. Đây là benchmark SLM
  riêng, không phải E2E perception latency.
- Verification: SLM tests pass, API/traffic-context/audio/playback tests pass,
  full `pytest -q tests` pass, Python compile pass, TypeScript/Vite build
  `dist-ui-v4` pass và `git diff --check` không phát hiện whitespace error.
- Fallback: nếu asset/provider/generation/validator fail, event deterministic
  vẫn giữ nguyên; chỉ `slm_status=fallback`, không thay đổi TTS Piper, beep,
  Traffic Context v1, Driver HUD hoặc AlertGovernor.

## 12.x POST-WORK — Hiển thị SLM runtime và giữ Event History khi seek

- Đã xác định `stale_queue`: SLM có nhận event nhưng event chờ quá lâu trong
  queue; với CPU local khoảng 11 giây/lần sinh, ngưỡng cũ 8 giây khiến nhiều
  event bị fallback. Default `max_queue_age_seconds` tăng lên 30 giây.
- Khi queue đầy, worker giữ event mới hơn và đánh dấu event cũ là
  `queue_replaced`; cảnh báo deterministic vẫn không bị ảnh hưởng.
- SLM status hiện báo thêm queue age, load time, last result status/event,
  failure reason, quality score, output tokens và timestamp. Engineer Console
  hiển thị Provider, Queue, Ready, Fallback, latency/quality và explanation gần
  nhất; Event History hiển thị `SLM:*` để kiểm tra lifecycle.
- Đã sửa seek: reset tracker/risk/active events và hủy SLM jobs pending để tránh
  dữ liệu session cũ chạy sang timestamp mới, nhưng giữ `_recent_events` và
  Event History audit. Bấm event để tua không còn làm bảng lịch sử biến mất.
- Real worker smoke sau sửa: `submit=pending`, callback `ready`, quality `100`,
  provider `CPUExecutionProvider`, model `qwen2.5-0.5b`, latency khoảng 11.6 s;
  `failed=0`, `queue_size=0`. DirectML vẫn chỉ là opt-in.
- Verification: full `pytest -q tests` pass, Python compile pass, TypeScript
  compiler pass, Vite build `dist-ui-v4` pass và `git diff --check` không có
  whitespace error.
- Fallback: `stale_queue`, `queue_replaced`, `playback_seek`, thiếu model hoặc
  validator fail chỉ ảnh hưởng explanation SLM. Audio/TTS, banner, Traffic
  Context v1, risk decision và các event history deterministic vẫn được giữ.

## 12.x PRE-WORK — Tạo báo cáo kỹ thuật tổng thể RoadWatch

- Phạm vi: tổng hợp trạng thái RoadWatch đến ngày 2026-08-29 từ source code,
  tài liệu kiến trúc, model registry, validation reports, user stories, cloud,
  AAOS, Traffic Context v1, TTS và SLM.
- Mục tiêu: tạo một báo cáo kỹ thuật có thể gửi cho Demo Day/doanh nghiệp,
  đồng thời có phần evidence, giới hạn, roadmap và changelog để tiếp tục cập nhật.
- Nguyên tắc: phân biệt rõ `Active`, `Candidate` và `Planned/Blocked`; không
  tuyên bố đã tích hợp VinFast, đã benchmark Jetson thật hoặc đã đạt chứng nhận
  an toàn nếu repo chưa có bằng chứng tương ứng.
- An toàn: chỉ chỉnh sửa tài liệu; không đổi model weights, rule engine,
  runtime, audio owner hoặc deployment path trong công việc này.

## 12.x POST-WORK — Hoàn tất báo cáo kỹ thuật tổng thể RoadWatch

- Đã tạo `docs/ROADWATCH_TECHNICAL_REPORT.md` phiên bản R0.9, snapshot ngày
  2026-08-29, gồm bài toán, người dùng, những gì đã build, nguyên lý end-to-end,
  model/runtime, metrics, evidence, cloud/AAOS/edge, demo runbook, giới hạn,
  roadmap và mẫu changelog cập nhật.
- Báo cáo phân biệt rõ `Active`, `Candidate` và `Planned/Blocked`; ghi rõ
  baseline/candidate model, Traffic Context v1, Piper/Trúc Ly, SLM optional,
  rollback và các giới hạn chưa có camera VinFast/CAN/calibration/Jetson thật.
- Không thay đổi model weights, rule engine, runtime, audio owner hoặc
  deployment path; chỉ thêm tài liệu và work log.
- Verification: `python -m pytest -q tests` trong `roadwatch` exit code 0 với
  một `StarletteDeprecationWarning`; `python -m compileall -q backend` pass;
  TypeScript `tsc -b` pass; `git diff --check` không có whitespace error.
- Bằng chứng chính trong báo cáo được đối chiếu từ `ARCHITECTURE.md`,
  `USER_STORY_REPORT.md`, `VALIDATION.md`, `MODEL_PROMOTION.md`,
  `TRAFFIC_CONTEXT_ALERT_POLICY.md`, `SLM_INTEGRATION.md`,
  `UI_METRICS_AND_CLOUD_FLOW.md` và `UNIFIED_DEPLOYMENT_ARCHITECTURE.md`.
- Fallback: báo cáo không thay đổi đường chạy; các quyết định rollback hiện tại
  vẫn là baseline object, YOLOP, Piper và `Traffic Context mode=off` khi cần.

## 12.x PRE-WORK — Tái thiết kế bộ slide Demo Day RoadWatch

- Phạm vi: đọc deck PDF Demo Day hiện có và tạo một bộ slide mới, có thể chỉnh
  sửa, bám theo trạng thái RoadWatch đã được kiểm chứng đến 2026-08-29.
- Mục tiêu: trình bày rõ bài toán, người dùng, kiến trúc, cảnh báo theo ngữ
  cảnh, bằng chứng định lượng, mô hình triển khai và giới hạn an toàn cho
  giám khảo/doanh nghiệp.
- Nguyên tắc: chỉ sử dụng các metric/evidence có trong repo; loại bỏ các claim
  thị trường hoặc thống kê bên ngoài nếu chưa có nguồn kiểm chứng; phân biệt
  rõ Active, Candidate và Planned/Blocked.
- Fallback: giữ nguyên PDF nguồn và toàn bộ runtime/model của RoadWatch; bộ
  slide mới là artifact trình bày độc lập, không được thay đổi đường chạy demo.

## 12.x POST-WORK — Hoàn tất bộ slide Demo Day RoadWatch

- Đã tạo bộ slide editable 11 trang từ định hướng thị giác của PDF tham chiếu,
  nhưng cập nhật toàn bộ nội dung theo trạng thái RoadWatch thực tế: Driver HUD,
  Engineer Console, Traffic Context v1, evidence metrics, deployment planes,
  model promotion và safety boundary.
- Đã loại bỏ các claim thị trường/thống kê không có evidence trong repo; các
  số liệu trong deck được lấy từ validation/model promotion hiện tại và được
  đặt trong ngữ cảnh prototype, không phải chứng nhận ADAS thương mại.
- Đã tạo các artifact:
  - `output/ROADWATCH_DEMO_DAY_FINAL.pptx` — bản editable để tiếp tục chỉnh sửa.
  - `output/pdf/ROADWATCH_DEMO_DAY_FINAL.pdf` — bản PDF để gửi/chiếu.
  - `artifacts/demo_day_build/build_deck.mjs` — script tái tạo deck.
  - `artifacts/demo_day_build/export_pdf.py` — script đóng gói PDF từ bản render.
- Verification: 11/11 slide render thành công; `slides_test.py` báo
  `Test passed. No overflow detected`; đã visual-review montage và các slide
  có tiêu đề dài; PDF có 11 trang, kích thước 1440×810 pt và đã render lại để
  kiểm tra hình ảnh.
- Fallback: giữ nguyên `c3_162_roadwatch_slide_demo.pdf` và các asset nguồn;
  không thay đổi model, backend, frontend, AAOS, TTS hoặc deployment runtime.
