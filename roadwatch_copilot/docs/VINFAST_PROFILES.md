# Định hướng profile VF 5–VF 9

Các profile dưới đây là **layout/deployment baseline**, không phải ngưỡng an toàn đã hiệu chuẩn cho từng xe. Không được suy TTC theo kích thước thân xe. Camera intrinsic/extrinsic, vị trí lắp, vùng che bởi nắp ca-pô và ego speed phải được đo trên chính xe trước khi dùng metric distance.

| Profile | Baseline thân xe dùng cho cấu hình | HMI | Khuyến nghị |
|---|---:|---|---|
| VF 5 | width 1.723 mm | compact | HUD tối giản, ít panel, alert audio-first |
| VF 6 | width 1.834 mm | 12,9-inch class | profile mặc định phát triển |
| VF 7 | width 1.890 mm | 12,9-inch class | giữ touch target lớn, engineer view qua laptop |
| VF 8 | width 1.934 mm | 15,6-inch class | scale UI 1.08; ưu tiên kiosk landscape |
| VF 9 | width 2.004 mm | 15,6-inch class | scale UI 1.08; không suy ego corridor từ width nếu chưa calibration |

Nguồn tham khảo chính thức dùng để chọn layout baseline:

- [VinFast VF 5 product data](https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf5.html)
- [VF 6 brochure](https://shop.vinfastauto.com/on/demandware.static/-/Sites-app_vinfast_vn-Library/default/dwbc3cab90/Document/VF6_Brochure_T032025.pdf)
- [VF 7 technical overview](https://vinfastauto.com/vn_vi/thong-so-vf-7)
- [VF 8 specifications and 15.6-inch display](https://vinfastauto.com/vn_vi/thong-so-ky-thuat-vf-8)
- [VF 9 technical overview and 15.6-inch display](https://vinfastauto.com/vn_vi/thong-so-ky-thuat-vinfast-vf9)

## Calibration record bắt buộc khi đổi xe

- vehicle/profile ID và camera serial;
- độ phân giải/FPS/lens distortion;
- camera height, pitch, yaw và intrinsic matrix;
- vanishing point, hood mask, expected ego-lane corridor;
- benchmark dataset + config version + model checksum;
- ngày/người duyệt và rollback configuration.

RoadWatch hiện chỉ lưu `vehicle.profile` để chọn UI baseline và audit. Các thông số thân xe không được đưa trực tiếp vào FCW/LDW MVP nhằm tránh tạo cảm giác chính xác giả.

