# RoadWatch — Catalog câu cảnh báo theo bằng chứng và hướng triển khai

**Ngày cập nhật:** 2026-08-27  
**Trạng thái:** Catalog vNext đã tích hợp qua profile, đang chờ video/human trial  
**Phạm vi:** Driver HUD, TTS tiếng Việt, beep, ưu tiên cảnh báo và biển báo

## 1. Kết luận điều hành

RoadWatch không nên coi “tối đa 7 từ” là một tiêu chuẩn an toàn bắt buộc.

Qua đối chiếu các tài liệu chính thức đến tháng 08/2026, không tìm thấy tiêu chuẩn quốc tế hoặc tài liệu OEM nào quy định mọi câu cảnh báo trên xe phải có không quá 7 từ. Hướng dẫn thực tế tập trung vào:

- mức khẩn cấp và thời gian tài xế phải phản ứng;
- số **đơn vị thông tin** (information units), tức các ý chính cần hiểu;
- thời lượng phát âm và khả năng nghe rõ trong tiếng ồn;
- sự nhất quán giữa âm thanh, banner và tín hiệu không gian trái/phải;
- ưu tiên cảnh báo để không che khuất cảnh báo nguy hiểm hơn.

Vì vậy, quyết định phù hợp cho RoadWatch là:

1. Giữ giới hạn 7 từ hiện tại như một **baseline UX/fallback** trong runtime, vì nó đang giúp câu ngắn và dễ kiểm thử.
2. Không cắt câu máy móc chỉ để đạt 7 từ nếu việc đó làm mất chủ thể, hướng, mức nguy hiểm hoặc hành động cần thiết.
3. Dùng ma trận severity × time-frame × information-units làm quy tắc chính cho catalog vNext.
4. Critical warning phải phát beep và banner trước; TTS chỉ là phần bổ sung nếu không làm chậm tín hiệu khẩn cấp.
5. Chỉ phát TTS cho thông tin mà perception đã xác nhận đủ lâu và có liên quan tới làn/đường đi của xe. Detector nhìn thấy một frame chưa đủ để nói với tài xế rằng một biển báo đang áp dụng cho họ.

Catalog trong tài liệu này là **profile thử nghiệm đã tích hợp**, không phải bằng chứng RoadWatch đã đạt chứng nhận an toàn hay đã tuân thủ đầy đủ tiêu chuẩn xe thật.

## 2. Cơ sở nghiên cứu công khai

### 2.1. Tiêu chuẩn ergonomics trên xe

- [ISO 15006:2011 — In-vehicle auditory presentation](https://www.iso.org/standard/55322.html) mô tả các yêu cầu và khuyến nghị cho tín hiệu âm thanh bằng tiếng nói hoặc âm thanh, nhằm tăng khả năng hiểu và giảm quá tải thính giác/tâm lý. Trang ISO cho biết phiên bản này vẫn được xác nhận hiện hành sau lần review năm 2024.
- [ISO 15005:2017 — Dialogue management principles](https://www.iso.org/standard/69238.html) đặt nguyên tắc ergonomics cho đối thoại giữa tài xế và hệ thống thông tin, điều khiển khi xe đang chạy.
- [ISO/TS 16951:2021 — Priority of on-board messages](https://www.iso.org/standard/81103.html?browse=tc) cung cấp quy trình xác định thứ tự ưu tiên của cảnh báo, trạng thái hệ thống, thông tin giao thông và các thông điệp khác. Đây là cơ sở cho việc không cho biển báo thông tin che khuất FCW/VRU.
- [ISO 15623:2013 — Forward vehicle collision warning](https://www.iso.org/standard/56655.html?browse=tc) mô tả yêu cầu và quy trình thử cho cảnh báo va chạm phía trước với ô tô, xe tải, xe buýt và xe máy; trách nhiệm vận hành an toàn vẫn thuộc tài xế.

Các tiêu chuẩn trên đưa ra yêu cầu, quy trình hoặc nguyên tắc ergonomics; chúng không tạo ra một danh sách câu tiếng Việt cố định và cũng không xác nhận rằng RoadWatch đã được chứng nhận.

### 2.2. Hướng dẫn human factors của NHTSA

[NHTSA Human Factors Design Guidance](https://www.nhtsa.gov/sites/nhtsa.dot.gov/files/documents/812360_humanfactorsdesignguidance.pdf) đưa ra các điểm trực tiếp áp dụng cho RoadWatch:

- Speech truyền tải được thông tin phức tạp nhưng cần thời gian để nghe hết, nên phải dùng thận trọng trong tình huống time-critical.
- Cảnh báo khẩn cấp nên là một từ hoặc cụm rất ngắn, với ít âm tiết nhất có thể.
- Cảnh báo thận trọng nên giới hạn khoảng 3–4 information units; ví dụ của tài liệu có cấu trúc tương đương “vehicle ahead — merge right”.
- Speech nên đi cùng thông báo hình ảnh có nội dung tương ứng, không tạo một câu trên banner và một câu khác trên TTS.
- Giọng tổng hợp phải rõ và dễ hiểu ở tốc độ cao; tốc độ khoảng 150–200 từ mỗi phút được dùng như dải tham khảo để truyền mức độ khẩn cấp.
- Tín hiệu đơn giản phù hợp với cảnh báo va chạm tức thời; speech phù hợp hơn với thông tin ít khẩn cấp nhưng cần nêu rõ đối tượng hoặc ngữ cảnh.
- Chỉ nên giữ một số lượng nhỏ loại tone khác nhau; quá nhiều âm báo làm tăng nhầm lẫn và khó học.
- Cảnh báo có hướng nên khớp với vị trí âm thanh/ý nghĩa trái-phải; nói sai hướng làm tăng rủi ro thay vì giúp định vị.

NHTSA cũng trình bày các khoảng thời gian tham khảo theo SAE J2395:

| Time frame | Khoảng tham khảo | Ý nghĩa cho RoadWatch |
|---|---:|---|
| Emergency | 0–3 giây | Beep/banner ngay; TTS tối thiểu hoặc không chờ TTS |
| Immediate | 3–10 giây | TTS ngắn, nêu đối tượng + vị trí/nguy cơ + hành động |
| Near term | 10–20 giây | Cảnh báo có ngữ cảnh, vẫn phải ngắn và có liên quan |
| Preparatory | 20–120 giây | Ưu tiên HUD; TTS chỉ khi có giá trị an toàn rõ |
| Discretionary | Trên 120 giây | Thường chỉ hiển thị, không chiếm kênh âm thanh |

Đây là khung thiết kế để RoadWatch dùng cho arbitration, không phải ngưỡng chứng nhận được tự suy ra cho mọi loại xe.

### 2.3. Bằng chứng từ hệ thống sản xuất

- [Tesla Model 3 Collision Avoidance Assist](https://www.tesla.com/ownersmanual/model3/en_gb/GUID-8EA7EF10-7D27-42AC-A31A-96BCE5BC0A85.html) cho thấy FCW có cảnh báo hình ảnh và âm thanh, bao gồm đối tượng là ô tô, xe máy, xe đạp và người đi bộ. Cảnh báo dừng khi nguy cơ giảm; tài xế vẫn phải tự xử lý. Tesla cũng cảnh báo thời tiết, camera bị che và vạch đường mờ có thể làm cảnh báo không chính xác, không cần thiết hoặc bị bỏ sót.
- [Hyundai Owner's Manual — Forward Collision-Avoidance](https://ownersmanual.hyundai.com/full_webhelp/NE1N/2026/en_US/id23BSE4000E6.html) minh họa kiểu thông báo ngắn kết hợp cluster message và âm báo; tài liệu cũng nêu giới hạn nhận diện ban đêm, ảnh hưởng của âm thanh môi trường và việc cảnh báo khác có thể làm thay đổi cách trình bày.
- [NHTSA Driver Assistance Technologies](https://www.nhtsa.gov/vehicle-safety/driver-assistance-technologies) nhấn mạnh FCW và LDW là chức năng hỗ trợ/cảnh báo, không thay thế sự chú ý và trách nhiệm của tài xế. Đây là nguyên tắc guardrail cho mọi câu chữ của RoadWatch.

## 3. Quy tắc viết câu cảnh báo RoadWatch vNext

### 3.1. Thay “đếm từ” bằng “đơn vị thông tin”

Đếm token cách nhau bằng khoảng trắng hữu ích cho kiểm thử tự động, nhưng không phải thước đo tốt nhất cho tiếng Việt. Ví dụ “người đi bộ” có ba token kỹ thuật nhưng chỉ là một khái niệm đối tượng. Câu cần được chấm theo các đơn vị mà tài xế phải nhận biết:

1. **Đối tượng/nguy cơ:** xe máy, người đi bộ, chướng ngại vật, va chạm.
2. **Vị trí/hướng:** phía trước, bên trái, bên phải.
3. **Hành vi:** cắt ngang, nhập làn, giảm tốc, ngã.
4. **Hành động đề nghị:** giảm tốc, giữ khoảng cách, kiểm tra hướng.

Một câu cảnh báo trực tiếp thường nên có 2–4 đơn vị thông tin. Không thêm các cụm không làm tài xế ra quyết định nhanh hơn như “đã nhận diện”, “hệ thống phát hiện” hoặc “hãy chú ý” sau mọi câu.

### 3.2. Ngân sách theo mức độ

Đây là **engineering gate đề xuất**, không phải giới hạn pháp lý:

| Mức | Kênh ưu tiên | Mục tiêu copy | Ngân sách thời lượng |
|---|---|---|---:|
| Critical/Emergency | Beep + banner đỏ | 1–2 đơn vị; TTS chỉ là bổ sung | Beep tức thời; TTS khoảng ≤1,0 giây nếu bật |
| Warning/Immediate | TTS + banner | 2–4 đơn vị: đối tượng + vị trí/nguy cơ + hành động | Khoảng ≤2,0 giây |
| Advisory/Near term | Banner; TTS chọn lọc | 2–4 đơn vị, thêm số/ý nghĩa nếu thật sự cần | Khoảng ≤3,0 giây |
| Informational | HUD-only | Mô tả ngắn, không chen kênh âm thanh | Không TTS mặc định |

Nếu câu cần dài hơn để không gây mơ hồ, giữ nghĩa và chuyển sang Advisory/HUD thay vì cắt mất thông tin quan trọng. Với câu Critical, không chờ một câu dài được tổng hợp xong mới phát beep.

### 3.3. Quy tắc ngôn ngữ

- Dùng tiếng Việt tự nhiên, không đọc “TTC”, “ego lane”, “path conflict”, “confidence” cho tài xế.
- Dùng “bên trái/bên phải” theo góc nhìn camera và hình học ego-lane đã xác nhận; không tự chuyển thành trái/phải chỉ vì hướng chuyển động của object.
- Với cross-traffic phương tiện, nói nguồn xung đột (“cắt ngang từ bên trái/phải”); với người đi bộ đã xác nhận đang băng qua an toàn, có thể nói hướng chuyển động “đang cắt ngang từ trái sang phải/phải sang trái”.
- Không dùng event `cut_in` cho người đi bộ. Người đi bộ trên vỉa hè chỉ là object; chỉ phát VRU/FCW khi path conflict và risk phù hợp, hoặc cross-traffic khi có bằng chứng đi vào vùng đường xe chạy.
- “Cảnh báo” không cần lặp ở mọi câu nếu màu banner và beep đã biểu thị mức độ; giữ nó cho câu Critical khi cần làm rõ.
- “Đã nhận diện” là trạng thái của máy, không phải lợi ích trực tiếp cho tài xế; loại khỏi câu nói.
- Không suy ra hành vi sống của người từ một biển báo. Ví dụ biển “Pedestrian Crossing” nên nói về lối/vạch sang đường, không nói chắc “người đang sang”.
- Không phát lại cùng một semantic event chỉ vì detector tiếp tục thấy cùng object; dùng event_id, lifecycle, cooldown và nâng cấp severity khi risk thực sự tăng.

## 4. Catalog cảnh báo động đề xuất

Đây là catalog ưu tiên cho các engine FCW/VRU/cut-in/cross-traffic/LDW và lead-braking. <đối tượng> có thể là “Người đi bộ”, “Xe máy”, “Xe đạp”, “Ô tô”, “Xe buýt” hoặc “Xe tải”.

| Event | Severity/time-frame | Câu canonical đề xuất | Điều kiện phát |
|---|---|---|---|
| FCW imminent | Critical / 0–3s | **Cảnh báo va chạm** | Risk vượt ngưỡng critical, temporal confirmation; beep/banner phát ngay, TTS không được làm chậm beep |
| FCW warning | Warning / 3–10s | **<đối tượng> <vị trí>; giảm tốc độ.** | Object nằm trong ego path và closing trend ổn định |
| Lead braking | Warning / 3–10s | **<phương tiện> phía trước đang giảm tốc. Hãy chú ý.** | Chỉ áp dụng `car/bus/truck`; kích hoạt từ biến thiên scale/kinematics nhiều frame |
| VRU pedestrian | Critical hoặc Warning | **Người đi bộ <vị trí>; giảm tốc độ.** | Có path conflict, không chỉ có bbox ở lề đường |
| VRU motorcycle | Critical hoặc Warning | **Xe máy <vị trí>; giảm tốc độ.** | Xe máy nằm trong vùng xung đột và hướng/độ gần ổn định |
| VRU bicycle | Critical hoặc Warning | **Xe đạp <vị trí>; giảm tốc độ.** | Tương tự xe máy, có xác nhận theo thời gian |
| Fallen rider | Critical hoặc Warning | **Xe máy ngã phía trước; giảm tốc.** | Tư thế/độ nghiêng + trạng thái dừng + còn trong ego path |
| Cut-in phương tiện | Warning / Immediate | **<phương tiện> nhập làn từ bên trái. Hãy chú ý.** | Chỉ áp dụng xe máy/xe đạp/ô tô/xe buýt/xe tải; hướng nhập làn đủ tin cậy |
| Cut-in phương tiện | Warning / Immediate | **<phương tiện> nhập làn từ bên phải. Hãy chú ý.** | Có temporal confirmation và cooldown theo vùng/semantic event |
| Cut-in người đi bộ | None | **Không dùng câu “người đi bộ nhập làn”.** | Người đi bộ ở vỉa hè không phải cut-in; chuyển sang VRU/FCW hoặc cross-traffic nếu có path conflict |
| Cross-traffic phương tiện | Warning / Immediate | **<phương tiện> cắt ngang từ bên trái.** | Có xung đột đường đi, chuyển động ngang đủ mạnh/gần; không báo phương tiện đi ngang an toàn ở xa |
| Cross-traffic phương tiện | Warning / Immediate | **<phương tiện> cắt ngang từ bên phải.** | Điều kiện tương tự; cooldown giúp tránh lặp trong dòng xe máy dày |
| Cross-traffic người đi bộ an toàn | Advisory/Warning | **Người đi bộ đang cắt ngang từ trái sang phải.** | Có path conflict nhưng risk chưa vào ngưỡng VRU/FCW và không phải chỉ đứng ở vỉa hè |
| Cross-traffic người đi bộ an toàn | Advisory/Warning | **Người đi bộ đang cắt ngang từ phải sang trái.** | Điều kiện tương tự |
| Cross-traffic không rõ hướng | Warning | **<đối tượng> cắt ngang phía trước.** | Chỉ dùng khi có chuyển động ngang nhưng trái/phải chưa đủ tin cậy |
| LDW | Warning / Immediate | **Cảnh báo lệch làn bên trái.** | Lane quality đủ cao, streak nhiều frame, không phải đang chủ động đổi làn |
| LDW | Warning / Immediate | **Cảnh báo lệch làn bên phải.** | Điều kiện tương tự |
| Lane quality thấp | Informational | **Không đọc TTS.** | Hiển thị trạng thái camera/làn không tin cậy cho kỹ sư; không cảnh báo tài xế |

### 4.1. Vì sao không dùng “Phanh ngay!” làm câu mặc định

RoadWatch hiện chỉ là hệ thống cảnh báo/hỗ trợ, không có quyền điều khiển phanh hoặc đánh lái. “Phanh ngay!” có thể là câu rất mạnh và phù hợp trong một số thiết kế FCW đã được xác nhận, nhưng với pipeline camera đơn hiện tại, việc hệ thống ra lệnh phanh có thể khiến tài xế phản ứng quá mức khi perception sai. Vì vậy catalog vNext dùng “Cảnh báo va chạm” cho Critical: beep và banner đỏ báo mức nguy hiểm, còn tài xế quyết định hành động; khi có closed-course validation và thiết kế HMI an toàn riêng, câu hành động có thể được A/B test như một candidate, không tự động đưa vào production.

### 4.2. Mẫu dữ liệu canonical bắt buộc

Banner và TTS phải nhận cùng một payload, không tự dịch lại ở hai nơi:

~~~
{
  "event_id": "evt-00042",
  "semantic_key": "cut_in.motorcycle.right",
  "severity": "warning",
  "time_frame": "immediate",
  "subject": "Xe máy",
  "location": "bên phải",
  "action": "nhập làn từ bên phải",
  "canonical_message": "Xe máy nhập làn từ bên phải. Hãy chú ý.",
  "display_message": "Xe máy nhập làn từ bên phải. Hãy chú ý.",
  "spoken_message": "Xe máy nhập làn từ bên phải. Hãy chú ý.",
  "direction_confidence": 0.97,
  "lifecycle": "active",
  "audio_mode": "tts"
}
~~~

Nếu direction_confidence thấp, không được tự chọn trái/phải; chuyển sang “<đối tượng> cắt ngang phía trước.” hoặc HUD-only. event_id phải giữ nguyên trong lifecycle của một nguy cơ và chỉ tạo event mới khi nguy cơ kết thúc rồi tái xuất hiện hoặc tăng cấp severity.

## 5. Catalog biển báo đầy đủ đề xuất

Các message dưới đây là cách diễn đạt driver-facing cho taxonomy hiện tại của RoadWatch. “Audio” không có nghĩa “luôn đọc ngay”; biển vẫn phải vượt qua temporal confirmation, lane relevance, orientation và arbitration.

| Detector label | Câu driver-facing đề xuất | Kênh |
|---|---|---|
| No Entry | Biển cấm đi vào; kiểm tra hướng. | HUD; TTS chỉ khi đủ ngữ cảnh |
| Stop | Biển dừng phía trước. | TTS chọn lọc + HUD |
| Red Light | Đèn đỏ phía trước. | TTS chọn lọc + HUD |
| Traffic light ahead | Đèn tín hiệu phía trước. | TTS chọn lọc + HUD |
| Pedestrian Crossing | Lối sang đường phía trước. | TTS chọn lọc + HUD |
| Pedestrian Lane | Làn người đi bộ phía trước. | TTS chọn lọc + HUD |
| Children Crossing | Khu vực trẻ em; giảm tốc. | TTS chọn lọc + HUD |
| Road Work Ahead | Công trường phía trước; giảm tốc. | TTS chọn lọc + HUD |
| Accident area | Khu vực tai nạn; giảm tốc. | TTS chọn lọc + HUD |
| Obstacle on the Road | Chướng ngại vật phía trước; giảm tốc. | TTS chọn lọc + HUD |
| Slippery Road | Đường trơn; giảm tốc. | TTS chọn lọc + HUD |
| Speed Bump | Gờ giảm tốc phía trước. | TTS chọn lọc + HUD |
| Uneven road | Mặt đường gồ ghề. | TTS chọn lọc + HUD |
| Danger | Nguy hiểm phía trước. | TTS chọn lọc + HUD |
| Slow Down | Giảm tốc phía trước. | TTS chọn lọc + HUD |
| Level Crossing with Barriers | Giao cắt đường sắt; giảm tốc. | TTS chọn lọc + HUD |
| Narrow bridge | Cầu hẹp phía trước. | TTS chọn lọc + HUD |
| Narrow Road Left Side | Đường hẹp bên trái. | HUD; TTS theo relevance |
| Narrow Road Right Side | Đường hẹp bên phải. | HUD; TTS theo relevance |
| Narrow road both sides | Đường hẹp hai bên. | HUD; TTS theo relevance |
| Sharp Left Turn | Cua gấp bên trái. | HUD; TTS theo relevance |
| Sharp Right Turn | Cua gấp bên phải. | HUD; TTS theo relevance |
| Double curve first to right | Nhiều cua; đầu tiên bên phải. | HUD; TTS theo relevance |
| Steep ascent | Dốc lên phía trước. | HUD; TTS theo relevance |
| No Overtaking | Cấm vượt phía trước. | HUD; TTS khi lane relevance rõ |
| No Left Turn | Cấm rẽ trái. | TTS chọn lọc + HUD |
| No Right Turn | Cấm rẽ phải. | TTS chọn lọc + HUD |
| No U-Turn | Cấm quay đầu. | TTS chọn lọc + HUD |
| No U-Turn and No Left Turn | Cấm quay đầu, rẽ trái. | TTS chọn lọc + HUD |
| No U-Turn and No Right Turn | Cấm quay đầu, rẽ phải. | TTS chọn lọc + HUD |
| No U-Turn for Cars | Cấm ô tô quay đầu. | TTS chọn lọc + HUD |
| No left turn for cars | Cấm ô tô rẽ trái. | TTS chọn lọc + HUD |
| No Motobike Left Turn | Cấm xe máy rẽ trái. | TTS chọn lọc + HUD |
| No Two or Three-wheeled Vehicles | Cấm xe hai, ba bánh. | TTS chọn lọc + HUD |
| No Cars | Cấm ô tô. | TTS chọn lọc + HUD |
| No Trucks | Cấm xe tải. | TTS chọn lọc + HUD |
| No Trucks and Bus | Cấm xe tải, xe buýt. | TTS chọn lọc + HUD |
| Low Clearance | Chiều cao giới hạn phía trước. | TTS chọn lọc + HUD |
| Height Limit | Chiều cao giới hạn phía trước. | TTS chọn lọc + HUD |
| Turn Left Only | Chỉ rẽ trái. | TTS chọn lọc + HUD |
| Turn Right Only | Chỉ rẽ phải. | TTS chọn lọc + HUD |
| Turn Left | Hướng đi bên trái. | HUD; TTS khi liên quan |
| Turn Right | Hướng đi bên phải. | HUD; TTS khi liên quan |
| Keep left | Giữ bên trái. | HUD; TTS khi liên quan |
| Roundabout | Vòng xuyến phía trước. | TTS chọn lọc + HUD |
| Lane Allocation | Biển phân làn phía trước. | HUD; TTS khi cần chuẩn bị |
| One way street | Đường một chiều phía trước. | TTS chọn lọc + HUD |
| End of all prohibition | Hết các lệnh cấm. | HUD; thường không TTS |
| End of 50km/h speed limit | Hết giới hạn 50 ki-lô-mét/giờ. | HUD; TTS theo relevance |
| Parking | Khu vực đỗ xe. | HUD-only |
| Bus Stop | Điểm dừng xe buýt. | HUD-only |
| Hospital | Bệnh viện phía trước. | HUD-only |
| Green Light | Đèn xanh phía trước. | HUD-only |
| No Moto | Cấm xe máy. | TTS chọn lọc + HUD |
| No bus | Cấm xe buýt. | TTS chọn lọc + HUD |
| No Horns | Cấm dùng còi. | HUD; thường không TTS |
| No Straight and Right Turn | Cấm đi thẳng, rẽ phải. | TTS chọn lọc + HUD |
| No Left or Right Turn | Cấm rẽ trái, rẽ phải. | TTS chọn lọc + HUD |
| No U-Turn and Left Turn for Cars | Cấm ô tô quay đầu, rẽ trái. | TTS chọn lọc + HUD |
| Intersection with a Priority Road | Giao nhau đường ưu tiên. | TTS chọn lọc + HUD |
| Intersection with Equal Roads | Giao nhau đường đồng cấp. | HUD; TTS theo relevance |
| Intersection with a Minor Road | Giao nhau đường nhánh. | TTS chọn lọc + HUD |
| Residential area | Vào khu đông dân cư. | TTS chọn lọc + HUD |
| sparsely populated area | Rời khu đông dân cư. | HUD; thường không TTS |
| Dual carriageway | Bắt đầu đường đôi. | HUD; TTS theo relevance |
| U-Turn Area | Khu vực quay đầu phía trước. | HUD-only |
| Road with Surveillance Camera | Camera giám sát phía trước. | HUD-only |
| No Stopping & No Parking | Cấm dừng và đỗ. | HUD-only |
| No Parking | Cấm đỗ xe. | HUD-only |
| No Parking Odd Days | Cấm đỗ ngày lẻ. | HUD-only |
| Even Days | Hạn chế đỗ ngày chẵn. | HUD-only |

### 5.1. Speed-limit signs

Với nhãn số hoặc nhãn dạng Speed limit <N>km/h, profile vNext dùng câu:

~~~
Giới hạn <N> ki-lô-mét/giờ phía trước.
~~~

Ví dụ: “Giới hạn 60 ki-lô-mét/giờ phía trước.” Profile legacy vẫn đọc
“Tối đa 60 ki-lô-mét/giờ.” để rollback không đổi hành vi đã kiểm thử.

RoadWatch cũng nhận diện policy dạng `Minimum speed Nkm/h` khi model/dataset có
nhãn này. Khi biển tối đa và tối thiểu đều được chứng minh áp dụng cho ego lane,
vNext dùng một câu duy nhất:

~~~
Giới hạn <N> ki-lô-mét/giờ và tối thiểu <M> ki-lô-mét/giờ.
~~~

Nếu có nhiều biển tốc độ nhưng chưa biết biển nào áp dụng cho ego lane, dùng
“Nhiều biển giới hạn tốc độ; xem làn mình.” và không đọc một con số tùy tiện.

Điều kiện bắt buộc trước khi đọc:

- biển được xác nhận qua nhiều frame;
- OCR/classifier thống nhất số tốc độ;
- bbox không bị trộn với biển khác;
- biển có vị trí, kích thước và hướng nhìn hợp lý;
- arbitration biết biển thuộc hướng/làn đang đi bằng metadata explicit như
  `applies_to_ego_lane=true`, `lane_binding_status=ego_lane/all_lanes` và
  `lane_binding_confidence >= 0.75`; nếu thiếu thì chỉ hiển thị ambiguity;
- cooldown theo speed-sign semantic key, mặc định 20 giây;
- nếu cùng frame có 60 và 80 mà chưa gắn được biển nào với lane ego, không được chọn ngẫu nhiên một số để đọc.

“Giới hạn <N> ki-lô-mét/giờ phía trước.” giữ đủ số, đơn vị và ngữ cảnh để
người nghe biết đây là thông tin về đoạn đường phía trước. Đây là Advisory,
không phải Critical; nếu TTS chưa sẵn sàng thì banner vẫn phải hiển thị số rõ
ràng.

### 5.2. Biển cấm đi vào

Đây là nhóm cần bảo thủ nhất vì biển có thể áp dụng cho hướng đối diện:

| Mức bằng chứng | Banner | TTS |
|---|---|---|
| Chưa xác định orientation | Biển cấm đi vào; kiểm tra hướng. | Không đọc mặc định; chỉ đọc nếu người dùng bật chế độ hỗ trợ |
| Đã xác định thuộc chiều đối diện | Biển cấm đi vào chiều đối diện. | Cấm đi vào chiều đối diện. |
| Đã xác định áp dụng cho ego lane | Biển cấm đi vào chiều này. | Cấm đi vào chiều này. |

Camera trước đơn thuần thường chưa đủ để xác nhận orientation tuyệt đối. Vì vậy không được đổi sang câu “Cấm đi vào chiều này” chỉ vì detector confidence cao; cần thêm lane geometry, hướng di chuyển, biển bổ sung hoặc bản đồ/OEM context trong phiên bản tương lai.

## 6. Ma trận phát âm thanh và chống quá tải

### 6.1. Quyền ưu tiên

Thứ tự đề xuất:

1. **Critical FCW/VRU/fallen rider:** beep + banner đỏ; preempt mọi advisory.
2. **Warning cut-in/cross-traffic/lead-braking/LDW:** một TTS ngắn nếu event đã temporal-confirmed.
3. **Advisory speed sign/stop/road work:** TTS chọn lọc theo relevance và cooldown.
4. **Informational/parking/hospital/green light:** HUD-only.

Không để một câu biển báo hoặc câu TTS đang phát che khuất beep Critical. Khi nguy cơ giảm, banner và âm thanh phải kết thúc theo lifecycle thay vì lặp lại cho mỗi frame.

### 6.2. Các giới hạn runtime nên giữ

Đây là các giá trị hiện có/đề xuất để kiểm thử, có thể tinh chỉnh bằng evidence:

~~~
Global audio gap: 2,5 giây
Advisory tối đa: 3 lần/phút/semantic key
Speed-sign cooldown: 20 giây
Cut-in/cross-traffic cooldown: 15 giây theo semantic key
Critical event: được preempt advisory khi risk tăng cấp
~~~

Global audio gap không được áp dụng theo cách làm chậm beep Critical. TTS candidate cũng không được dùng browser voice ngẫu nhiên vì có thể đọc tiếng Việt bằng giọng tiếng Anh; provider phải là VieNeu hoặc Piper tiếng Việt đã kiểm tra.

## 7. So sánh với catalog runtime hiện tại

Tại thời điểm viết tài liệu:

- runtime mặc định dùng catalog vNext; catalog tối đa 7 từ cũ vẫn được giữ ở profile legacy từ [ALERT_COPY_7_WORD_POLICY.md](./ALERT_COPY_7_WORD_POLICY.md);
- banner và TTS đã dùng chung canonical message;
- Piper là baseline fallback; VieNeu là candidate đã được đánh giá về độ rõ, tự nhiên và dứt khoát nhưng vẫn cần sửa/kiểm chứng lỗi mất âm đầu;
- các lỗi sai trái/phải và sai số biển tốc độ là lỗi perception/arbitration, không thể giải quyết chỉ bằng đổi giọng TTS;
- vNext đã sửa các template động trong risk.py, policy sign cần thay đổi trong signs.py, corpus trong tts.py, profile khởi chạy, health/status và cơ chế No Entry orientation. Đây là feature-flagged change để bảo toàn rollback.

### 7.1. Mapping triển khai sau khi được duyệt

| Mục tiêu | File/khối nên cập nhật |
|---|---|
| Template FCW/VRU/cut-in/cross-traffic/LDW | backend/roadwatch/risk.py |
| Policy và message biển báo | backend/roadwatch/signs.py |
| Orientation/no-entry/speed arbitration | backend/roadwatch/sign_arbitration.py và signs.py |
| Canonical equality và priority | backend/roadwatch/alerts.py |
| Corpus/pre-cache TTS | backend/roadwatch/tts.py, scripts/prepare_audio.py |
| TTS candidate/fallback | backend/roadwatch/tts_vieneu.py, tts.py |
| Regression và human gate evidence | tests/, docs/, reports/ |

Không dùng LLM/SLM để tự viết câu cảnh báo trong vòng Critical. Câu phải đến từ template/catalog đã review; model ngôn ngữ nếu có chỉ được dùng ngoài safety path cho phân tích kỹ sư.

## 8. Quality Gate cho catalog câu cảnh báo

### 8.1. Static gate

- 100% display_message == spoken_message cho mỗi event có TTS.
- Không còn “đã nhận diện”, “hệ thống phát hiện” trong driver-facing copy.
- Mỗi câu có chủ thể/nguy cơ và vị trí khi vị trí là điều kiện cần để phản ứng.
- Câu Critical không dài đến mức beep phải chờ TTS.
- Speed message bảo toàn đúng số và đơn vị.
- No-entry message không khẳng định chiều áp dụng khi orientation chưa đủ dữ liệu.
- Câu cross-traffic không dùng trái/phải nếu direction confidence thấp.
- Word count 7 vẫn được chạy như kiểm tra tương thích, nhưng là **soft warning** trong catalog vNext; không tự động cắt câu hợp lệ chỉ vì vượt 7 token.

### 8.2. Audio gate

- Corpus canonical sinh audio thành công 100%.
- Không mất 1–2 âm đầu sau khi phát trên browser và AAOS.
- Cùng một câu được nghe giống nghĩa trên Piper và VieNeu candidate.
- Cache hit bắt đầu phát trong mục tiêu khoảng ≤750 ms; uncached short alert khoảng ≤2 giây trên máy target đã công bố.
- 5 người nghe tiếng Việt độc lập chấm tối thiểu 4/5 cho rõ, tự nhiên, dứt khoát và đúng nghĩa; phải kiểm riêng các cặp trái/phải và các số 40/50/60/80.
- Kiểm thử thêm trong tiếng ồn mô phỏng cabin, không chỉ trong phòng yên tĩnh.

### 8.3. Event/video regression gate

- Critical FCW/VRU recall mục tiêu ≥0,95 trên tập có ground truth.
- False critical alert mục tiêu ≤0,1/phút.
- All-alert false positive mục tiêu ≤1/phút.
- Hướng trái/phải đúng ≥0,95 trên các clip đã gắn nhãn.
- Speed-sign value accuracy ≥0,98 trên tập biển đã khóa.
- Duplicate alert không tăng khi video pause/seek/chuyển video.
- Audio completion ≥99%, TTS error rate bằng 0 trên locked corpus.

Các chỉ số trên là target nội bộ của RoadWatch; không được trình bày như kết quả đạt được nếu chưa có evidence tương ứng.

## 9. Lộ trình áp dụng có fallback

~~~
Catalog runtime 7-word hiện tại
        ↓
Review tài liệu và chọn các câu vNext
        ↓
Unit test + static lint + kiểm tra canonical equality
        ↓
Audio benchmark Piper/VieNeu trên corpus khóa
        ↓
Human listening gate trong yên tĩnh và tiếng ồn
        ↓
Video regression direction/speed/sign/FCW/VRU
        ↓
Canary local/AAOS
        ↓
Promote từng nhóm event, không thay toàn bộ một lần
~~~

Nếu bất kỳ gate nào fail, quay về catalog hiện tại bằng cách giữ nguyên provider và runtime baseline; không xóa artifact, không force-push và không làm thay đổi model perception. Chỉ sau khi copy pass mới cập nhật corpus/pre-cache và triển khai provider mới.

## 10. Quyết định đề xuất cuối cùng

1. **Không công nhận giới hạn 7 từ là chuẩn bên ngoài.** Giữ nó như một kiểm tra tương thích mềm và baseline UX trong phiên bản hiện tại.
2. **Dùng 2–4 information units làm nguyên tắc chính** cho cảnh báo thận trọng; câu Critical ưu tiên beep/banner và cụm rất ngắn.
3. **Dùng “Cảnh báo va chạm” cho FCW Critical**, không mặc định dùng “Phanh ngay!” trong hệ thống chỉ cảnh báo.
4. **Chuẩn hóa hướng theo vùng xung đột**; phương tiện dùng “cắt ngang từ bên trái/phải”, còn người đi bộ an toàn có thể dùng “đang cắt ngang từ trái sang phải/phải sang trái”.
5. **Speed sign phải nói đúng số và đơn vị**, chỉ đọc theo ego-lane binding; nếu đồng thời có tối đa/tối thiểu cùng ego lane thì gộp thành một câu.
6. **No Entry mặc định không đọc nếu chưa biết hướng áp dụng**; dùng câu kiểm tra hướng hoặc các variant đã xác nhận orientation.
7. **Không để TTS tự dịch nội dung banner.** Một event chỉ có một canonical message đi qua cả HUD và audio.
8. **vNext đã được tích hợp qua profile thử nghiệm.** Chạy mặc định bằng vNext; nếu catalog không phù hợp, restart với legacy để quay về bản trước. Chỉ promote permanently sau video regression và human listening gate.

## 11. Tài liệu tham chiếu nội bộ

- [ALERT_COPY_7_WORD_POLICY.md](./ALERT_COPY_7_WORD_POLICY.md): lịch sử của baseline giới hạn 7 từ đã triển khai.
- [MASTER_ACTION_PLAN.md](./MASTER_ACTION_PLAN.md): blueprint kỹ thuật và quality gate tổng thể của RoadWatch.
- [UI_METRICS_AND_CLOUD_FLOW.md](./UI_METRICS_AND_CLOUD_FLOW.md): cách đo latency, audio và luồng cloud hiện tại.
- backend/roadwatch/risk.py: template event động.
- backend/roadwatch/signs.py: policy biển báo và speed-sign.
- backend/roadwatch/alerts.py: lifecycle, priority và canonical output.
- backend/roadwatch/tts.py: corpus, Piper baseline và gateway candidate.

---

**Giới hạn tuyên bố:** RoadWatch là hệ thống hỗ trợ/cảnh báo dựa trên camera và video replay. Tài liệu này không tuyên bố RoadWatch tự lái, tự phanh, đã có CAN/OEM calibration, hoặc đã đạt chứng nhận an toàn trên xe VinFast hay bất kỳ OEM nào.
