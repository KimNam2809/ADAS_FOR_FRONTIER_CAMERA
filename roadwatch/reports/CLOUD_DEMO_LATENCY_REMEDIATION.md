# RoadWatch Cloud Demo Latency Remediation

Ngày kiểm tra: 2026-08-24

GCP project: `c3-roadwatch-162`

Service: `roadwatch-web`

Revision acceptance: `roadwatch-web-00010-rbk`

Fallback URL: `https://roadwatch-web-bx6lfekcba-as.a.run.app`

## Root cause

1. Cloud Run cũ dùng `concurrency=1`, `min=0`, `max=2` trong khi session và
   latest frame nằm trong RAM process. WebSocket/MJPEG/status có thể giữ hoặc đi
   sang instance khác, khiến UI không nhìn thấy đúng phiên.
2. Full CPU perception quá nặng cho public service. Một phiên thực tế ghi nhận
   object `89.117,27 ms`, lane `560.955,81 ms` và E2E frame đầu
   `650.359,62 ms`.
3. Background inference bị CPU throttling giữa các HTTP request.
4. UI chỉ mở MJPEG sau khi start nên không có progressive video trong thời gian
   model loading.
5. Khi đổi video, `frame_id` cũ chưa reset trước worker mới.

## Remediation

- Frontend dùng authenticated HTTP polling 500 ms thay vì phụ thuộc WebSocket.
- Thêm `/api/media/file` có path guard, token và HTTP Range để phát video ngay
  trong lúc model warmup; MJPEG overlay tiếp quản sau processed frame đầu.
- Export baseline đã promote thành `yolo11n_320.onnx`; artifact để trong GCS,
  không commit Git. Cloud fast profile chỉ chạy object detection; sign/lane/TTS
  vẫn chạy ở local/AAOS full profile.
- Cloud Run dùng 4 CPU, 8 GiB, concurrency 8, session affinity, min/max 1,
  startup CPU boost và CPU always allocated.
- Tách `warmup_ms` khỏi E2E latency; reset frame/source/tracks/signs/lane/JPEG
  trước mỗi session.
- Upload control được thiết kế lại theo cùng hệ màu/khoảng cách/card của RoadWatch.

## Before/after evidence

| Metric | Trước | Sau |
|---|---:|---:|
| Start API | Không khóa được ổn định | `189 ms` |
| Time-to-visible video | `> 5 phút` theo kiểm thử người dùng | tức thời qua source preview |
| Time-to-processed frames | frame đầu có thể `> 10 phút` | 6 frame sau `2 s` |
| E2E p50 | `31.027,96 ms` do người dùng ghi nhận | `34,24 ms` sau 37 sample |
| E2E p95 | `31.027,96 ms` do người dùng ghi nhận | `71,25 ms` sau 37 sample |
| Processed FPS | không tương tác được | `5,57` trên Cloud Run CPU |
| Object runtime | ONNX 640 / lỗi hoặc rất chậm | `yolo11n_320.onnx`, error `null` |
| Video Range | chưa có | HTTP `206`, `video/mp4` |
| Video switch reset | stale frame/session | `frame_id=0`, `source_time=0`, state rỗng |

## Scope và giới hạn

- Đây là benchmark public web replay, không phải benchmark edge realtime và
  không chứng minh an toàn thực địa.
- Cloud fast profile không chạy traffic sign, lane hoặc TTS. Full profile vẫn ở
  local/AAOS; muốn full perception mượt trên cloud cần GPU worker hoặc cached
  results bất đồng bộ.
- `min=1` và CPU always allocated tạo chi phí liên tục. Sau giai đoạn demo cần
  theo dõi billing hoặc hạ về scale-to-zero.
- Official domain `https://c3-roadwatch-162.io.vn`, signed resumable upload,
  cached-result worker và durable result plane vẫn chưa hoàn tất.
