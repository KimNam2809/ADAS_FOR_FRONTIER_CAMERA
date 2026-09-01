# YOLO11S Drive Scene Carla vs YOLO11n Baseline — Replay Report

## Phạm vi

- Candidate: `UNIC0RN-Zhu/yolo11s-drive-scene-carla-v1`, Hugging Face revision
  `860985a2bff65d0a25c2805f8ac18094d7040a0b`.
- Candidate classes: `vehicle`, `pedestrian`, `cyclist`, `motorcycle`,
  `traffic_light`, `traffic_sign`, `road_barrier`, `traffic_cone`.
- Baseline: `roadwatch/models/yolo11n.onnx`/`models/yolo11n.pt`.
- Candidate đã được tải vào `roadwatch/models/yolo11s-drive-scene/`; `best.pt`
  khớp SHA-256 trong upstream `SHA256SUMS`.
- Candidate ONNX được export local từ `best.pt` với input cố định `1x3x640x640`.
- Video: `dashcam_vietnam_night.mp4`,
  `dashcam_vietnam_rain+night.mp4`, `dashcam_vietnam_traffic_multi.mp4`.
  `dashcam_vietnam.mp4` được loại trừ theo quy tắc replay trước đó vì là file
  nặng nhất.
- Điều kiện: cùng frame, sampling `1 FPS`, confidence `0.25`, IoU `0.60`,
  CPUExecutionProvider, batch `1` cho ONNX.
- Tổng cộng: `982` frame mẫu. Không có ground truth frame-level; kết quả là
  diagnostic replay, không phải mAP, event recall hoặc quyết định promotion.

## Integrity và published reference

Candidate upstream công bố:

```text
precision  = 0.6786
recall     = 0.4974
mAP50      = 0.5405
mAP50-95   = 0.2643
```

Các số trên được đo trên dataset của tác giả, không được so sánh trực tiếp
với metric RoadWatch nếu chưa chạy cùng split và cùng ground truth.

## Same-frame ONNX replay

| Video | Frames | Candidate detections | Baseline detections | Candidate FPS | Baseline FPS |
|---|---:|---:|---:|---:|---:|
| Night | 181 | 1.717 | 568 | 9,681 | 23,771 |
| Rain + night | 112 | 1.071 | 418 | 10,681 | 23,528 |
| Traffic multi | 689 | 13.465 | 8.241 | 10,753 | 24,188 |
| **Tổng/gộp** | **982** | **16.253** | **9.227** | **10,530** | **24,034** |

Candidate đạt throughput gộp khoảng `56,2%` thấp hơn baseline trong replay CPU
này. Đây không phải benchmark Jetson/AMD GPU, nhưng là tín hiệu candidate chưa
phù hợp để thay baseline trong runtime cần realtime.

### Presence theo lớp của candidate

| Video | vehicle | pedestrian | cyclist | motorcycle | traffic_light | traffic_sign |
|---|---:|---:|---:|---:|---:|---:|
| Night | 0,9448 | 0,1436 | 0,5249 | 0,5525 | 0,3646 | 0,6851 |
| Rain + night | 0,9732 | 0,3571 | 0,4286 | 0,4196 | 0,2589 | 0,3571 |
| Traffic multi | 1,0000 | 0,7649 | 0,9623 | 0,9695 | 0,6386 | 0,6284 |

Presence chỉ cho biết có ít nhất một detection trong frame, không chứng minh
detection đó đúng. `road_barrier` và `traffic_cone` không xuất hiện trong các
frame mẫu của replay; không được hiểu là model không hỗ trợ hai lớp này.

## Phân tích kỹ thuật

### Điểm có tiềm năng

- Candidate có semantic classes phù hợp để nghiên cứu `pedestrian`, `cyclist`,
  `motorcycle`, `traffic_light` và `traffic_sign`.
- Domain mix BDD100K/nuScenes/CARLA có thể giúp thử nghiệm scene diversity.
- `road_barrier` và `traffic_cone` là các lớp bổ sung hữu ích cho hard-negative
  hoặc scene-understanding nếu sau này có requirement tương ứng.

### Điểm chưa thể thay baseline

- `vehicle` gộp car/bus/truck, trong khi Risk Engine và nội dung TTS RoadWatch
  cần phân biệt loại phương tiện. Mapping ngược từ `vehicle` sang ba loại là
  không xác định và có thể làm sai FCW/lead-braking/copy cảnh báo.
- `pedestrian`/`cyclist` không tương đương 1:1 với taxonomy `person`/`rider`;
  cần annotation và mapping policy riêng trước khi đưa vào orchestrator.
- Candidate không nhận diện loại biển báo Việt Nam hay chữ số tốc độ; lớp
  `traffic_sign` không thể thay `roadwatch_detector_v2` + speed classifier.
- Preview cho thấy nhiều box chồng lấn và nhiều detection generic ở cảnh tối,
  nên phải kiểm tra temporal stability, NMS và false-alert/event metrics bằng
  ground truth trước khi cho phép dùng trong alert path.
- Throughput CPU replay `10,530 FPS` thấp hơn baseline `24,034 FPS`; chưa đạt
  mục tiêu realtime hiện tại và chưa có benchmark DirectML/TensorRT/Jetson.

## Quyết định

`R&D / diagnostic only — KHÔNG PROMOTE`.

Candidate được lưu riêng ở `roadwatch/models/yolo11s-drive-scene/` và không thay
model production, Web, AAOS hoặc GCP. Baseline tiếp tục là model active.

## Hướng tiếp theo nếu muốn nghiên cứu candidate

1. Tạo adapter taxonomy có confidence/reject state, không map mù `vehicle` thành
   `car`.
2. Đánh giá trên bộ frame có ground truth cho person/rider/motorcycle,
   night/rain, cut-in và cross-traffic.
3. Đo event recall, false alerts/minute, direction accuracy và latency P95.
4. Chỉ cân nhắc fine-tune tiếp candidate nếu semantic mapping và event metrics
   vượt baseline; nếu không, giữ nó làm scene-context auxiliary model.

