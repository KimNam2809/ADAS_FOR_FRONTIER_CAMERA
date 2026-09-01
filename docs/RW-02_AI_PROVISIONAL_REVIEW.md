# RW-02 — AI Provisional Review Handover

Ngày thực hiện: 2026-08-21  
Trạng thái: **AI PROVISIONAL COMPLETE — HUMAN AUDIT PENDING**

## Kết quả bootstrap

- 60/60 cửa sổ đã được xem qua storyboard 20 frame/10 giây.
- 16 cửa sổ được đánh dấu candidate, ưu tiên review cao.
- 44 cửa sổ được đánh dấu provisional negative, tổng 440 giây.
- Mọi nhãn mang trạng thái `ai_provisional`; không cửa sổ nào bị ghi sai thành
  `verified`.
- Full backend test suite pass sau thay đổi.
- Human promotion gate vẫn trả exit code `1` đúng thiết kế.

Nguồn nhãn là `evaluation/dashcam_annotation_queue.ai_provisional.json`. 60
storyboard nằm trong `reports/review/rw02_storyboards/` và không được commit.

## 16 cửa sổ cần audit trước

| Window | Candidate | Object | Direction | Hazard onset (s) | Confidence |
|---|---|---|---|---:|---:|
| dashcam-vn-001 | cross_traffic | motorcycle | left_to_right | 22.03 | 0.55 |
| dashcam-vn-004 | cross_traffic | car | left_to_right | 134.64 | 0.45 |
| dashcam-vn-007 | cross_traffic | motorcycle | right_to_left | 267.37 | 0.50 |
| dashcam-vn-014 | cut_in | car | left | 535.54 | 0.55 |
| dashcam-vn-017 | cut_in | car | left | 640.14 | 0.45 |
| dashcam-vn-018 | cut_in | car | left | 686.19 | 0.50 |
| dashcam-vn-021 | cross_traffic | bus | left_to_right | 814.62 | 0.65 |
| dashcam-vn-026 | cut_in | car | left | 1002.30 | 0.60 |
| dashcam-vn-027 | cut_in | car | left | 1051.21 | 0.55 |
| dashcam-vn-029 | cross_traffic | motorcycle | right_to_left | 1130.24 | 0.45 |
| dashcam-vn-030 | cross_traffic | motorcycle | right_to_left | 1140.24 | 0.45 |
| dashcam-vn-037 | speed_sign 50 | traffic_sign | right | 1430.93 | 0.80 |
| dashcam-vn-039 | cut_in | car | left | 1509.51 | 0.45 |
| dashcam-vn-048 | cut_in | car | right | 1846.55 | 0.55 |
| dashcam-vn-050 | cut_in | car | right | 1942.94 | 0.50 |
| dashcam-vn-051 | cross_traffic | motorcycle | left_to_right | 1988.49 | 0.50 |

## Cách Human audit nhanh

1. Xem 16 cửa sổ trên trước bằng video full-motion.
2. Chấp nhận, sửa event/timestamp hoặc đổi thành negative.
3. Để kiểm tra nhanh chất lượng bootstrap, chọn ngẫu nhiên tối thiểu 15 trong 44
   provisional negatives và ưu tiên `review_priority=medium`. Để **pass chính thức
   RW-02**, Human vẫn phải xác nhận đủ cả 60 cửa sổ.
4. Reviewer thứ hai kiểm tra độc lập những cross-traffic được giữ lại.
5. Chỉ sau audit mới đổi `primary_review.status` thành `verified`.

## Giới hạn bắt buộc công bố

Storyboard 2 FPS có thể bỏ lỡ phanh gấp, cut-in ngắn và LDW. Video không có CAN,
ego speed, depth hay calibration TTC. Vì thế bản này giúp giảm công sức review và
chuẩn bị RW-03, nhưng không phải ground truth để promote model hoặc tuyên bố safety.
