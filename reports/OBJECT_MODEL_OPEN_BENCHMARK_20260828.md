# RoadWatch — Benchmark Object Detector Public 28/08/2026

## Kết luận ngắn

**Chưa promote model public nào.** `yolo11n.onnx` vẫn là object detector
production/fallback của RoadWatch vì là model duy nhất trong lần benchmark này
giữ được event recall và không làm tăng alert density vượt gate. YOLO26s là
candidate nghiên cứu đáng giữ lại; YOLO26n bị loại do giảm recall nguy hiểm.

Đây là quyết định theo safety metrics, không theo mAP COCO hoặc cảm giác nhìn
bounding box.

## Model được khảo sát

Ultralytics công bố YOLO26 là dòng YOLO real-time mới nhất, phát hành tháng
01/2026, có head end-to-end/NMS-free và hỗ trợ export ONNX/TensorRT. Bảng COCO
chính thức công bố:

| Model | Params | FLOPs | COCO mAP50-95 | CPU ONNX công bố |
|---|---:|---:|---:|---:|
| YOLO11n | 2.6M | 6.5B | 39.5 | 56.1 ms |
| YOLO26n | 2.4M | 5.4B | 40.9 | 38.9 ms |
| YOLO26s | 9.5M | 20.7B | 48.6 | 87.2 ms |

Nguồn: [YOLO26 official model page](https://docs.ultralytics.com/models/yolo26),
[YOLO11 vs YOLO26 comparison](https://docs.ultralytics.com/compare/yolo11-vs-yolo26),
[YOLO26 model repository](https://huggingface.co/Ultralytics/YOLO26).

Các model được tải từ repository public `Ultralytics/YOLO26`, export ONNX cố
định `640x640`, sau đó chạy qua cùng `OnnxYoloDetector` của RoadWatch.

## Điều kiện benchmark local

- Runtime: ONNX Runtime `DmlExecutionProvider` trên AMD Radeon.
- Confidence threshold: `0.38`, giống cấu hình RoadWatch.
- Taxonomy so sánh: `person`, `bicycle`, `motorcycle`, `car`, `bus`, `truck`.
- Dữ liệu: 7 video đại diện gồm day/night/rain-night/dense-traffic,
  cut-in/cross-traffic/fallen-rider.
- Sampling: `0.25 FPS`, 415 frame/model.
- Không fine-tune local và không dùng kết quả này để tuyên bố mAP.
- File nặng nằm trong `models/` và bị `.gitignore`; không commit Git.

## Kết quả replay rộng

| Model | Detections/frame | Mean latency | P50 | P95 | Nhận xét |
|---|---:|---:|---:|---:|---|
| YOLO11n baseline | 4.4193 | 27.634 ms | 27.541 ms | 31.107 ms | Baseline ổn định |
| YOLO26n public | 3.6241 | 27.267 ms | 26.829 ms | 30.579 ms | Ít detection hơn, không có lợi thế tốc độ đáng kể trên máy AMD này |
| YOLO26s public | 6.1542 | 32.129 ms | 32.106 ms | 36.359 ms | Nhiều detection hơn nhưng có nguy cơ duplicate/false alert và chậm hơn |

### Presence proxy theo class

| Class | YOLO11n | YOLO26n | YOLO26s |
|---|---:|---:|---:|
| person | 0.5229 | 0.4964 | 0.6120 |
| bicycle | 0.0048 | 0.0072 | 0.0145 |
| motorcycle | 0.3855 | 0.2867 | 0.4892 |
| car | 0.8434 | 0.7831 | 0.8361 |
| bus | 0.0916 | 0.0651 | 0.0819 |
| truck | 0.1325 | 0.1566 | 0.2361 |

Presence rate chỉ nói model có emit class trên frame sampled hay không; không
phân biệt được true positive và false positive nếu không có bbox ground truth.

## Locked event regression

Phạm vi: 3 scenario đã có timestamp ground truth, tổng coverage verified là
73 giây. Đây là phép đo gần với RoadWatch hơn replay thuần detection.

| Metric | YOLO11n | YOLO26n | YOLO26s |
|---|---:|---:|---:|
| Scenario presence recall | 0.8333 | 0.7222 | 0.8333 |
| Semantic recall proxy | 0.8333 | 0.7222 | 0.8333 |
| Timestamp event recall | 0.7500 | 0.3750 | 0.7500 |
| Timestamp event precision | 0.6667 | 0.4286 | 0.6667 |
| Timestamp false alerts/min | 2.4658 | 3.2877 | 2.4658 |
| Mean object P95 | 27.13 ms | 25.25 ms | 31.29 ms |
| Total alerts/min proxy | 13.2110 | 8.8073 | 15.4128 |

### Quyết định gate

- **YOLO26n: REJECT** — event recall giảm `0.75 → 0.375`, precision giảm và
  false-alert rate tăng.
- **YOLO26s: KEEP AS CANDIDATE** — event recall ngang baseline nhưng tổng
  alert density tăng hơn 10% và object P95 cao hơn; chưa đủ điều kiện promote.
- **YOLO11n: KEEP ACTIVE** — tiếp tục là baseline/fallback cho Web, AAOS và
  local demo.

Các report gốc:

- `reports/ab-yolo26n-vs-yolo11n-event.json`
- `reports/ab-yolo26s-vs-yolo11n-event.json`
- `reports/object_open_models_representative.json`

## Vì sao YOLO26 không tự động thắng dù là model mới hơn?

Model COCO pretrained chỉ biết taxonomy chung và phân phối dữ liệu COCO. Nó
chưa được huấn luyện riêng cho camera góc chữ A, giao thông xe máy Việt Nam,
occlusion, mưa/đêm, cut-in và fallen rider của RoadWatch. YOLO26n có thể nhẹ
và nhanh hơn trên benchmark công bố nhưng lại bỏ sót nhiều object có ảnh hưởng
đến FCW/VRU. YOLO26s phát hiện nhiều hơn nhưng trong pipeline cảnh báo, nhiều
detection không đồng nghĩa nhiều cảnh báo đúng.

Ngoài ra, YOLO26 dùng output end-to-end `[x1,y1,x2,y2,confidence,class_id]`,
khác output raw của YOLO11. RoadWatch đã thêm adapter riêng để benchmark đúng
contract; thay model mà không có adapter sẽ cho kết quả sai.

## Lựa chọn cuối cùng

```text
Production / demo primary: yolo11n.onnx
Rollback: yolo11n.pt hoặc yolo11n.onnx
R&D candidate: yolo26s.onnx
Rejected candidate: yolo26n.onnx
```

Bước cải thiện có giá trị tiếp theo không phải đổi checkpoint mù quáng, mà là
fine-tune YOLO26s trên taxonomy RoadWatch với hard negatives Việt Nam, sau đó
chạy lại locked event regression. Nếu không thể fine-tune trong thời gian còn
lại, giữ YOLO11n là lựa chọn an toàn hơn cho demo.

## License và triển khai doanh nghiệp

Checkpoint YOLO26 public mang license **AGPL-3.0** theo metadata của model.
Việc tải miễn phí không tự động đồng nghĩa được tích hợp vào sản phẩm thương
mại đóng nguồn. Cần review pháp lý/enterprise terms trước khi giới thiệu
production cho doanh nghiệp.
