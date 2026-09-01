# RoadWatch — Catalog cảnh báo `legacy` và `vNext` đã hiệu chỉnh

**Ngày cập nhật:** 2026-08-27  
**Trạng thái:** `vNext-proposed-for-owner-review`  
**Phạm vi:** câu hiển thị HUD, câu TTS tiếng Việt, quyền phát beep và điều kiện
phát cho cảnh báo động cùng 71 nhãn biển báo hiện có.

> Đây là catalog nội dung để review. Bản cập nhật này **chưa tự động thay đổi
> runtime**. Runtime hiện vẫn có thể chạy `vnext` hoặc fallback `legacy`; chỉ
> cập nhật `backend/roadwatch/alert_copy.py`/`signs.py` sau khi chủ dự án duyệt
> từng nhóm câu và chạy lại regression/audio gate.

## 1. Mục tiêu thiết kế

RoadWatch là hệ thống cảnh báo hỗ trợ lái, không phải hệ thống tự lái. Một câu
cảnh báo phải giúp tài xế trả lời nhanh ba câu hỏi: **đối tượng nào, ở đâu, cần
phản ứng gì**. Câu chữ không được giả vờ chắc chắn khi perception chưa chứng
minh được hướng, làn hoặc mức nguy hiểm.

### 1.1 Nguyên tắc đã dùng để viết lại

- **Critical:** chỉ nói phần tối quan trọng; beep/hazard đỏ truyền mức khẩn cấp,
  TTS không thêm chỉ thị phanh/đánh lái.
- **Warning:** nêu đối tượng + vị trí + hành động ngắn; không lặp lại cùng một
  sự kiện khi risk không tăng.
- **Advisory:** chỉ nói khi có temporal confirmation và relevance với ego lane;
  biển nhìn thấy một frame chưa đủ điều kiện đọc.
- **HUD-only:** dùng cho thông tin ít khẩn cấp, hướng áp dụng chưa xác định hoặc
  câu có thể khiến tài xế hiểu nhầm tình huống.
- **Canonical message:** HUD và TTS phải nhận cùng một `message`/`event_id`;
  frontend không rút gọn riêng và TTS không tự dịch lại.
- **Không suy diễn từ class:** `person` đi trên vỉa hè không phải cut-in; một
  biển `No Entry` không chứng minh nó áp dụng cho chiều xe đang đi; một detector
  speed không chứng minh số tốc độ thuộc làn ego.
- **Punctuation là nhịp đọc:** dấu chấm phẩy tạo khoảng nghỉ ngắn; không dùng
  câu quá dài chỉ để nhồi nhiều sự kiện vào một lần phát.
- **Quy tắc 7 từ:** là ngân sách tương thích của `legacy`, không phải tiêu chuẩn
  an toàn cứng. `vNext` ưu tiên đủ chủ thể/vị trí/hành động; chỉ cần giữ hard
  ceiling hiện tại `12` từ và kiểm tra thời lượng nghe bằng human listening gate.

`legacy` giữ nguyên catalog đã dùng làm fallback. `vNext` dưới đây là bản copy
đề xuất mới, được thiết kế để giảm câu mơ hồ, giảm cảnh báo thừa trong giao
thông đông và không làm perception error trông như lỗi TTS.

## 2. Điều phối cảnh báo và quyền phát âm thanh

### 2.1 Thứ tự ưu tiên

```text
Critical collision / VRU danger
        ↓ preempt
Warning maneuver / lead braking / LDW
        ↓ preempt
Advisory traffic sign / safe crossing
        ↓
HUD-only information
```

Quy tắc runtime cần giữ khi catalog được áp dụng:

- Critical được phát beep ngay khi đạt temporal confirmation; TTS chỉ phát nếu
  audio queue còn phù hợp. Critical có thể ngắt advisory.
- Khoảng cách giữa hai audio event thông thường tối thiểu `2.5 giây`.
- Cùng một advisory semantic key tối đa `3 lần/phút`; speed-sign cùng giá trị
  có cooldown `20 giây`.
- Một đối tượng chỉ có một lifecycle cảnh báo đang hoạt động. Cross-traffic
  không được phát thêm nếu cùng frame đã được nâng thành VRU/FCW.
- Người đi bộ trên vỉa hè, phương tiện chạy ổn định cùng hướng và dòng xe đông
  nhưng không có path conflict: **không phát TTS**.
- Cảnh báo chỉ được phát lại sớm hơn cooldown khi risk tăng cấp, track mới có
  path conflict rõ ràng hoặc đối tượng rời rồi tái nhập vùng nguy hiểm.

### 2.2 Các ngưỡng không được hiểu là chất lượng model

`risk`, `confidence`, `lane_binding` và `TTC proxy` là bằng chứng khác nhau.
Rule engine chỉ được phát câu khi evidence đủ; đổi câu chữ không thể sửa lỗi
nhận nhầm xe máy thành người đi bộ, sai trái/phải hoặc đọc sai số tốc độ. Các
lỗi đó phải quay về perception, tracking, sign arbitration hoặc ground truth.

## 3. Cảnh báo động — bảng đối chiếu hoàn chỉnh

Trong bảng, `{đối tượng}` thuộc tập `Người đi bộ`, `Xe đạp`, `Xe máy`, `Ô tô`,
`Xe buýt`, `Xe tải`; `{bên}` là `bên trái` hoặc `bên phải` theo góc nhìn camera
ego. `vNext` là câu đề xuất, chưa phải quyết định promote.

| Tình huống | Legacy | vNext đề xuất | Audio và điều kiện |
|---|---|---|---|
| FCW critical | `Cảnh báo va chạm phía trước!` | `Cảnh báo va chạm` | Beep + TTS khi risk critical, temporal confirmation và path conflict. Không đọc thêm “hãy phanh”. |
| FCW warning | `{đối tượng} {vị trí}; tiến gần.` | `{đối tượng} {vị trí}; giảm tốc độ.` | TTS khi closing trend tăng và đối tượng nằm trong ego path. |
| VRU nguy hiểm | `{đối tượng} {vị trí}; giảm tốc.` | `{đối tượng} {vị trí}; giảm tốc độ.` | Critical/warning theo risk; ưu tiên hơn cross-traffic. |
| Người/xe máy ngã trong ego path | Không có catalog riêng | `Có người ngã phía trước; giảm tốc độ.` hoặc `Xe máy ngã phía trước; giảm tốc độ.` | Chỉ khi fallen state bền vững qua nhiều frame và có path relevance. |
| Lead braking — ô tô | `Ô tô phía trước; giảm tốc.` | `Ô tô phía trước đang giảm tốc. Hãy chú ý.` | Chỉ phương tiện; cần closing trend ổn định, không cần nhận diện đèn phanh. |
| Lead braking — xe buýt | `Xe buýt phía trước; giảm tốc.` | `Xe buýt phía trước đang giảm tốc. Hãy chú ý.` | Như trên. |
| Lead braking — xe tải | `Xe tải phía trước; giảm tốc.` | `Xe tải phía trước đang giảm tốc. Hãy chú ý.` | Như trên. |
| Cut-in phương tiện từ trái | `{đối tượng} phía trước bên trái; nhập làn.` | `{đối tượng} nhập làn từ bên trái. Hãy chú ý.` | Chỉ `car/bus/truck/motorcycle/bicycle` khi có quỹ đạo tiến vào ego lane; cooldown theo maneuver. |
| Cut-in phương tiện từ phải | `{đối tượng} phía trước bên phải; nhập làn.` | `{đối tượng} nhập làn từ bên phải. Hãy chú ý.` | Không phát chỉ vì phương tiện chạy song song hoặc rời rồi nhập lại mà chưa có conflict mới. |
| Người đi bộ trên vỉa hè | Có thể bị báo như cut-in | **Không tạo cut-in** | Không TTS/HUD maneuver; chỉ theo dõi nếu người tiến vào vùng xe. |
| Cross-traffic phương tiện, nguy cơ từ trái | `{đối tượng} cắt trái sang phải.` | `{đối tượng} cắt ngang từ bên trái.` | TTS khi lateral motion rõ, nhanh/gần hoặc path conflict; không đọc mọi xe máy trong giờ cao điểm. |
| Cross-traffic phương tiện, nguy cơ từ phải | `{đối tượng} cắt phải sang trái.` | `{đối tượng} cắt ngang từ bên phải.` | Như trên. |
| Cross-traffic phương tiện an toàn | `{đối tượng} cắt trái sang phải.` | **HUD-only hoặc im lặng** | Khi đối tượng ở ngoài ego path, tốc độ ego thấp và risk không tăng. |
| Người đi bộ qua đường an toàn | `Người đi bộ cắt trái sang phải.` | `Người đi bộ đang cắt ngang từ trái sang phải.` | Chỉ một advisory nếu người ở gần vùng quan sát; không phát lặp trong dòng người đi bộ an toàn. |
| Người đi bộ cắt ngang nguy hiểm | `Người đi bộ cắt trái sang phải.` | `Người đi bộ phía trước; giảm tốc độ.` | Nâng thành VRU/FCW; không phát thêm câu cross-traffic. |
| Xe hai bánh cắt ngang nguy hiểm | `Xe hai bánh cắt trái sang phải.` | `Xe máy cắt ngang từ bên trái.` | Dùng class đã được track-level xác nhận; nếu chỉ biết “hai bánh” thì dùng `Xe hai bánh`. |
| LDW trái | `Lệch làn bên trái.` | `Cảnh báo lệch làn bên trái.` | TTS/beep warning khi lane quality đủ, offset/hướng lệch ổn định qua nhiều frame. |
| LDW phải | `Lệch làn bên phải.` | `Cảnh báo lệch làn bên phải.` | Như trên. |
| Không đủ bằng chứng | `Hãy chú ý.` | `Hãy chú ý.` | Fallback an toàn; không dùng để thay thế một event cụ thể đã biết. |
| Nhiều speed sign, chưa bind ego lane | Không có câu riêng | `Nhiều biển tốc độ; chưa rõ làn áp dụng.` | HUD-only; không đọc số bất kỳ. |

### 3.1 Ví dụ và cách tránh cảnh báo quá tải

| Quan sát thực tế | Kết luận đúng | Audio |
|---|---|---|
| Mười xe máy chạy cùng chiều, không cắt quỹ đạo ego | Dense traffic bình thường | Không TTS; hiển thị số track nếu cần. |
| Xe máy từ phải tiến vào corridor ego, lateral displacement tăng và khoảng cách giảm | Cut-in hoặc FCW tùy risk | Một câu cut-in warning; nếu risk tăng thì thay bằng FCW critical. |
| Người đi bộ đi dọc vỉa hè, không tiến vào corridor | Không phải cut-in | Im lặng. |
| Người đi bộ băng qua nhưng ego rất chậm, còn ngoài conflict zone | Safe cross-traffic | Có thể HUD-only hoặc một câu advisory, không lặp. |
| Người đi bộ bất ngờ bước vào corridor | VRU danger | `Người đi bộ phía trước; giảm tốc độ.` hoặc `Cảnh báo va chạm`; không phát câu safe-crossing. |
| Ô tô vào làn, ra làn rồi vào lại khi risk không tăng | Một maneuver lifecycle | Không phát lại cho tới khi re-arm và có evidence mới. |

## 4. Speed sign, minimum speed và nhiều làn

### 4.1 Câu canonical

| Tình huống | Legacy | vNext đề xuất | Audio |
|---|---|---|---|
| Giới hạn tối đa `{N}` | `Tối đa {N} ki-lô-mét/giờ.` | `Giới hạn {N} ki-lô-mét/giờ phía trước.` | Có sau ít nhất 3 hit/temporal confirmation và sign geometry hợp lệ. |
| Giới hạn tối thiểu `{N}` | Chưa chuẩn hóa | `Tối thiểu {N} ki-lô-mét/giờ phía trước.` | Chỉ khi minimum-sign được phân loại chắc chắn. |
| Cả tối đa `{MAX}` và tối thiểu `{MIN}` cùng ego lane | `Tối đa {MAX}; tối thiểu {MIN}.` | `Làn này giới hạn {MAX} ki-lô-mét/giờ; tối thiểu {MIN}.` | Chỉ đọc khi cả hai sign có lane binding đủ tin cậy. |
| Hết giới hạn `{N}` | `Hết giới hạn {N} ki-lô-mét/giờ.` | `Hết giới hạn {N} ki-lô-mét/giờ.` | Advisory, cooldown theo semantic key. |
| Có nhiều số tốc độ nhưng chưa xác định làn | `Nhiều biển tốc độ; xem làn mình.` | `Nhiều biển tốc độ; chưa rõ làn áp dụng.` | HUD-only, không TTS. |

Các giá trị hiện có trong taxonomy gồm `10, 20, 30, 40, 50, 60, 70, 80, 90,
100, 110, 120` và dạng nhãn `Speed limit Nkm/h`. Giá trị `10` được giữ vì là
class dữ liệu; việc hiếm gặp ngoài thực tế không phải lý do để remap nhầm sang
`40` hoặc bỏ qua annotation.

### 4.2 Chính sách nhiều làn

1. Xác định ego lane bằng lane mask/geometry và track hướng di chuyển.
2. Gắn sign vào lane bằng vị trí, hướng mặt biển, độ cao/độ lớn tương đối và
   temporal tracking.
3. Nếu bind được, chỉ đọc sign áp dụng cho làn hiện tại: `Làn này giới hạn ...`.
4. Nếu tài xế đổi làn sau khi đã nghe cảnh báo, không phát lại sign cũ chỉ vì
   nó còn trong frame; cần một sign/lane lifecycle mới.
5. Nếu hai sign mâu thuẫn mà chưa bind được, HUD ghi ambiguity và TTS im lặng.

## 5. Biển cấm đi vào — policy bắt buộc theo hướng

Detector chỉ chứng minh `No Entry`; camera monocular không tự chứng minh sign áp
dụng cho chiều nào. Vì vậy vNext phải tách ba trạng thái:

| Trạng thái orientation | HUD canonical | TTS | Điều kiện |
|---|---|---|---|
| Chưa rõ | `Biển cấm đi vào; chưa rõ hướng.` | Không phát | Mặc định an toàn khi thiếu orientation evidence. |
| Áp dụng cho chiều đối diện | `Cấm đi vào chiều đối diện.` | `Cấm đi vào chiều đối diện.` | Orientation status hợp lệ, confidence `>= 0.85`. |
| Áp dụng cho chiều ego | `Cảnh báo: cấm đi vào chiều này.` | `Cảnh báo: cấm đi vào chiều này.` | Chỉ khi có orientation/lane evidence đáng tin cậy; severity cao hơn advisory. |

Không dùng câu trần `Cấm đi vào` khi chưa biết hướng. Đây là một guardrail nội
dung, không phải bằng chứng rằng model đã giải được orientation.

## 6. Toàn bộ 71 biển báo — mapping legacy/vNext

`Audio` ở đây là quyền phát TTS sau khi sign đã qua temporal confirmation,
geometry gate và sign arbitration. `Không` là HUD-only mặc định; không có nghĩa
detector không được phép nhận diện.

| # | Detector label | Legacy | vNext đề xuất | Audio vNext |
|---:|---|---|---|:---:|
| 1 | No Entry | `Biển cấm đi vào; kiểm tra hướng.` | `Biển cấm đi vào; chưa rõ hướng.` | Không* |
| 2 | Stop | `Biển dừng phía trước.` | `Biển dừng phía trước.` | Có |
| 3 | Red Light | `Đèn đỏ phía trước.` | `Đèn đỏ phía trước.` | Có |
| 4 | Traffic light ahead | `Đèn tín hiệu phía trước.` | `Đèn tín hiệu phía trước.` | Có |
| 5 | Pedestrian Crossing | `Người đi bộ sang đường.` | `Lối sang đường phía trước.` | Có |
| 6 | Pedestrian Lane | `Làn người đi bộ phía trước.` | `Lối đi bộ phía trước.` | Có |
| 7 | Children Crossing | `Trẻ em sang đường; giảm tốc.` | `Khu vực trẻ em; giảm tốc.` | Có |
| 8 | Road Work Ahead | `Công trường phía trước; giảm tốc.` | `Công trường phía trước; giảm tốc.` | Có |
| 9 | Accident area | `Khu vực tai nạn; giảm tốc.` | `Khu vực tai nạn; giảm tốc.` | Có |
| 10 | Obstacle on the Road | `Chướng ngại vật phía trước.` | `Chướng ngại vật phía trước; giảm tốc.` | Có |
| 11 | Slippery Road | `Đường trơn; giảm tốc.` | `Đường trơn; giảm tốc.` | Có |
| 12 | Speed Bump | `Gờ giảm tốc phía trước.` | `Gờ giảm tốc phía trước.` | Có |
| 13 | Uneven road | `Mặt đường gồ ghề.` | `Mặt đường gồ ghề.` | Có |
| 14 | Danger | `Nguy hiểm phía trước.` | `Cảnh báo nguy hiểm phía trước.` | Có |
| 15 | Slow Down | `Giảm tốc phía trước.` | `Giảm tốc độ phía trước.` | Có |
| 16 | Level Crossing with Barriers | `Giao cắt đường sắt; giảm tốc.` | `Giao cắt đường sắt; giảm tốc.` | Có |
| 17 | Narrow bridge | `Cầu hẹp phía trước.` | `Cầu hẹp phía trước.` | Có |
| 18 | Narrow Road Left Side | `Đường hẹp bên trái.` | `Đường hẹp bên trái.` | Có |
| 19 | Narrow Road Right Side | `Đường hẹp bên phải.` | `Đường hẹp bên phải.` | Có |
| 20 | Narrow road both sides | `Đường hẹp hai bên.` | `Đường hẹp hai bên.` | Có |
| 21 | Sharp Left Turn | `Cua gấp bên trái.` | `Cua gấp bên trái.` | Có |
| 22 | Sharp Right Turn | `Cua gấp bên phải.` | `Cua gấp bên phải.` | Có |
| 23 | Double curve first to right | `Nhiều cua; đầu tiên bên phải.` | `Nhiều cua; đầu tiên bên phải.` | Có |
| 24 | Steep ascent | `Dốc lên phía trước.` | `Dốc lên phía trước.` | Có |
| 25 | No Overtaking | `Cấm vượt phía trước.` | `Cấm vượt phía trước.` | Có |
| 26 | No Left Turn | `Cấm rẽ trái.` | `Cấm rẽ trái.` | Có |
| 27 | No Right Turn | `Cấm rẽ phải.` | `Cấm rẽ phải.` | Có |
| 28 | No U-Turn | `Cấm quay đầu.` | `Cấm quay đầu.` | Có |
| 29 | No U-Turn and No Left Turn | `Cấm quay đầu, rẽ trái.` | `Cấm quay đầu và rẽ trái.` | Có |
| 30 | No U-Turn and No Right Turn | `Cấm quay đầu, rẽ phải.` | `Cấm quay đầu và rẽ phải.` | Có |
| 31 | No U-Turn for Cars | `Cấm ô tô quay đầu.` | `Cấm ô tô quay đầu.` | Có |
| 32 | No left turn for cars | `Cấm ô tô rẽ trái.` | `Cấm ô tô rẽ trái.` | Có |
| 33 | No Motobike Left Turn | `Cấm xe máy rẽ trái.` | `Cấm xe máy rẽ trái.` | Có |
| 34 | No Two or Three-wheeled Vehicles | `Cấm xe hai, ba bánh.` | `Cấm xe hai và ba bánh.` | Có |
| 35 | No Cars | `Cấm ô tô.` | `Cấm ô tô phía trước.` | Có |
| 36 | No Trucks | `Cấm xe tải.` | `Cấm xe tải phía trước.` | Có |
| 37 | No Trucks and Bus | `Cấm xe tải, xe buýt.` | `Cấm xe tải và xe buýt.` | Có |
| 38 | Low Clearance | `Giới hạn chiều cao phía trước.` | `Giới hạn chiều cao phía trước.` | Có |
| 39 | Height Limit | `Giới hạn chiều cao phía trước.` | `Giới hạn chiều cao phía trước.` | Có |
| 40 | Turn Left Only | `Bắt buộc rẽ trái.` | `Chỉ được rẽ trái.` | Có |
| 41 | Turn Right Only | `Bắt buộc rẽ phải.` | `Chỉ được rẽ phải.` | Có |
| 42 | Turn Left | `Hướng đi bên trái.` | `Hướng đi bên trái.` | Có |
| 43 | Turn Right | `Hướng đi bên phải.` | `Hướng đi bên phải.` | Có |
| 44 | Keep left | `Đi về bên trái.` | `Giữ bên trái.` | Có |
| 45 | Roundabout | `Vòng xuyến phía trước.` | `Vòng xuyến phía trước.` | Có |
| 46 | Lane Allocation | `Chú ý biển phân làn phía trước.` | `Phân làn phía trước.` | Có |
| 47 | One way street | `Đường một chiều phía trước.` | `Đường một chiều phía trước.` | Có |
| 48 | End of all prohibition | `Hết các lệnh cấm.` | `Hết các lệnh cấm.` | Có |
| 49 | End of 50km/h speed limit | `Hết giới hạn 50 ki-lô-mét/giờ.` | `Hết giới hạn 50 ki-lô-mét/giờ.` | Có |
| 50 | Parking | `Khu vực đỗ xe.` | `Khu vực đỗ xe.` | Không |
| 51 | Bus Stop | `Điểm dừng xe buýt.` | `Điểm dừng xe buýt.` | Không |
| 52 | Hospital | `Bệnh viện phía trước.` | `Bệnh viện phía trước.` | Không |
| 53 | Green Light | `Đèn xanh phía trước.` | `Đèn xanh phía trước.` | Không |
| 54 | No Moto | `Cấm xe máy.` | `Cấm xe máy phía trước.` | Có |
| 55 | No bus | `Cấm xe buýt.` | `Cấm xe buýt phía trước.` | Có |
| 56 | No Horns | `Cấm dùng còi.` | `Cấm dùng còi.` | Có |
| 57 | No Straight and Right Turn | `Cấm đi thẳng, rẽ phải.` | `Cấm đi thẳng và rẽ phải.` | Có |
| 58 | No Left or Right Turn | `Cấm rẽ trái, rẽ phải.` | `Cấm rẽ trái và rẽ phải.` | Có |
| 59 | No U-Turn and Left Turn for Cars | `Cấm ô tô quay đầu, rẽ trái.` | `Cấm ô tô quay đầu và rẽ trái.` | Có |
| 60 | Intersection with a Priority Road | `Giao nhau đường ưu tiên.` | `Giao nhau với đường ưu tiên.` | Có |
| 61 | Intersection with Equal Roads | `Giao nhau đường đồng cấp.` | `Giao nhau đồng cấp phía trước.` | Có |
| 62 | Intersection with a Minor Road | `Giao nhau đường nhánh.` | `Giao nhau với đường nhánh.` | Có |
| 63 | Residential area | `Vào khu đông dân cư.` | `Vào khu đông dân cư.` | Có |
| 64 | sparsely populated area | `Rời khu đông dân cư.` | `Rời khu đông dân cư.` | Có |
| 65 | Dual carriageway | `Bắt đầu đường đôi.` | `Bắt đầu đường đôi.` | Có |
| 66 | U-Turn Area | `Khu vực quay đầu phía trước.` | `Khu vực quay đầu phía trước.` | Không |
| 67 | Road with Surveillance Camera | `Camera giám sát phía trước.` | `Camera giám sát phía trước.` | Không |
| 68 | No Stopping & No Parking | `Cấm dừng và đỗ.` | `Cấm dừng và đỗ.` | Không |
| 69 | No Parking | `Cấm đỗ xe.` | `Cấm đỗ xe.` | Không |
| 70 | No Parking Odd Days | `Cấm đỗ ngày lẻ.` | `Cấm đỗ ngày lẻ.` | Không |
| 71 | Even Days | `Hạn chế đỗ ngày chẵn.` | `Cấm đỗ ngày chẵn.` | Không |

\* `No Entry` không dùng Audio vNext ở trạng thái chưa rõ hướng. Xem §5 để
phát biến thể có orientation evidence.

## 7. Quy tắc ưu tiên biển báo trong cùng frame

Khi một frame có nhiều biển, sign arbitration phải làm theo thứ tự:

1. Loại candidate không qua geometry/temporal gate hoặc bị xem là watermark,
   biển quảng cáo, biển mặt sau hoặc detection rung.
2. Ưu tiên biển ảnh hưởng trực tiếp đến ego lane và có hướng áp dụng rõ.
3. Trong các sign cùng relevance, ưu tiên `critical/warning` rồi mới đến
   `advisory`; không đọc đồng thời nhiều câu.
4. Với nhiều speed sign, chọn một sign bind ego lane. Nếu không bind được,
   phát HUD ambiguity và không đọc số.
5. Nếu một biển đã tạo event rồi nhưng candidate mới mâu thuẫn, giữ lifecycle
   cũ cho tới khi evidence mới vượt gate; không đổi 80 thành 50 chỉ vì một frame.
6. Khi FCW/VRU/cut-in critical xuất hiện, sign advisory bị xếp hàng hoặc bỏ qua;
   không để câu biển báo che mất cảnh báo va chạm.

## 8. Canonical payload bắt buộc

Mỗi event nên có tối thiểu:

```json
{
  "event_id": "speed_sign:60",
  "event_type": "speed_sign",
  "severity": "advisory",
  "canonical_message": "Giới hạn 60 ki-lô-mét/giờ phía trước.",
  "display_message": "Giới hạn 60 ki-lô-mét/giờ phía trước.",
  "spoken_message": "Giới hạn 60 ki-lô-mét/giờ phía trước.",
  "audio_eligible": true,
  "evidence": {
    "temporal_confirmed": true,
    "ego_lane_bound": true,
    "confidence": 0.96
  }
}
```

`display_message != spoken_message` là lỗi contract, không phải một khác biệt
UX được chấp nhận. `audio_eligible=false` phải hiện rõ trong evidence để kỹ sư
biết tại sao HUD có cảnh báo nhưng loa im lặng.

## 9. Fallback và kế hoạch áp dụng

### 9.1 Runtime fallback

```powershell
# Candidate mới sau khi đã được owner duyệt
.\scripts\start.ps1 -AlertCopyProfile vnext

# Rollback tức thời về catalog đã kiểm thử
.\scripts\start.ps1 -AlertCopyProfile legacy
```

Nếu candidate làm tăng false alert, TTS overlap, sai semantics hoặc fail audio
listening gate, giữ `legacy`; không revert model chỉ vì thay copy. Nếu code mới
không khởi động được, revert riêng commit tài liệu/runtime liên quan và bảo toàn
model/artifact baseline.

### 9.2 Quality Gate trước khi đưa vNext vào runtime

- 100% dynamic builder trả đúng object, vị trí, hướng và action theo test fixture.
- 71/71 sign labels có mapping; speed/minimum-speed/No Entry có test riêng.
- `display_message == spoken_message` đạt 100% trên event corpus.
- Không có người đi bộ trên vỉa hè tạo cut-in trong regression.
- Dòng xe đông nhưng không path conflict không phát cross-traffic audio.
- Speed sign mâu thuẫn không phát số không bind ego lane.
- Critical preempt advisory và không có audio overlap.
- Không mất âm đầu; TTS output không bị truncate; 3 người nghe tiếng Việt chấm
  rõ nghĩa/hướng/hành động tối thiểu `4/5`.
- Regression object/sign/lane/risk không giảm critical event recall so với
  baseline; copy change không được dùng để che perception miss.

## 10. Những gì catalog này giải quyết và những gì không giải quyết

### Đã giải quyết ở tầng nội dung/policy

- Tách rõ `cut-in`, `cross-traffic`, `VRU` và `FCW` để không nói “nhập làn” với
  người đi bộ trên vỉa hè.
- Câu FCW critical ngắn; warning/VRU có hành động `giảm tốc độ`.
- Lead braking chỉ áp dụng phương tiện và nói “đang giảm tốc. Hãy chú ý”.
- Safe crossing không bị phát lặp như nguy cơ va chạm trong dense traffic.
- Speed sign nhiều làn không tự chọn một con số khi thiếu lane binding.
- No Entry không gây hoảng loạn bằng câu mơ hồ; orientation chưa rõ là HUD-only.
- Các biển ít khẩn cấp được HUD-only để giảm alert fatigue.

### Chưa thể giải quyết chỉ bằng câu chữ

- Sai trái/phải: cần camera-relative geometry, track history và test direction.
- Sai số 80/60/50: cần detector/classifier/sign arbitration và lane binding.
- Bỏ sót xe tải phanh, người ngã hoặc xe máy cắt ngang: cần model/temporal
  evidence/dataset, không phải đổi TTS.
- Độ chính xác TTC mét, ego speed, orientation biển hoặc hành vi xe thật: cần
  calibration, telemetry/OEM interface và closed-course validation.

## 11. Cơ sở tham khảo và giới hạn tuyên bố

Các nguyên tắc này tham khảo tài liệu công khai về driver-assistance và human
factors của NHTSA: FCW/LDW là các hệ thống cảnh báo có thể dùng tín hiệu âm thanh
hoặc hiển thị; tài xế vẫn phải duy trì trách nhiệm điều khiển. NHTSA cũng nhấn
mạnh hiệu quả cảnh báo phụ thuộc khả năng thu hút chú ý và gợi ra phản ứng phù
hợp. Đây là tài liệu tham khảo thiết kế, **không phải chứng nhận OEM, tiêu chuẩn
VinFast hay bằng chứng RoadWatch đã an toàn trên đường công cộng**.

- [NHTSA — Driver Assistance Technologies](https://www.nhtsa.gov/vehicle-safety/driver-assistance-technologies)
- [NHTSA — Human Factors Design Guidance](https://www.nhtsa.gov/sites/nhtsa.dot.gov/files/documents/812360_humanfactorsdesignguidance.pdf)
- [NHTSA — Advanced Technologies / crash-warning interface research](https://www.nhtsa.gov/crash-avoidance/advanced-technologies)

## 12. Checklist owner review

Chủ dự án có thể phản hồi theo nhóm, không cần sửa trực tiếp source:

```text
Động: PASS / SỬA / GIỮ LEGACY
Speed + multi-lane: PASS / SỬA / GIỮ LEGACY
No Entry orientation: PASS / SỬA / GIỮ LEGACY
Biển warning/local hazard: PASS / SỬA / GIỮ LEGACY
Biển prohibition/mandatory: PASS / SỬA / GIỮ LEGACY
Biển informational/HUD-only: PASS / SỬA / GIỮ LEGACY
```

Sau khi có owner decision, agent mới chuyển mapping được duyệt vào
`alert_copy.py`/`signs.py`, sinh lại TTS corpus, chạy unit/regression/audio gate
và giữ `legacy` làm rollback cho toàn bộ rollout.
