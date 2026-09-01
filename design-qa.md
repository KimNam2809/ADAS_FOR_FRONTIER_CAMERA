# RoadWatch UI Design QA — Automotive HUD Assets

**Ngày:** 2026-08-29  
**Viewport:** 1680 × 928 (khớp mockup Engineer)  
**Kết quả cuối:** `passed`

## Nguồn đối chiếu

- Mockup Engineer đã duyệt:
  `C:\Users\ADMIN\.codex\generated_images\01a03c43-c1fa-71c0-ba1a-ba6122f1a049\exec-f9a55855-3229-4431-9c0e-7ea319bca980.png`
- Engineer render cuối:
  `C:\Users\ADMIN\.codex\visualizations\2026\08\26\01a03c43-c1fa-71c0-ba1a-ba6122f1a049\roadwatch-hud-engineer-final.png`
- Driver render cuối:
  `C:\Users\ADMIN\.codex\visualizations\2026\08\26\01a03c43-c1fa-71c0-ba1a-ba6122f1a049\roadwatch-hud-driver-final.png`
- So sánh mockup/implementation cùng viewport:
  `C:\Users\ADMIN\.codex\visualizations\2026\08\26\01a03c43-c1fa-71c0-ba1a-ba6122f1a049\roadwatch-hud-reference-vs-final.jpg`

Ảnh implementation được chụp từ React production bundle và FastAPI thật,
không dùng fixture UI. Replay `test_video10.mp4` được chạy để xác minh track
sprites lấy từ telemetry thật.

## Kết quả trực quan

| Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|
| Ego vehicle | PASS | CSS box `EGO VEHICLE` đã được thay bằng ảnh xe thật nền trong suốt. |
| Lane geometry | PASS | Đúng hai biên làn nét liền; DOM audit có `2` lane line và `0` dashed center. |
| Tác nhân giao thông | PASS | Car/truck/motorcycle/person/bicycle dùng PNG thật; replay đã hiển thị 4 track động. |
| Vị trí tác nhân | PASS | X lấy từ `projected_x_norm/origin_x_norm/location`; Y và scale lấy từ `proximity_score`; có spread chống chồng hình. |
| Trạng thái dừng | PASS | Sprite, object count và lane quality về 0 khi session không chạy; không giữ hình track cũ. |
| Logo theo vai trò | PASS | DOM Driver/Engineer có `0` logo RoadWatch; logo vẫn tồn tại ở trang login. |
| Video không méo | PASS | Browser đo tỷ lệ viewport `1.7778`; CSS tiếp tục dùng `16 / 9` và `object-fit: contain`. |
| Driver/Engineer parity | PASS | Cả hai role dùng cùng dark automotive HUD, khác nhau ở nội dung màn hình phải. |

## Performance gate

- HUD chỉ dùng dữ liệu `/api/status` đã tồn tại; không thêm endpoint, request,
  model inference hoặc animation loop.
- Tối đa `5` sprite, `HudPanel` được memo hóa, actor mapping dùng `useMemo`.
- Tổng sáu PNG runtime: `388,172 bytes`, tải một lần và được cache như static
  assets.
- JS production: `223.96 kB` (`70.63 kB gzip`); CSS: `33.83 kB`
  (`7.73 kB gzip`). So với bundle trước, JS tăng khoảng `1.6 kB`, CSS giảm
  khoảng `1.4 kB`; phần thay đổi UI không phải nút thắt inference.
- Vite production build: **PASS** (`201 ms`).
- UI contract tests: **PASS** (`8/8`).
- Full test suite: **PASS** (`190/190`), còn một cảnh báo deprecation
  Starlette/httpx không liên quan HUD.
- Browser replay trong Codex sandbox đã tạo track đủ để kiểm tra 4 sprite,
  nhưng dừng ở lần ghi event đầu tiên vì sandbox không có quyền ghi vào file
  SQLite `data/roadwatch.db` hiện hữu. Tạo/ghi SQLite mới cùng thư mục vẫn PASS
  và toàn bộ storage/API tests PASS; đây là giới hạn ACL của phiên QA, không
  phải thay đổi HUD. Cần chạy `scripts/start.ps1` bằng user Windows bình thường
  để xác nhận event persistence trước khi demo.

## Sai khác có chủ đích so với mockup

- Giữ tỷ lệ cột trái `20%` theo quyết định sản phẩm trước đó, thay vì tỷ lệ
  gần `25%` trong ảnh mockup.
- Không render logo ở Driver/Engineer theo yêu cầu mới nhất.
- Tốc độ, track, lane quality và cảnh báo luôn lấy từ runtime; không hard-code
  trạng thái `42 km/h` hay sự kiện mẫu chỉ để giống ảnh.
- Không vẽ bezel vật lý màn hình xe trong Web app.

Không còn lỗi P0/P1/P2 trong phạm vi HUD. Model/risk accuracy và tốc độ neural
inference vẫn phải được đánh giá riêng; visual QA không được dùng làm bằng
chứng model tốt hơn.
