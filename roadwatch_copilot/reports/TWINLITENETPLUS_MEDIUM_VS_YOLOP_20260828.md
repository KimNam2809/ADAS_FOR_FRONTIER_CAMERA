# RoadWatch Lane Benchmark — TwinLiteNet+ Medium vs YOLOP

**Ngày:** 2026-08-28  
**Phạm vi:** benchmark/evaluation-only trên máy local; không thay model lane
production, không train local và không promote vào Web/AAOS/GCP.

## 1. Tóm tắt quyết định

`TwinLiteNet+ Medium` load thành công và cho tốc độ tốt hơn YOLOP trong replay
CPU hiện tại. Candidate có thể tiếp tục ở nhánh R&D/edge optimization, nhưng
chưa đủ bằng chứng để thay YOLOP vì replay hiện tại không có ground-truth lane
mask, lane count hoặc LDW event labels.

**Quyết định:** `R&D / diagnostic only — KHÔNG PROMOTE`.

Model active vẫn là:

```text
models/yolop_lane_detection_640.onnx
```

Candidate mới:

```text
models/twinlitenetplus_medium.pth
```

## 2. Nguồn và artifact

- Upstream repository: [TwinLiteNetPlus](https://github.com/cream1nve02/TwinLiteNetPlus)
- Bản quyền vendor: `third_party/twinlitenetplus/LICENSE`
- Checkpoint upstream được lấy từ thư mục pretrained được README của
  repository dẫn tới Google Drive; cấu hình sử dụng là `medium`.
- Model source được vendor-lock tối thiểu tại:
  `third_party/twinlitenetplus/model/config.py` và `model/model.py`.
- SHA-256 checkpoint local:

  ```text
  04A7959946F687482256D1A499EE4E0AB5D523E9C1760BE41E7E797DC65066FF
  ```

- Tham số thực tế khi load: `478,876`.
- Hai output được kiểm tra: drivable-area logits và lane logits, mỗi output có
  dạng `(1, 2, H, W)`.

## 3. Cách benchmark

Script tái lập:

```text
scripts/benchmark_twinlitenetplus_vs_yolop.py
```

Lệnh đã chạy:

```powershell
roadwatch/.venv/Scripts/python.exe roadwatch/scripts/benchmark_twinlitenetplus_vs_yolop.py `
  --runtime cpu `
  --output roadwatch/reports/twinlitenetplus_medium_vs_yolop.json `
  --render-dir roadwatch/reports/review/twinlitenetplus-vs-yolop
```

Điều kiện:

- 41 timestamp trên 7 video trong `media`.
- Cùng frame đầu vào cho cả hai model.
- YOLOP dùng adapter RoadWatch hiện tại: resize 640x640, RGB và ImageNet
  normalization.
- TwinLiteNet+ dùng preprocessing theo demo upstream: letterbox, RGB và
  `/255.0`, sau đó unpad mask về kích thước frame gốc.
- Cả hai đều chạy CPU; YOLOP chạy qua ONNX Runtime và TwinLiteNet+ chạy bằng
  PyTorch CPU.
- Đã warmup trước khi lấy latency từng sample.

Artifact số liệu đầy đủ:

```text
reports/twinlitenetplus_medium_vs_yolop.json
```

Ảnh overlay cùng frame:

```text
reports/review/twinlitenetplus-vs-yolop/
```

## 4. Kết quả replay thực tế

| Chỉ số | YOLOP baseline | TwinLiteNet+ Medium | Nhận xét |
|---|---:|---:|---|
| Số frame | 41 | 41 | Cùng tập frame |
| Latency P50 | 190.393 ms | 132.204 ms | Candidate giảm khoảng 30.6% |
| Latency P95 | 206.980 ms | 142.956 ms | Candidate giảm khoảng 30.9% |
| Latency trung bình | 193.701 ms | 132.755 ms | Candidate nhanh hơn |
| Mean lane-quality proxy | 0.4772 | 0.5167 | Chỉ là proxy, không phải IoU |
| Mean temporal lane-mask IoU | 0.0567 | 0.0710 | Diagnostic trên timestamp thưa |
| Model load/inference | PASS | PASS | Không có lỗi load/inference |

### Theo nhóm video

| Nhóm | YOLOP quality proxy | TwinLiteNet+ quality proxy | Nhận xét |
|---|---:|---:|---|
| Night | 0.78 | 0.70 | YOLOP nhỉnh hơn ở sample này |
| Rain + night | 0.02 | 0.13 | Candidate có tín hiệu mask tốt hơn, nhưng cả hai còn yếu |
| Dense/multi traffic | 0.76 | 0.73 | Gần tương đương |
| `test_video1` | 0.21 | 0.35 | Candidate nhỉnh hơn |
| `test_video10` | 1.00 | 1.00 | Cùng đạt proxy tối đa |
| `test_video11` | 0.44 | 1.00 | Candidate nhỉnh hơn rõ trên sample |
| `video_test` | 0.24 | 0.04 | YOLOP nhỉnh hơn; candidate có frame không thấy lane |

Các kết quả theo nhóm chỉ mô tả những frame replay đã chọn, không đại diện
cho toàn bộ điều kiện lái xe.

## 5. Đối chiếu với số liệu upstream

README và bài báo của TwinLiteNet+ công bố kết quả trên protocol/dataset của
họ. Các số liệu này là tham khảo kiến trúc, không phải kết quả RoadWatch:

| Model | Params | FLOPs | Drivable mIoU | Lane IoU |
|---|---:|---:|---:|---:|
| YOLOP gốc | 5.53M | 8.11G | 91.6% | 26.5% |
| TwinLiteNet+ Medium | 0.48M | 4.63G | 92.0% | 32.3% |

Nguồn: [README upstream](https://github.com/cream1nve02/TwinLiteNetPlus) và
[bài báo TwinLiteNet+](https://arxiv.org/html/2403.16958v6). Cần tránh suy luận
rằng bảng này chứng minh candidate đã thắng YOLOP trên dữ liệu RoadWatch;
muốn kết luận đó phải có test split và ground truth của chính RoadWatch.

## 6. Vì sao chưa promote

1. Chưa có ground truth cho lane mask và drivable-area trên 41 frame, nên
   không thể tính mIoU/F1 thật.
2. Chưa đo được lane-count accuracy, ego-boundary F1 và LDW event recall.
3. Temporal IoU đang được tính giữa các timestamp cách nhau nhiều giây; đây
   chỉ là chỉ báo thô, không thay thế contiguous-frame stability.
4. Hai model đang dùng runtime khác nhau: YOLOP là ONNX Runtime, candidate là
   PyTorch CPU. Cần export/benchmark ONNX và kiểm tra DirectML/CUDA/TensorRT
   trước khi so sánh deployment công bằng.
5. Candidate có output segmentation nhưng chưa có adapter production, health
   gate, lane-quality lock và rollback integration vào Perception Orchestrator.

## 7. Kế hoạch xác minh tiếp theo

### Gate A — Data

- Gắn nhãn lane count, ego-left/right boundary, lane mask và drivable mask cho
  một test split khóa.
- Tách theo video/đoạn lái, không trộn frame liền kề giữa train và test.
- Bảo đảm có night, rain, dense traffic, multi-lane và faded markings.

### Gate B — Model metrics

- Chạy YOLOP và TwinLiteNet+ trên cùng test split.
- Báo cáo drivable mIoU, lane IoU/F1, lane-count accuracy và boundary F1 theo
  từng điều kiện.
- Không dùng mean toàn bộ dataset để che khuất lỗi ở night/rain.

### Gate C — System/event metrics

- Chạy LDW regression trên contiguous frames.
- Đo lane-quality gating, false LDW/phút, missed LDW và direction left/right.
- Kiểm tra lane count ổn định khi có 2–3 làn cùng chiều.

### Gate D — Deployment

- Export candidate ONNX với preprocessing/postprocessing được khóa.
- Benchmark CPU, AMD DirectML, NVIDIA CUDA và Jetson/TensorRT khi có target.
- Chỉ promote nếu candidate đạt chất lượng event không thấp hơn YOLOP và đáp
  ứng latency budget của target edge.

## 8. Fallback

Không cần rollback vì chưa có thay đổi production. Nếu thử nghiệm candidate
tiếp theo không đạt, chỉ cần tiếp tục dùng:

```text
models/yolop_lane_detection_640.onnx
```

Checkpoint và báo cáo candidate được giữ riêng để phân tích, không ảnh hưởng
Web, AAOS, GCP hoặc lane runtime hiện tại.
