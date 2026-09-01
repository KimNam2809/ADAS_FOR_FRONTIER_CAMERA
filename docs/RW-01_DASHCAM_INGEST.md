# RW-01 — Dashcam Việt Nam Ingest và Stratification

Ngày thực hiện: 2026-08-21  
Nguồn: `media/dashcam_vietnam.mp4`  
Trạng thái phần mềm: **PASS**  
Trạng thái coverage điều kiện: **PARTIAL — Human Gate pending**

## Inventory đã xác nhận

| Thuộc tính | Giá trị |
|---|---:|
| SHA-256 | `513AE901474C2B050CC51C65E97A914EA24FB0B27E2D2673DA55B230409201E3` |
| Dung lượng | 892.132.767 bytes |
| Khung hình | 1920×1080 |
| FPS | 29,9700 |
| Thời lượng | 2.356,020 giây (39:16) |
| Frame metadata / decode | 70.610 / 70.610 |
| Mẫu index 2 FPS | 4.708 |
| Frame review đã chọn | 600 |
| Contact sheet | 24 trang |
| Scene-cut candidate | 404 |

## Phương pháp

`scripts/ingest_dashcam.py` giải mã tuần tự toàn video, tính brightness, contrast,
Laplacian blur, frame delta và quality score. Bộ chọn chia đều toàn timeline rồi
chọn frame có chất lượng cao quanh mỗi mốc. Ảnh review và report được ghi vào
`reports/review/rw01_dashcam/`, là vùng Git ignore; video thô không được copy hay
commit.

## Kết luận quality gate

- Decode integrity đạt `100%` theo frame count.
- Có đủ 600 frame để tạo queue review.
- Auto light tag: 596 day, 4 low-light, 0 night.
- Kiểm tra contact sheet đầu/cuối xác nhận nội dung là giao thông đô thị Việt Nam,
  có xe máy, giao lộ, mật độ giao thông thay đổi, bóng râm và đoạn đường nội bộ.
- Video này **không đủ** để chứng minh night/rain/adverse coverage. Các nhãn
  `rain`, `intersection`, `dense_traffic` phải do Human review; không suy đoán từ
  brightness.

## Artifact cục bộ

- `reports/review/rw01_dashcam/inventory.json`
- `reports/review/rw01_dashcam/sample_index_2fps.csv`
- `reports/review/rw01_dashcam/selected_frames.csv`
- `reports/review/rw01_dashcam/contact_sheets/`
- `reports/review/rw01_dashcam/selected_frames/`

## Giới hạn hiệu năng

OpenCV software decode Full HD mất gần thời lượng video trên máy hiện tại. Đây là
offline data job, không phải FPS runtime. Batch ingest tiếp theo nên thêm ffmpeg
sampling, progress checkpoint và resume.
