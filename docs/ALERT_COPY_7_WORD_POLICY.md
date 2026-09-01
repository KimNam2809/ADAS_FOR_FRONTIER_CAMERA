# RoadWatch — Chính sách câu cảnh báo tối đa 7 từ (legacy baseline)

> **Lịch sử/fallback:** Tài liệu này mô tả profile `legacy` được tạo trong
> WORK-20260826-013. Runtime hiện mặc định dùng catalog vNext; xem
> [ALERT_COPY_EVIDENCE_BASED_RECOMMENDATIONS.md](./ALERT_COPY_EVIDENCE_BASED_RECOMMENDATIONS.md)
> để biết nội dung đang thử nghiệm và lý do 7 từ không phải chuẩn bắt buộc.

## 1. Mục tiêu và quyết định

Profile legacy của RoadWatch dùng câu cảnh báo ngắn cho Driver HUD và TTS. Mỗi
câu canonical message phải có **không quá 7 token phân tách bằng khoảng trắng**.
Đây là quy tắc UX nội bộ của profile legacy, không phải là một giới hạn pháp lý
hay tiêu chuẩn bắt buộc của mọi hãng xe.

Không được cắt chuỗi tùy tiện ở ký tự thứ 7. Nếu một candidate bên ngoài đưa
vào câu dài, `AlertGovernor` dùng câu an toàn `Hãy chú ý.` và lưu số từ cùng
message gốc trong evidence để kỹ sư xử lý, thay vì phát một câu bị mất nghĩa.

Banner và TTS vẫn lấy cùng một `message` canonical. Vì vậy rút gọn câu không
được tạo ra hai phiên bản nội dung khác nhau cho màn hình và âm thanh.

## 2. Cơ sở thiết kế từ nguồn công khai

Các tài liệu công khai được dùng để đối chiếu nguyên tắc, không dùng để tuyên
bố RoadWatch đã đạt chứng nhận OEM:

- [Tesla Autopilot](https://www.tesla.com/en_GB/support/autopilot) mô tả các
  chức năng hỗ trợ lái và yêu cầu người lái tiếp tục giám sát; đây là cơ sở để
  RoadWatch giữ cảnh báo ngắn, dễ hiểu và không mô tả hệ thống là tự lái.
- [Mobileye Products](https://www.mobileye.com/products/) cho thấy nhóm tính
  năng camera trước tập trung vào các nguy cơ như va chạm, người đi bộ/xe đạp,
  lệch làn, khoảng cách và tốc độ; đây là cơ sở để câu cảnh báo ưu tiên
  `đối tượng + vị trí/nguy cơ + hành động`.
- [Volvo owner manual](https://www.volvocars.com/static/support/pdf/ca_en-US_ec40_2026_UM_adc6b6ff4aba27d80584a0803f109c81.pdf)
  minh họa cách cảnh báo collision/lane-keeping được gắn với loại đối tượng
  và hành vi lái, thay vì đọc một thông báo kỹ thuật dài.
- [openpilot documentation](https://docs.comma.ai/) là ví dụ công khai về một
  hệ thống driver-assistance có FCW/LDW và yêu cầu người lái chịu trách nhiệm.

Các nguồn trên không công bố một chuẩn chung kiểu “mọi cảnh báo phải <= 7
từ”. Vì vậy giới hạn 7 từ là quyết định có thể kiểm thử của RoadWatch, cần
được xác nhận tiếp bằng human listening gate trong tiếng ồn xe thật.

## 3. Quy tắc viết

Ưu tiên thông tin theo thứ tự:

1. Nguy cơ hoặc đối tượng.
2. Hướng camera: `bên trái`, `bên phải`, `phía trước`.
3. Hành động ngắn: `giảm tốc`, `nhập làn`, `tiến gần`.

Một số quy tắc cụ thể:

- Critical FCW giữ câu `Cảnh báo va chạm phía trước!`.
- Cảnh báo cut-in/cross-traffic giữ hướng chuyển động, ví dụ `Xe máy cắt
  trái sang phải.`.
- VRU không còn dùng cụm dài `chú ý khoảng cách an toàn`; thay bằng `giảm
  tốc` khi đã có path conflict.
- Speed sign dùng `Tối đa 80 ki-lô-mét/giờ.`; số tốc độ và đơn vị vẫn được giữ.
- Hai biển tốc độ không gắn được vào lane dùng `Nhiều biển tốc độ; xem làn
  mình.`; hệ thống không chọn ngẫu nhiên một giới hạn.
- `No Entry` dùng `Biển cấm đi vào; kiểm tra hướng.` để không làm tài xế
  hoảng loạn khi biển thuộc chiều đối diện hoặc chưa đủ thông tin orientation.

## 4. Template cảnh báo động của profile legacy

Các template này được sinh cho toàn bộ nhãn road-user được cấu hình:

| Sự kiện | Template canonical | Ví dụ |
|---|---|---|
| FCW thường | `<đối tượng> <vị trí>; tiến gần.` | `Ô tô bên phải; tiến gần.` |
| FCW critical | `Cảnh báo va chạm phía trước!` | — |
| VRU/path conflict | `<đối tượng> <vị trí>; giảm tốc.` | `Người đi bộ phía trước; giảm tốc.` |
| Cut-in | `<đối tượng> <bên>; nhập làn.` | `Xe máy bên phải; nhập làn.` |
| Cross-traffic | `<đối tượng> cắt <hướng>.` | `Xe máy cắt trái sang phải.` |
| Lead braking | `<đối tượng> phía trước; giảm tốc.` | `Ô tô phía trước; giảm tốc.` |
| LDW | `Lệch làn bên <trái/phải>.` | `Lệch làn bên trái.` |

`rider` được đọc là `Xe hai bánh` thay vì `Người đi xe hai bánh` để giữ thông
tin đối tượng mà không làm câu vượt ngân sách.

## 5. Catalog biển báo đã rút gọn của profile legacy

Đây là các message baseline của profile legacy trong `backend/roadwatch/signs.py`.
Các dòng
`HUD-only` vẫn phải <=7 từ dù không phát TTS.

| Detector label | Message | Audio |
|---|---|---|
| No Entry | Biển cấm đi vào; kiểm tra hướng. | Có |
| Stop | Biển dừng phía trước. | Có |
| Red Light | Đèn đỏ phía trước. | Có |
| Traffic light ahead | Đèn tín hiệu phía trước. | Có |
| Pedestrian Crossing | Người đi bộ sang đường. | Có |
| Pedestrian Lane | Làn người đi bộ phía trước. | Có |
| Children Crossing | Trẻ em sang đường; giảm tốc. | Có |
| Road Work Ahead | Công trường phía trước; giảm tốc. | Có |
| Accident area | Khu vực tai nạn; giảm tốc. | Có |
| Obstacle on the Road | Chướng ngại vật phía trước. | Có |
| Slippery Road | Đường trơn; giảm tốc. | Có |
| Speed Bump | Gờ giảm tốc phía trước. | Có |
| Uneven road | Mặt đường gồ ghề. | Có |
| Danger | Nguy hiểm phía trước. | Có |
| Slow Down | Giảm tốc phía trước. | Có |
| Level Crossing with Barriers | Giao cắt đường sắt; giảm tốc. | Có |
| Narrow bridge | Cầu hẹp phía trước. | Có |
| Narrow Road Left Side | Đường hẹp bên trái. | Có |
| Narrow Road Right Side | Đường hẹp bên phải. | Có |
| Narrow road both sides | Đường hẹp hai bên. | Có |
| Sharp Left Turn | Cua gấp bên trái. | Có |
| Sharp Right Turn | Cua gấp bên phải. | Có |
| Double curve first to right | Nhiều cua; đầu tiên bên phải. | Có |
| Steep ascent | Dốc lên phía trước. | Có |
| No Overtaking | Cấm vượt phía trước. | Có |
| No Left Turn | Cấm rẽ trái. | Có |
| No Right Turn | Cấm rẽ phải. | Có |
| No U-Turn | Cấm quay đầu. | Có |
| No U-Turn and No Left Turn | Cấm quay đầu, rẽ trái. | Có |
| No U-Turn and No Right Turn | Cấm quay đầu, rẽ phải. | Có |
| No U-Turn for Cars | Cấm ô tô quay đầu. | Có |
| No left turn for cars | Cấm ô tô rẽ trái. | Có |
| No Motobike Left Turn | Cấm xe máy rẽ trái. | Có |
| No Two or Three-wheeled Vehicles | Cấm xe hai, ba bánh. | Có |
| No Cars | Cấm ô tô. | Có |
| No Trucks | Cấm xe tải. | Có |
| No Trucks and Bus | Cấm xe tải, xe buýt. | Có |
| Low Clearance / Height Limit | Giới hạn chiều cao phía trước. | Có |
| Turn Left Only | Bắt buộc rẽ trái. | Có |
| Turn Right Only | Bắt buộc rẽ phải. | Có |
| Turn Left | Hướng đi bên trái. | Có |
| Turn Right | Hướng đi bên phải. | Có |
| Keep left | Đi về bên trái. | Có |
| Roundabout | Vòng xuyến phía trước. | Có |
| Lane Allocation | Chú ý biển phân làn phía trước. | Có |
| One way street | Đường một chiều phía trước. | Có |
| End of all prohibition | Hết các lệnh cấm. | Có |
| End of 50km/h speed limit | Hết giới hạn 50 ki-lô-mét/giờ. | Có |
| Parking | Khu vực đỗ xe. | HUD-only |
| Bus Stop | Điểm dừng xe buýt. | HUD-only |
| Hospital | Bệnh viện phía trước. | HUD-only |
| Green Light | Đèn xanh phía trước. | HUD-only |
| No Moto | Cấm xe máy. | Có |
| No bus | Cấm xe buýt. | Có |
| No Horns | Cấm dùng còi. | Có |
| No Straight and Right Turn | Cấm đi thẳng, rẽ phải. | Có |
| No Left or Right Turn | Cấm rẽ trái, rẽ phải. | Có |
| No U-Turn and Left Turn for Cars | Cấm ô tô quay đầu, rẽ trái. | Có |
| Intersection with a Priority Road | Giao nhau đường ưu tiên. | Có |
| Intersection with Equal Roads | Giao nhau đường đồng cấp. | Có |
| Intersection with a Minor Road | Giao nhau đường nhánh. | Có |
| Residential area | Vào khu đông dân cư. | Có |
| sparsely populated area | Rời khu đông dân cư. | Có |
| Dual carriageway | Bắt đầu đường đôi. | Có |
| U-Turn Area | Khu vực quay đầu phía trước. | HUD-only |
| Road with Surveillance Camera | Camera giám sát phía trước. | HUD-only |
| No Stopping & No Parking | Cấm dừng và đỗ. | HUD-only |
| No Parking | Cấm đỗ xe. | HUD-only |
| No Parking Odd Days | Cấm đỗ ngày lẻ. | HUD-only |
| Even Days | Hạn chế đỗ ngày chẵn. | HUD-only |

Với nhãn số hoặc `Speed limit <N>km/h`, message được sinh theo template:

```text
Tối đa <N> ki-lô-mét/giờ.
```

## 6. Thay đổi source đã tạo profile legacy

| File | Vai trò |
|---|---|
| `backend/roadwatch/alert_copy.py` | Profile legacy 7 từ, hard safety ceiling vNext và rút gọn location/hướng. |
| `backend/roadwatch/signs.py` | Catalog sign policy, speed-sign và kiểm tra message khi khởi tạo policy. |
| `backend/roadwatch/risk.py` | Template FCW, VRU, cut-in, cross-traffic, lead braking và LDW. |
| `backend/roadwatch/sign_arbitration.py` | Câu ambiguity khi nhiều biển tốc độ cùng frame. |
| `backend/roadwatch/alerts.py` | Fallback an toàn cho candidate dài; vẫn giữ banner/TTS canonical. |
| `backend/roadwatch/tts.py` | Corpus warmup và `_normalise_text` cùng áp dụng giới hạn 7 từ. |
| `tests/` | Regression cho nội dung mới, word budget, fallback và canonical equality. |

## 7. Verification và human gate của baseline legacy

Các kiểm tra tự động bắt buộc:

```text
default_alert_corpus(): mọi câu <= 7 từ
spoken_sign_messages(): mọi câu <= 7 từ
RiskEngine: message động giữ đúng đối tượng/hướng
AlertGovernor: display_message == spoken_message
AlertGovernor: candidate dài chuyển sang fallback an toàn
```

Kiểm thử tự động không chứng minh được giọng đọc tự nhiên. Trước khi promote
provider TTS, tối thiểu ba người nghe tiếng Việt cần kiểm tra trong yên tĩnh và
tiếng ồn xe: mất âm đầu, sai trái/phải, sai số tốc độ, độ rõ và khả năng hiểu
trong một lần nghe. Nếu câu ngắn làm mất ý nghĩa hoặc hướng, ưu tiên sửa copy
và policy chứ không nới word budget một cách tùy tiện.

## 8. Giới hạn cần ghi rõ khi demo

- Bảy từ là budget UX, không phải bằng chứng safety certification.
- Câu ngắn không sửa được lỗi nhận diện sai class, sai hướng hoặc sai số tốc
  độ; các lỗi đó vẫn cần model/event regression riêng.
- `phía trước`, `bên trái`, `bên phải` là theo góc nhìn camera trước; không có
  nghĩa RoadWatch đã biết chắc hướng áp dụng của mọi biển báo.
- RoadWatch chỉ cảnh báo/hỗ trợ, không tự phanh, đánh lái hoặc điều khiển xe.
