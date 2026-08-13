# Safety scope và guardrails

RoadWatch là prototype hỗ trợ cảnh báo, không phải hệ thống ADAS đã chứng nhận.

## Tuyệt đối ngoài phạm vi

- Không xuất lệnh tới phanh, ga, vô lăng, motor hoặc ECU.
- Không ghi CAN/OBD; adapter tương lai chỉ đọc.
- Không dùng SLM/LLM để phát critical alert hoặc thay đổi ngưỡng runtime.
- Không tuyên bố TTC theo giây/khoảng cách mét khi chưa calibration và ego-speed đáng tin cậy.
- Không thử nghiệm ngoài đường công cộng như một hệ thống an toàn chính.

## Fail-safe theo phạm vi prototype

- Model lỗi được báo `degraded`; model còn lại/API không crash theo.
- Lane quality thấp khóa LDW.
- Detection một frame không đủ phát cảnh báo.
- Critical beep có quyền ưu tiên; warning/advisory chịu audio gap và cooldown.
- Cấu hình safety chỉ engineer sửa và có audit log; phải dừng session trước khi reload.
- UI mất kết nối không dừng pipeline.

## Quy trình thử xe thật đề xuất

1. Replay offline với event labels.
2. Bench camera khi xe đỗ, không phát lệnh điều khiển.
3. Closed-course với safety driver, observer và nút tắt audio.
4. Chỉ sau calibration mới bật metric TTC; so sánh ground truth.
5. Không triển khai sản phẩm thương mại nếu chưa hazard analysis, validation và chứng nhận theo quy định áp dụng.

## Metric an toàn cần báo cáo

- Alert precision/recall và miss rate theo event.
- False alerts/minute; repeated-alert rate.
- Time-to-warning so với nhãn sự kiện.
- End-to-end P50/P95, frame-drop ratio.
- Lane-confidence coverage và tỷ lệ LDW bị suppress.
- Audio interruption/suppression rate.

