# RoadWatch SLM Integration

## Mục đích

RoadWatch có một lớp Small Language Model (SLM) tùy chọn để giải thích kỹ thuật
cho các event đã được hệ thống deterministic chấp nhận. SLM không phải thành
phần safety-critical và không được quyền tạo, sửa, loại bỏ hoặc nâng cấp cảnh
báo.

```text
Perception → Tracking/Kinematics → Risk Engine → Traffic Context v1
→ AlertGovernor → Canonical Event → Audio/HUD
                                      └→ SLM explanation (async, Engineer only)
```

Thiết kế này giữ nguyên các công việc đã có: Traffic Context v1, selective
audio, Piper tiếng Việt, audio single-owner, UI v4, playback controls và
actuator guardrail.

## Model và tài sản

Candidate hiện được hỗ trợ là Qwen2.5-0.5B-Instruct dạng ONNX Q4F16, dùng
`onnxruntime` và `tokenizers`. Khi có asset, đặt đúng cấu trúc:

```text
roadwatch/models/qwen2.5-0.5b/config.json
roadwatch/models/qwen2.5-0.5b/tokenizer.json
roadwatch/models/qwen2.5-0.5b/onnx/model_q4f16.onnx
```

Không commit các file model lớn vào Git. Các hash tham chiếu từ nhánh tích hợp
P-162 được lưu để đối chiếu khi tải asset:

```text
config.json:       777e01f0fbb3346eb229cb6fb278ed6533c1e4dcb9ebf4bed0f6e94ef17fa1b5
tokenizer.json:    a8506e7111b80c6d8635951a02eab0f4e1a8e4e5772da83846579e97b16f61bf
model_q4f16.onnx:  b11c1dd99efd57e6c6e5bc4443a019931a5fbd5dd500d48644d8225f5ce0b2cb
```

Nếu thiếu asset hoặc package, hệ thống vẫn chạy và event được đánh dấu
`slm_status=fallback` hoặc `disabled`; không ảnh hưởng beep, TTS, banner hay
perception.

## Cấu hình

Mặc định trong `configs/default.json`:

```json
{
  "slm": {
    "enabled": false,
    "model_dir": "qwen2.5-0.5b",
    "device": "auto",
    "max_new_tokens": 128,
    "queue_size": 8,
    "max_queue_age_seconds": 30.0
  }
}
```

Các biến môi trường tương ứng:

```powershell
$env:ROADWATCH_SLM_ENABLED = "1"
$env:ROADWATCH_SLM_MODEL_DIR = "qwen2.5-0.5b"
$env:ROADWATCH_SLM_DEVICE = "auto"
$env:ROADWATCH_SLM_MAX_NEW_TOKENS = "128"
$env:ROADWATCH_SLM_QUEUE_SIZE = "8"
```

`device=auto` chọn CUDA nếu runtime có CUDA, sau đó CPU. DirectML không được
chọn tự động cho SLM Q4F16 vì trên một số stack AMD Windows session vẫn mở
được nhưng greedy decoding có thể sinh output sai; chỉ thử DirectML có chủ đích
với `ROADWATCH_SLM_DEVICE=directml` sau khi đã kiểm tra output.

Trong lần đầu kiểm thử nên bật SLM có chủ đích sau khi đã đặt asset. Bản demo
release có thể để mặc định `false` để bảo toàn latency và đường fallback.

## Luồng và guardrails

- Chỉ event thuộc taxonomy được hỗ trợ mới được đưa vào queue.
- Queue là FIFO giới hạn tối đa 8 item; item chờ quá 30 giây bị bỏ qua. Khi có
  burst event, worker ưu tiên giữ event mới hơn và đánh dấu event bị thay thế là
  `queue_replaced`.
- Model được lazy-load trên worker thread, không block perception, AlertGovernor,
  HUD, beep hoặc Piper.
- Payload chỉ gồm evidence đã có: loại đối tượng, vị trí, track, risk,
  confidence, ngưỡng và số frame xác nhận.
- Validator từ chối câu nhiều dòng, câu không có evidence, suy diễn TTC/khoảng
  cách/tốc độ vật lý, tên khóa JSON hoặc lời khuyên hành động.
- Kết quả chỉ cập nhật các trường `slm_*` của event và hiển thị ở Engineer
  Console; Driver không đọc phần giải thích này.
- Session mới, stop, seek, đổi video và loop đều xóa queue pending.

Các trạng thái event:

```text
disabled  → SLM chưa bật
pending   → đang chờ worker
ready     → explanation đã được validate
fallback  → event vẫn hợp lệ nhưng SLM không sinh được explanation
```

## Chạy và quan sát

```powershell
cd roadwatch
pip install -r requirements.txt
.\scripts\start.ps1
```

Khi SLM được bật, Engineer Console hiển thị trạng thái model, queue, số lần
generated/failed và explanation gần nhất. API cũng trả về:

```text
GET /api/health  → slm
GET /api/status  → slm và event.slm_*
```

Event History hiển thị thêm `SLM:pending|ready|fallback|disabled`, giúp phân
biệt rõ explanation lỗi với cảnh báo deterministic.

## Kiểm thử và promote

Trước khi bật candidate cho cloud hoặc AAOS:

1. Chạy unit test SLM và storage migration.
2. Kiểm tra API vẫn trả `slm` khi SLM disabled.
3. Bật SLM trong một session local, kiểm tra explanation chỉ xuất hiện ở
   Engineer Console.
4. Kiểm tra event critical vẫn phát đúng một lần qua audio owner hiện hành.
5. Seek, pause, stop và đổi video; bảo đảm không có explanation cũ xuất hiện ở
   session mới.
6. Đo generation latency, queue drop và E2E P95; SLM không được làm tăng
   latency của perception/HUD/audio quá 10%.

SLM chỉ được coi là candidate đạt khi test contract, fallback và latency pass.
Nếu fail, giữ SLM `disabled`, không rollback Traffic Context v1 hoặc Piper.

## Nguồn tích hợp

Thiết kế được port từ `feature/slm-integration` của repo P-162, nhưng code hiện
tại đã được ghép vào pipeline RoadWatch mới hơn thay vì ghi đè toàn bộ thư mục.
Nhánh tham chiếu gồm tài liệu, worker ONNX và test contract; backup trước khi
tích hợp được lưu ở commit `797468c9eb93fdf645e19d10e980d31302175e1e` trên
repo P-162/main.

SLM không thay thế fine-tuning perception, không phải hệ thống tự lái và không
được dùng để tuyên bố RoadWatch đã đạt chứng nhận an toàn.
