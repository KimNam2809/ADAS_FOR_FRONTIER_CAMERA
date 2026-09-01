# RoadWatch Lane Benchmark — TwinLiteNet+ Medium ONNX vs YOLOP

**Ngày:** 2026-08-28  
**Phạm vi:** export ONNX và replay evaluation-only trên máy local; không thay
YOLOP production, không train local và không promote vào Web/AAOS/GCP.

## 1. Kết luận

TwinLiteNet+ Medium đã được export sang ONNX static shape và vượt qua các gate
kỹ thuật: ONNX checker, ONNX Runtime load và PyTorch–ONNX output parity.
Benchmark cùng ONNX Runtime CPU cho thấy candidate nhanh hơn YOLOP rõ rệt.

**Quyết định:** tiếp tục giữ candidate ở trạng thái `R&D / diagnostic only`.
Chưa promote vì chưa có ground truth lane/drivable-area, lane-count accuracy,
boundary F1 hoặc LDW event regression trên cùng test split.

YOLOP production vẫn giữ nguyên:

```text
models/yolop_lane_detection_640.onnx
```

## 2. Artifact export

Checkpoint nguồn:

```text
models/twinlitenetplus_medium.pth
```

ONNX candidate:

```text
models/twinlitenetplus_medium.onnx
```

Thông tin export:

| Thuộc tính | Giá trị |
|---|---|
| Config | Medium |
| Parameters | 478,876 |
| Input | `1x3x384x640`, RGB float32, giá trị `[0,1]` |
| Output 1 | `drivable_logits`, `1x2x384x640` |
| Output 2 | `lane_logits`, `1x2x384x640` |
| Opset | 17 |
| Graph | Static spatial shape |
| ONNX Runtime provider | `CPUExecutionProvider` |
| ONNX SHA-256 | `62381628607522d7e8813f4c33cfd9633afebfee9ef9cce6a63809ef0b381717` |

Input 640x384 được chọn vì các video dashcam hiện tại là 16:9 và preprocessing
letterbox upstream tạo tensor đúng shape này. Với aspect ratio khác cần export
một artifact static shape riêng; không giả định graph dynamic hiện tại hỗ trợ
mọi kích thước.

## 3. Export và parity gate

Script tái lập:

```text
scripts/export_twinlitenetplus_onnx.py
```

Lệnh:

```powershell
roadwatch/.venv/Scripts/python.exe roadwatch/scripts/export_twinlitenetplus_onnx.py `
  --height 384 `
  --width 640
```

Kết quả:

| Gate | Kết quả |
|---|---|
| PyTorch checkpoint load | PASS |
| ONNX graph export | PASS |
| `onnx.checker.check_model` | PASS |
| ONNX Runtime load | PASS |
| Output shape | PASS |
| Max absolute output error | `9.2387e-05` |
| Mean absolute output error | `2.2581e-06` |
| Parity threshold | `max_abs <= 1e-04` |
| Parity decision | PASS |

Artifact kiểm chứng:

```text
models/twinlitenetplus_medium.export.json
```

Export dynamic spatial shape đã được thử trước đó nhưng bị PyTorch ONNX
exporter từ chối tại `adaptive_avg_pool2d` khi input size không truy cập được.
Static export là lựa chọn ổn định và phù hợp hơn với edge deployment hiện tại.

## 4. Benchmark ONNX công bằng hơn

Script:

```text
scripts/benchmark_twinlitenetplus_onnx_vs_yolop.py
```

Điều kiện:

- 41 timestamp thuộc 7 video RoadWatch.
- Cùng frame, cùng CPU và cùng ONNX Runtime CPU provider.
- YOLOP: adapter hiện tại, input 640x640, RGB ImageNet normalization.
- TwinLiteNet+ ONNX: letterbox 640x384, RGB `/255.0`, unpad mask về frame gốc.
- Warmup 2 lượt trước khi thu latency.
- Không dùng kết quả này để tuyên bố mIoU hoặc lane-count accuracy.

Kết quả:

| Chỉ số | YOLOP | TwinLiteNet+ Medium ONNX | Chênh lệch |
|---|---:|---:|---:|
| Samples | 41 | 41 | Cùng tập |
| Latency P50 | 203.254 ms | 76.815 ms | Candidate nhanh hơn 62.2% |
| Latency P95 | 254.416 ms | 90.080 ms | Candidate nhanh hơn 64.6% |
| Latency trung bình | 211.194 ms | 78.848 ms | Candidate nhanh hơn |
| Mean lane-quality proxy | 0.4772 | 0.5167 | Candidate nhỉnh hơn |
| Mean temporal lane-mask IoU | 0.0567 | 0.0710 | Diagnostic, candidate nhỉnh hơn |
| Inference/runtime error | 0 | 0 | PASS |

JSON đầy đủ:

```text
reports/twinlitenetplus_medium_onnx_vs_yolop.json
```

Ảnh overlay cùng frame:

```text
reports/review/twinlitenetplus-onnx-vs-yolop/
```

### 4.1. Replay trên AMD DirectML

Máy local có `DmlExecutionProvider`, vì vậy đã chạy thêm một profile AMD
DirectML với cùng provider cho YOLOP và candidate:

| Chỉ số | YOLOP | TwinLiteNet+ Medium ONNX | Chênh lệch |
|---|---:|---:|---:|
| Samples | 41 | 41 | Cùng tập |
| Provider | DmlExecutionProvider | DmlExecutionProvider | Cùng provider |
| Latency P50 | 58.780 ms | 34.228 ms | Candidate nhanh hơn 41.8% |
| Latency P95 | 62.611 ms | 36.408 ms | Candidate nhanh hơn 41.8% |
| Latency trung bình | 58.867 ms | 34.212 ms | Candidate nhanh hơn |
| Mean lane-quality proxy | 0.4772 | 0.5167 | Giống profile CPU |
| Mean temporal lane-mask IoU | 0.0567 | 0.0710 | Giống profile CPU |
| Runtime error | 0 | 0 | PASS |

JSON DirectML:

```text
reports/twinlitenetplus_medium_onnx_vs_yolop_directml.json
```

Đây là bằng chứng tốt cho khả năng chạy candidate trên laptop AMD hiện tại,
nhưng vẫn chưa phải benchmark Jetson/TensorRT.

## 5. Diễn giải đúng kết quả

Kết quả latency là tín hiệu rất tích cực cho edge vì candidate có model nhỏ và
ONNX Runtime xử lý nhanh hơn trong môi trường CPU hiện tại. Tuy nhiên:

1. `lane-quality proxy` chỉ là tỷ lệ pixel lane ở vùng dưới ảnh; nó không phải
   lane IoU và không chứng minh boundary đúng.
2. `temporal lane-mask IoU` được tính giữa các timestamp cách nhau nhiều giây;
   nó chưa thay thế test contiguous-frame để đo flicker.
3. Candidate dùng input `640x384`, còn YOLOP adapter hiện tại dùng `640x640`;
   vì vậy chênh lệch latency phản ánh cả input area thấp hơn của candidate,
   không phải chỉ riêng kiến trúc. Cần thêm profile cùng input shape trước khi
   dùng số liệu này để so sánh FLOPs thuần túy.
4. Benchmark chưa có nhãn ground truth nên chưa thể biết mask nào đúng hơn.
5. Kết quả CPU/DirectML không đại diện trực tiếp cho NVIDIA CUDA hoặc
   Jetson TensorRT.
6. Chưa đo được lane-count accuracy, ego-boundary F1, LDW recall và false
   LDW/phút.

## 6. Liên hệ với số liệu upstream

Repository và bài báo upstream công bố TwinLiteNet+ Medium có 0.48M parameters,
4.63G FLOPs, drivable mIoU 92.0% và lane IoU 32.3% trên protocol/dataset của
họ. Đây không phải số liệu đo trên RoadWatch. Nguồn: [repository chính thức](https://github.com/cream1nve02/TwinLiteNetPlus)
và [bài báo TwinLiteNet+](https://arxiv.org/html/2403.16958v6).

## 7. Quyết định rollout và fallback

Không có thay đổi production trong task này. Candidate ONNX chỉ được phép dùng
cho benchmark/R&D cho đến khi hoàn thành:

- test split lane/drivable có ground truth;
- lane IoU/F1, drivable mIoU, lane-count accuracy và boundary F1;
- contiguous-frame LDW regression trong day/night/rain/multi-lane;
- benchmark target edge, DirectML/CUDA và TensorRT khi có môi trường;
- kiểm tra Perception Orchestrator, quality lock và rollback.

Nếu candidate fail bất kỳ gate nào, runtime tiếp tục dùng:

```text
models/yolop_lane_detection_640.onnx
```

Candidate ONNX không được tự động đưa vào Web, AAOS hoặc GCP.
