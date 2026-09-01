# Ground-truth độc lập cho TwinLiteNet+ — Trạng thái và quy trình

**Ngày:** 2026-08-28  
**Mục tiêu:** tạo một evaluation set độc lập để so sánh TwinLiteNet+ Medium
với YOLOP mà không dùng dự đoán của bất kỳ model nào làm nhãn thật.

## 1. Trạng thái hiện tại

Pipeline đã được tạo và chạy:

```text
scripts/build_twinlitenetplus_ground_truth.py
scripts/evaluate_twinlitenetplus_ground_truth.py
```

Đã tạo queue review sạch từ held-out/test của provisional queue. Queue này chỉ
giữ metadata frame và **không chứa model proposal hoặc nhãn AI**:
`evaluation/twinlitenetplus_ground_truth_review_queue_v1.json`.

Kết quả hiện tại:

| Mục | Kết quả |
|---|---:|
| Tổng queue review sạch | 400 |
| Record thuộc evaluation split `test` | 400 |
| Human-verified hợp lệ | 0 |
| Bị loại vì chưa `review_status=verified` | 400 |
| Ground-truth package | `blocked_insufficient_human_ground_truth` |
| Model comparison | BLOCKED |

Các record AI/Gemini, `pending`, `needs_recheck` hoặc `uncertain=true` không
được tính là ground-truth chính. Đây là kết quả đúng về mặt an toàn đánh giá;
không được biến dự đoán của model thành sự thật để tạo ra mIoU/F1 giả.

Manifest được sinh tại:

```text
evaluation/twinlitenetplus_ground_truth_v1/manifest.json
```

Kết quả evaluator:

```text
reports/twinlitenetplus_ground_truth_evaluation.json
```

## 2. Ground-truth package sẽ chứa gì khi đủ nhãn

Mỗi record hợp lệ sẽ có:

- Frame JPEG trích xuất từ video gốc tại đúng timestamp.
- Lane boundary mask PNG được rasterize từ polyline người duyệt.
- `ground_truth_lane_count` — số làn cùng chiều nhìn thấy được.
- `ego_left_boundary` và `ego_right_boundary` — polyline trong tọa độ frame
  gốc 1920x1080.
- `marking_type`, `visibility`, `road_direction`, `uncertain` và provenance
  reviewer.
- Source video, split và timestamp để audit lại.

Mask raster hiện tại là **boundary mask**, không phải drivable-area mask. Vì
queue lane hiện chưa có nhãn drivable-area độc lập, manifest luôn ghi
`drivable_mask_available=false`; không được báo cáo drivable mIoU khi chưa có
mask tương ứng.

## 3. Cách review để tạo nhãn hợp lệ

### Triển chiêu cần review ở đâu

Review queue sạch dành riêng cho TwinLiteNet+:

```text
evaluation/twinlitenetplus_ground_truth_review_queue_v1.json
```

Review UI hiện có:

```text
scripts/lane_review_app.py
```

Khởi chạy review trên Windows:

```powershell
& ".\\roadwatch\\.venv\\Scripts\\python.exe" `
  roadwatch/scripts/lane_review_app.py `
  --queue roadwatch/evaluation/twinlitenetplus_ground_truth_review_queue_v1.json `
  --frames-dir roadwatch/artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames `
  --media-dir roadwatch/media `
  --backup-dir roadwatch/evaluation/twinlitenetplus_ground_truth_review_backups `
  --port 8051
```

Mở `http://127.0.0.1:8051`. Review theo thứ tự sidebar từ `rain_night`; không
bật hoặc sao chép proposal model. Queue mới đã loại proposal nên vùng overlay
model sẽ không có dữ liệu để tác động đến nhãn.

### Quy tắc cho từng frame

1. Chỉ dùng frame thuộc `test` cho test comparison cuối; không dùng `train`.
2. Đếm các làn cùng chiều với xe, không đếm làn ngược chiều hoặc vệt rẽ
   riêng lẻ.
3. Vẽ biên trái/phải của ego lane khi có thể bảo vệ bằng ảnh gốc.
4. Khi trời tối, mưa phản chiếu, vạch mờ hoặc bị xe che:
   - đặt `uncertain=true`;
   - ghi chú lý do;
   - không dùng record đó cho metric chính.
5. Chỉ đặt `review_status="verified"` sau khi người thật đã kiểm tra.
6. Không copy `model_proposal` sang ground truth.
7. Ghi reviewer và thực hiện double-review cho một phần sample độc lập.

Sau khi review, chạy builder đúng queue mới:

```powershell
& ".\\roadwatch\\.venv\\Scripts\\python.exe" `
  roadwatch/scripts/build_twinlitenetplus_ground_truth.py `
  --queue roadwatch/evaluation/twinlitenetplus_ground_truth_review_queue_v1.json `
  --output-dir roadwatch/evaluation/twinlitenetplus_ground_truth_v1 `
  --min-records 300 `
  --splits test
```

Khi manifest chuyển sang `ready_for_model_comparison`, chạy:

```powershell
& ".\\roadwatch\\.venv\\Scripts\\python.exe" `
  roadwatch/scripts/evaluate_twinlitenetplus_ground_truth.py `
  --ground-truth roadwatch/evaluation/twinlitenetplus_ground_truth_v1/manifest.json `
  --runtime directml
```

## 4. Quality Gate trước khi cân nhắc thay YOLOP

### Gate dữ liệu pilot

- Tối thiểu 300 human-verified record thuộc test/held-out split.
- Có night, rain/night, dense traffic và multi-lane.
- Không có duplicate ID, tọa độ ngoài frame hoặc source leakage.
- Double-review và disagreement được ghi riêng, không suy đoán.

### Gate model

Trên cùng một test set và cùng preprocessing:

- Boundary F1 candidate không thấp hơn YOLOP.
- Recall ở night/rain không thấp hơn YOLOP.
- Lane-count accuracy mục tiêu `>= 0.95`.
- Ego-boundary F1 mục tiêu `>= 0.90`.
- Nếu có drivable masks: drivable mIoU phải được báo cáo riêng.

### Gate hệ thống

- LDW false alerts `<= 1/phút`.
- Không tăng missed LDW hoặc sai trái/phải.
- Candidate không làm xấu FCW/VRU/cross-traffic vì thay đổi lane quality.
- AMD DirectML benchmark và target-edge benchmark đều không vượt latency
  budget đã khóa.

Chỉ khi tất cả gate đạt mới tạo candidate release và thử canary. Nếu fail bất
kỳ critical gate nào, giữ:

```text
models/yolop_lane_detection_640.onnx
```

## 5. Quyết định hiện tại

TwinLiteNet+ Medium đang có lợi thế latency, nhưng **chưa chứng minh tốt hơn
YOLOP về độ chính xác**. Hiện chưa đủ điều kiện thay thế model cũ. Ground-truth
pipeline đã sẵn sàng; việc còn thiếu là human review độc lập cho evaluation
split và, nếu muốn đánh giá drivable-area, bổ sung drivable masks.
