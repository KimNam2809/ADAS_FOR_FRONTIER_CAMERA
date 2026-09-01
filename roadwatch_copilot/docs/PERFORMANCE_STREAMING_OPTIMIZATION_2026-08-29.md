# RoadWatch — Performance và Video Streaming

## Kết luận chẩn đoán

`Processed FPS` và FPS người dùng nhìn thấy là hai đại lượng khác nhau.
`Processed FPS` chỉ đếm số frame đã đi qua perception, tracking và risk engine.
Trước thay đổi này, cùng một thread còn phải annotate và encode JPEG, trong khi
frame bị sampling skip bị bỏ khỏi stream. Vì vậy một pipeline có E2E khoảng
119–189 ms vẫn có thể tạo cảm giác video chỉ chạy 15–20 FPS hoặc bị đứng hình.

Việc bổ sung HUD không phải nguyên nhân chính: HUD chỉ dùng dữ liệu `/api/status`
đã có, giới hạn năm sprite và không gọi model/API mới. Nút thắt là inference
serial, JPEG encode trong inference thread và stream lặp lại cùng một JPEG.

## Thay đổi đã triển khai

### 1. Display renderer bất đồng bộ

`backend/roadwatch/pipeline.py` hiện có một display worker riêng:

```text
capture → inference/risk thread ───────────────→ status/events
       └→ bounded latest-frame queue → annotate/JPEG worker → MJPEG
```

- Queue có đúng một phần tử để không tích lũy trễ.
- Khi encoder bận, frame cũ bị thay thế; inference không phải chờ encoder.
- Frame sampling skip chỉ được render để giữ chuyển động video, không chạy risk
  rule và không thể tạo cảnh báo mới.
- Metadata được copy trước khi giao cho renderer để tránh race với tracker.
- Seek, stop và đổi video xóa queue, reset JPEG sequence và giữ session identity.

### 2. Hiển thị phân biệt với inference

Metrics có thêm:

- `processed_fps`: FPS frame đã hoàn tất inference/risk, bắt đầu tính sau warmup.
- `display_fps`: FPS frame đã encode thành công cho màn hình.
- `display_frames`: số frame encoder đã phát hành.
- `display_dropped_frames`: số frame hiển thị bị thay thế do queue latest-frame.

MJPEG chỉ gửi JPEG mới theo sequence, không lặp vô hạn cùng một ảnh. Tốc độ
stream được giới hạn bởi `app.stream_fps` (mặc định 30, tối đa 60).

### 3. Chất lượng ảnh stream riêng

`app.jpeg_quality` giữ ý nghĩa tương thích cũ; stream dùng
`app.stream_jpeg_quality` (mặc định 60) để giảm CPU/băng thông mà không thay
đổi model hoặc chất lượng dữ liệu evidence. Có thể điều chỉnh bằng:

```powershell
$env:ROADWATCH_STREAM_FPS = "30"
$env:ROADWATCH_STREAM_JPEG_QUALITY = "60"
```

### 4. Bảo vệ DirectML trên AMD

Optional lane/sign async vẫn được hỗ trợ cho CPU/CUDA cloud/edge. Nếu runtime
phát hiện `DmlExecutionProvider`, worker tự động quay về serial mode vì driver
DirectML trên Windows có thể trả `DmlFusedNode` khi nhiều session chạy đồng
thời. Có thể yêu cầu async qua `ROADWATCH_ASYNC_OPTIONAL=1`, nhưng nó vẫn bị
chặn an toàn khi DirectML đang active. Đây là fallback chủ động, không phải
lỗi im lặng.

## Kết quả benchmark local

Video `test_video10.mp4`, Windows 11, AMD64/Ryzen + Radeon, audio tắt để tách
perception. Đây là replay benchmark, không phải chứng nhận Jetson.

| Phiên bản | Warmup | Processed FPS | Display FPS | E2E P50 | E2E P95 | Pipeline error |
|---|---:|---:|---:|---:|---:|---|
| Trước tối ưu | ~7,160 ms* | ~5.40* | Không tách đo | — | ~191.43 ms* | 0 |
| Sau display worker + lightweight skip overlay + 960px stream | 7,990.83 ms | 11.28 | **23.07** | **89.96 ms** | **149.91 ms** | 0 |

`*` là số đo benchmark trước đó với thời lượng/cadence khác; chỉ dùng làm
tham chiếu xu hướng, không phải A/B tuyệt đối cùng một process state.

Artifact đầy đủ:

- `reports/benchmark-performance-release-20260829.json`

Một lần thử `ROADWATCH_ASYNC_OPTIONAL=1` trên DirectML đã tái hiện lỗi
`DmlFusedNode`; sau đó đã thêm tự động serial fallback. Không dùng kết quả lỗi
đó làm benchmark release.

## Fallback và vận hành

### Quay về cách stream cũ

Nếu thiết bị/driver có vấn đề, có thể tắt các thay đổi hiển thị bằng runtime
override:

```powershell
$env:ROADWATCH_PUBLISH_SKIPPED_FRAMES = "0"
$env:ROADWATCH_STREAM_JPEG_QUALITY = "80"
```

Để rollback hoàn toàn, khôi phục các file `pipeline.py`, `metrics.py`,
`config.py`, `configs/default.json`, `frontend/src/api.ts`,
`frontend/src/main.tsx`, `frontend/src/styles.css` về commit/artifact backup
trước task này. Không cần và không được xóa model, media hay database.

### Diễn giải khi demo

- `Display FPS` cao hơn `Processed FPS` là có chủ đích: hình ảnh vẫn chuyển
  động mượt, còn cảnh báo chỉ được tính trên frame perception.
- `Sampling skip` không phải số frame bị lỗi; đó là cadence giảm tải đã cấu
  hình. `display_dropped_frames` mới phản ánh queue renderer bị thay thế.
- E2E P50/P95 hiện chỉ đo đường inference/risk, không cộng thời gian encode
  JPEG; đây là cách đo đúng để phát hiện model/rule chậm.
- Tối ưu này không biến laptop thành Jetson và không chứng minh 30 FPS trên
  phần cứng xe thật. Jetson Orin vẫn cần benchmark FP16/TensorRT trên thiết bị
  thật trước khi phát hành edge claim.
