- 6 nhóm cảnh báo động.
- 71 chính sách biển báo.
- 44 chính sách biển báo có thể phát TTS.
- 27 chính sách chỉ hiển thị trên HUD.
- 55 câu được đưa vào corpus TTS mặc định để cache trước.
- Profile mặc định hiện tại: `vnext`.

Nguồn đối chiếu chính:

- [risk.py](D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/backend/roadwatch/risk.py)
- [alert_copy.py](D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/backend/roadwatch/alert_copy.py)
- [alerts.py](D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/backend/roadwatch/alerts.py)
- [signs.py](D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/backend/roadwatch/signs.py)

## 1. Luồng quyết định cảnh báo

```text
Model detection/lane/sign
→ Tracking
→ Kinematics và risk score
→ Xác nhận nhiều frame
→ AlertGovernor
→ Chọn cảnh báo ưu tiên
→ Hazard banner/HUD
→ TTS hoặc beep
```

Model chỉ tạo ra dữ liệu nhận thức. `AlertGovernor` mới là thành phần duy nhất được phép phát cảnh báo đến người dùng.

Một object được nhận diện nhưng chưa đủ điều kiện sẽ chỉ hiển thị bounding box, không phát cảnh báo.

## 2. Các kênh thông báo

| Kênh | Ý nghĩa |
|---|---|
| Bounding box/HUD | Cho biết object hoặc biển báo đang được nhận diện |
| Hazard banner | Hiển thị cảnh báo đang có mức ưu tiên cao nhất |
| Event History | Lưu cả cảnh báo đã phát và cảnh báo bị suppress |
| TTS | Đọc một cảnh báo đã được cấp quyền audio |
| Beep | Dùng cho cảnh báo critical |
| Metrics | Cho kỹ sư, không phải cảnh báo tài xế |

Quy tắc audio hiện tại:

- `critical` → `beep_tts`.
- `warning/advisory` → chỉ một event được cấp `tts` trong mỗi khoảng audio gap.
- Event còn lại → `hud`.
- `audio_eligible=false` → chỉ HUD, không TTS.
- Browser dùng Web Audio + WAV Piper.
- AAOS/native có thể dùng server speaker.

## 3. Cảnh báo động

### 3.1. FCW — nguy cơ va chạm phía trước

Câu critical:

```text
Cảnh báo va chạm
```

Câu warning:

```text
{đối tượng} {vị trí}; giảm tốc độ.
```

Ví dụ:

```text
Ô tô phía trước; giảm tốc độ.
Xe máy bên trái; giảm tốc độ.
Xe tải bên phải; giảm tốc độ.
```

Đối tượng có thể là:

- Ô tô
- Xe buýt
- Xe tải
- Xe máy
- Xe đạp
- Xe hai bánh

Điều kiện chính:

- Object phải được tracker xác nhận.
- Tuổi track tối thiểu khoảng `0.4 giây`.
- Có nguy cơ nằm trong ego path hoặc đang tiến vào ego path.
- Có relative closing rate hoặc near-field evidence.
- Bounding box đủ lớn.
- Risk score tối thiểu `0.56` cho warning.
- Critical cần risk cao hơn, proximity cao hơn và approach rõ hơn.
- Warning cần xác nhận tối thiểu 3 frame.
- Critical cần xác nhận tối thiểu 2 frame.
- Một object đã cảnh báo sẽ bị khóa bằng `fcw cooldown/hysteresis`.

FCW không dựa trực tiếp vào khoảng cách mét nếu camera chưa được calibration. Runtime hiện dùng image-space risk và relative scale.

### 3.2. VRU — người đi bộ, xe máy, xe đạp

Câu cảnh báo:

```text
{đối tượng} {vị trí}; giảm tốc độ.
```

Ví dụ:

```text
Người đi bộ phía trước; giảm tốc độ.
Người đi bộ bên trái; giảm tốc độ.
Xe máy bên phải; giảm tốc độ.
Xe đạp phía trước; giảm tốc độ.
```

Điều kiện chính:

- Nhãn thuộc `person`, `rider`, `motorcycle`, `bicycle`.
- Object nằm trên vùng có thể lái hoặc trong ego lane.
- Có path conflict.
- Proximity tối thiểu `0.10`.
- Track tồn tại tối thiểu `0.4 giây`.
- Risk tối thiểu `0.52`, trừ một số near-field fallback.
- Xác nhận tối thiểu 3 frame.

Người đi bộ trên vỉa hè, không nằm trong ego path và không có path conflict sẽ không nên phát VRU.

### 3.3. Lead vehicle braking

Chỉ áp dụng cho:

- Ô tô
- Xe buýt
- Xe tải

Câu cảnh báo:

```text
Ô tô phía trước đang giảm tốc. Hãy chú ý.
Xe buýt phía trước đang giảm tốc. Hãy chú ý.
Xe tải phía trước đang giảm tốc. Hãy chú ý.
```

Điều kiện:

- Phương tiện nằm trong path phía trước.
- Track đã ổn định tối thiểu `0.4 giây`.
- Có một trong hai loại bằng chứng:
  - Kinematic image-space: relative rate và acceleration tăng.
  - Brake-light heuristic: phát hiện vùng đỏ dạng hai đèn.
- Cue phải duy trì tối thiểu 3 frame.
- Đây chưa phải tốc độ tuyệt đối của xe phía trước.
- Chưa có CAN, ego speed hoặc radar nên đây là cảnh báo giảm tốc tương đối.

### 3.4. Cut-in — phương tiện nhập làn

Câu cảnh báo:

```text
{đối tượng} nhập làn từ bên trái. Hãy chú ý.
{đối tượng} nhập làn từ bên phải. Hãy chú ý.
```

Ví dụ:

```text
Xe máy nhập làn từ bên phải. Hãy chú ý.
Ô tô nhập làn từ bên trái. Hãy chú ý.
Xe tải nhập làn từ bên phải. Hãy chú ý.
```

Đối tượng hiện được phép:

- Xe máy
- Xe đạp
- Xe hai bánh
- Ô tô
- Xe buýt
- Xe tải

Người đi bộ hiện không được đưa vào nhóm cut-in trong runtime hiện tại để tránh trường hợp người đi bộ đi trên vỉa hè bị báo nhầm là nhập làn.

Điều kiện:

- Object ban đầu nằm ngoài ego lane.
- Có chuyển động hướng vào tâm làn.
- Có displacement ngang đủ lớn.
- Có projection đi vào corridor của ego lane.
- Track tồn tại tối thiểu `0.5 giây`.
- Không chỉ dựa trên một frame.
- Xác nhận quỹ đạo tối thiểu 2 frame.
- Có cooldown theo maneuver.

### 3.5. Cross-traffic — đối tượng cắt ngang

Với phương tiện:

```text
Xe máy cắt ngang từ bên trái.
Xe máy cắt ngang từ bên phải.
Ô tô cắt ngang từ phía trước.
Xe tải cắt ngang từ bên phải.
Xe đạp cắt ngang từ bên trái.
```

Với người đi bộ:

```text
Người đi bộ đang cắt ngang từ trái sang phải.
Người đi bộ đang cắt ngang từ phải sang trái.
Người đi bộ đang cắt ngang phía trước.
```

Điều kiện:

- Object nằm ngoài ego lane.
- Có lateral displacement và lateral velocity.
- Chuyển động ngang phải chiếm ưu thế so với chuyển động dọc.
- Có ít nhất 5 quan sát chuyển động.
- Với ô tô, xe buýt, xe tải cần confidence và số quan sát cao hơn.
- Không đồng thời là cut-in.
- Không phải near-field imminent đã chuyển thành FCW.
- Phải có path conflict hoặc hướng tiến vào ego corridor.
- Người đi bộ đi ngang an toàn ở tốc độ thấp chỉ tạo cảnh báo cross-traffic mức warning nếu đủ điều kiện.

### 3.6. LDW — lệch làn

Câu cảnh báo:

```text
Cảnh báo lệch làn bên trái.
Cảnh báo lệch làn bên phải.
```

Điều kiện:

- Lane quality tối thiểu `0.48`.
- Lane offset vượt `0.34`.
- Độ lệch duy trì ít nhất 5 frame.
- Nếu lane quality thấp, LDW bị khóa.
- Nếu lane detection không chắc chắn, hệ thống không được cảnh báo lệch làn.

## 4. Biển giới hạn tốc độ

### 4.1. Biển tốc độ tối đa

Runtime nhận các giá trị:

```text
10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120
```

Câu thông báo:

```text
Giới hạn {tốc độ} ki-lô-mét/giờ phía trước.
```

Ví dụ:

```text
Giới hạn 60 ki-lô-mét/giờ phía trước.
Giới hạn 80 ki-lô-mét/giờ phía trước.
```

### 4.2. Biển tốc độ tối thiểu

Câu thông báo:

```text
Tối thiểu {tốc độ} ki-lô-mét/giờ phía trước.
```

### 4.3. Có cả tốc độ tối đa và tối thiểu

Chỉ dùng khi cả hai biển được chứng minh thuộc ego lane:

```text
Giới hạn 80 ki-lô-mét/giờ và tối thiểu 60 ki-lô-mét/giờ.
```

### 4.4. Nhiều biển tốc độ nhưng chưa xác định được làn

Câu hiển thị:

```text
Nhiều biển giới hạn tốc độ; xem làn mình.
```

Hoặc:

```text
Nhiều biển tốc độ tối thiểu; xem làn mình.
```

Trạng thái này hiện `audio_eligible=false`, nghĩa là chỉ hiển thị HUD, không đọc TTS để tránh đọc sai biển của làn bên cạnh.

Điều kiện để biển tốc độ được xác nhận:

- Detection có geometry hợp lệ.
- Kích thước biển hợp lý.
- Đúng aspect ratio.
- Đúng vị trí trong ảnh.
- Có red-ring visual evidence hoặc fallback confidence + motion.
- Xuất hiện tối thiểu 3 lần.
- Duy trì tối thiểu `0.25 giây`.
- Nếu có nhiều biển, `sign_arbitration` sẽ chọn biển phù hợp ego lane.

## 5. Biển cấm đi vào

Mặc định vNext:

```text
Biển cấm đi vào; kiểm tra hướng.
```

Câu này chỉ hiển thị HUD, không phát TTS vì camera trước chưa đủ biết biển áp dụng cho chiều nào.

Chỉ khi có orientation evidence confidence tối thiểu `0.85`:

```text
Cấm đi vào chiều đối diện.
```

hoặc:

```text
Cấm đi vào chiều này.
```

Đây là một guardrail quan trọng để không làm tài xế hoảng loạn khi hệ thống chưa xác định được hướng áp dụng.

## 6. Toàn bộ chính sách biển báo hiện tại

### 6.1. Biển có thể TTS hoặc HUD

| Nhãn model | Nội dung |
|---|---|
| Stop | Biển báo dừng phía trước. |
| Red Light | Đèn đỏ phía trước. |
| Traffic light ahead | Đèn tín hiệu phía trước. |
| Pedestrian Crossing | Lối sang đường phía trước. |
| Pedestrian Lane | Làn người đi bộ phía trước. |
| Children Crossing | Khu vực trẻ em; giảm tốc. |
| Road Work Ahead | Công trường phía trước; giảm tốc. |
| Accident area | Khu vực tai nạn; giảm tốc. |
| Obstacle on the Road | Chướng ngại vật phía trước; giảm tốc. |
| Slippery Road | Đường trơn; giảm tốc. |
| Speed Bump | Gờ giảm tốc phía trước. |
| Uneven road | Mặt đường gồ ghề phía trước. |
| Danger | Nguy hiểm phía trước. |
| Slow Down | Giảm tốc phía trước. |
| Level Crossing with Barriers | Giao cắt đường sắt; giảm tốc. |
| Narrow bridge | Cầu hẹp phía trước. |
| Narrow Road Left Side | Đường hẹp bên trái. |
| Narrow Road Right Side | Đường hẹp bên phải. |
| Narrow road both sides | Đường hẹp hai bên. |
| Sharp Left Turn | Cua gấp bên trái. |
| Sharp Right Turn | Cua gấp bên phải. |
| Double curve first to right | Nhiều cua; đầu tiên bên phải. |
| Steep ascent | Dốc lên phía trước. |
| No Overtaking | Cấm vượt phía trước. |
| No Two or Three-wheeled Vehicles | Phía trước cấm xe hai, ba bánh. |
| No Cars | Phía trước cấm ô tô. |
| No Trucks | Phía trước cấm xe tải. |
| No Trucks and Bus | Phía trước cấm xe tải, xe buýt. |
| Low Clearance | Chiều cao giới hạn phía trước. |
| Height Limit | Chiều cao giới hạn phía trước. |
| Roundabout | Vòng xuyến phía trước. |
| Lane Allocation | Biển phân làn phía trước. |
| One way street | Đường một chiều phía trước. |
| End of all prohibition | Hết các lệnh cấm phía trước. |
| End of 50km/h speed limit | Hết giới hạn 50 ki-lô-mét/giờ. |
| No Moto | Cấm xe máy. |
| No bus | Cấm xe buýt. |
| No Horns | Cấm dùng còi. |
| Intersection with a Priority Road | Giao nhau đường ưu tiên. |
| Intersection with Equal Roads | Giao nhau đường đồng cấp. |
| Intersection with a Minor Road | Giao nhau đường nhánh. |
| Residential area | Vào khu đông dân cư. |
| sparsely populated area | Rời khu đông dân cư. |
| Dual carriageway | Bắt đầu đường đôi. |

Các biển trên không phải lúc nào cũng phát TTS. Chúng vẫn phải đi qua geometry gate, temporal confirmation, sign arbitration, cooldown và audio priority.

### 6.2. Biển chỉ hiển thị HUD

| Nhãn model | Nội dung |
|---|---|
| No Entry | Biển cấm đi vào; kiểm tra hướng. |
| Parking | Khu vực đỗ xe. |
| Bus Stop | Điểm dừng xe buýt. |
| Hospital | Bệnh viện phía trước. |
| Green Light | Đèn xanh phía trước. |
| U-Turn Area | Khu vực quay đầu phía trước. |
| Road with Surveillance Camera | Camera giám sát phía trước. |
| No Stopping & No Parking | Cấm dừng và đỗ. |
| No Parking | Cấm đỗ xe. |
| No Parking Odd Days | Cấm đỗ ngày lẻ. |
| Even Days | Hạn chế đỗ ngày chẵn. |
| No Left Turn | Phía trước cấm rẽ trái. |
| No Right Turn | Phía trước cấm rẽ phải. |
| No U-Turn | Phía trước cấm quay đầu. |
| No U-Turn and No Left Turn | Phía trước cấm quay đầu, rẽ trái. |
| No U-Turn and No Right Turn | Phía trước cấm quay đầu, rẽ phải. |
| No U-Turn for Cars | Phía trước cấm ô tô quay đầu. |
| No left turn for cars | Phía trước cấm ô tô rẽ trái. |
| No Motobike Left Turn | Phía trước cấm xe máy rẽ trái. |
| No Straight and Right Turn | Cấm đi thẳng, rẽ phải. |
| No Left or Right Turn | Cấm rẽ trái, rẽ phải. |
| No U-Turn and Left Turn for Cars | Cấm ô tô quay đầu, rẽ trái. |
| Turn Left Only | Phía trước chỉ được rẽ trái. |
| Turn Right Only | Phía trước chỉ được rẽ phải. |
| Turn Left | Hướng đi được rẽ trái phía trước. |
| Turn Right | Hướng đi được rẽ phải phía trước. |
| Keep left | Giữ bên trái phía trước. |

Nhóm này bị tắt audio vì mô tả hướng đi, cấm rẽ hoặc giữ làn có thể bị hiểu
thành chỉ đạo đánh lái khi RoadWatch không có GPS, bản đồ hay quyền điều khiển.
Các biển `No Entry` chỉ được đọc khi có bằng chứng orientation đủ tin cậy; nếu
không, banner vẫn ghi rõ cần kiểm tra hướng.

### 6.3. Dense traffic context

Khi `ROADWATCH_TRAFFIC_CONTEXT_MODE=enforce` và context đã xác nhận giao thông
đông, các event vẫn được lưu vào Event History nhưng chỉ event có nguy cơ tác
động lên ego path mới được phát audio. Speed sign và event rủi ro thấp chuyển
sang `HUD-only`; FCW critical luôn được phép preempt. Chi tiết ngưỡng và cơ chế
fallback nằm trong [TRAFFIC_CONTEXT_ALERT_POLICY.md](TRAFFIC_CONTEXT_ALERT_POLICY.md).

## 7. Cơ chế chống cảnh báo liên tục hiện tại

Các giới hạn hiện đang dùng:

```text
Global audio gap: 2.5 giây
Warning cooldown: 12 giây
Cut-in/cross-traffic cooldown: 15 giây
Critical cooldown: 2 giây
Traffic-sign cooldown: 20 giây
Advisory tối đa: 3 lần/phút/semantic key
LDW confirmation: 5 frame
Object confirmation: 3 frame
Traffic-sign confirmation: 3 hit và 0.25 giây
```

Ngoài ra còn có:

- Gộp nhiều cảnh báo cùng một object.
- Critical được ưu tiên hơn advisory.
- Một cảnh báo critical có thể preempt biển báo.
- Sign arbitration chọn một biển trong cùng nhóm.
- Banner chỉ hiển thị event active có ưu tiên cao nhất.
- Audio browser chỉ xử lý một event tại một thời điểm.

## 8. Vì sao vẫn có thể xuất hiện cảnh báo liên tục?

Đây là điểm quan trọng: Rule Engine hiện đã có cooldown, nhưng model không ổn định vẫn có thể tạo ra nhiều semantic key khác nhau.

Các nguyên nhân thường gặp:

- Cùng một xe lúc được nhận là `car`, lúc thành `truck`.
- Object di chuyển từ `bên trái` sang `phía trước`, tạo cooldown key khác.
- Một nguy cơ lần lượt chuyển từ `cross_traffic` → `cut_in` → `fcw`.
- Track bị mất rồi tạo lại, làm trạng thái confirmation khởi động lại.
- Lane model dao động khiến trạng thái `in_ego_lane` thay đổi.
- Biển báo bị đổi class hoặc đổi số tốc độ.
- Mức risk tăng từ warning lên critical nên được phép phát lại.
- Một cảnh báo hết TTL rồi được tạo lại bởi detection mới.
- Banner và bounding box có thể nhấp nháy ngay cả khi TTS đã bị suppress.

Vì vậy, hiện tượng cảnh báo liên tục không chỉ là lỗi Rule Engine. Nó chủ yếu là tương tác giữa:

```text
Model quality
+ tracking stability
+ lane stability
+ semantic event key
+ risk threshold
+ cooldown policy
```

Kết luận hiện tại:

- Cơ chế chống quá tải đã tồn tại.
- Nhưng với chất lượng object/lane model hiện tại, nó chưa đủ mạnh để đạt trải nghiệm production.
- Trước khi chốt bản final, nên khóa lại một chính sách mới theo hướng:
  - Một nguy cơ vật lý chỉ có một `hazard_id`.
  - Không đổi câu liên tục khi chỉ thay đổi vị trí nhỏ.
  - Warning không được lặp nếu risk không tăng.
  - Critical chỉ phát lại khi nguy cơ thực sự tăng cấp.
  - Người đi bộ an toàn ngoài ego path không được cảnh báo.
  - Biển báo không có lane relevance chỉ hiển thị HUD.
  - Event History vẫn lưu đầy đủ, nhưng tài xế chỉ nghe cảnh báo quan trọng.

Đây là danh sách và hành vi của runtime hiện tại; tôi chưa thay đổi rule hoặc nội dung cảnh báo ở bước này để chúng ta thống nhất trước.
