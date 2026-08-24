# RW-02 — Event Ground Truth Human Quality Gate

Ngày khởi tạo: 2026-08-21  
Trạng thái tooling: **PASS**  
Trạng thái dữ liệu: **BLOCKED — HUMAN REVIEW REQUIRED**

## Artifact đã tạo

`evaluation/dashcam_annotation_queue.json` chứa 60 cửa sổ không chồng lặp, mỗi
cửa sổ 10 giây, tổng planned exhaustive coverage là 600 giây. Các cửa sổ trải đều
toàn bộ `dashcam_vietnam.mp4` và ưu tiên frame có scene delta cao trong từng đoạn
thời gian.

`scripts/validate_event_annotation_queue.py` là promotion gate máy đọc được. Gate
không chấp nhận review đang pending, critical event thiếu reviewer thứ hai, event
timing sai, negative window có event, coverage dưới 600 giây hoặc negative dưới
150 giây.

## Trạng thái hiện tại

| Gate | Kết quả |
|---|---|
| Schema integrity | PASS |
| Planned coverage | 600 giây |
| Verified exhaustive coverage | 0/600 giây |
| Verified negative coverage | 0/150 giây |
| Event coverage | Pending |
| Critical second review | Chưa phát sinh vì chưa có nhãn |

Validator trả exit code `1` là kết quả **đúng** ở thời điểm này.

## Quy trình Human Review

Với từng `window_id`:

1. Mở video gốc đúng `start_seconds`–`end_seconds`; reference frame chỉ giúp định
   vị, không thay thế việc xem đủ clip 10 giây.
2. Chọn scene conditions: day/night/rain/intersection/dense traffic/other.
3. Nếu không có bất kỳ event RoadWatch nào, đặt `is_negative=true`; ngược lại đặt
   `false` và thêm mọi event theo schema trong policy.
4. Điền start → hazard onset → deadline → end, object class và location.
5. Đặt primary review thành `verified` kèm reviewer/timestamp.
6. Mọi cửa sổ có FCW, VRU, cross-traffic, lead braking hoặc fallen rider phải có
   reviewer độc lập thứ hai. Bất đồng phải được adjudicate.
7. Nếu một event type không đạt 20 event vì video không chứa đủ tình huống, ghi
   lý do cụ thể trong `event_coverage_exceptions`; không được để trống.

## Lệnh xác nhận

```powershell
roadwatch\.venv\Scripts\python.exe roadwatch\scripts\validate_event_annotation_queue.py
```

Chỉ khi lệnh trả exit code `0` và status `pass` mới được dùng queue để mở gate
RW-03/RW-04 promotion. AI có thể code validator/scorer 100%; Human bắt buộc chịu
trách nhiệm nhãn quan sát và adjudication.
