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

