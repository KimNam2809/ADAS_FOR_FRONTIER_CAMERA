# RW-02 — Owner Confirmation Workflow

> Trạng thái cập nhật 2026-08-21: chủ dự án `trien_chieu` đã xác nhận toàn bộ
> nhãn không thay đổi. File `dashcam_annotation_queue.owner_verified.json` đã
> được tạo. Primary review hoàn thành; 7 critical windows còn chờ second-review.

## Kết quả đã chuẩn bị

Toàn bộ 60 cửa sổ, mỗi cửa sổ 10 giây, đã được điền sẵn nhãn đề xuất trong
`evaluation/dashcam_annotation_queue.owner_review_draft.json`:

- 16 cửa sổ có candidate event;
- 44 cửa sổ được đề xuất là negative, tương đương 440 giây;
- mọi cửa sổ có `proposed_decision: accept_ai_proposal`;
- mọi cửa sổ vẫn có `status: pending_owner_confirmation`.

Đây là cơ chế **accept-by-default**: chủ dự án không phải ghi chú từng đoạn hợp
lệ. Chỉ những đoạn sai mới cần sửa.

## Quy trình đã sử dụng để chủ dự án kiểm tra

1. Chạy video đầy đủ hoặc ưu tiên 16 cửa sổ candidate trong
   `docs/RW-02_AI_PROVISIONAL_REVIEW.md`.
2. Nếu một cửa sổ không hợp lệ, đổi `proposed_decision` thành
   `reject_ai_proposal`, ghi lý do/correction trong `changes`, và sửa nhãn event
   hoặc negative tương ứng.
3. Nếu toàn bộ nhãn hợp lệ và không thay đổi, chỉ cần xác nhận trong cuộc trò
   chuyện bằng câu: **“Tôi xác nhận toàn bộ nhãn RW-02 không thay đổi.”**

Sau xác nhận rõ ràng, AI Agent đã chạy:

```powershell
.venv/Scripts/python.exe scripts/finalize_owner_confirmation.py `
  --reviewer trien_chieu `
  --confirm-all-unchanged
```

Lệnh tạo `evaluation/dashcam_annotation_queue.owner_verified.json` và chuyển
primary review sang `verified`. Script cố ý từ chối hoàn tất nếu còn cửa sổ bị
đánh dấu `reject_ai_proposal` hoặc thiếu cờ xác nhận rõ ràng.

## Ranh giới chất lượng

Owner confirmation đã hoàn thành **primary review**. Theo Definition of Done
trong Master Action Plan, các critical windows (`fcw`, `vulnerable_road_user`,
`cross_traffic`, `lead_vehicle_braking`, `fallen_rider`) vẫn cần một người thứ
hai review độc lập. Vì vậy không được tuyên bố RW-02 hoàn thành hoặc dùng bộ
nhãn để promote model an toàn cho đến khi secondary-review và validator đều
pass.

## Bằng chứng kỹ thuật

- Generator: `scripts/prepare_owner_confirmation.py`
- Explicit finalizer: `scripts/finalize_owner_confirmation.py`
- Safety tests: `tests/test_owner_confirmation.py`
- Human gate validator: `scripts/validate_event_annotation_queue.py`
