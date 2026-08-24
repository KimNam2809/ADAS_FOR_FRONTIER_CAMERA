# RW-10 Lane V2 — Human review queue

## Kết quả chuẩn hóa

- Nguồn: Lane V2 Version 3 candidate manifest.
- Tổng: `599` frame.
- Candidate từ UFLDv2: `217`.
- Bị model reject và cần human xác định là không nhìn thấy/không đủ chắc chắn:
  `382`.
- Trạng thái review: `599 pending`.
- Source-group split: pass; không có một video xuất hiện ở nhiều split.

| Split | Source |
|---|---|
| train | `dashcam_vietnam.mp4`, `dashcam_vietnam_traffic_multi.mp4` |
| val | `dashcam_vietnam_night.mp4` |
| test | `dashcam_vietnam_rainnight.mp4` |

## Nguyên tắc nhãn

`model_proposal` chỉ là gợi ý từ UFLDv2, không phải ground truth. Người review
phải tự xác nhận lane count, ordered polyline của ego-left/ego-right,
visibility, marking type, road direction và `uncertain` khi boundary không thể
biện minh. Không copy proposal vào ground truth chỉ để làm đầy gate.

Review được sắp ưu tiên rain-night → night → dense traffic → day để kiểm tra
những điều kiện làm hệ thống hiện tại dễ bỏ lane nhất. Queue giữ cả frame reject
để phân biệt “không có lane nhìn thấy” với “model bỏ sót lane”.

## Gate hiện tại

Queue validation: **PASS**. RW-10 metric gate: **PENDING HUMAN REVIEW**.
Fine-tune vẫn bị khóa cho tới khi có tối thiểu 3.000 verified polyline frames,
500 night, 400 rain-night, 1.000 multi-lane, 400 faded/missing-marking và 300
double-review với disagreement không quá 5%.

Machine artifact: `artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/quality_gate.json`.
Queue: `evaluation/rw10_lane_review_queue_v2.json`.
