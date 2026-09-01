# RW-10 lane review queue repair

## Kết quả

- Queue được quét toàn bộ `599` record.
- Backup nguyên gốc: `evaluation/backups/rw10_lane_review_queue_v2.pre_repair_20260825T092700.json`.
- SHA-256 trước repair: `28cba423ca645b983e3c33a51757d636212f6c36e41e6fa0f5012546398b7805`.
- SHA-256 sau repair: `fd6334dc8d087ff89d5b0f978682f90e254ee830b7ccd6fc3d42b6b72cbbead2`.
- Kết quả sau repair: `19 verified`, `579 pending`, `1 needs_recheck`.

## Quy tắc đã áp dụng

- Resolution target được xác minh từ video local: `1920x1080`.
- Không clip tọa độ và không tự đoán semantic lane count.
- Chỉ scale một trục khi trục đó vượt bounds và có đúng transform `1/3` đưa
  toàn bộ điểm về trong frame; không có record nào hiện tại thỏa điều kiện này.
- Record `dashcam_vietnam_rainnight-0062` có `ground_truth_lane_count=0` nhưng
  vẫn chứa polyline, nên được chuyển sang `needs_recheck` và giữ nguyên polyline
  để người review quyết định; không xóa nhãn.

## Kết luận

Repair validation: **PASS** cho tính toàn vẹn queue sau repair. Human review gate:
**NOT PASS** — file hiện tại chỉ có 19 verified hợp lệ sau quarantine, chưa đạt
300 pilot frames và chưa đủ điều kiện fine-tune 3.000 verified frames.

Nguyên nhân chênh lệch với báo cáo “300 verified” là file đã được script Gemini
cập nhật dở dang: tại thời điểm repair chỉ có 20 verified, không phải 300. Cần
chạy hoàn tất script review rồi mới chạy repair lại trên queue mới.
