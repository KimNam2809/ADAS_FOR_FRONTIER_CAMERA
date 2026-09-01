# Validation evidence — Windows AMD baseline

Ngày đo: 2026-08-14 (Asia/Bangkok). Máy: Windows 11, AMD Ryzen 5 7535HS, Radeon RX 6550M/660M, Python 3.12.13. Video: `test_video10.mp4`, 1920×1080, 30 FPS. Audio tắt trong benchmark để tách latency perception.

## Kết quả tự động

| Hạng mục | Bằng chứng |
|---|---|
| Backend tests | 11 passed |
| React production build | thành công; JS gzip 65,01 kB, CSS gzip 4,03 kB |
| Docker Compose schema | `docker compose config --quiet` thành công |
| Heavy assets | model, media, voice, `.venv` đều được `git check-ignore` xác nhận |
| Object runtime | Ultralytics CPU, P50 44,57 ms, P95 70,23 ms |
| YOLOP runtime | DirectML, P50 70,43 ms, P95 76,00 ms |
| Traffic-sign runtime | Ultralytics CPU, P50 81,47 ms, P95 115,67 ms |
| End-to-end | P50 148,44 ms, P95 245,40 ms |
| Throughput | 4,31 processed FPS với ba model bật |
| Lane evidence cuối cửa sổ | segmentation 1,00; geometry 1,00; offset 0,052 |
| Model health | 3/3 loaded; không degraded |

Số liệu nằm trong `reports/benchmark-amd-windows-video10.json` ở máy benchmark; report JSON bị loại khỏi Git vì chứa thông tin máy/runtime theo phiên. Tạo lại bằng:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark.py --source test_video10.mp4 --seconds 20
```

## Event evidence quan sát được

- FCW warning sau 18 frame track, confidence 0,568, risk 0,596; evidence ghi rõ image-space risk, không phải metric TTC.
- Speed limit 40 km/h chỉ xuất hiện sau 3 lần xác nhận, confidence 0,779.
- Trong cùng cửa sổ, Alert Governor đã suppress sự kiện lặp qua cooldown/audio budget.

Các event cụ thể phụ thuộc thời điểm benchmark và threshold version; xem SQLite qua Engineer Console thay vì coi các số trên là ground truth safety.

## Checklist demo thủ công

- [ ] Mở UI ở 1920×1080 và 1280×800; không tràn bố cục.
- [ ] Driver đăng nhập được và không truy cập config engineer.
- [ ] Engineer thấy model provider, P50/P95, evidence timeline và threshold panel.
- [ ] Chạy `test_video10.mp4`, kiểm tra overlay object/lane và biển 40 km/h.
- [ ] Ngắt Internet; refresh UI, login, replay và TTS vẫn chạy.
- [ ] Đóng tab browser; xác nhận pipeline/audio vẫn tiếp tục trong edge service.
- [ ] Dừng session trước khi đổi ngưỡng; audit log được tạo.
- [ ] Critical beep ngắt/ưu tiên hơn TTS advisory trong scenario test.

RoadWatch chưa được hiệu chuẩn/certify cho xe thật. Checklist giao diện và audio phải được người demo chạy lại trên chính màn hình/loa dùng trước hội đồng.

## RoadWatch v0.2 — 2026-08-17

Runtime AMD đã chuyển hai detector sang ONNX DirectML; YOLOP tiếp tục DirectML. Năm scenario video đầy đủ đã được replay bằng `scripts/evaluate.py` (audio tắt để tách latency perception).

| Scenario | FPS | E2E P50/P95 | Presence recall proxy | Repeated proxy | Lane coverage | Kết luận chính |
|---|---:|---:|---:|---:|---:|---|
| test_video10 | 8,65 | 95,56 / 141,02 ms | 1,00 | 0,294 | 0,686 | Bắt LDW/sign type; model vẫn dự đoán 40 thay vì ground truth 60. |
| test_video11 | 9,03 | 99,29 / 148,86 ms | 0,50 | 0,067 | 0,213 | Biển 80 đúng; miss `lead_vehicle_braking`, nhưng có FCW critical cho xe tải. |
| test_video2 | 5,05 | 96,50 / 143,25 ms | 1,00 | 0,333 | 0,633 | Đã phát cross-traffic và vulnerable-road-user. |
| test_video3 | 8,55 | 95,11 / 139,41 ms | 1,00 | 0,348 | 0,231 | Có FCW event; audio playback thật chưa đo trong evaluation. |
| video_test ngày/đêm | 9,52 | 97,33 / 137,82 ms | 0,667 | 0,265 | 0,189 | Bắt cross-traffic/vulnerable/cut-in; vẫn miss lead braking và lane coverage đêm thấp. |

So với baseline v0.1 trên `test_video10`, processed FPS tăng từ 4,31 lên 8,65–9,03 trong full replay; P95 end-to-end giảm từ 245,40 ms xuống khoảng 141–149 ms. Một benchmark 30 giây có pacing đo 8,26 FPS, P50 104,71 ms, P95 155,25 ms.

FCW hysteresis/re-arm cùng cooldown 12 giây giảm event trên `test_video10` từ 30 (bản thử đầu v0.2) xuống 17; repeated proxy giảm từ 0,567 xuống 0,294. Đây vẫn chưa phải false-alert metric vì manifest mới có expectation cấp video.

### Metric chưa đủ điều kiện đo

- Object/sign mAP, precision, recall: chưa có bounding-box ground truth cho bộ RoadWatch.
- Event-level alert precision/recall, false alerts/minute và time-to-warning: chưa có timestamp ground truth cho từng event.
- Audio stale rate thực: evaluation tắt audio; regression test đã xác minh expired event không được phát.
- Metric TTC, Jetson/TensorRT, CAN và closed-course: bị gate do chưa có calibration/phần cứng/thẩm quyền thử xe.

Report JSON local: `reports/evaluation-v0.2-*.json`, `reports/benchmark-v0.2-amd-onnx.json`, `reports/edge-preflight-latest.json` (đều Git ignore).

## RoadWatch v0.2.1 — targeted incident regression

Các lỗi được tái hiện từ phản hồi thực tế: `test_video1` từng xử lý đủ 1.046 frame nhưng phát 0 event vì lane quality chỉ đạt gate ở 4,58% frame; watermark trong `video_test` bị phân loại nhầm thành biển tốc độ; một object đồng thời tạo nhiều banner FCW/cut-in/vulnerable.

Biện pháp: near-field threat fallback không phụ thuộc YOLOP khi nguy cơ rất gần, motion window ngắn cho cut-in, brake-light cue có confirmation, sign geometry/red-ring/motion validation, semantic cooldown, deduplicate cảnh báo cùng object, và canonical `display_message == spoken_message`. Piper cache v2 có 140 ms silence để tránh thiết bị audio cắt từ đầu câu.

| Scenario mục tiêu | Events | Event types đạt | FPS | E2E P50/P95 | Speed false positive |
|---|---:|---|---:|---:|---|
| test_video1, 0–42 s | 9 | cut-in, FCW, lead-braking | 8,85 | 93,06 / 142,14 ms | 0 |
| video_test đêm, 0–34 s | 9 | cross-traffic, vulnerable, FCW | 9,93 | 91,33 / 132,57 ms | 0 |
| video_test ngày, 34–67 s | 32 | cross-traffic, vulnerable, cut-in, FCW | 8,53 | 100,75 / 151,10 ms | 0 |

Trong `test_video1`, FCW critical được tạo tại source time 16,64 s và 31,52 s; evaluation đánh dấu `beep_tts` nhưng tắt thiết bị audio. Đoạn đêm tạo cảnh báo cross-traffic từ 13,33 s, xe máy từ 15,83 s và FCW critical tại 29,83 s. Payload banner/TTS đạt 100% consistency trên ba scenario.

Đoạn ngày vẫn có mật độ event cao do video đông road user, camera/scene thay đổi và tracker bị phân mảnh. Đây là giới hạn còn phải đánh giá bằng timestamp/object ground truth; không được gọi mọi event ngoài expectation là false alert.

YOLOP hiện xuất binary lane mask; `_fit_ego_lane` chỉ fit hành lang ego để phục vụ LDW/FCW, không phải mô hình lane-instance và không có khả năng đếm chính xác 2/3 lane. Khi chất lượng thấp, LDW bị khóa thay vì hiển thị số lane sai.
