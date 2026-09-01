# RoadWatch — Benchmark `models/layer1_test` vs production

**Ngày:** 28/08/2026  
**Loại kiểm thử:** inference-only, same-frame replay; không fine-tune local và không thay đổi production.

## Kết luận ngắn

Chưa có artifact mới nào đủ điều kiện thay thế model đang chạy. Bộ production hiện tại vẫn là lựa chọn tốt nhất **ở cấp hệ thống** vì đã có adapter, taxonomy, rule-engine contract và fallback:

| Nhánh | Production đang dùng | Artifact test tương ứng | Quyết định |
|---|---|---|---|
| Object / road users | `models/yolo11n.pt` | `layer1_test/BEST_detection_bdd7_ep18.pt` | Giữ `yolo11n`; candidate R&D |
| Traffic signs | `models/roadwatch_detector_v2.pt` + speed classifier | `layer1_test/BEST_signs_vn27_ep21.pt` | Giữ detector 82 lớp; candidate R&D |
| Lane / drivable area | `models/yolop_lane_detection_640.onnx` | `layer1_test/yolopv2.pt` | Giữ YOLOP ONNX; candidate chưa promote |

Thư mục còn có `layer1_test/yolo26s-depth.pt`. Đây là model **depth-only** (`task=depth`, lớp `depth`), không phải object detector hoặc lane detector nên không có cặp so sánh 1:1 trong benchmark này. Nó chỉ có thể được nghiên cứu như một head ước lượng chiều sâu bổ trợ.

## Phạm vi và phương pháp

- Video: `dashcam_vietnam_night.mp4`, `dashcam_vietnam_rain+night.mp4`, `dashcam_vietnam_traffic_multi.mp4`.
- Mỗi video lấy 24 timestamp cố định, tổng cộng 72 frame/model; loại trừ `dashcam_vietnam.mp4` vì dung lượng/thời lượng lớn.
- Cùng frame và cùng ngưỡng Ultralytics (`conf=0.25`, `iou=0.60`) cho hai detector.
- Object detector: PyTorch/Ultralytics CPU; baseline dùng input 640, candidate theo checkpoint `imgsz=960`.
- Sign detector: PyTorch/Ultralytics CPU; baseline dùng input 640, candidate theo checkpoint `imgsz=1280`.
- Lane baseline: ONNX Runtime CPU với adapter production; lane candidate: TorchScript CPU với YOLOPv2 vendor post-processing.
- Warm-up được chạy riêng và không đưa vào latency summary. Có lưu ảnh prediction/overlay để review trực quan.
- Không có ground-truth frame-level mới trong benchmark này. Vì vậy detection-rate, số box, confidence, mask IoU và quality là **proxy chẩn đoán**, không phải precision/recall/mAP/lane accuracy.

Dữ liệu chi tiết và từng timestamp nằm trong [JSON benchmark](./layer1_test_models_benchmark_20260828.json); ảnh review nằm trong [thư mục preview](./review/layer1-test-models/).

## 1. Object detection

| Metric trên 72 frame | `yolo11n` production | `BEST_detection_bdd7_ep18` | Nhận xét |
|---|---:|---:|---|
| Frame có detection | 65/72 (90.28%) | 71/72 (98.61%) | Candidate phủ nhiều frame hơn nhưng chưa chứng minh recall |
| Detection/frame | 5.92 | 12.58 | Candidate tạo nhiều box hơn 2.13 lần |
| Latency P50 | 38.764 ms | 139.111 ms | Candidate chậm hơn 3.59 lần trong cấu hình test |
| Latency P95 | 55.204 ms | 202.281 ms | Candidate vượt xa latency edge hiện tại |

Taxonomy baseline là COCO với các lớp riêng `car`, `bus`, `truck`, `motorcycle`, `person`; candidate có 7 lớp `person`, `two_wheeler`, `car`, `large_vehicle`, `tl_red`, `tl_yellow`, `tl_green`. Candidate không tách `bus/truck`, nên chưa thể đưa thẳng vào rule engine hiện tại.

Review preview cho thấy candidate có độ tin cậy cao hơn ở một số box nhưng cũng sinh nhiều box chồng lấn/over-detection trong cảnh đông xe. Số box tăng không thể được xem là tăng độ chính xác. Candidate chỉ đáng giữ để nghiên cứu adapter + taxonomy mapping, sau đó phải chạy event regression có ground truth cho FCW, VRU, cut-in, cross-traffic và false alert.

**Quyết định:** `KEEP BASELINE`; không promote candidate.

## 2. Traffic-sign detection

| Metric trên 72 frame | `roadwatch_detector_v2` production | `BEST_signs_vn27_ep21` | Nhận xét |
|---|---:|---:|---|
| Frame có detection | 12/72 (16.67%) | 25/72 (34.72%) | Candidate phát hiện nhiều hơn; chưa phân biệt TP/FP |
| Detection/frame | 0.22 | 0.56 | Candidate tạo nhiều detection hơn 2.50 lần |
| Latency P50 | 71.374 ms | 256.816 ms | Candidate chậm hơn 3.60 lần |
| Latency P95 | 101.795 ms | 322.250 ms | Không phù hợp để đưa thẳng vào realtime path hiện tại |

Production có 82 lớp và được nối với speed-digit classifier. Candidate có 27 lớp, gồm `speed_limit`, `min_speed_limit`, `no_entry`, `no_stopping_parking`, `direction_mandatory` và các lớp khác; không thay thế đầy đủ taxonomy 82 lớp. Candidate cũng không cung cấp speed value đã được xác minh bởi classifier trong benchmark này.

Candidate có thể hữu ích cho một nhánh sign detector nhẹ hơn sau khi có benchmark riêng trên các frame biển báo đã gán nhãn. Cần đặc biệt kiểm tra temporal confirmation, sign orientation, speed value 60/80 và false positive biển báo trước khi cho phép TTS.

**Quyết định:** `KEEP PRODUCTION 82-CLASS`; không promote candidate.

## 3. Lane / drivable area

| Metric proxy trên 72 frame | YOLOP production | YOLOPv2 candidate | Nhận xét |
|---|---:|---:|---|
| Lane latency P50 | 197.640 ms | 303.935 ms | Candidate chậm hơn 1.54 lần trên CPU |
| Lane latency P95 | 264.659 ms | 473.677 ms | Candidate chưa đáp ứng edge latency gate trong artifact hiện tại |
| Neutral lane coverage proxy | 0.0915 | 0.2411 | Không phải lane accuracy; mask rộng hơn không đồng nghĩa tốt hơn |
| Lane pixels/frame | 11,078 | 29,087 | Candidate tạo mask dày hơn |
| Drivable pixels/frame | 183,041 | 209,289 | Chỉ là diện tích mask, chưa có GT |
| Lane-mask IoU giữa hai model | — | 0.2953 | Hai model cho hình học khác nhau đáng kể |
| Drivable-mask IoU giữa hai model | — | 0.5703 | Có tương đồng một phần |

`yolopv2.pt` là TorchScript đa nhiệm với output contract `[pred, anchor_grid], drivable_logits, lane_logits`, không phải ONNX artifact mà backend production hiện tại có thể nạp trực tiếp. Nó cần adapter riêng và hiện benchmark bằng CPU. Do đó không được suy ra rằng candidate tốt hơn chỉ vì có lane mask/ drivable mask khác hoặc phủ nhiều pixel hơn.

**Quyết định:** `KEEP YOLOP ONNX`; giữ YOLOPv2 như candidate R&D/fallback research, chưa đưa vào Web/AAOS/GCP.

### Sanity check trên runtime AMD DirectML

Đã chạy lại cùng 72 timestamp với `--runtime directml`. Kết quả lane là:

| Runtime lane | P50 | P95 |
|---|---:|---:|
| YOLOP production + ONNX Runtime DirectML | 58.184 ms | 76.195 ms |
| YOLOPv2 candidate + TorchScript CPU | 302.070 ms | 435.972 ms |

Đây **không phải** phép so sánh backend công bằng vì candidate chưa có ONNX/DirectML adapter. Tuy nhiên nó xác nhận rằng artifact `yolopv2.pt` hiện tại chưa thể thay thế runtime AMD của RoadWatch. Muốn đánh giá lại cần export YOLOPv2 sang ONNX, xác minh output contract rồi benchmark `DirectML vs DirectML`.

## 4. Artifact depth

`yolo26s-depth.pt` load được bằng Ultralytics với `task=depth`, `names={0: "depth"}`. Nó không có bounding-box taxonomy và không xuất lane/drivable mask, nên không thể thay thế bất kỳ model nào trong ba nhánh trên. Không benchmark nó như object detector để tránh kết luận sai.

Smoke inference trên một frame bằng CPU hoàn tất trong `2085.870 ms`, trả về `boxes=None`; đây là kiểm tra khả năng load/chạy, không phải phép so sánh chất lượng với các head production.

## 5. Fallback và thay đổi production

- `configs/default.json`, `configs/release_manifest.json` và `configs/model_registry.json` không bị đổi active model.
- Không thêm candidate vào Perception Orchestrator.
- Rollback/giữ release hiện tại vẫn là:

```text
object       -> yolo11n / baseline_coco
traffic sign -> roadwatch_detector_v2 + speed_digits_v2
lane         -> yolop_lane_detection_640.onnx
```

Script benchmark có thể chạy lại bằng:

```powershell
$py = Resolve-Path 'roadwatch/.venv/Scripts/python.exe'
& $py 'roadwatch/scripts/benchmark_layer1_test_models.py' `
  --runtime cpu `
  --samples-per-video 24 `
  --output 'roadwatch/reports/layer1_test_models_benchmark_20260828.json'
```

## 6. Gate tiếp theo nếu muốn promote candidate

1. Gán ground truth cùng split cho 3 điều kiện day/night/rain và cảnh đông xe.
2. Với object: đo mAP50-95, class recall, critical-event recall, direction accuracy và false alerts/phút sau temporal tracking.
3. Với sign: đo recall/precision theo 27 lớp, speed-value accuracy, orientation/relevance và false TTS trên hard negatives.
4. Với lane: đo lane-count accuracy, ego-boundary F1, night/rain recall, LDW false alerts và latency trên đúng runtime DirectML/CUDA/TensorRT đích.
5. Chỉ promote khi candidate không làm giảm critical recall, không vượt false-alert budget và có adapter/rollback độc lập.
