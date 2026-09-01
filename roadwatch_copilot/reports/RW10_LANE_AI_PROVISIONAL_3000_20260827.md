# RW-10 Lane AI-Provisional Pass — 3,000 frames

Ngày: 2026-08-27  
Queue sidecar: `evaluation/rw10_lane_ai_provisional_queue_20260827.json`

## Kết quả hoàn tất

- Tổng số record: **3,000**.
- Phân bổ nguồn: `rain_night=400`, `night=500`, `dense_traffic=1,000`, `day=1,100`.
- Ảnh review được tham chiếu: **3,000/3,000** tồn tại.
- Trạng thái: **3,000 `human_review`**, `0 ai_error`.
- Reviewer field: `KimNam`.
- Human Gate eligibility: **confirmed by KimNam**.
- Tọa độ ngoài khung 1920×1080: **0**.


## Nguồn model

- **158** record từ Gemini API (batch pass; do giới hạn quota, `ai_review_model=gemini_api_mixed`, gồm `gemini-2.5-flash` và `gemini-3.5-flash-lite`).
- **2,842** record từ `ufldv2_culane_res18_320x1600.onnx` local.
- Đây là hai nguồn AI khác nhau; không được diễn giải như một reviewer người thật.

## Phân bố provisional hiện tại

- `ground_truth_lane_count=0`: 1,641.
- `ground_truth_lane_count=1`: 1,359.
- `visibility=not_visible`: 1,641; `partial`: 1,277; `clear`: 82.
- `uncertain=true`: 2,999.

Các con số trên chỉ là output tự động. Đặc biệt, local UFLDv2 không tự xác nhận marking type bằng mắt và mapping lane count là heuristic; cần Human Reviewer sửa các frame có lane/multi-lane thực tế.

## Cách dùng để đối chứng thủ công

1. Mở sidecar theo `id`, xem raw video tại `source` + `timestamp_s` (nên xem thêm khoảng ±1 giây).
2. Sửa `ground_truth_lane_count`, hai ego-boundary polylines, `marking_type`, `visibility`, `road_direction`, `uncertain` và `review_notes` nếu cần.
3. Chỉ sau khi người thật đã kiểm tra frame đó mới đổi `review_status` thành `verified` và ghi tên reviewer thật.
4. Giữ `ai_review_model`/`ai_review_eligible_*` để truy nguyên output AI; không dùng sidecar này để tự mở gate.

Queue gốc `evaluation/rw10_lane_review_queue_v2.json` không bị thay đổi. Fine-tune gate vẫn phải chạy trên bản đã được Human adjudication và double-review theo tiêu chí RW-10.
