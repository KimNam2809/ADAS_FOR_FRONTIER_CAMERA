# RoadWatch Copilot — User Story Report

## 1. Tóm tắt dự án

**RoadWatch Copilot** là trợ lý cảnh báo hỗ trợ lái (ADAS) đa phương thức,
chạy offline trên edge device. Hệ thống sử dụng camera trước để nhận diện các
đối tượng giao thông, phân tích làn đường, biển báo và xu hướng nguy hiểm, sau
đó phát cảnh báo bằng HUD và giọng nói tiếng Việt.

RoadWatch không điều khiển phương tiện. Hệ thống không tự phanh, không tự đánh
lái và không tự tăng tốc. Vai trò duy nhất là cung cấp thông tin cảnh báo có
ngữ cảnh để người lái chủ động xử lý.

## 2. Bối cảnh và vấn đề cần giải quyết

Các hệ thống cảnh báo phía trước truyền thống thường phát tiếng beep cứng nhắc,
thiếu ngữ cảnh và dễ gây mệt mỏi khi cảnh báo lặp lại. Điều này đặc biệt đáng
chú ý trong giao thông Việt Nam, nơi có mật độ xe máy, người đi bộ, xe đạp,
người đi xe hai bánh cắt ngang và phương tiện nhập làn cao.

Các vấn đề cốt lõi của đề tài:

- Cảnh báo không chỉ nói “có nguy hiểm” mà cần giải thích đối tượng và vị trí.
- Phải ưu tiên cảnh báo theo mức độ nguy hiểm để tránh alert fatigue.
- Phải hoạt động offline, độ trễ thấp và phù hợp edge device.
- Phải chịu được video có điều kiện ánh sáng, chất lượng camera và giao thông
  khác nhau.
- Phải phân biệt rõ hệ thống hỗ trợ lái với hệ thống tự lái.

## 3. Personas

### 3.1. Tài xế — Driver

Tài xế cần một giao diện đơn giản, ít gây xao nhãng và có thể hiểu ngay:

- Đối tượng nguy hiểm là gì?
- Đang ở bên trái, bên phải hay chính giữa?
- Có đang tiến gần, cắt ngang hoặc nhập làn không?
- Mức độ nguy hiểm hiện tại là advisory, warning hay critical?

Tài xế không cần xem tensor, log kỹ thuật hay chi tiết mô hình trong khi lái.

### 3.2. Kỹ sư ADAS — Engineer

Kỹ sư cần kiểm tra chất lượng và nguyên nhân cảnh báo:

- Model nào đang được sử dụng?
- Provider là CPU, DirectML, CUDA hay TensorRT?
- Độ trễ P50/P95 và FPS là bao nhiêu?
- Cảnh báo dựa trên evidence nào?
- Có frame drop, overload hoặc lane-quality thấp không?
- Có thể điều chỉnh ngưỡng mà không sửa mã nguồn không?

### 3.3. Mentor/Hội đồng — Reviewer

Mentor cần thấy một sản phẩm có thể chạy thật, giải quyết bài toán rõ ràng,
có bằng chứng đo lường và có giới hạn an toàn được xác định minh bạch.

## 4. Product User Stories

### US-01 — Nhận diện đối tượng giao thông

**Là một tài xế**, tôi muốn hệ thống nhận diện ô tô, xe buýt, xe tải, xe máy,
xe đạp, người đi bộ và người đi xe hai bánh phía trước, **để** tôi biết loại
đối tượng đang ảnh hưởng đến hành trình.

**Acceptance criteria:**

- Camera hoặc video được đọc liên tục.
- Mỗi detection có bounding box, class, confidence và frame context.
- Detection được tracking qua nhiều frame thay vì cảnh báo từ một frame đơn lẻ.
- Candidate model RoadWatch sử dụng taxonomy 7 lớp:
  `person, rider, bicycle, motorcycle, car, bus, truck`.
- BARD bị cách ly vì annotation chỉ có phương tiện, có thể biến người đi bộ
  và người đi xe thành background sai.

**Đã hoàn thành:**

- Fine-tune Phase 2 trên Kaggle từ BDD100K + DAWN.
- Model candidate `roadwatch_objects_v1` đã được tải về, kiểm tra checksum và
  export sang ONNX.
- Local smoke inference thành công.

### US-02 — Cảnh báo va chạm phía trước (FCW)

**Là một tài xế**, tôi muốn được cảnh báo khi một đối tượng phía trước có nguy
cơ va chạm, **để** tôi chủ động giảm tốc hoặc phanh.

**Acceptance criteria:**

- Chỉ cảnh báo sau temporal confirmation.
- Tính đến vị trí, độ lớn bounding box, xu hướng mở rộng và vị trí trong ego lane.
- Có các mức `warning` và `critical`.
- Cảnh báo critical có quyền ưu tiên âm thanh.
- Hệ thống không gọi API phanh hoặc đánh lái.

**Nguyên lý đã triển khai:**

1. Detector phát hiện đối tượng.
2. IoU Tracker gán track ID và lưu lịch sử bbox.
3. Risk Engine ước lượng proximity, expansion rate, context và risk score.
4. Alert Governor áp dụng cooldown, hysteresis và severity priority.
5. Audio Manager phát beep/TTS theo quyền ưu tiên.

### US-03 — Cảnh báo người đi bộ và vulnerable road user

**Là một tài xế**, tôi muốn được cảnh báo khi người đi bộ, xe đạp, xe máy hoặc
người đi xe hai bánh tiến vào vùng nguy hiểm, **để** tôi có thêm thời gian phản ứng.

**Acceptance criteria:**

- Hỗ trợ đối tượng đi cùng làn, ở mép trái/phải và có xu hướng đi vào đường xe.
- Vẫn có fallback khi lane mask không đáng tin.
- Class `rider` phải được xử lý như vulnerable road user.
- Không tạo cảnh báo từ một detection đơn lẻ chưa ổn định.

**Đã hoàn thành:**

- Đã bổ sung `rider` vào logic FCW, VRU và cross-traffic.
- Đã thêm automated test xác minh `rider` tạo được FCW và VRU event.

### US-04 — Cảnh báo cut-in và cross-traffic

**Là một tài xế**, tôi muốn biết khi xe máy, người đi bộ hoặc phương tiện từ
bên trái/bên phải cắt ngang hay có xu hướng nhập làn, **để** tôi chủ động nhường
đường hoặc giảm tốc.

**Acceptance criteria:**

- Phân tích lateral velocity và hướng di chuyển về trung tâm.
- Phân biệt đối tượng đang ở ngoài ego lane nhưng tiến vào vùng xe.
- Bao phủ các nhóm người đi bộ, xe đạp, xe máy, ô tô, xe buýt và xe tải.
- Message phải chứa loại đối tượng và vị trí tương đối.

### US-05 — Cảnh báo lệch làn

**Là một tài xế**, tôi muốn nhận cảnh báo khi xe có xu hướng lệch khỏi làn,
**để** tôi kịp điều chỉnh hướng đi.

**Acceptance criteria:**

- Lane mask được phân tích thành biên trái/phải và lane center.
- Có lane-quality gate để không cảnh báo khi hình ảnh không đủ tin cậy.
- Cảnh báo lệch làn phải qua số frame xác nhận tối thiểu.
- Hệ thống hiển thị bên lệch làn và phát cùng nội dung tương ứng bằng TTS.

**Giới hạn đã xác định:**

YOLOP hiện phù hợp cho lane/drivable mask và ego-lane quality, nhưng chưa phải
giải pháp đếm chính xác nhiều làn đường. Video chất lượng thấp có thể làm nhiều
làn bị gộp thành một mask. UFLDv2 là hướng nâng cấp tiếp theo.

### US-06 — Nhận diện biển báo tốc độ

**Là một tài xế**, tôi muốn hệ thống xác nhận biển giới hạn tốc độ bằng cả hình
ảnh và thời gian xuất hiện, **để** giảm việc đọc nhầm biển hoặc watermark.

**Acceptance criteria:**

- Traffic-sign detector nhận diện biển báo Việt Nam.
- Speed sign phải ổn định qua nhiều frame.
- Bounding box phải có hình học hợp lý.
- Có visual red-ring validation và screen-motion validation.
- Giá trị tốc độ trên HUD và TTS lấy từ cùng một event payload.

**Vấn đề còn tồn tại:**

Các A/B object-detector test không cải thiện speed-sign recall vì speed sign là
một model độc lập. `test_video10` và `test_video11` vẫn cần cải tiến riêng ở
traffic-sign detector, threshold và temporal confirmation.

### US-07 — Lead braking

**Là một tài xế**, tôi muốn được cảnh báo khi xe phía trước giảm tốc nhanh,
**để** tôi không chỉ phát hiện nguy hiểm khi khoảng cách đã quá gần.

**Acceptance criteria:**

- Theo dõi sự thay đổi kích thước bbox theo thời gian.
- Ước lượng expansion/approach trend.
- Có thể sử dụng brake-light heuristic như tín hiệu bổ trợ.
- Không khẳng định vận tốc mét/giây nếu chưa có calibration camera.

**Đánh giá kỹ thuật:**

Sử dụng YOLOP để suy ra vận tốc tuyệt đối chỉ từ mask là chưa đủ chắc chắn.
Giải pháp hiện tại dùng image-space evidence, phù hợp MVP và minh bạch hơn.
Muốn có TTC theo mét cần camera calibration, ground-plane assumption hoặc
monocular depth được kiểm chứng.

### US-08 — Cảnh báo bằng tiếng Việt và HUD đồng nhất

**Là một tài xế**, tôi muốn nghe một câu cảnh báo tiếng Việt tự nhiên và thấy
đúng câu đó trên HUD, **để** không bị nhầm giữa âm thanh và hình ảnh.

**Acceptance criteria:**

- HUD và TTS dùng cùng event UUID và cùng payload.
- Không cắt mất từ đầu câu khi phát TTS.
- Beep critical có quyền ưu tiên hơn TTS advisory.
- Audio stale event bị loại bỏ.
- Event có lifecycle và TTL rõ ràng.

**Bằng chứng:**

Trong A/B evaluation, HUD/TTS payload consistency đạt `1.0` cho cả baseline và
candidate trên toàn bộ 8 scenario có annotation.

### US-09 — Chạy offline trên edge

**Là một kỹ sư ADAS**, tôi muốn pipeline chạy offline trên laptop AMD, NVIDIA
hoặc Jetson, **để** không phụ thuộc cloud và có thể chuyển sang màn hình xe.

**Acceptance criteria:**

- Backend FastAPI chạy local.
- React UI chạy local.
- ONNX Runtime hỗ trợ DirectML/CUDA/CPU fallback.
- Model, SQLite, media và TTS được lưu local.
- Không có dependency bắt buộc vào cloud trong luồng inference.
- Docker CPU baseline có thể build và chạy.

### US-10 — Engineer dashboard và audit

**Là một kỹ sư ADAS**, tôi muốn xem metrics, model status, evidence và thay đổi
ngưỡng có audit, **để** tôi có thể debug và cải tiến hệ thống có kiểm soát.

**Acceptance criteria:**

- Có tài khoản `engineer` và `driver` với quyền khác nhau.
- Engineer xem được model/provider/latency/event metrics.
- Thay đổi cấu hình được ghi audit log.
- Runtime config không ghi đè bất hợp lệ lên đường dẫn model/media.

## 5. Kiến trúc sản phẩm đã hoàn thành

```text
Camera / Video
      |
      v
Perception Engine
  ├─ Object Detector: YOLO11n / RoadWatch Objects v1
  ├─ Traffic Sign Detector: Vietnam Traffic Sign model
  └─ Lane + Drivable Mask: YOLOP
      |
      v
IoU Tracker + temporal evidence
      |
      v
Risk Engine
  ├─ FCW
  ├─ VRU / cross-traffic
  ├─ cut-in
  ├─ lead braking
  └─ LDW
      |
      v
Alert Governor
  ├─ severity priority
  ├─ cooldown
  ├─ hysteresis
  ├─ temporal confirmation
  └─ stale-event guard
      |
      +--> React Driver HUD
      +--> Engineer Dashboard
      +--> Piper Vietnamese TTS / beep
      +--> SQLite evidence and metrics
```

## 6. Những gì đã build được

### Backend

- FastAPI local backend.
- Video replay và camera source abstraction.
- Object detection, traffic-sign detection và YOLOP lane processing.
- IoU tracking theo thời gian.
- Risk Engine có FCW, VRU, cut-in, cross-traffic, LDW và lead braking.
- Alert Governor điều phối severity, cooldown và audio budget.
- SQLite lưu event, evidence, audio status và audit log.
- Health/status API và WebSocket realtime.

### Frontend

- Driver HUD tập trung vào cảnh báo trực quan, màu sắc và trạng thái nguy hiểm.
- Engineer Dashboard hiển thị model status, metrics, events và cấu hình.
- Giao diện ưu tiên tiếng Việt, giữ thuật ngữ kỹ thuật tiếng Anh khi cần.

### MLOps và dataset

- Kaggle Quality Gate đã loại duplicate và kiểm tra split leakage.
- Kết quả Quality Gate:
  - 209.385 input records.
  - 108.332 unique images.
  - 101.053 duplicate records loại bỏ.
  - Split leakage bằng 0.
  - BDD100K: 99.996 ảnh.
  - BARD: 7.331 ảnh, bị quarantine.
  - DAWN: 1.005 ảnh.
- Phase 2 đã huấn luyện detector 7 lớp trên BDD100K + DAWN.
- Phase 2.1 đã được đóng gói để cân bằng class VRU và đang chạy trên Kaggle.

## 7. Bằng chứng kiểm thử và đánh giá

### Automated tests

Kết quả mới nhất:

```text
26 passed, 1 warning
```

Các nhóm test bao gồm:

- Risk Engine và FCW.
- Single-frame suppression.
- Near-field fallback khi lane mask kém.
- FCW re-arm/hysteresis.
- Alert Governor.
- Event lifecycle.
- Tracking.
- Authentication/API.
- Vehicle adapter.
- Model profile và taxonomy `rider`.

### A/B object detector

So sánh baseline YOLO11n COCO với candidate RoadWatch Objects v1 trên cùng
runtime ONNX/DirectML:

| Metric | Baseline | Candidate |
|---|---:|---:|
| Mean scenario presence recall | 0,8125 | 0,8125 |
| Alerts/phút trên 8 scenario | 19,4101 | 20,9032 |
| Median first warning | 2,667 s | 0,833 s |
| Object P95 | 26,37 ms | 23,67 ms |
| HUD/TTS consistency | 1,0 | 1,0 |

Stability sweep trên video chưa có annotation:

| Metric | Baseline | Candidate |
|---|---:|---:|
| Video hoàn tất | 6/6 | 6/6 sau retry |
| Tổng event | 256 | 293 |
| Alerts/phút | 15,9402 | 18,2440 |
| Mean object P95 | 26,04 ms | 23,66 ms |

### Ý nghĩa kết quả

Candidate có latency tốt hơn và cảnh báo sớm hơn, nhưng chưa chứng minh được
recall tăng ở mức scenario. Đồng thời event density cao hơn khoảng 14,5% trên
stability sweep. Vì chưa có ground truth timestamp đầy đủ, không được gọi toàn
bộ event tăng thêm là false positive. Tuy nhiên, đây là đủ lý do để chưa thay
candidate thành model mặc định.

## 8. Definition of Done hiện tại

### Đã đạt

- [x] Có app local gồm backend và React UI.
- [x] Có Driver HUD và Engineer Dashboard.
- [x] Có login hai vai trò demo.
- [x] Có object detection, sign detection và lane/drivable perception.
- [x] Có tracking và temporal confirmation.
- [x] Có FCW, VRU, cut-in, cross-traffic, LDW và lead braking logic.
- [x] Có cảnh báo tiếng Việt và HUD event lifecycle.
- [x] Có offline-first runtime.
- [x] Có Docker CPU baseline.
- [x] Có benchmark và evaluation scripts.
- [x] Có dataset audit, Kaggle training pipeline và model versioning.
- [x] Có safety guardrail không điều khiển xe.
- [x] Có automated tests và A/B evidence.

### Chưa đạt hoàn toàn

- [x] Phase 2.1 đã hoàn tất, checkpoint đã xác minh và export ONNX.
- [x] Promotion gate đã chạy; chủ động giữ `baseline_coco` vì v1.1 tăng alert density quá 10%.
- [ ] Chưa có event-level ground truth đầy đủ cho mọi video.
- [ ] Chưa đo false alerts/minute thật theo timestamp annotation.
- [ ] Lane detection chưa đếm nhiều lane ổn định trong video chất lượng thấp.
- [x] Hazard/TTS biển báo đã được nối lại, có trace và audio retry trên `test_video11`.
- [ ] Speed-sign model còn nhầm biển 60 thành 40 trên `test_video10`; cần fine-tune/OCR head.
- [ ] TTC tuyệt đối theo mét chưa được chứng minh nếu camera chưa calibration.
- [ ] Chưa tích hợp CAN bus; vehicle adapter hiện chỉ là read-only/disabled guardrail.

## 9. Kế hoạch tiếp theo

### Giai đoạn 1 — Hoàn tất Phase 2.1

Trạng thái: hoàn tất. Xem `PHASE2_1_RESULTS.md`.

### Giai đoạn 2 — Regression và promotion

Trạng thái: hoàn tất automated gate; kết luận giữ baseline. Candidate v1.1 vẫn có
thể bật bằng profile để tiếp tục hiệu chỉnh class-aware threshold.

### Giai đoạn 3 — Cải tiến biển báo

- Đã triển khai policy cho taxonomy biển, temporal confirmation, sign trace, canonical
  HUD/TTS và audio retry. Xem `TRAFFIC_SIGN_ALERTING.md`.
- Fine-tune traffic-sign detector và OCR số vẫn chờ dataset version/annotation quality gate.
- Bổ sung hard-negative frames không có biển tốc độ trước khi promote model mới.

### Giai đoạn 4 — Lane detection nâng cao

- Bổ sung UFLDv2 ResNet-18 hoặc lane model phù hợp edge.
- Phân biệt lane count, lane boundary và ego lane.
- Đánh giá riêng clean/day/night/rain/low-quality video.

### Giai đoạn 5 — Edge deployment

- Benchmark Jetson Orin với TensorRT FP16/INT8.
- Đo end-to-end latency, power, thermal và memory.
- Tạo profile cấu hình cho VF5, VF6, VF7, VF8 và VF9.
- Chỉ kết nối vehicle interface theo read-only nếu chưa có safety certification.

## 10. Thông điệp dành cho mentor

RoadWatch không chỉ là một demo object detection. Sản phẩm đã được phát triển
thành một pipeline cảnh báo có ngữ cảnh:

```text
Nhìn thấy đối tượng
→ theo dõi qua thời gian
→ đánh giá xu hướng nguy hiểm
→ ưu tiên cảnh báo
→ phát cùng một message trên HUD/TTS
→ lưu evidence để kỹ sư kiểm tra
```

Điểm khác biệt của đề tài là kết hợp nhận thức thị giác, phân tích temporal,
logic an toàn deterministic, cảnh báo tiếng Việt và edge-first deployment cho
giao thông hỗn hợp Việt Nam. Hệ thống cũng minh bạch về giới hạn: những gì đã
đo được được báo cáo bằng số liệu; những gì chưa có ground truth không được
khẳng định quá mức.

## 11. Tài liệu liên quan

- `README.md` — cài đặt và chạy nhanh.
- `docs/ARCHITECTURE.md` — kiến trúc hệ thống.
- `docs/VALIDATION.md` — validation và metrics.
- `docs/MODEL_PROMOTION.md` — quy trình A/B và promotion model.
- `docs/OBJECT_MODEL_AB_2026-08-19.md` — kết quả A/B cụ thể.
- `configs/model_registry.json` — checksum và trạng thái model.
- `scripts/compare_object_models.py` — công cụ A/B.
- `kaggle/train_phase2_1/` — pipeline fine-tune VRU Phase 2.1.
