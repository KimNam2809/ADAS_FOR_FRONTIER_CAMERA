# RoadWatch Copilot — Hồ sơ sản phẩm gửi VinFast

> **Trạng thái sản phẩm:** Technical PoC / Demo-ready. RoadWatch chưa phải là
> hệ thống ADAS được chứng nhận để điều khiển xe và chưa được kiểm thử trên một
> xe VinFast thật. Các số liệu trong tài liệu này là bằng chứng của prototype,
> không phải cam kết an toàn vận hành.

## 1. Tên dự án

**RoadWatch Copilot**

## 2. Mô tả ngắn

RoadWatch Copilot là trợ lý cảnh báo hỗ trợ lái đa phương thức, chạy theo hướng
edge-first, phân tích camera trước để nhận diện người đi bộ, xe máy, ô tô, làn
đường, biển báo và nguy cơ va chạm trong giao thông hỗn hợp Việt Nam. Hệ thống
hợp nhất rủi ro thành hazard trực quan, beep và cảnh báo giọng nói tiếng Việt có
ngữ cảnh, nhưng **chỉ hỗ trợ người lái và không tự lái, phanh hoặc đánh lái**.

## 3. Mô tả chi tiết

### 3.1. Vấn đề triển khai cần nói rõ ngay

Trong lần triển khai public Web ban đầu, RoadWatch từng có **E2E P50/P95 đều
`31.027,96 ms`** và khi chọn video mẫu, màn hình có thể chờ hơn **5 phút** mà
chưa trả kết quả. Đây là một vấn đề kiến trúc và tài nguyên của public cloud
demo, không phải bằng chứng rằng pipeline edge mục tiêu cũng có độ trễ như vậy.

Nguyên nhân chính đã được xác định:

- Các nhánh traffic-sign/lane chạy đồng bộ trong đường xử lý replay, tranh chấp
  CPU với object detection và request stream.
- Một số model ONNX có input shape cố định nhưng adapter chưa xử lý đúng biến thể
  input; asset runtime chưa được bootstrap theo allowlist/checksum đầy đủ.
- Cloud Run có cold start, giới hạn concurrency và session/video-state chưa tách
  đủ rõ; stream dài giữ slot khiến request mới có thể nhận `429`.
- Đường replay public chưa có progressive/latest-frame processing và cơ chế
  worker bất đồng bộ cho các nhánh không cần chạy ở mọi frame.

Các biện pháp đã triển khai:

- Dùng ONNX runtime với bounded threads và adapter cho fixed-shape model.
- Tách sign/lane thành latest-frame worker, có `session generation` và
  `staleness cap` để kết quả cũ không rò sang video mới hoặc sau thao tác seek.
- Dùng Cloud Storage allowlist + checksum để đưa model, media và voice vào GCP
  dù các file nặng vẫn được `.gitignore` khỏi GitHub.
- Tách Piper TTS thành Cloud Run service riêng; warm graph, pre-cache 149 câu
  cảnh báo chuẩn và giữ beep critical path ở browser.
- Tăng web concurrency từ 8 lên 80 vì MJPEG stream chiếm request slot; giữ TTS
  concurrency ở mức 4 và giới hạn một synthesizer lock.
- Dùng warm instance và session affinity cho public replay; audio được phát ở
  trình duyệt thay vì chờ server speaker.

Kết quả sau khắc phục cho thấy trải nghiệm public đã cải thiện đáng kể: revision
cuối của Web là `roadwatch-web-00019-x8h`, TTS là
`roadwatch-tts-00003-rt7`; burst health đạt **12/12 HTTP 200, 0 HTTP 429**.
Một FCW acceptance run có E2E **P50 63,89 ms, P95 94,02 ms**, public Piper
round-trip **308,16 ms**, `tts_failed=0`; browser QA ghi nhận UI P95 **84,3 ms**
và không có warning/error trong console.

Tuy nhiên, public GCP vẫn là **evaluation/replay plane**, không phải đường chạy
critical của xe. Throughput cloud CPU được ghi nhận khoảng **4,39–5,16 FPS** ở
các phiên acceptance; con số này không được diễn giải thành realtime 30 FPS trên
xe. Kiến trúc triển khai thực tế vẫn phải đưa perception, risk và audio cốt lõi
về edge/AAOS, còn GCP dùng cho demo, HITL, telemetry được cho phép và quản trị
model.

### 3.2. Bài toán kinh doanh và kỹ thuật

#### Bối cảnh giao thông Việt Nam

Các tình huống tại Việt Nam có mật độ xe máy và người đi bộ cao, hành vi cắt
ngang hoặc nhập làn không luôn tuân theo làn chuẩn, biển báo có thể bị che khuất,
ngược sáng, mưa hoặc xuất hiện đồng thời nhiều loại. Một cảnh báo cứng kiểu
“beep” không trả lời được ba câu hỏi mà tài xế cần biết:

1. Đối tượng nào đang tạo nguy cơ?
2. Đối tượng ở hướng nào so với xe của mình?
3. Tôi cần chú ý hoặc giảm tốc trong tình huống nào?

Với VinFast, đây là hướng R&D có giá trị vì nó kết nối Computer Vision, HMI trên
xe, tiếng Việt, edge computing và quy trình kiểm thử theo dữ liệu địa phương.
RoadWatch không tuyên bố thay thế hệ thống ADAS hiện hữu của VinFast; nó là một
prototype cho lớp **local-context warning copilot** có thể được đánh giá, đo
lường và tích hợp theo contract rõ ràng.

#### Định vị sản phẩm

RoadWatch được thiết kế như một lớp trợ lý cảnh báo:

- **Edge-first:** mô hình và quyết định cảnh báo cốt lõi có thể chạy offline,
  không phụ thuộc Internet để phản hồi nguy hiểm.
- **Vietnamese-context:** cảnh báo bằng tiếng Việt, nêu đối tượng và hướng,
  ví dụ “Xe máy phía trước bên phải, hãy chú ý”.
- **Explainable:** hazard banner, canonical event, risk state và metric có thể
  được kỹ sư truy vết; TTS và banner lấy từ cùng một payload.
- **Safety-bounded:** chỉ cảnh báo/hỗ trợ; không có actuator để phanh, đánh lái,
  tăng ga hoặc tự điều khiển xe.
- **Human-in-the-loop:** kỹ sư có thể xem replay, kiểm tra frame, ghi nhận false
  positive/false negative và dùng evidence đó cho model promotion.

### 3.3. Kiến trúc kỹ thuật thống nhất

```text
Video library / upload / camera contract
                |
                v
      Perception Engine (ONNX/ORT; edge có thể dùng TensorRT)
       | object | traffic sign + speed | lane + drivable area
                |
                v
      Tracking + image-space kinematics + temporal evidence
                |
                v
      Deterministic Risk Engine
      FCW / VRU / cut-in / cross-traffic / LDW / sign relevance
                |
                v
      Alert Governor: severity, debounce, cooldown, deduplication, preemption
                |
                v
      Canonical Alert Event (event_id, object, direction, risk, message)
          |                         |                         |
          v                         v                         v
       HUD/banner              Browser beep              Piper Vietnamese TTS
```

Ba mặt phẳng triển khai được tách riêng:

| Mặt phẳng | Vai trò | Trạng thái hiện tại |
|---|---|---|
| **Edge / AAOS** | Chạy perception, risk và audio cục bộ; hướng tới camera thật và offline | AAOS hiện đã mô phỏng import/replay video và HMI nền; Camera HAL, CAN và vehicle API thật còn chờ phần cứng |
| **Public Web / GCP** | Demo cho ban tổ chức, upload/replay video, HUD, Engineer Dashboard và đo metric | Đã deploy Cloud Run/GCS; URL hiện tại: <https://roadwatch-web-bx6lfekcba-as.a.run.app> |
| **Engineer / HITL** | Xem timeline, hazard, model health, review frame và evidence | Đã có React Engineer Dashboard; workflow HITL và closed-course validation tiếp tục mở rộng |

### 3.4. Model đã dùng và quyết định promotion

| Bài toán | Runtime artifact/kiến trúc | Quyết định hiện tại | Ý nghĩa |
|---|---|---|---|
| Road-user detection | `yolo11n_320.onnx` | **Promoted baseline** | Nhận diện `person`, `bicycle`, `motorcycle`, `car`, `bus`, `truck` với chi phí tính toán phù hợp edge |
| Traffic-sign detection | `roadwatch_detector_v2_416.onnx` | **Promoted Traffic Sign Phase 2 runtime export** | Phát hiện biển báo Việt Nam; resolution 416 dành cho cloud CPU replay, không phải một model train mới độc lập |
| Speed value recognition | `roadwatch_speed_digits_v2.onnx` | **Promoted** | Xác nhận giá trị biển giới hạn tốc độ thay vì chỉ đọc class detector |
| Lane/drivable area | `yolop_lane_detection_640.onnx` | **Release lane hiện hành** | Sinh lane mask và drivable-area mask; LDW bị khóa khi lane quality thấp |
| UFLDv2 candidate | UFLDv2 ResNet-18 | **Chưa promote** | Chưa vượt edge FPS gate và chưa đủ bằng chứng multi-lane ổn định |
| Fallen rider | Taxonomy + research plan | **Chưa có model production** | Cần dataset có license, nhãn chuẩn và hard-negative/temporal evaluation trước khi đưa vào alert path |

Việc không promote Object V2 hoặc UFLDv2 chỉ vì model mới “có vẻ chính xác hơn”
là một quyết định có chủ đích. RoadWatch dùng event-level regression, false-alert
budget, latency và điều kiện đêm/mưa để tránh làm giảm chất lượng cảnh báo quan
trọng. Fine-tuning nặng được đóng gói và chạy trên Kaggle GPU; laptop AMD chỉ
dùng development/test, không bị ép chạy full training.

### 3.5. Những user story đã giải quyết

| User story | Cách giải quyết | Bằng chứng |
|---|---|---|
| Là tài xế, tôi muốn biết nguy cơ phía trước là gì | Object detection + tracking + risk engine sinh đối tượng, hướng và mức nguy hiểm | FCW canonical message: “Cảnh báo va chạm phía trước!”; VRU/cut-in/cross-traffic có schema cảnh báo riêng |
| Là tài xế, tôi muốn nhận cảnh báo tiếng Việt tự nhiên | Một `canonical alert event` dùng chung cho banner và TTS; Piper `vi_VN-vais1000-medium` phát WAV xác định | HUD báo `piper/vi_VN-vais1000-medium`; không còn `speechSynthesis`; `tts_failed=0` |
| Tôi không muốn bị làm phiền bởi cảnh báo lặp | Alert Governor dùng severity, debounce, cooldown, deduplicate, hysteresis và audio preemption | Critical beep được ưu tiên; TTS không tự ghi đè nội dung banner; các câu cảnh báo chuẩn được pre-cache |
| Tôi muốn biết biển báo tốc độ có thực sự được xác nhận | Detector + speed classifier + temporal confirmation + sign arbitration | `test_video10`: tốc độ 60, detector confidence `0,9136`, classifier confidence `0,9806`, `hits=3`, `audio_action=tts` |
| Tôi muốn theo dõi làn và được cảnh báo lệch làn khi đủ tin cậy | YOLOP lane/drivable mask, lane quality gate và LDW logic | Lane acceptance: final quality `0,9688`, max `1,00`, coverage `0,60`; frame chất lượng thấp không cố vẽ/cảnh báo bằng mọi giá |
| Kỹ sư muốn tái lập lỗi và review mô hình | React Engineer Dashboard, video timeline, frame evidence, review queue và regression harness | Python regression `156/156`; queue RW-10 được review theo schema `verified` và có audit trail |
| Ban tổ chức muốn mở sản phẩm từ một URL | Cloud Run + GCS asset bootstrap + Video Library/custom upload + browser HUD | Public URL hoạt động; 12/12 health requests trả 200 sau khi sửa concurrency |
| Tôi muốn chuyển sang xe thật sau prototype | Tách interface video/camera, perception, risk và HMI; AAOS giữ contract replay để thay input adapter | AAOS replay đã có; Camera HAL/CAN/vehicle integration được xác định là hardware gate, chưa tuyên bố đã tích hợp |

### 3.6. Bằng chứng kỹ thuật tiêu biểu

Các số liệu dưới đây là các acceptance run khác nhau và phải đọc cùng revision,
video window, hardware và backend; chúng không phải một tuyên bố chung rằng mọi
video đều đạt cùng throughput.

| Hạng mục | Kết quả đã ghi nhận |
|---|---|
| Local regression | `156/156` Python tests pass; compile, TypeScript, Vite production build và diff-check pass |
| Final public Web | `roadwatch-web-00019-x8h`, URL Cloud Run hoạt động |
| Final public Piper | `roadwatch-tts-00003-rt7`, private IAM-only service |
| FCW public acceptance | E2E P50/P95 `63,89/94,02 ms`; processed FPS `4,39`; Piper round-trip `308,16 ms`; `tts_failed=0` |
| Browser QA | UI P95 `84,3 ms`; FPS `5,16`; console không có warning/error |
| Full-perception sign run | `test_video10`: event speed 60, message banner/TTS giống nhau, E2E P95 `83,42 ms` |
| Full-perception lane run | `test_video10`: E2E P95 `84,18 ms`; object/sign/speed/lane providers loaded, error `null` |
| Availability correction | Health burst `12/12 HTTP 200`, `0 HTTP 429` |

Các bằng chứng chi tiết hơn nằm trong:

- [`CLOUD_FULL_PERCEPTION_DEPLOYMENT.md`](./CLOUD_FULL_PERCEPTION_DEPLOYMENT.md)
- [`PIPER_VI_WEB_DEPLOYMENT.md`](./PIPER_VI_WEB_DEPLOYMENT.md)
- [`MASTER_ACTION_PLAN.md`](./MASTER_ACTION_PLAN.md)
- [`AGENTS.md`](../AGENTS.md), mục Work Execution Ledger

### 3.7. Tính khả thi khi đưa lên xe thật

#### Có thể thực hiện bằng phần mềm ngay

- Đóng gói object/sign/lane ONNX cho ONNX Runtime; trên NVIDIA/Jetson có thể
  benchmark TensorRT FP16/INT8 sau khi xác minh độ chính xác.
- Chuyển `VideoSource` hiện tại sang `CameraSource` mà không thay risk/alert
  contract; frame cần timestamp, sequence number và session identity.
- Chạy Piper offline hoặc audio artifact pre-generated trên edge để không phụ
  thuộc Internet.
- Dùng AAOS app làm HMI: nhận state/event, hiển thị HUD tối giản và chạy audio
  ở foreground/background theo chính sách Android Automotive.
- Dùng GCP làm control/evaluation plane: lưu evidence, dashboard kỹ sư, model
  registry, OTA candidate và fleet telemetry đã được cho phép.

#### Cần human hoặc hardware gate

| Hạng mục chưa có | Phương án tạm thời | Điều kiện để xác nhận trên xe |
|---|---|---|
| Camera trước thật/Camera HAL | Import video, AAOS replay và camera adapter giả lập | Camera stream thật, timestamp, exposure/rolling-shutter profile và quyền hệ thống |
| Ego speed, gear, brake, steering, turn signal | Image-space relative motion và heuristic lead-braking; mọi giá trị gắn `estimated/uncalibrated` | CAN/vehicle signal hợp pháp, data contract và kiểm thử lỗi tín hiệu |
| Khoảng cách mét/TTC tuyệt đối | Relative closing trend, path conflict và risk score; không tuyên bố mét hoặc ground-truth TTC | Camera calibration, depth/stereo/radar hoặc telemetry đủ tin cậy |
| Jetson Orin thật | EC2 ARM64/GPU dùng cho packaging/preflight | Benchmark trên đúng Jetson Orin, nhiệt độ, điện năng, FPS, p95 và dropped frames |
| VinFast API/vehicle actuator | AAOS contract mock; không truy cập API nội bộ | NDA/API/Camera HAL/CAN và phê duyệt an toàn từ OEM |
| Chứng nhận an toàn | Locked regression, hazard analysis và closed-course protocol | Test track, safety driver, FMEA/FTA, logging, cybersecurity và quy trình chứng nhận phù hợp |

Do đó, câu trả lời kỹ thuật chính xác là: **RoadWatch có đường triển khai thực tế
rõ ràng**, nhưng prototype hiện tại mới chứng minh được perception/replay/HMI
contract và cloud demo. Nó chưa chứng minh được hành vi an toàn trên VF5, VF6,
VF7, VF8 hoặc VF9, và không nên quảng bá như tính năng OEM đã sẵn sàng tích hợp.

### 3.8. Lộ trình phát triển đề xuất cho VinFast

Các mục tiêu sau là release gate đề xuất, chưa được ghi nhận là đã đạt:

**Giai đoạn A — Safety/data baseline**

- Mở rộng locked ground truth cho ngày, đêm, mưa, ngược sáng, đông xe, occlusion
  và negative samples; mỗi event phải có timestamp, class, hướng, severity và
  secondary review.
- Đặt mục tiêu nội bộ: critical-event recall không giảm so với baseline; event
  recall held-out hướng tới `>=90%`, false alert hướng tới `<=1 alert/phút` trên
  negative windows và không có audio duplicate trong cùng một event.
- Đánh giá riêng motorcycle/person, fallen rider, cut-in/cross-traffic thay vì
  chỉ nhìn mAP tổng.

**Giai đoạn B — Edge performance**

- Export và benchmark FP16/INT8; mục tiêu demo edge `>=20 FPS`, mục tiêu release
  trên thiết bị đích `>=30 FPS`, p95 critical alert pipeline `<150 ms` khi đã
  định danh phần cứng.
- Đo RAM/VRAM, điện năng, nhiệt độ, dropped frames và cold/warm start trên
  Jetson Orin thật; không suy diễn từ laptop AMD hoặc EC2 sang xe.

**Giai đoạn C — Camera/AAOS integration**

- Thay replay source bằng Camera HAL adapter; khóa frame timestamp, resolution,
  camera calibration và lifecycle/background policy.
- Tích hợp vehicle signals theo read-only contract trước; không cho phép
  RoadWatch phát lệnh phanh/đánh lái.
- Closed-course test với safety driver, checklist fail-safe, đánh giá cabin
  audio và human listening gate cho tiếng Việt.

**Giai đoạn D — OEM pilot và MLOps**

- Model registry có version/hash/promotion gate; OTA chỉ cho candidate đã qua
  regression và rollback.
- Fleet dashboard chỉ thu thập dữ liệu được phê duyệt, có consent/privacy,
  anonymization và retention policy.
- Xây vehicle-profile configuration thay vì hard-code một dòng xe; mọi khác biệt
  về camera/FOV, màn hình, loa và tín hiệu xe phải được calibration theo platform.

### 3.9. Giá trị RoadWatch thể hiện với VinFast

RoadWatch cho thấy một kỹ sư không chỉ gọi một model object detection rồi vẽ
bounding box, mà có thể xây dựng một sản phẩm end-to-end:

- Chuyển yêu cầu ADAS mơ hồ thành Task ID, DoD, metrics và Quality Gate.
- Chọn model theo safety/event regression, biết giữ baseline khi candidate chưa
  đủ tốt và tách Fallen Rider thành workstream cần dataset/license riêng.
- Xử lý dữ liệu Việt Nam, fine-tuning trên Kaggle GPU, taxonomy, HITL review,
  temporal confirmation và hard-negative.
- Đóng gói ONNX/ORT, thiết kế async pipeline, session isolation, asset checksum,
  GCS/Cloud Run/IAM và xử lý sự cố latency/429 theo bằng chứng thực tế.
- Xây HMI React, Driver HUD, Engineer Dashboard, AAOS replay và tiếng Việt Piper
  xác định; không dựa vào voice ngẫu nhiên của máy demo.
- Giữ ranh giới an toàn: cảnh báo hỗ trợ người lái, không phóng đại thành
  autonomous driving và không bỏ qua hardware/calibration gate.

### 3.10. Kết luận đề xuất hợp tác

RoadWatch Copilot phù hợp được trình bày như một **prototype R&D cho ADAS
warning trong giao thông Việt Nam**. Giá trị cốt lõi không chỉ là nhận diện vật
thể, mà là chuỗi hoàn chỉnh từ dữ liệu địa phương → perception → risk reasoning
→ ưu tiên cảnh báo → tiếng Việt → HMI → kiểm thử và bằng chứng triển khai.

Nếu được tiếp tục trong môi trường doanh nghiệp, bước hợp lý nhất là một pilot
giới hạn trên dữ liệu/camera được VinFast phê duyệt, không nối actuator, đo trên
closed course và benchmark đúng hardware. Sau khi có calibration, vehicle
signals, test track và review an toàn, RoadWatch mới có thể được đánh giá như một
ứng viên component trong hệ sinh thái ADAS/AAOS của VinFast.

### 3.11. Nguồn tham khảo cho thành phần Piper tiếng Việt

- [Piper Vietnamese voice model](https://huggingface.co/rhasspy/piper-voices/blob/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx)
- [Piper voice configuration](https://huggingface.co/rhasspy/piper-voices/blob/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json)
- [VAIS-1000 model card và license](https://huggingface.co/rhasspy/piper-voices/blob/main/vi/vi_VN/vais1000/medium/MODEL_CARD)
- [Piper runtime](https://github.com/OHF-Voice/piper1-gpl)

