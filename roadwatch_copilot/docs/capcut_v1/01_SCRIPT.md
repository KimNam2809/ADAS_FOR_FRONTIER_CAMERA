# Script

Story name: RoadWatch — Biết khi nào cần lên tiếng
Genre: factual technology documentary with restrained dramatic storytelling.
Language: Vietnamese. Duration: 170 seconds, including pauses and final hold.

Priority: authenticity > comprehensibility > spectacle. Time windows are editorial
targets; read narration once at natural speed before locking the edit. Shorten copy
if necessary, never accelerate speech into an unnatural delivery.

## S01 — 00:00–00:12 — Con đường thật

Assets: A01 dense source, optionally A03 night source.
Visual: forward dashcam point of view, 2–3 cuts of 3–5 seconds. Show vehicles
moving near each other, not an invented collision. Preserve frame proportions.
NARRATOR, observant, warm, not alarmist:
“Trên đường phố Việt Nam, xe máy có thể chạy rất gần. Nhưng nhìn thấy nhiều
phương tiện… chưa có nghĩa là đang gặp nguy hiểm.”
Sound: quiet traffic ambience only if licensed; otherwise a soft music bed.
On-screen: “Giao thông hỗn hợp. Sự chú ý có giới hạn.”

## S02 — 00:12–00:25 — Câu hỏi

Assets: A01 freeze frame, optional neutral editorial highlights.
Visual: briefly highlight several road users, label “Minh họa”, then remove
highlights. Do NOT invent red danger boxes or imply model output.
NARRATOR, slightly slower, pause one second at the end:
“Nếu mọi chuyển động đều trở thành một tiếng cảnh báo, tài xế sẽ phải nghe quá
nhiều. Vậy điều gì thực sự cần được lên tiếng?”
On-screen: “Không phải mọi đối tượng đều cần một cảnh báo.”

## S03 — 00:25–00:38 — Giới thiệu RoadWatch

Assets: A09 project logo → A10 Driver screenshot, or H01 real product capture.
Visual: logo on navy for 2 seconds, clean cut into the real interface. No car ad montage.
NARRATOR, clear and confident:
“Đó là bài toán RoadWatch Copilot đang giải quyết: trợ lý cảnh báo camera trước,
bằng tiếng Việt, hướng đến xử lý ngay trên thiết bị.”
On-screen: “RoadWatch Copilot” / “Chỉ hỗ trợ cảnh báo — không điều khiển xe.”

## S04 — 00:38–00:57 — Pipeline thật

Assets: A06 day replay, A08 rain replay; H01 if recorded.
Visual: play recorded output, keep labels legible. If H01 exists, show video
selection and start before the replay. Otherwise do not fake clicks. Use a small
caption “Replay pipeline local · đã tắt âm thanh · không phải suy luận trực tiếp”.
NARRATOR, precise, accessible:
“Từ hình ảnh phía trước, RoadWatch nhận diện tác nhân giao thông, làn đường và
biển báo. Hệ thống theo dõi sự thay đổi qua nhiều khung hình để đánh giá nguy cơ.”
On-screen: “Nhận diện → Theo dõi → Đánh giá → Chọn kênh cảnh báo”.
Do not claim every object or lane visible in these clips was correctly detected.

## S05 — 00:57–01:14 — Nghe sản phẩm

Assets: A13 motorcycle.wav. Use a dedicated neutral voice-demo card, not an
arbitrary vehicle in A06. H03 verified synced alert may replace this card later.
NARRATOR:
“Khi cần chú ý, thông tin được chuyển thành một cảnh báo ngắn, có đối tượng và
vị trí. Đây là một mẫu giọng tiếng Việt của RoadWatch.”
Pause narrator. PRODUCT VOICE: play A13 once, original speed:
“Xe máy bên phải; giảm tốc độ.”
Visual during WAV: exact transcript, label “Mẫu giọng sản phẩm · Piper tiếng Việt”.
Hold transcript for 2 seconds after playback. Never synthesize fake live evidence.

## S06 — 01:14–01:33 — Biết khi nào nên im lặng

Assets: A05 dense replay as background context; editable policy card or H02.
Visual fallback: split policy text into “Thông tin ít nguy cơ → HUD” and
“Nguy cơ khẩn cấp → cảnh báo ưu tiên”; label “Minh họa chính sách”.
Only show real dense-mode transitions if H02 is owner-reviewed with matching logs.
NARRATOR, calm:
“RoadWatch không chỉ được thiết kế để lên tiếng. Cơ chế chọn lọc âm thanh giúp
thông tin ít nguy cơ ưu tiên hiển thị, trong khi cảnh báo khẩn cấp vẫn giữ quyền ưu tiên.”
On-screen footnote: “Chính sách không thay thế chất lượng nhận diện.”
Do not add two beeps as if they occurred in the supplied muted replay.

## S07 — 01:33–01:53 — Kỹ sư có thể kiểm chứng

Assets: A11 Engineer screenshot, or H04 actual Event History screen recording.
Visual: show whole UI first; then a gentle crop into Event History and explanation
area. With a still image do not animate fabricated cursor clicks or changing values.
NARRATOR:
“Với kỹ sư, mỗi cảnh báo cần có căn cứ để kiểm tra. RoadWatch lưu lịch sử sự kiện
và lý do lựa chọn kênh thông báo, giúp quay lại đúng thời điểm để tìm hiểu điều gì đã xảy ra.”
On-screen: “Event History · Evidence · HITL”.

## S08 — 01:53–02:09 — Quyết định có trách nhiệm

Assets: A17 source report; build an editable text card, not an AI-generated chart.
Visual: Baseline event recall 0,80 / V3 Full candidate 0,60 / Giữ baseline.
Footnote always legible: “Locked regression trong báo cáo dự án; không đại diện mọi tình huống”.
NARRATOR, deliberate:
“Chúng tôi không thay mô hình chỉ vì nó mới hơn. Trong một lần đánh giá, mô hình
mới bỏ sót nhiều sự kiện hơn baseline. Vì vậy, chúng tôi giữ bản cũ. Cải tiến phải được chứng minh.”
Source: ROADWATCH_TECHNICAL_REPORT.md section on Object V3 Full. No generic accuracy claim.

## S09 — 02:09–02:27 — Từ demo tới thiết bị

Assets: A10/A11; H05 AAOS capture and H06 cloud capture if available.
Fallback: editable diagram labelled “Minh họa kiến trúc”, not mock footage of a real car.
NARRATOR:
“Hiện tại, RoadWatch được kiểm thử bằng video, có giao diện tài xế và kỹ sư,
cùng hướng tích hợp AAOS. Cloud phục vụ demo và đánh giá; đường cảnh báo trên xe
được định hướng xử lý tại thiết bị.”
On-screen labels: “Local: xử lý tại thiết bị”; “AAOS: emulator, chưa OEM”;
“Cloud: demo và kiểm chứng, có độ trễ mạng”.

## S10 — 02:27–02:40 — Bước tiếp theo

Assets: H07 real developer over-shoulder shot; fallback roadmap text over A11.
NARRATOR, matter-of-fact, not apologetic:
“Để tiến gần hơn tới xe thật, chúng tôi cần dữ liệu tốt hơn, kiểm chứng trên
phần cứng mục tiêu và thử nghiệm có kiểm soát.”
On-screen: “Dữ liệu có nhãn → Edge hardware → Closed-course”.
Additional readable line: “Chưa có chứng nhận an toàn hoặc tích hợp OEM”.

## S11 — 02:40–02:50 — Lời mời

Assets: H08 real presenter if available, otherwise A09 and editable end card.
PRESENTER or NARRATOR, warm, concise:
“Chúng tôi mong có cơ hội cùng doanh nghiệp phát triển RoadWatch, bằng những
lần cải tiến có thể đo được.”
Keep last 2–3 seconds free of narration for the end card.
On-screen:
“ROADWATCH COPILOT”
“Team 162 · Cohort 3”
“Hợp tác · Thực tập · Phát triển sản phẩm”
“Chỉ hỗ trợ cảnh báo — không tự lái.”
Only insert real verified contact information supplied by the team. If missing,
show the repository URL, not invented email or fabricated QR.

