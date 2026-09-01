# RoadWatch Copilot — Báo cáo kỹ thuật tổng thể

> **Phiên bản báo cáo:** R0.9 — Demo Day handoff  
> **Ngày chốt trạng thái:** 2026-08-29  
> **Sản phẩm:** RoadWatch Copilot  
> **Phạm vi:** Edge-first multimodal ADAS warning prototype cho giao thông hỗn hợp Việt Nam  
> **Nguyên tắc an toàn:** Warning-only; không tự lái, không phanh, không đánh lái, không điều khiển ga

## Cách đọc báo cáo

Báo cáo này là snapshot kỹ thuật của repo tại ngày 2026-08-29. Các kết luận
được phân loại như sau:

| Trạng thái | Ý nghĩa |
|---|---|
| **Active** | Đang nằm trên đường chạy mặc định hoặc đã được nối vào sản phẩm demo |
| **Candidate** | Đã có artifact/thử nghiệm nhưng chưa vượt promotion gate |
| **Planned/Blocked** | Có thiết kế hoặc prototype, nhưng còn thiếu dữ liệu, phần cứng, quyền OEM hoặc bằng chứng |

Điều này rất quan trọng khi trình bày với doanh nghiệp: RoadWatch đã có một
pipeline sản phẩm chạy được, nhưng chưa phải hệ thống ADAS thương mại đã chứng
nhận và chưa được tích hợp camera/CAN của xe VinFast thật.

---

## Tóm tắt điều hành

RoadWatch Copilot là một trợ lý cảnh báo hỗ trợ lái dùng camera trước hoặc video
replay để nhận diện tác nhân giao thông, làn đường, vùng có thể lái và biển báo.
Hệ thống biến kết quả thị giác thành bằng chứng theo thời gian, đánh giá rủi ro
bằng logic deterministic, chọn cảnh báo theo mức nguy hiểm và phát cùng một
nội dung trên HUD, banner, beep và TTS tiếng Việt.

Điểm cốt lõi của sản phẩm không phải chỉ là “chạy YOLO trên một video”. Sản phẩm
đã được cấu trúc thành một vòng lặp cảnh báo có kiểm soát:

```text
Video/camera abstraction
    → Perception đa nhiệm
    → Tracking + temporal evidence
    → Risk Engine
    → Traffic Context v1
    → Alert Governor
    → Canonical AlertEvent
    → HUD / TTS / beep / Event History / evidence
                           └→ SLM giải thích kỹ thuật tùy chọn
```

Kiến trúc triển khai thống nhất là **one Core, three deployments**:

1. **Local/Edge plane:** đường chạy cảnh báo offline, hướng tới edge device và
   Jetson Orin.
2. **AAOS HMI plane:** Android Automotive emulator/app mô phỏng màn hình xe,
   video replay và vehicle contract read-only.
3. **GCP evaluation plane:** URL public cho hội đồng, video library, upload,
   HITL, evidence và replay; không phải critical path của cảnh báo trên xe.

Tại thời điểm báo cáo, RoadWatch đã có Driver HUD, Engineer Dashboard, FastAPI,
React/Vite, SQLite audit, Piper tiếng Việt, Traffic Context v1, model registry,
Kaggle training/evaluation pipeline, Docker CPU baseline và AAOS replay path.
Các điểm chưa thể tuyên bố hoàn tất là camera thật của VinFast, CAN/telemetry,
camera calibration, benchmark Jetson Orin vật lý, ground truth đầy đủ cho mọi
video và safety certification.

---

# 1. Bài toán chúng ta giải quyết là gì?

## 1.1. Bối cảnh thực tế

Camera trước có thể nhìn thấy ô tô, xe máy, người đi bộ, biển báo và hình dạng
làn đường. Tuy nhiên, một hệ thống chỉ phát beep cứng nhắc sẽ trả lời chưa đủ
các câu hỏi mà tài xế cần biết:

- Đối tượng nào đang tạo rủi ro?
- Đối tượng ở phía trước, trái hay phải?
- Nó đang đứng yên, đi cùng làn, nhập làn hay cắt ngang?
- Đây là nguy cơ thật sự hay chỉ là một phương tiện đang đi gần trong giao thông
  đông?
- Cảnh báo này có cần chiếm sự chú ý bằng âm thanh ngay lúc này không?

Giao thông Việt Nam làm bài toán khó hơn bởi mật độ xe máy cao, người đi bộ
cắt ngang, phương tiện chuyển hướng không đồng nhất, làn đường mờ, ngã tư dày
đặc, xe buýt/xe tải gây che khuất và điều kiện ban đêm/mưa/nén video.

## 1.2. Bài toán sản phẩm

RoadWatch giải quyết bài toán:

> Dùng camera trước hoặc video mô phỏng để phát hiện các tác nhân và tín hiệu
> đường bộ, theo dõi chúng qua thời gian, ước lượng nguy cơ ảnh hưởng đến quỹ
> đạo xe, rồi đưa ra cảnh báo tiếng Việt ngắn gọn, có đối tượng/vị trí/hành
> động và được ưu tiên để không làm tài xế quá tải.

Các nhóm event chính:

| Nhóm | Mục đích |
|---|---|
| FCW | Cảnh báo nguy cơ va chạm phía trước |
| VRU | Bảo vệ người đi bộ, người đi xe đạp, xe máy, người đi xe hai bánh |
| Cut-in | Phát hiện phương tiện có xu hướng nhập vào ego lane |
| Cross-traffic | Phát hiện người/phương tiện di chuyển cắt ngang vùng xe |
| Lead braking | Nhận ra xe phía trước đang giảm tốc mạnh qua bằng chứng ảnh theo thời gian |
| LDW | Cảnh báo xe có xu hướng lệch khỏi biên làn |
| Traffic sign | Nhận diện biển tốc độ, biển cảnh báo và biển có liên quan đến đường đi |
| Traffic context | Phân biệt giao thông đông an toàn với nguy cơ thật sự cần âm thanh |

## 1.3. Ràng buộc không được vi phạm

- Hệ thống chỉ cảnh báo/hỗ trợ; không điều khiển phanh, ga, vô lăng hoặc ECU.
- Không gọi kết quả ảnh là khoảng cách mét hoặc TTC vật lý nếu chưa có camera
  calibration, ground plane và ego speed đáng tin cậy.
- Không để một detection đơn lẻ kích hoạt cảnh báo critical.
- Không dùng SLM/LLM để tự tạo hoặc nâng cấp cảnh báo an toàn.
- Không dùng cloud làm điều kiện bắt buộc cho critical warning trên xe.
- Không nhận diện phương tiện gần là nguy hiểm nếu chưa có path conflict hoặc
  closing evidence đủ mạnh.
- Không đưa model candidate lên production chỉ vì mAP tăng; phải kiểm tra event
  recall, false alert, hướng trái/phải và latency.

---

# 2. Đối tượng người dùng là ai?

## 2.1. Tài xế — Driver

Tài xế là người nhận lợi ích trực tiếp. Họ cần một giao diện ít gây xao nhãng:

- HUD bên trái mô phỏng vùng hiển thị thông tin xe và tình hình trước đầu xe.
- Video/overlay và hazard banner ở vùng bên phải.
- Cảnh báo âm thanh tiếng Việt có câu ngắn, rõ đối tượng và vị trí.
- Chỉ thấy thông tin cần để phản ứng: “Cảnh báo va chạm”, “Xe máy bên phải;
  giảm tốc độ”, “Cảnh báo lệch làn bên trái”.
- Không cần tensor, log, model hash hay thông số training trong khi lái.

Driver demo account: `driver` / `driver123`. Đây là credential cho phòng demo;
không được dùng nguyên trạng ngoài môi trường thử nghiệm.

## 2.2. Kỹ sư ADAS — Engineer

Kỹ sư dùng RoadWatch để kiểm tra vì sao hệ thống cảnh báo hoặc im lặng:

- Model/profile/provider hiện tại là gì?
- Có bao nhiêu frame được xử lý và bị bỏ qua?
- P50/P95 có tăng do model, audio, render hay network không?
- Event có đủ confidence, track history, lane quality và path conflict không?
- Cảnh báo bị phát, bị debounce, chuyển HUD-only hay bị stale vì lý do nào?
- TTS và banner có dùng cùng canonical message không?
- SLM có `ready`, `pending`, `fallback`, hay `disabled` không?
- Ngưỡng có thay đổi và có audit log không?

Engineer demo account: `engineer` / `engineer123`. Tài khoản này chỉ phục vụ
demo/HITL; khi public hóa phải thay đổi.

## 2.3. Mentor, hội đồng và doanh nghiệp

Nhóm này cần kiểm chứng ba điều:

1. RoadWatch giải quyết một bài toán giao thông cụ thể, không phải một mockup
   hình ảnh.
2. Có thể chạy demo bằng URL, video mẫu hoặc video upload.
3. Kiến trúc có đường chuyển sang edge/AAOS/xe thật, đồng thời nhóm phát triển
   trung thực về những gì đã và chưa được kiểm chứng.

## 2.4. Nhóm tích hợp OEM/edge trong tương lai

Đây là người sẽ thay `FileReplaySource` bằng USB/CSI/Camera2/EVS, kết nối audio
focus/HMI và cung cấp calibration/telemetry. RoadWatch hiện chuẩn bị interface
cho nhóm này nhưng chưa có quyền camera hoặc API OEM của VinFast.

---

# 3. Chúng ta đã làm gì?

## 3.1. Xây dựng sản phẩm end-to-end

Đã xây dựng một ứng dụng gồm:

- FastAPI backend và worker phân tích.
- React + TypeScript + Vite frontend.
- Driver HUD và Engineer Dashboard.
- Login hai vai trò.
- Video library, upload, replay, pause, seek, tua và đổi video.
- MJPEG/HTTP/WebSocket/status path cho kết quả theo thời gian.
- SQLite event/evidence/audit store.
- Docker CPU baseline và profile triển khai.
- Android Automotive replay app/WebView trong Android Studio.
- Tài liệu architecture, safety, validation, model promotion, alert policy,
  cloud flow và SLM.

## 3.2. Các model perception

RoadWatch giữ ba model độc lập và hợp nhất bằng `Perception Orchestrator`.
Không ghép trực tiếp ba file weights thành một neural network duy nhất.

### Object detection — Active baseline

- `yolo11n.pt`/`yolo11n.onnx`.
- Taxonomy runtime cơ sở: `person`, `bicycle`, `motorcycle`, `car`, `bus`,
  `truck`.
- Profile ONNX/DirectML/CUDA/CPU tùy môi trường.
- Mục tiêu là road-user detection nhẹ, portable và ít rủi ro tích hợp.

Các artifact fine-tune `roadwatch_objects_v1`, `roadwatch_objects_v1_1` và
Object V3 là **Candidate**, chưa thay baseline mặc định vì event-level recall
chưa vượt gate. Object V3 Full có locked event recall `0.6000`, trong khi
baseline là `0.8000`; vì vậy giữ baseline là quyết định có căn cứ.

### Traffic sign — Active/promoted runtime

- `roadwatch_detector_v2.onnx` cho detector biển báo.
- `roadwatch_speed_digits_v2.onnx` cho nhận diện giá trị tốc độ.
- Artifact gốc `.pt` được giữ để export/đối chiếu.
- Có temporal confirmation, geometric/visual validation, lane relevance và
  sign arbitration.

Các số liệu promotion đã ghi nhận:

```text
Detector precision:       0.95847
Detector recall:          0.96651
mAP50:                    0.98741
mAP50-95:                 0.83217
Speed classifier top-1:   0.98254
```

### Lane và drivable area — Active baseline

- `yolop_lane_detection_640.onnx` là runtime mặc định.
- `yolop_lane_detection.pth` là artifact gốc/đường nghiên cứu.
- Model cung cấp lane mask và drivable-area mask.
- Pipeline fit ego-lane corridor để dùng cho LDW/FCW; đây không phải lane-instance
  model hoàn chỉnh có thể đếm chắc chắn mọi lane.

UFLDv2 ResNet-18 và TwinLiteNet+ Medium là **Candidate**. UFLDv2 từng cho
coverage `0.8571`, DirectML fusion khoảng `3.04 FPS`, lane P95 `124.68 ms` và
E2E P95 `149.37 ms` trên sample đã đo; chưa đủ điều kiện thay YOLOP. TwinLiteNet+
được giữ để benchmark/fallback cho tới khi có ground truth và parity evaluation
đủ tin cậy.

## 3.3. Temporal perception và risk

Đã xây dựng:

- IoU temporal tracker và track ID ổn định hơn so với cảnh báo từng frame.
- Lịch sử bounding box, center, diện tích và xu hướng mở rộng.
- Lane/drivable association và ego-path corridor.
- Risk Engine cho FCW, VRU, cut-in, cross-traffic, lead braking và LDW.
- Temporal confirmation, hysteresis, cooldown, severity priority và stale-event
  guard.
- Evidence packet cho từng quyết định.

Tracker hiện là deterministic IoU tracker nhẹ, chưa phải ByteTrack đầy đủ. Thiết
kế interface cho phép thay adapter tracking mà không phải viết lại Risk Engine.

## 3.4. Alert Governor và Traffic Context v1

`AlertGovernor` là cổng duy nhất quyết định event nào được gửi ra audio/HUD.
Traffic Context Engine đứng trước governor để nhận biết dense traffic:

- Chỉ đếm track đã xác nhận, tuổi tối thiểu khoảng `0.5 s`.
- Loại track phải nằm trong drivable area, ego lane hoặc path corridor.
- Người đi bộ rõ ràng trên vỉa hè không làm tăng density nguy hiểm.
- Đếm theo `track_id`, không đếm box duplicate.
- Vào dense khi `>= 8` road users, hoặc `>= 6` với tối thiểu `2` xe hai bánh,
  ổn định trong `3/5` frame inference.
- Thoát dense khi `< 5` road users liên tục `2 s`.

Trong dense mode:

- FCW critical và nguy cơ path conflict thật vẫn được phát âm thanh.
- Phương tiện đi gần nhưng không xung đột đường đi chủ yếu hiển thị HUD-only.
- Speed sign và cut-in/cross-traffic rủi ro thấp được hạ kênh để giảm quá tải.
- Khi vừa vào dense, phát một lần hai beep nhẹ và hiển thị context card.

Chế độ rollout:

```text
off       → hành vi audio cũ, đường fallback
shadow    → tính density và ghi log, chưa đổi audio
enforce   → áp dụng selective audio
```

## 3.5. TTS tiếng Việt và audio safety

Release baseline hiện tại:

- Piper `vi_VN-vais1000-medium`.
- Sample rate `22.050 Hz`, một speaker, không có `speaker_id_map`.
- Trong sản phẩm, tên hiển thị là **Trúc Ly**; đây là product alias, không phải
  speaker ID do model khai báo.
- Browser/server audio owner được tách rõ.
- Cache key có provider/model hash/config hash/canonical message.
- Browser Web Speech/voice hệ điều hành không được dùng làm fallback mặc định.

Đã sửa các lỗi từng xảy ra:

- TTS bị phát kép hoặc lặp “Cảnh cảnh báo báo...” bằng single-owner,
  claim/dedupe/serialize audio.
- Banner và TTS lấy cùng `canonical_message`.
- Event cũ bị stale sau pause/seek/đổi video không được phát sang session mới.
- Critical beep có quyền preempt advisory nhưng không phát chồng audio.
- Voice sai model được chặn bằng metadata và SHA-256 fingerprint.

VieNeu/Minh Triết vẫn là candidate A/B; không thay Piper release nếu chưa vượt
quality gate âm đầu, latency, audio integrity và human listening.

## 3.6. SLM giải thích kỹ thuật

Đã tích hợp worker tùy chọn Qwen2.5-0.5B-Instruct ONNX Q4F16:

- Chỉ nhận event deterministic đã được governor chấp nhận.
- Chỉ giải thích bằng chứng cho Engineer Console.
- Không tạo, sửa, nâng cấp, hạ cấp hoặc phát critical alert.
- Không điều khiển TTS/audio/actuator.
- Queue giới hạn, stale-event guard, validator và fallback deterministic.
- Model lazy-load; `device=auto` ưu tiên CUDA rồi CPU; DirectML chỉ opt-in.

Trạng thái SLM có thể là `disabled`, `pending`, `ready` hoặc `fallback`. Smoke
test local đã sinh explanation hợp lệ bằng CPU, nhưng latency khoảng `11–12 s`
cho một lần decode nên SLM mặc định tắt trong đường demo để bảo vệ latency.

## 3.7. UI/HMI và lifecycle

Đã thiết kế theo màn hình ô tô mô phỏng:

- Khoảng 20% bên trái cho Driver HUD/telemetry/ego vehicle/context.
- Khoảng 80% bên phải cho video và thông tin phụ.
- Video giữ nguyên tỷ lệ bằng layout/fit đúng; không kéo méo hình.
- Driver xem tối thiểu thông tin cần phản ứng.
- Engineer xem metrics ở phía trên video, event history và evidence ở phía dưới.
- Logo RoadWatch chỉ hiển thị ở login theo quyết định UI.
- Có event history, status, health, model/provider và SLM runtime state.

Replay state machine đã xử lý pause, resume, seek, stop, reset và video switch
để vị trí/video của session A không rò sang session B. Seek reset tracker/risk
đang hoạt động nhưng giữ audit history để Engineer không mất lịch sử.

## 3.8. Cloud, AAOS và MLOps

Đã chuẩn bị:

- Cloud Run web/evaluation plane.
- Cloud Build + Docker + Artifact Registry.
- Cloud Storage cho model/media nặng ngoài Git.
- Secret/IAM/config separation.
- URL fallback `run.app` và quy ước custom URL
  `https://c3-roadwatch-162.io.vn` khi DNS/domain mapping hoàn tất.
- Kaggle GPU notebooks cho data audit, quality gate và fine-tune.
- Android Studio AAOS emulator/app cho replay HMI.
- ARM64/Docker/TensorRT preflight scripts; benchmark Jetson thật vẫn blocked.

---

# 4. Chúng ta đã giải quyết như thế nào?

## 4.1. Kiến trúc lớp

```text
┌──────────────────────────────────────────────────────────────┐
│ Input: file replay / USB camera / CSI / Camera2 / EVS adapter │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Frame scheduler: timestamp, bounded queue, sampling/drop     │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Perception Orchestrator                                     │
│  YOLO11n object | sign detector + speed | YOLOP lane/drive  │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Normalized perception: bbox/class/confidence/mask/geometry   │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Tracking + temporal history + lane/path association          │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Risk Engine: FCW/VRU/cut-in/cross-traffic/LDW/lead braking  │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Traffic Context v1 + Alert Governor                         │
└──────────────┬───────────────┴──────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Canonical AlertEvent: severity, message, evidence, lifecycle │
└──────┬───────────────┬───────────────┬───────────────────────┘
       ▼               ▼               ▼
 Driver HUD       Beep/Piper       SQLite/API/WebSocket
       │               │               │
       └───────────────┴───────────────┴── Engineer Console
                                               └→ SLM async
```

Mỗi tầng có một trách nhiệm rõ ràng. Perception không tự phát âm thanh; SLM
không tự quyết định nguy hiểm; UI không tự tính risk; cloud không nằm trong
đường critical warning.

## 4.2. Vì sao giữ ba model thay vì gộp thành một?

Có thể nghiên cứu multi-task model với shared backbone và ba heads:

```text
shared backbone
├── road-user detection head
├── traffic-sign detection head
└── lane/drivable segmentation head
```

Nhưng không thể nối trực tiếp ba file weights hiện tại. Ba model khác kiến trúc,
preprocessing, tensor output và annotation. Biển báo cần giữ chi tiết nhỏ; lane
cần output dense; object cần taxonomy/classification khác. Dataset cũng không có
annotation đồng bộ cho cùng một frame.

Vì vậy, production path dùng:

```text
ba model riêng → Perception Orchestrator → schema output thống nhất
```

Ưu điểm là rollback độc lập, chẩn đoán rõ, thay model từng tầng và benchmark
riêng. Multi-task chỉ mở lại khi có annotation đồng bộ, benchmark đầy đủ và
không làm giảm critical event recall, lane quality hoặc sign recall.

## 4.3. Perception và model selection

Model output không được dùng trực tiếp để cảnh báo. Mỗi output qua:

1. confidence threshold;
2. class normalization;
3. coordinate conversion;
4. NMS/post-processing;
5. track association;
6. temporal confirmation;
7. lane/drivable/path relevance;
8. risk scoring.

Tiêu chí chọn model không chỉ là mAP:

| Cấp đánh giá | Chỉ số/ý nghĩa |
|---|---|
| Static | precision, recall, mAP, lane IoU/F1, speed top-1 |
| Event | critical recall, first warning time, direction accuracy, miss rate |
| System | false alerts/min, duplicate rate, E2E P50/P95, audio completion, pipeline errors |
| Deployment | FPS, memory, provider portability, startup/warmup, thermal/power |

Một model có mAP cao nhưng bỏ sót xe máy cắt ngang hoặc tạo nhiều cảnh báo sai
không được promote vào warning path.

## 4.4. Từ detection đến FCW/VRU

Ví dụ một xe máy tiến vào ego path:

1. Object model phát hiện `motorcycle` với bounding box và confidence.
2. Tracker giữ một `track_id` qua nhiều frame.
3. Risk Engine quan sát vị trí theo chiều ngang, diện tích box tăng, lane/path
   overlap và trạng thái drivable.
4. Nếu có đủ temporal hits và risk vượt ngưỡng, sinh candidate FCW/VRU hoặc
   cross-traffic.
5. Alert Governor chọn severity, kiểm tra cooldown và dense mode.
6. Event được chuẩn hóa thành một `canonical_message`, ví dụ:
   `Xe máy bên phải; giảm tốc độ.`
7. Driver nhận banner/HUD và Piper TTS; Engineer nhận evidence packet.

Nếu model không thấy xe máy, rule engine không có đối tượng để tính. Nếu model
nhận xe máy thành người đi bộ, logic vẫn có thể đúng về risk nhưng message sai
ngữ nghĩa. Đây là lý do rule engine phụ thuộc chất lượng perception.

## 4.5. FCW và khoảng cách

RoadWatch hiện dùng image-space risk proxy:

- độ lớn bounding box;
- tốc độ thay đổi diện tích/chiều cao box;
- vị trí trong ego lane/path corridor;
- lateral motion và overlap;
- temporal persistence;
- lane/drivable quality.

TTC vật lý thường cần dạng `distance / closing_speed`, nhưng với camera đơn chưa
calibration và chưa có ego speed thì `distance` không phải mét và tốc độ không
phải m/s. Vì vậy evidence ghi rõ `image-space risk; không phải TTC theo mét`.

Muốn promote TTC vật lý cần camera intrinsic/extrinsic, ground-plane assumption
hoặc depth đã kiểm chứng, ego speed/yaw rate và closed-course ground truth.

## 4.6. Lead braking không phụ thuộc riêng đèn phanh

Trong MVP, lead braking chủ yếu dựa trên xu hướng ảnh:

- xe phía trước vẫn có track ổn định;
- box tăng kích thước nhanh hoặc khoảng cách ảnh giảm;
- closing trend kéo dài qua nhiều frame;
- có thể dùng brake-light heuristic như tín hiệu bổ trợ, không phải điều kiện duy nhất.

Cách này có thể cảnh báo sớm hơn nhận diện đèn phanh, nhưng không chứng minh được
vận tốc tuyệt đối nếu thiếu calibration. Nó phù hợp cho prototype; bản xe thật
cần fuse camera với CAN/radar/ego speed nếu OEM cho phép.

## 4.7. Traffic sign và lane relevance

Một biển báo không được đọc chỉ vì detector thấy trong một frame. Luồng sign:

1. detector phát hiện hộp biển;
2. classifier/recognizer xác định loại hoặc giá trị tốc độ;
3. temporal confirmation qua nhiều frame;
4. kiểm tra hình học/visual validity và loại hard negative;
5. xác định biển có liên quan đến hướng/lane xe đang chạy;
6. arbitrate nếu có nhiều biển trong cùng frame;
7. tạo banner và TTS từ cùng một event.

Ví dụ nếu có hai biển `80` và `60` ở các lane khác nhau, hệ thống phải chọn biển
liên quan ego lane; nếu chưa xác định được lane relevance thì hiển thị thận
trọng hoặc im lặng thay vì đọc số đoán.

## 4.8. Alert copy và TTS

Nguyên tắc câu cảnh báo:

```text
đối tượng nào → ở đâu → nguy hiểm gì → tài xế nên làm gì
```

Ví dụ theo mức:

| Tình huống | Kênh/câu mẫu |
|---|---|
| FCW critical | Beep ưu tiên + “Cảnh báo va chạm” |
| FCW warning | “Ô tô phía trước; giảm tốc độ.” |
| VRU path conflict | “Người đi bộ bên phải; giảm tốc độ.” |
| Lead braking | “Ô tô phía trước đang giảm tốc. Hãy chú ý.” |
| Cut-in phương tiện | “Xe máy nhập làn từ bên phải. Hãy chú ý.” |
| Cross-traffic | “Xe máy cắt ngang từ bên trái.”; chỉ đọc nếu có motion/path evidence |
| LDW | “Cảnh báo lệch làn bên trái.” |
| Speed sign | “Giới hạn 60 ki-lô-mét/giờ phía trước.”; chỉ đọc sau confirmation và relevance |
| Sign hướng rẽ/giữ làn | HUD-only khi không có safety relevance trực tiếp |

Trong dense traffic, một phương tiện đi gần nhưng không xung đột không được phát
TTS liên tục. Đây là cách RoadWatch giải quyết alert fatigue thay vì chỉ giảm
confidence threshold.

## 4.9. SLM và giới hạn an toàn

SLM nhận payload kiểu:

```json
{
  "event_type": "fcw",
  "severity": "warning",
  "object_class": "motorcycle",
  "location": "right",
  "risk_score": 0.78,
  "confidence": 0.87,
  "hits": 6,
  "lane_quality": 0.74
}
```

SLM có thể giải thích: event dựa trên xe máy ở bên phải, track đã ổn định, risk
vượt ngưỡng. SLM không được suy diễn rằng khoảng cách là 3 m, tốc độ là 40 km/h
hoặc yêu cầu đánh lái nếu payload không có bằng chứng.

Nếu SLM chậm, lỗi model, queue stale hoặc validator fail, event deterministic
vẫn giữ nguyên. SLM chỉ hiện `fallback`/`disabled` ở Engineer Console.

## 4.10. Video lifecycle và tính nhất quán UI

Mỗi replay có `run_id`, nguồn video, timestamp và trạng thái riêng. Khi pause/seek
hoặc đổi video:

- renderer chuyển sang frame/timestamp đúng của run hiện tại;
- queue SLM cũ bị hủy;
- tracker/risk state được reset;
- event audit đã xảy ra vẫn giữ trong Event History;
- không phát audio stale từ video cũ.

Điều này giải quyết lỗi nghiêm trọng trước đây khi video B hiển thị frame/video A
ở vị trí đã pause.

---

# 5. Chúng ta tạo ra cách giải quyết như thế nào?

## 5.1. Luồng chạy từng bước

### Bước 1 — Khởi động runtime

`setup.ps1` chuẩn bị Python environment, dependency, Piper voice/config,
model asset validation và frontend bundle. `start.ps1` đặt release profile:

- Piper/Trúc Ly;
- Traffic Context v1 `enforce`;
- audio owner browser cho local web;
- `dist-ui-v4` nếu có;
- các fallback rõ ràng nếu frontend/model thiếu.

**Ý nghĩa:** khóa môi trường demo để không kế thừa nhầm biến của phiên benchmark
trước đó.

### Bước 2 — Chọn nguồn vào

Nguồn hiện có là file replay/video library hoặc upload. Interface đã dành chỗ cho:

- `FileReplaySource` hiện tại;
- USB camera;
- CSI camera trên Jetson;
- AAOS Camera2/EVS khi OEM cấp quyền.

**Ý nghĩa:** video chỉ là camera simulator trong demo, nhưng contract không bị
gắn cứng vào file.

### Bước 3 — Đọc và điều phối frame

Frame được gắn timestamp/frame ID. Scheduler dùng queue giới hạn, sampling/drop
policy và không tích lũy frame cũ. Runtime mặc định hiện có scheduling:

- object: mỗi processed frame;
- YOLOP: mặc định mỗi 2 frame, dùng mask gần nhất;
- sign: mặc định mỗi 5 frame vì biển thay đổi chậm hơn FCW.

**Ý nghĩa:** giữ latency có giới hạn và dành tài nguyên cho những tác vụ thực sự
cần phản ứng nhanh.

### Bước 4 — Chạy perception

Các adapter phát ra schema thống nhất gồm class, bbox, confidence, mask,
geometry, model/profile và health. Nếu một model lỗi, trạng thái degraded được
ghi mà không làm cả API crash.

**Ý nghĩa:** model có thể thay thế/rollback độc lập.

### Bước 5 — Tạo bằng chứng theo thời gian

Tracker nối detection vào track ID. Lịch sử cho phép phân biệt:

- vật thể thật so với nhiễu một frame;
- đang đi gần so với đang tiến vào path;
- người đi bộ trên vỉa hè so với người đi bộ cắt ngang;
- biển báo thật so với watermark/false sign.

### Bước 6 — Tính risk

Risk Engine kết hợp proximity proxy, expansion/closing trend, lateral motion,
ego-lane/path conflict, drivable mask, lane quality, confidence và số frame xác
nhận.

**Ý nghĩa:** “đã nhìn thấy” không đồng nghĩa “cần cảnh báo”.

### Bước 7 — Phân loại traffic context

Traffic Context Engine quyết định normal hay dense. Nó không thay thế risk
engine; nó chỉ quyết định mức audio cần thiết trong bối cảnh đông.

**Ví dụ:** 12 xe máy đi chậm xung quanh nhưng không ai vào ego path → context
beep một lần + HUD; một xe máy cắt vào path với risk cao → TTS cảnh báo vẫn được
phát.

### Bước 8 — Alert Governor chọn một event

Governor áp dụng:

- severity priority;
- temporal confirmation;
- cooldown/global audio gap;
- deduplication;
- stale-event guard;
- dense selective audio;
- canonical message;
- display/audio route.

Các event bị suppression không mất hoàn toàn: Engineer vẫn có thể xem lý do
`hud_only`, `suppressed:dense_traffic_context`, `stale`, `cooldown` hoặc
`queue_replaced`.

### Bước 9 — Phát ra cho tài xế

Một `AlertEvent` duy nhất được dùng cho:

- hazard banner;
- Driver HUD;
- beep;
- Piper WAV;
- Event History;
- evidence packet.

Audio controller bảo đảm browser hoặc server là owner, không phải cả hai cùng
phát. Một event có thể là `claimed → playing → completed`, hoặc bị ghi rõ là
duplicate/suppressed.

### Bước 10 — SLM giải thích cho Engineer

Nếu bật chủ đích, SLM nhận event đã accepted qua queue bất đồng bộ. Engineer xem
provider, queue, latency, quality, output tokens và explanation gần nhất. Tài xế
không bị đọc explanation này.

### Bước 11 — Lưu và hiển thị bằng chứng

SQLite/API lưu event type, severity, message, object/track, risk, confidence,
context, lifecycle, audio route, suppression reason, SLM status và timestamp.

Engineer dùng dữ liệu đó để review model/rule thay vì chỉ nhìn một banner.

## 5.2. Ý nghĩa các metrics chính

| Metric | Ý nghĩa | Cách xác định |
|---|---|---|
| Processed FPS | Tốc độ vòng perception/risk xử lý frame | `số frame đã xử lý / thời gian xử lý` |
| Display FPS | Tốc độ frame overlay thực sự render tới UI | đếm frame render/MJPEG/WebSocket trong cửa sổ đo |
| Sampling skip | Số frame nguồn không chạy inference đầy đủ | so sánh frame nguồn với frame processed; không đồng nhất với lỗi |
| E2E P50 | Median latency một frame từ input đến kết quả | percentile 50 của các mẫu latency hợp lệ |
| E2E P95 | Tail latency; 95% frame không chậm hơn giá trị này | percentile 95, quan trọng để phát hiện spike |
| Warmup | Thời gian load model/graph/cache trước steady state | đo từ startup tới health ready/inference ổn định |
| FCW warning threshold | Biên risk để tạo cảnh báo warning | cấu hình deterministic, cần hiệu chỉnh trên data target-domain |
| FCW critical threshold | Biên risk cao hơn để preempt audio và banner đỏ | threshold + temporal/near-field guard, không chỉ một frame |
| Evidence risk | Mức nguy cơ tổng hợp từ feature đã quan sát | risk engine snapshot tại event |
| Evidence confidence | Mức tin cậy của perception/model | confidence sau post-process/track, không phải xác suất tai nạn |
| Lifecycle | Vòng đời event | `candidate/accepted/playing/completed/suppressed/stale` |
| Audio state | Trạng thái audio | owner, route, claim, start, completion, suppression |

### Ví dụ latency

Nếu 100 frame có E2E latency được sắp xếp, mẫu thứ 50 là `119 ms` và mẫu thứ
95 là `189 ms`, UI có thể hiển thị P50 khoảng `119 ms`, P95 khoảng `189 ms`.
P95 cao hơn thường do model optional, CPU contention, encode JPEG, audio/network
hoặc Cloud Run cold start; không được kết luận ngay rằng model “chậm toàn bộ”.

### Bằng chứng benchmark local đã ghi nhận

Validation Windows AMD trên `test_video10.mp4`, 1920×1080, 30 FPS, audio tắt:

```text
Object runtime P50/P95:       44.57 / 70.23 ms
YOLOP runtime P50/P95:        70.43 / 76.00 ms
Traffic-sign P50/P95:         81.47 / 115.67 ms
E2E P50/P95:                  148.44 / 245.40 ms
Throughput ba model:            4.31 processed FPS
Model health:                   3/3 loaded, không degraded
```

Đây là bằng chứng của một cửa sổ benchmark cụ thể, không phải cam kết mọi máy
hoặc mọi video đều đạt cùng số liệu.

## 5.3. Local/edge, AAOS và cloud hoạt động ra sao?

### Local/edge

```text
camera/file → RoadWatchCore → local audio/HUD → SQLite
```

Không cần internet để chạy inference critical path. Windows AMD ưu tiên
ONNX Runtime DirectML khi phù hợp, fallback CPU; NVIDIA/Jetson có CUDA/TensorRT
profile. Artifact model/voice/media nằm ngoài Git và được kiểm hash.

### AAOS

AAOS hiện là HMI/replay showcase:

```text
AAOS emulator/app → local WebView/native HMI → local RoadWatchCore/replay
```

Ứng dụng có thể chứng minh bố cục màn hình, audio focus, playback và read-only
vehicle telemetry mô phỏng. Camera thật cần Camera2/EVS permission, OEM service,
camera HAL và policy của xe; chưa có trong môi trường hiện tại.

### GCP

GCP là evaluation plane:

```text
Browser public URL
   → Cloud Run web/API
   → Cloud Storage model/media hoặc upload
   → replay worker / status / evidence
   → browser trả video overlay, event, metrics, TTS
```

Cloud Run phù hợp public demo và scale-to-zero nhưng có network, container
startup, CPU replay và cold-start latency. Do đó cloud không được dùng làm bằng
chứng cứ cho edge realtime và không được là đường duy nhất để cảnh báo trên xe.

## 5.4. Các file/source giải quyết từng vấn đề ở đâu?

| Vấn đề | Vị trí chính trong project |
|---|---|
| Cấu hình model/runtime | `roadwatch/backend/roadwatch/config.py`, `roadwatch/configs/default.json` |
| Perception adapters | `roadwatch/backend/roadwatch/perception.py`, `roadwatch/models/` |
| Pipeline và scheduling | `roadwatch/backend/roadwatch/pipeline.py` |
| Tracking | `roadwatch/backend/roadwatch/tracking.py` |
| Kinematics/image-space trend | `roadwatch/backend/roadwatch/kinematics.py` |
| FCW/VRU/risk | `roadwatch/backend/roadwatch/risk.py` |
| Alert priority/dedupe | `roadwatch/backend/roadwatch/alerts.py` |
| Traffic Context v1 | `roadwatch/backend/roadwatch/traffic_context.py` |
| Sign validation/arbitration | `roadwatch/backend/roadwatch/signs.py`, `sign_arbitration.py` |
| Beep/TTS/audio owner | `roadwatch/backend/roadwatch/audio.py`, `tts.py` |
| SLM explanation | `roadwatch/backend/roadwatch/slm.py` |
| Event/audit storage | `roadwatch/backend/roadwatch/storage.py` |
| HTTP/WebSocket/MJPEG/API | `roadwatch/backend/roadwatch/api.py` |
| Driver/Engineer UI | `roadwatch/frontend/src/` |
| UI production bundle | `roadwatch/frontend/dist-ui-v4/` |
| Windows setup/start | `roadwatch/scripts/setup.ps1`, `start.ps1` |
| Unit/regression/benchmark | `roadwatch/tests/`, `roadwatch/scripts/`, `roadwatch/reports/` |
| Dataset/fine-tune | `roadwatch/kaggle/`, `evaluation/`, `reports/` |
| AAOS | `roadwatch/android/roadwatch-aaos/` |
| Docker/cloud | `roadwatch/Dockerfile*`, `docker-compose*`, `deploy/` |
| Quy tắc làm việc | `roadwatch/AGENTS.md` |

---

# 6. Tại sao sản phẩm có giá trị hơn so với các sản phẩm khác?

So sánh dưới đây là so sánh theo nhóm giải pháp, không phải tuyên bố RoadWatch
đã vượt các hệ thống thương mại được chứng nhận.

| Tiêu chí | Beep ADAS tối giản | Cloud-only demo | Generic CV demo | RoadWatch Copilot |
|---|---|---|---|---|
| Ngữ cảnh Việt Nam | Thường chung chung | Phụ thuộc dữ liệu/cloud | Thường tập trung object | Ưu tiên xe máy, người đi bộ, cắt ngang và dense traffic |
| Nội dung cảnh báo | Beep hoặc câu cố định | Có thể sinh câu nhưng khó kiểm soát | Thường chỉ box/label | Canonical Vietnamese message có đối tượng, vị trí, hành động |
| Giảm alert fatigue | Thường hạn chế | Không bảo đảm | Không phải mục tiêu chính | Tracking, temporal confirmation, cooldown, hysteresis, Traffic Context v1 |
| Safety boundary | Có thể khó quan sát | Phụ thuộc server | Không rõ | Warning-only, không actuator, không tự tuyên bố TTC mét |
| Explainability | Ít evidence | Log server | Box/confidence | Risk, track, lane, context, lifecycle và suppression reason |
| Offline/edge | Tùy thiết bị | Không | Tùy model | Core offline, ONNX provider path, Piper local, Docker/AAOS boundary |
| Kỹ sư cải tiến | Thường không có | Log rời rạc | Notebook rời rạc | Engineer Dashboard, HITL, model profile, audit và promotion gate |
| Đường tới xe thật | Khó thay nguồn camera | Không phù hợp critical | Chưa có HMI contract | Một Core, replay/USB/CSI/Camera2/EVS adapter boundary |
| Rollback | Không rõ | Phụ thuộc deploy | Thường thủ công | Model/profile/audio/UI fallback và checksum |

## 6.1. Điểm nổi bật thứ nhất: Vietnam-first nhưng không chỉ dịch tiếng Việt

RoadWatch không chỉ dịch “object detected” sang tiếng Việt. Logic cố gắng phân
biệt xe máy, rider, người đi bộ, cắt ngang, nhập làn, đi trên vỉa hè và path
conflict. Traffic Context v1 còn xử lý tình huống đặc trưng: giao thông đông
không đồng nghĩa nguy hiểm.

## 6.2. Điểm nổi bật thứ hai: “biết im lặng”

Một hệ thống hỗ trợ lái tốt không phải hệ thống nói nhiều nhất. RoadWatch có
selective audio:

- nguy cơ critical vẫn được ưu tiên;
- vật thể an toàn chuyển HUD-only;
- người đi bộ rõ ràng trên vỉa hè không gây cảnh báo;
- context beep chỉ phát một lần khi vào dense;
- warning phải có path/risk/closing evidence đủ mạnh.

Đây là giá trị UX và safety quan trọng vì alert fatigue có thể làm tài xế bỏ qua
cả cảnh báo thật.

## 6.3. Điểm nổi bật thứ ba: Explainable-by-construction

Mỗi cảnh báo có thể truy ngược:

```text
event → track → frame history → bbox/mask → risk feature → rule → audio/display route
```

SLM chỉ được thêm ở phía sau để viết giải thích cho kỹ sư, không được làm “nguồn
chân lý” an toàn. Đây là thiết kế phù hợp để audit và debug hơn một agent tự do
sinh câu.

## 6.4. Điểm nổi bật thứ tư: Một core, nhiều môi trường

Cùng contract có thể chạy local web, Docker, AAOS replay và edge candidate. Web
public giúp hội đồng test được; edge boundary bảo đảm câu chuyện triển khai xe
thật không phụ thuộc cloud.

## 6.5. Điểm nổi bật thứ năm: Model promotion theo event-level safety

RoadWatch không promote candidate chỉ vì latency hoặc mAP. Ví dụ:

- Object V1.1 giảm false alerts từ `10.3846` xuống `5.7692/phút`, nhưng event
  recall giảm từ `0.5000` xuống `0.3750` → không promote.
- Object V2 candidate có latency tốt hơn nhưng event recall giảm `0.80 → 0.60`
  và false alerts tăng `3.8462 → 4.6154/phút` → không promote.
- UFLDv2 có geometry tiềm năng nhưng DirectML fusion/coverage chưa đạt gate →
  giữ YOLOP.

Quyết định này cho thấy sản phẩm ưu tiên đúng cảnh báo quan trọng, không tối ưu
một con số cô lập.

## 6.6. Điểm nổi bật thứ sáu: Minh bạch về giới hạn

RoadWatch có thể nói chính xác:

> Đây là một production-shaped, edge-first warning prototype; video replay là
> camera simulator, AAOS emulator chứng minh HMI/contract, GCP chứng minh demo
> và evaluation. Tích hợp camera VinFast, CAN, calibration, Jetson thật và
> chứng nhận vẫn là các bước cần OEM/hardware/closed-course.

Không tuyên bố quá mức cũng là một năng lực kỹ thuật khi thuyết phục doanh nghiệp.

---

# 7. Bằng chứng kỹ thuật và trạng thái hiện tại

## 7.1. Bằng chứng automated/software

Các lần kiểm tra đã ghi nhận trong repo/AGENTS gồm:

- full backend tests đã pass trong các phiên xác minh gần nhất;
- Python `compileall` pass;
- TypeScript compiler pass;
- Vite build `dist-ui-v4` pass;
- Docker Compose schema pass;
- model/media/voice/.venv được ignore khỏi Git;
- SLM worker smoke sinh output hợp lệ và có fallback;
- `git diff --check` không có whitespace error cho phần đã kiểm.

Một validation snapshot trước đó ghi `26 passed, 1 warning`; một benchmark local
riêng ghi `11 passed` cho test suite tại thời điểm đó. Khi chuẩn bị release cuối,
cần chạy lại test suite hiện tại và ghi số thực tế vào changelog, vì số lượng test
có thể thay đổi theo commit.

## 7.2. Bằng chứng model/sign/object/lane

| Hạng mục | Bằng chứng | Kết luận |
|---|---|---|
| Sign detector | P/R/mAP và speed top-1 ở §3.2 | Đang dùng active, vẫn cần mở rộng low-light/orientation |
| Object baseline | Presence/event regression và runtime portable | Active baseline |
| Object candidate | V3 recall `0.60` < baseline `0.80` | Candidate, không promote |
| Lane YOLOP | Mask/LDW integration, runtime sẵn | Active baseline |
| Lane UFLDv2 | Coverage `0.8571`, DirectML fusion `3.04 FPS` | Candidate, không promote |
| Traffic Context | Unit/replay policy, hysteresis/audio routing | Active policy, cần replay gate mỗi release |
| Piper | Model/config metadata, cache/audio owner | Active release baseline |
| VieNeu | Human listening sơ bộ tốt nhưng còn audio-start/semantic gate | Candidate |
| SLM | CPU worker smoke ready, latency 11–12 s | Optional Engineer-only, mặc định off |

## 7.3. Promotion gate mục tiêu

Các mục tiêu R1/R2 đã thống nhất, cần hiểu là target trên bộ test có ground truth,
không phải cam kết cho mọi video bất kỳ:

```text
Critical FCW/VRU recall:          >= 0.95
Object/direction semantic acc.:  >= 0.95
False critical alert:            <= 0.1/phút
All-alert false positive:        <= 1/phút
E2E P95:                         <= 150 ms
Lane count accuracy:             >= 0.95
Ego-boundary F1:                 >= 0.90
Night/rain lane recall:          >= 0.85
LDW false alerts:                <= 1/phút
AMD full-pipeline FPS:           >= 12
```

Các target này chưa được trình bày như kết quả hiện tại nếu chưa có report tương
ứng cho đúng dataset/runtime.

## 7.4. What is proven vs not proven

| Đã có bằng chứng | Chưa đủ bằng chứng |
|---|---|
| Local web chạy pipeline/video replay | Camera trước trên xe VinFast thật |
| Driver HUD + Engineer Dashboard | Camera2/EVS/OEM permission |
| Object/sign/lane model adapters | Calibration và TTC theo mét |
| TTS Piper tiếng Việt local | Audio route được OEM chứng nhận |
| Tracking/risk/governor/evidence | Closed-course safety validation đầy đủ |
| Traffic Context selective audio | Safety certification/ISO process hoàn tất |
| AAOS emulator replay | AAOS emulator tương đương xe VinFast |
| GCP public evaluation plane | Cloud realtime safety path |
| Docker/ARM64 preparation | Jetson Orin vật lý FPS/thermal/power |
| Kaggle training/evaluation pipeline | Ground truth timestamp cho mọi video |

---

# 8. Cách demo với hội đồng

## 8.1. Chuẩn bị local

Trong PowerShell:

```powershell
cd roadwatch
.\scripts\setup.ps1
.\scripts\start.ps1 -Port 8013
```

Mở `http://localhost:8013`. Đăng nhập bằng `driver` hoặc `engineer`, chọn video
trong library hoặc upload video được cho phép, sau đó bắt đầu phân tích.

## 8.2. Kịch bản Driver nên trình diễn

1. Chọn video có traffic bình thường.
2. Cho thấy object/lane/sign overlay.
3. Chờ một FCW/VRU/cross-traffic event để nghe Piper và thấy banner.
4. Chọn `dashcam_vietnam_traffic_multi.mp4` để trình diễn Traffic Context v1:
   giao thông đông an toàn chỉ tạo context beep nhẹ/HUD, còn path conflict thật
   mới được audio warning.
5. Pause, tua tới event, resume và đổi sang video khác để chứng minh session
   state không bị lẫn.
6. Nhấn mạnh hệ thống không phanh/đánh lái; tài xế vẫn là người quyết định.

## 8.3. Kịch bản Engineer nên trình diễn

1. Đăng nhập engineer.
2. Hiển thị model/profile/provider, Process FPS, E2E P50/P95 và warmup.
3. Mở một event để xem risk, confidence, track/lane/context và lifecycle/audio.
4. Cho thấy event bị `hud_only` trong dense không biến mất khỏi Event History.
5. Nếu bật SLM có chủ đích, chỉ cho thấy explanation ở Engineer Console:

```powershell
$env:ROADWATCH_SLM_ENABLED = "1"
.\scripts\start.ps1 -Port 8013
```

SLM có thể chậm vì CPU; không bật trong kịch bản cần chứng minh cảnh báo critical
realtime. Nếu SLM không ready, hiển thị `fallback` và giải thích rằng warning
deterministic vẫn hoạt động.

## 8.4. Thông điệp pitch chính

> RoadWatch biến camera/video thành một hệ thống cảnh báo có bằng chứng: nhìn
> thấy, theo dõi, đánh giá nguy cơ, chọn mức cảnh báo, nói tiếng Việt và lưu lại
> lý do. Hôm nay chúng tôi chứng minh được core và HMI bằng replay/local/AAOS;
> bước tích hợp tiếp theo là camera thật, calibration, telemetry và closed-course
> validation với OEM.

---

# 9. Hướng tới triển khai thực tế trên ô tô

## 9.1. Kiến trúc được đề xuất

```text
Camera trước thật
   │ USB/CSI/Camera2/EVS adapter
   ▼
Edge Agent trên Jetson/edge compute box
   ├─ perception ONNX/TensorRT
   ├─ tracking/risk/Traffic Context
   ├─ Piper/beep local
   └─ AlertEvent qua local gRPC/IPC
              ▼
AAOS head unit
   ├─ Driver HUD
   ├─ audio focus/HMI
   ├─ read-only telemetry
   └─ health/control display
              │ opt-in, non-critical
              ▼
GCP MLOps/evaluation
   ├─ evidence/HITL
   ├─ model registry/OTA package
   └─ monitoring
```

## 9.2. Điều kiện cần từ OEM/hardware

- Camera FOV, mounting position và frame timing.
- Camera2/EVS/CSI access, permission và lifecycle.
- Vehicle speed, yaw rate, turn signal hoặc radar nếu muốn tăng chất lượng risk.
- Audio route/audio focus chính thức.
- Calibration intrinsic/extrinsic và ground-plane.
- Thermal, RAM, power budget và watchdog.
- Safety driver, closed-course và quy trình hazard analysis.
- Chính sách ký model, OTA và rollback.

## 9.3. VinFast claim boundary

RoadWatch có thể giới thiệu là **kiến trúc sẵn sàng để tích hợp** vào màn hình
AAOS/edge của xe VinFast khi được cấp API và hardware. Không được nói đã tích
hợp VF5/VF6/VF7/VF8/VF9 thật nếu chưa có camera/OEM permission/test evidence.

---

# 10. Các vấn đề còn thiếu và kế hoạch sau Demo Day

## P0 — Khóa demo và regression

- Freeze model/profile/audio/UI đang dùng.
- Chạy full test/regression hiện tại trên máy demo.
- Đo riêng display FPS và process FPS.
- Ghi hash model/voice/frontend build ID.
- Chuẩn bị fallback `Traffic Context off`, Piper, YOLOP và baseline object.

## P1 — Ground truth và perception quality

- Hoàn tất timestamp GT cho FCW/VRU/cut-in/cross-traffic/LDW.
- Review night/rain/dense/multi-lane với double-review.
- Mở rộng hard negatives: xe đi gần nhưng an toàn, vỉa hè, watermark, biển
  không liên quan ego lane.
- Chỉ promote object/lane candidate nếu critical recall không giảm và false
  alert không tăng.

## P2 — Lane và geometry

- Tạo lane GT có lane count, ego boundaries, visibility, marking type và
  uncertainty.
- Benchmark YOLOP, UFLDv2 và TwinLiteNet+ trên cùng split.
- Cải thiện multi-lane/low-light trước khi bật LDW mạnh hơn.
- Không dùng model có FPS tốt nhưng boundary/LDW false alert kém.

## P3 — Camera calibration và telemetry

- Dùng chessboard/AprilTag để đo intrinsic/extrinsic.
- Xác định ground plane/road homography.
- Thêm read-only ego speed/yaw rate adapter.
- Sau đó mới đánh giá TTC vật lý và lead braking định lượng.

## P4 — Edge/Jetson

- Build ARM64 image trên target-compatible environment.
- Export ONNX và TensorRT FP16; chỉ thử INT8 sau khi có calibration set.
- Đo sustained FPS, E2E P95, VRAM/RAM, power, nhiệt độ trong tối thiểu 30 phút.
- Có watchdog và rollback nếu model/provider degraded.

## P5 — AAOS/OEM

- Thay replay bằng Camera2/EVS adapter khi có quyền.
- Xác minh audio focus, UX restriction, lifecycle, boot/resume và screen density.
- Tách Edge Agent khỏi head unit nếu tài nguyên màn hình xe không đủ.

## P6 — GCP/MLOps production shape

- Signed/resumable upload, quota, rate limit và retention policy.
- Worker bất đồng bộ cho video dài; Cloud Storage làm source artifact.
- Cloud SQL/registry/observability nếu cần fleet/evidence thật.
- Canary model, signed manifest, OTA rollback và audit trail.

## P7 — Safety engineering

- Hazard analysis, misuse cases, SOTIF/ISO 26262 alignment phù hợp phạm vi.
- Closed-course protocol có safety driver/observer/nút tắt audio.
- Đánh giá miss, false alarm, warning time và human factors.
- Không quảng bá thương mại cho tới khi quy trình chứng nhận phù hợp hoàn tất.

---

# 11. Changelog và cơ chế cập nhật báo cáo

Báo cáo này được thiết kế để cập nhật mà không phải viết lại từ đầu. Khi có
thay đổi, thêm một entry theo mẫu:

```markdown
## YYYY-MM-DD — <mã phiên bản/task>

- Thay đổi:
- Model/profile/provider:
- Dataset/video/split:
- Metric trước:
- Metric sau:
- Evidence file/link:
- Quality gate:
- Quyết định: active | candidate | rejected | blocked
- Fallback/rollback:
- Người xác nhận:
```

Quy tắc cập nhật:

1. Không ghi “đã tốt hơn” nếu chưa có cùng video/split/runtime để so sánh.
2. Không chuyển Candidate thành Active nếu chưa có promotion gate.
3. Mọi model/voice lớn phải ghi hash và giữ ngoài Git.
4. Mọi thay đổi critical path phải có unit test và replay evidence.
5. Mọi thay đổi UI/audio phải kiểm tra E2E, không chỉ chụp giao diện.
6. Mọi claim xe thật phải ghi rõ hardware/API/calibration đã có hay còn block.
7. Khi cập nhật code, ghi `PRE-WORK` trước và `POST-WORK` sau trong
   `roadwatch/AGENTS.md`.

## Các mốc đã hoàn thành cần giữ lại

- `Traffic Context v1` đã có policy, mode off/shadow/enforce và fallback.
- Piper `vi_VN-vais1000-medium` là release baseline; VieNeu là candidate.
- Object baseline được giữ do candidate chưa vượt event gate.
- YOLOP được giữ do lane candidate chưa vượt quality/latency gate.
- SLM chỉ là Engineer-only asynchronous explanation.
- AAOS/GCP là deployment planes khác nhau; edge mới là critical path tương lai.
- Backup, model registry, reports và test evidence phải được giữ khi refactor.

---

# 12. Kết luận

RoadWatch đã đi từ một ý tưởng “camera nhận diện rồi beep” thành một prototype
có hình dạng của một sản phẩm kỹ thuật thực tế:

```text
Perception đa model
  → temporal evidence
  → deterministic risk
  → traffic-aware alert policy
  → canonical Vietnamese audio/HUD
  → Engineer audit/SLM explanation
  → local/AAOS/GCP deployment boundary
```

Giá trị lớn nhất hiện tại là ba yếu tố cùng xuất hiện trong một hệ thống:

1. **Bài toán đúng:** giao thông hỗn hợp Việt Nam và alert fatigue.
2. **Cách giải quyết có kiểm soát:** model độc lập, rule deterministic,
   evidence, selective audio và rollback.
3. **Đường triển khai có thật:** local offline hôm nay, AAOS replay cho HMI,
   GCP public cho đánh giá và edge/OEM adapter cho bước tiếp theo.

RoadWatch đủ cơ sở để trình bày như một **production-shaped edge warning
prototype**. Để trở thành sản phẩm triển khai trên xe thật, các phần còn thiếu
không nằm ở việc thêm một banner đẹp hơn, mà ở camera access, calibration,
telemetry, edge benchmark, closed-course validation và safety/OEM process. Việc
chỉ rõ các ranh giới đó giúp doanh nghiệp đánh giá đúng năng lực kỹ thuật và cũng
cho thấy lộ trình phát triển tiếp theo là cụ thể, đo được và có thể triển khai.

## Tài liệu nguồn trong repo

- [`README.md`](../README.md) — cài đặt, chạy demo, account và model assets.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — pipeline và process boundary.
- [`USER_STORY_REPORT.md`](USER_STORY_REPORT.md) — personas, user stories và evidence.
- [`TECHNOLOGY_STACK_AND_DIFFERENTIATORS.md`](TECHNOLOGY_STACK_AND_DIFFERENTIATORS.md) — technology selection.
- [`MODEL_PROMOTION.md`](MODEL_PROMOTION.md) — model gate và rollback.
- [`VALIDATION.md`](VALIDATION.md) — benchmark/validation snapshot.
- [`TRAFFIC_CONTEXT_ALERT_POLICY.md`](TRAFFIC_CONTEXT_ALERT_POLICY.md) — dense traffic policy.
- [`SLM_INTEGRATION.md`](SLM_INTEGRATION.md) — SLM boundary và fallback.
- [`UI_METRICS_AND_CLOUD_FLOW.md`](UI_METRICS_AND_CLOUD_FLOW.md) — metrics và cloud flow.
- [`UNIFIED_DEPLOYMENT_ARCHITECTURE.md`](UNIFIED_DEPLOYMENT_ARCHITECTURE.md) — local/AAOS/GCP/edge architecture.
- [`SAFETY.md`](SAFETY.md) — safety scope và closed-course protocol.
- [`AGENTS.md`](../AGENTS.md) — development rules and work log.
