# RoadWatch — Landing Page Master Plan

> Phiên bản 1.0 · 2026-08-30 · Work ID: WORK-20260830-LP-001.

> **Cập nhật triển khai — WORK-20260830-LP-002:** bản local v1.0 đã build/prerender
> và kiểm tra tương tác. Xem [runbook và evidence](LANDING_PAGE_V1_RUNBOOK.md).
> Phần kế hoạch gốc bên dưới giữ nguyên để truy vết; không hiểu các task là đã
> PASS toàn bộ. LP-00/01/03/05 có implementation; LP-04 có 4 replay + 2 ảnh UI +
> 3 Piper WAV, còn public media/privacy gate; LP-06 đã test desktop/390px, chưa
> toàn bộ thiết bị; LP-07 có bundle/hash/SSR audit, chưa Core Web Vitals throttled;
> LP-08 human gate PENDING; LP-09 local preview + Docker package, chưa cloud/DNS;
> LP-10 có runbook. LP-02 được gộp thành một bản thiết kế navy/trắng/xanh chạy
> được theo yêu cầu triển khai tiếp, không tạo ba mockup thay cho sản phẩm.
> Trạng thái: **kế hoạch đề xuất, chưa triển khai hoặc deploy trong phiên này**.
> Đối tượng chính: giám khảo, mentor, kỹ sư tuyển dụng và đối tác thử nghiệm.
> Sản phẩm: prototype cảnh báo hỗ trợ lái; không phải hệ thống tự lái hoặc thiết bị an toàn đã chứng nhận.

## 1. Quyết định thiết kế và mục tiêu

Xây dựng landing page kể câu chuyện RoadWatch bằng tình huống giao thông thật,
giao diện sản phẩm, tương tác có thể thử và bằng chứng kỹ thuật có nguồn.
Kế thừa bản landing nháp trong project, giữ website demo/HMI và pipeline độc lập.

Thông điệp hero đề xuất:

> **Cảnh báo có ngữ cảnh. Dành cho giao thông Việt Nam.**
>
> RoadWatch phân tích video phía trước, tổng hợp nguy cơ và cảnh báo bằng tiếng
> Việt. Được thiết kế để ưu tiên điều tài xế cần chú ý và giảm cảnh báo quá tải.

Dòng trạng thái ngay hero: `Prototype · Video replay · Warning-only`.
CTA chính: **Trải nghiệm tình huống**. CTA phụ: **Mở demo phân tích video**.
Luôn hiển thị: “Chỉ hỗ trợ cảnh báo. Người lái chịu trách nhiệm điều khiển xe.”

### Mục tiêu có thể kiểm chứng

| Thời điểm đọc | Điều người xem cần hiểu | Cách nghiệm thu |
|---|---|---|
| 10–15 giây | RoadWatch làm gì, dành cho ai, không tự lái | 4/5 người ngoài nhóm diễn đạt đúng bằng lời của họ |
| 60–90 giây | Nghe một cảnh báo và hiểu vì sao có lúc hệ thống im lặng | 4/5 người thao tác được playground không cần hướng dẫn |
| 3–5 phút | Driver khác Engineer thế nào; edge khác cloud; khả năng và giới hạn hiện tại | 4/5 người trả lời đúng ít nhất 5/6 câu ở §11 |
| Khi muốn đào sâu | Có báo cáo, phương pháp đo, source và đường vào demo | Toàn bộ link/CTA có đích thật, không placeholder |

Không yêu cầu người xem đọc toàn bộ tài liệu kỹ thuật trên một trang. Trang có
ba mức: thông điệp dễ hiểu → tương tác/bằng chứng → tài liệu chi tiết.

## 2. Hiện trạng đã kiểm tra và phần tái sử dụng

| Thành phần | Hiện trạng từ source | Việc cần làm tiếp |
|---|---|---|
| `frontend/landing.html`, `src/landing-main.tsx` | Đã có entry riêng, đang untracked | Giữ nguyên, snapshot trước sửa; build output độc lập |
| `src/landing/LandingPage.tsx` | Đã có nhiều section, menu, tabs, FAQ, VI/EN | Tổ chức lại câu chuyện; sửa các CTA chỉ trỏ `#top`/`#cta` |
| `src/landing/content.ts` | Có copy VI/EN và benchmark | Thêm nguồn, phạm vi, ngày, độ mới và trạng thái vào mỗi claim |
| `src/landing/DashcamScene.tsx` | Canvas mô phỏng theo kịch bản viết sẵn | Chỉ giữ như minh họa có nhãn; không dùng làm bằng chứng inference |
| `src/landing/landing.css` | Tokens, responsive, reveal và reduced-motion | Đồng bộ xanh dương/trắng; rà global styles để không ảnh hưởng HMI |
| `frontend/vite.config.ts` | Build mặc định chưa khai báo entry landing | Thêm config/command riêng; không sửa mặc định `dist-ui-v4` |
| Logo | `data/assets/logo.png` có sẵn | Dùng logo thật thay logo CSS nháp; tối ưu kích thước |
| Các ảnh `data/assets/exec-*.png` | Là asset thiết kế từ các vòng mockup | Dùng cho hướng thiết kế; muốn gắn nhãn “giao diện hiện tại” phải chụp runtime mới |
| `media/` | Có day/night/rain/dense/test videos | Chọn clip ngắn và kiểm tra quyền công bố; không đưa cả thư mục lên landing |
| Public demo GCP | Có địa chỉ được ghi trong tài liệu | Kiểm tra live trước bàn giao; chưa kiểm tra GCP trong phiên lập kế hoạch |

Đây là rà soát source cho việc lập kế hoạch, chưa phải browser QA bản landing
nháp. Không coi file tồn tại là đã build, deploy hoặc hoạt động đầy đủ.

## 3. Hướng mỹ thuật: công nghệ cao nhưng có bản sắc RoadWatch

Học cách tổ chức câu chuyện sản phẩm từ các trang công nghệ; không sao chép
giao diện, video, logo hoặc tuyên bố năng lực của hãng khác.

| Tham khảo | Điểm nghiên cứu cho RoadWatch | Không mang sang |
|---|---|---|
| [Apple Vision Pro](https://www.apple.com/apple-vision-pro/) | Chia sản phẩm thành chương trải nghiệm, hình sản phẩm nổi bật, nội dung từng lớp | Asset Apple, branding và hiệu ứng nặng không phục vụ nội dung |
| [NVIDIA Automotive](https://www.nvidia.com/en-us/solutions/autonomous-vehicles/) | Đặt công nghệ trong luồng giải pháp, đường dẫn cho người muốn đọc sâu | Claim tự lái, đối tác hoặc chứng nhận không thuộc RoadWatch |
| [Mobileye Technology](https://www.mobileye.com/technology/) | Giải thích perception, safety và giới hạn qua các chủ đề rõ ràng | Claim hoặc số xe triển khai của Mobileye |

Các URL trên đã được đọc nội dung công khai; chưa capture/so sánh pixel giao
diện trong phiên này. LP-02 sẽ chụp reference trước khi dựng mockup.

Art direction đề xuất:

- Hero và chương “hiểu tình huống” dùng navy `#0B1220`; phần bằng chứng dùng
  nền trắng `#FFFFFF`/xám xanh rất nhạt. Primary blue `#2563EB`, cyan `#15B8DA`
  làm điểm nhấn. Đỏ/cam dành cho severity; không trang trí cả trang bằng màu cảnh báo.
- Typography: Be Vietnam Pro cho nội dung tiếng Việt; một weight lớn cho hero;
  IBM Plex Mono chỉ cho số đo nếu cần. Tự host WOFF2, tối đa hai family.
- Desktop hero 56–76 px, section title 32–48 px; mobile hero 36–44 px; body
  16–18 px, line-height 1.5–1.7. Giới hạn dòng văn khoảng 60–75 ký tự.
- Content max-width khoảng 1200–1280 px; một khối hình/video lớn làm trọng tâm
  mỗi chương. Không biến cả trang thành lưới card giống dashboard.
- Không cần 3D xe quay liên tục, particle nền, scroll hijacking hoặc con trỏ tùy
  biến. Hình giao thông và UI thật là nội dung chính.
- Header gọn: Sản phẩm / Trải nghiệm / Công nghệ / Bằng chứng / FAQ / Mở demo.
- Không áp dụng nguyên layout HUD 20/80 cho landing; đó là bố cục app HMI.

## 4. Câu chuyện và bố cục trang

| Section ID | Nội dung/copy đề xuất | Hình ảnh và tương tác | Điều người xem hiểu |
|---|---|---|---|
| S01 · Hero | Cảnh báo có ngữ cảnh. Dành cho giao thông Việt Nam. | Video UI replay 12–18 giây, có poster; hai CTA | Sản phẩm, người dùng, warning-only |
| S02 · Bài toán | Đông xe chưa chắc nguy hiểm. Cảnh báo liên tục làm tài xế mất tập trung. | Ba crop cùng bối cảnh: chạy gần / cắt vào quỹ đạo / biển báo | Phát hiện vật thể khác quyết định cảnh báo |
| S03 · Playground | Xem RoadWatch chọn điều cần chú ý | Chọn scenario, bật lớp perception, timeline, mở lý do, nghe TTS | Hệ thống vận hành cụ thể ra sao |
| S04 · Selective Audio | Khi cần nhắc. Khi cần giữ im lặng. | So sánh routing normal/dense trên cùng dữ liệu hoặc minh họa có nhãn | Giá trị của Traffic Context v1 |
| S05 · Hai người dùng | Tài xế cần rõ ràng. Kỹ sư cần bằng chứng. | Tab Driver/Engineer, ảnh runtime và hotspot keyboard-accessible | Hai vai trò và HITL |
| S06 · Công nghệ | Từ khung hình đến cảnh báo có lý do | Sơ đồ 6 bước, bấm mỗi bước để mở ví dụ output | Ba model + tracking + risk + governor + audio + audit |
| S07 · Edge và Cloud | Cảnh báo tại thiết bị. Đánh giá qua website. | Chuyển tab Local / AAOS / GCP; ghi rõ data flow | Offline có điều kiện asset; AAOS hiện là HMI/replay; cloud có độ trễ mạng |
| S08 · Bằng chứng | Mỗi con số đều có điều kiện đo | Bộ lọc báo cáo, chú thích, source link; không counter giả | Prototype đã chứng minh gì, còn thiếu gì |
| S09 · An toàn và lộ trình | Người lái luôn là người quyết định | Active / Candidate / Cần kiểm chứng; giới hạn và roadmap | Không tự lái, không OEM claim, cần calibration/closed-course |
| S10 · FAQ, Team, CTA | Trải nghiệm RoadWatch và xem bằng chứng | Demo thật, báo cáo, repo; liên hệ thật nếu owner cung cấp | Làm gì tiếp theo và trao đổi với ai |

S01–S04 đủ cho lượt xem nhanh; S05–S09 phục vụ người đánh giá kỹ thuật. Dùng
anchor để bỏ qua chương, không ép cuộn hết. Mobile giữ đủ nội dung, thay sticky
layout bằng các khối tuần tự và nút chạm rõ ràng.

## 5. Các tương tác phải hoạt động thật

### I01 — Scenario Explorer (P0)

Cho chọn bốn scenario: đông xe ít nguy cơ, xung đột phía trước, biển tốc độ,
vạch làn không rõ trong đêm/mưa. Mỗi scenario có 15–30 giây video đã chọn và
event fixture xuất từ chính một phiên replay đã kiểm tra.

Người xem có thể play/pause/seek, bật lớp box/lane nếu fixture có geometry,
chọn event trên timeline và nghe đoạn TTS. Media và overlay dùng cùng timestamp.
Hiển thị nhãn **“Replay đã xử lý trước — không suy luận trực tiếp”** sát player.
Video có cảnh báo sai không được sửa bằng tay rồi giả là output model đúng;
đánh dấu đó là case giới hạn hoặc chọn case khác có evidence.

Một thẻ giải thích gồm: đối tượng/hướng, loại event, risk/confidence, audio
route, suppression reason và ngày/model profile của lượt chạy. Không biến
confidence 0.8 thành “80% khả năng tai nạn”. Không hiển thị mét/tốc độ xe thật
nếu thiếu calibration/telemetry.

Ưu tiên một video nguồn và overlay đã xuất; không decode hai video đồng thời
chỉ để làm before/after. Nếu chưa có geometry export, dùng một clip đã annotate
và tab ảnh gốc ở cùng timestamp; công bố rõ đây là hai cách xem replay.

### I02 — Vì sao hệ thống im lặng? (P0)

- Scenario đông xe nhưng an toàn: giải thích context entry, hai beep nhẹ và các
  event bị chuyển HUD-only; critical vẫn có quyền ưu tiên.
- Người xem chọn “Xem cách định tuyến âm thanh”; không gửi thay đổi ngưỡng tới
  backend thật. Nếu minh họa một chính sách khác, gắn nhãn **mô phỏng chính sách**.
- Chỉ hiển thị số lần audio giảm, ví dụ x→y, sau khi đã đo trên cùng window,
  cùng event input và hai cấu hình. Không tự ghi “giảm 50%” vì đó từng là mục tiêu.
- Bình thường chỉ thể hiện trạng thái bằng hình; beep/TTS cần người dùng bấm nghe.

### I03 — Driver / Engineer Tour (P0)

Chuyển tab giữa hai screenshot hiện tại. Hotspot mở chú giải HUD, hazard,
metrics, Event History, HITL và SLM optional. Ảnh giữ tỷ lệ, có zoom; mobile dùng
danh sách chú giải tương đương. SLM dùng explanation đã lưu hoặc đoạn quay thật,
không gọi model sinh văn bản chỉ vì người xem mở landing.

### I04 — Nghe tiếng Việt (P0)

Ba mẫu WAV từ Piper release hiện tại: FCW critical, xe máy trong vùng xung đột,
biển giới hạn tốc độ. Lấy nguyên canonical text/copy profile đang active khi
xuất; không tạo bộ câu riêng chỉ cho quảng cáo. Hiển thị text cùng audio.

Một audio controller chung cho toàn trang: mỗi thời điểm chỉ một audio source;
chuyển clip/tab, đóng modal hoặc rời trang phải stop/reset; click liên tục không
gây lặp. Không gọi public TTS endpoint và không dùng browser/Windows voice.
Browser có chính sách hạn chế autoplay; cần click rõ ràng và xử lý promise
`play()` bị từ chối. [MDN autoplay](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay).

### I05 — Evidence Explorer (P0 cơ bản, P1 nâng cao)

Chọn nhóm Runtime / Traffic sign / Model promotion. Mỗi metric kèm dataset hoặc
window, ngày, runtime, hardware, đơn vị và nguồn. Nhóm chưa có report hiển thị
“Chưa công bố kết quả”, không đặt số 0. Runtime latency có thể đo dù chưa có
ground truth; thiếu GT chỉ chặn claim accuracy/recall, không đánh đồng hai việc.

### I06 — Mở demo thật (P0)

CTA dẫn tới app hiện có. Chọn/upload video và inference thuộc app Driver/Engineer,
không tạo thêm uploader trên landing. Có giải thích cloud cold start, giới hạn
video và quyền riêng tư. App vẫn yêu cầu auth/session như hiện tại; landing
không giữ tài khoản engineer, token hoặc API key trong JS.

## 6. Kế hoạch ảnh/video và quyền sử dụng

### Danh mục cụ thể

| Asset ID | Nguồn dự kiến đã biết | Sản phẩm biên tập | Vị trí |
|---|---|---|---|
| A01 | `data/assets/logo.png` | Logo PNG/WebP có alpha, favicon | Header/footer/OG |
| A02 | Quay runtime Driver với `media/test_video10.mp4` | Clip 12–18s, hero 720p/1080p + poster | S01 |
| A03 | `media/dashcam_vietnam_traffic_multi.mp4` | Clip 20–30s dense + event fixture thật | S02–S04 |
| A04 | `media/test_video1.mp4` hoặc `media/video_test.mp4` | Clip 15–25s xung đột đã replay kiểm chứng | S03; nếu model bỏ sót thì dùng như limitation |
| A05 | `media/test_video10.mp4`, `media/test_video11.mp4` | Clip tốc độ 60/80 có matching event | S03/sign |
| A06 | `media/dashcam_vietnam_night.mp4`, `media/dashcam_vietnam_rain+night.mp4` | Clip/ảnh thể hiện lane quality và giới hạn | S03/S09 |
| A07 | Chụp runtime `dist-ui-v4` Driver/Engineer mới | 2 screenshot desktop + crop mobile, không kéo giãn | S05 |
| A08 | Quay AAOS emulator thật khi chạy được | Clip 10–15s; nhãn “Android Automotive emulator” | S07 |
| A09 | Piper release + canonical message | 3 PCM WAV hoặc bản web encode đã nghe lại | I04 |
| A10 | Asset thiết kế RoadWatch hoặc hình stock đã duyệt | OG 1200×630; một ảnh bối cảnh nếu cần | Chia sẻ link/S02 |

Timestamp cắt clip phải được chọn sau khi xem video; bảng này không bịa rằng
các tình huống đã được xác nhận tại một timestamp cụ thể. Không tự dùng bất kỳ
file nào dưới `media/uploads/` làm tư liệu quảng bá.

Nguồn ngoài ưu tiên bổ sung: [Pexels](https://www.pexels.com/license/) cho ảnh
giao thông/đường phố. License cho phép sử dụng và chỉnh sửa miễn phí nhưng
không cho ngụ ý cá nhân/nhãn hàng trong ảnh bảo trợ sản phẩm. Chọn đúng asset,
ghi creator, URL, license, ngày truy cập và phạm vi sử dụng trước khi tải/public.
Không tải video YouTube hoặc clip hãng xe rồi mặc định được phép dùng.

Quyền sử dụng video test hiện có không tự chứng minh quyền công bố thương mại.
Owner xác nhận phạm vi public của từng asset; blur mặt/biển số khi cần; loại bỏ
âm thanh riêng tư, dữ liệu định danh, biển số và cảnh tai nạn gây sốc không cần
thiết. Stock/AI illustration không được gắn nhãn kết quả inference RoadWatch.

### Manifest đề xuất

Lưu metadata nhẹ trong `frontend/src/landing/data/media-manifest.json` gồm:
`asset_id`, `source_path_or_url`, `creator`, `license`, `public_permission`,
`privacy_review`, `sha256`, `kind`, `width`, `height`, `duration_seconds`,
`bytes`, `caption_url`, `scenario_id`, `evidence_id`, `poster_url`.
Kind chỉ nhận `actual_capture`, `processed_replay`, `policy_simulation`,
`design_mockup`, `stock`. Asset public phải có permission và privacy review
được ghi nhận; không dùng “unknown” như đã pass.

### Định dạng và ngân sách

- Video chính MP4 H.264 có fast-start; WebM là bản thêm nếu cần. Không cần 4K/GIF.
- Hero muted/playsinline, poster trước; target ≤3 MB cho clip 12–18s.
  Mặc định poster trên mobile/save-data và reduced-motion; play theo yêu cầu.
- Scenario 15–30s target ≤5 MB/clip 720p. Chỉ tải scenario đang chọn;
  fallback luôn có poster và transcript nếu video lỗi.
- Screenshot WebP/AVIF có fallback, mục tiêu ≤250 KB/ảnh full-width;
  hero poster ≤180 KB; logo ≤40 KB; dùng srcset/sizes và width/height rõ ràng.
- Tổng media phiên người xem chỉ mở hero + một scenario mục tiêu ≤10 MB;
  không preload toàn bộ video/corpus TTS hoặc clone cả `media/` vào build.
- Audio chỉ fetch khi bấm nghe; target tổng ba mẫu ≤1 MB, ghi provider và
  model fingerprint trong manifest. Không đổi voice đang release.
- File nặng ở thư mục artifact bị ignore/GCS prefix công khai đã duyệt;
  không đưa weights/dataset/video nguồn lên Git hoặc mở public bucket runtime.

## 7. Animation và khả năng truy cập

| Thành phần | Chuyển động đề xuất | Ràng buộc |
|---|---|---|
| Nội dung xuất hiện | Opacity + translateY 12–20px, 350–500ms | Một lần; nội dung vẫn đọc được nếu observer/JS lỗi |
| Hover/focus/nút | 120–180ms | Focus keyboard không phụ thuộc hover |
| Chuyển tab | Crossfade 180–250ms, vùng media giữ kích thước | Không layout shift; có loading/error state |
| Sơ đồ pipeline | Highlight bước đang chọn | Không chạy animation vô hạn khi ngoài viewport |
| Chương desktop | Sticky hình bên cạnh đoạn giải thích | Không giữ cuộn cưỡng bức; mobile trở về flow thường |
| Video + evidence | Overlay cập nhật theo thời gian video | Cập nhật cục bộ, không re-render cả landing mỗi frame |

Ưu tiên CSS transform/opacity + IntersectionObserver. Không thêm GSAP hoặc
WebGL ở P0. Nếu Motion/GSAP cần cho storyboard đã duyệt, chỉ chọn một thư viện,
dynamic import và chứng minh vẫn trong performance budget.

Hỗ trợ `prefers-reduced-motion`: tắt parallax/reveal phức tạp/autoplay, vẫn giữ
đủ nội dung và các nút chủ động. [MDN reduced motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion).

Keyboard tab/arrow/Enter/Escape đúng chức năng, focus trả về nút mở modal; mục
tiêu vùng chạm ≥44×44 CSS px. Tương phản chữ thường ≥4.5:1; text lớn ≥3:1.
TTS/video có transcript; màu không phải tín hiệu duy nhất của severity. Video
sản phẩm luôn `object-fit: contain`, tỷ lệ từ intrinsic dimensions; chỉ media
trang trí được crop có chủ đích. Không stretch video để lấp đầy box.

## 8. Stack, thư mục và tách khỏi demo

### Stack đề xuất

- React + TypeScript + Vite: giữ toolchain hiện tại và tái dùng content/components
  của bản nháp. Không migrate HMI sang Next.js chỉ để làm landing.
- Native HTML video/audio, CSS motion, IntersectionObserver; icon từ thư viện
  có license phù hợp nếu cần, logo dùng asset thật.
- Static/prerendered nội dung marketing cho crawler/no-JS; runtime hydrate các
  tương tác. Chọn cách prerender nhỏ, xác minh với React/Vite đang cài trong LP-03.
- Không import `src/main.tsx`, HMI API client hoặc model runtime vào bundle landing.
- Content VI/EN giữ trong data riêng; tiếng Việt là bản chính. EN có sẵn được
  rà lại trước public; bản P0 có thể VI-only nếu EN chưa review, không để nút giả.
- Self-host font; không cần Firebase, database/CMS hoặc chatbot trong P0.

### Cấu trúc dự kiến (giữ file nháp hiện có)

```text
roadwatch/
  frontend/
    landing.html
    vite.landing.config.ts          # mới, chỉ dành landing
    src/landing-main.tsx
    src/landing/
      LandingPage.tsx
      content.ts
      landing.css
      DashcamScene.tsx               # chỉ minh họa, có nhãn
      components/                   # player, audio, tabs, evidence
      data/                         # manifest + fixture đã làm sạch
    public/landing/                 # asset nhẹ/thumbnail/preview đã duyệt
    dist-landing/                   # output riêng; không commit
  deploy/gcp/landing/               # container static/build/deploy riêng, bước sau
  docs/LANDING_PAGE_MASTER_PLAN.md
  reports/landing/                  # QA, link check, performance, release manifest
```

Command triển khai dự kiến `npm run build:landing` dùng config riêng. Command
HMI, `setup.ps1`, `start.ps1` và `dist-ui-v4` không đổi trong P0. Đường preview
có thể là `landing.html`; đây chưa phải route đã tích hợp FastAPI production.

### GCP và URL

```text
Khách mở landing
  → Cloud Run service static riêng (HTML/CSS/JS)
  → media công khai đã duyệt từ GCS/CDN nếu cấu hình
  → replay/fixture tương tác trong browser

Khách bấm “Mở demo phân tích video”
  → URL app đã kiểm tra
  → auth + startup gate hiện tại
  → FastAPI/perception/TTS hiện tại
```

Đề xuất service riêng `roadwatch-landing`, image chỉ có static web server và
landing build. Cấu hình xuất phát dự kiến: 1 vCPU/512 MiB, min=0, max=2,
request-based; đo cold/warm trước chốt. Không cam kết zero cold start hoặc miễn
phí. Nếu cần CDN/load balancer, đo lợi ích và chi phí cố định trước khi thêm.
Cloud Run cung cấp HTTPS endpoint riêng cho service; đó là cơ sở triển khai
độc lập với inference. [Google Cloud Run](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run).

GCS có thể phục vụ static asset, nhưng custom HTTPS website cần cấu hình
hosting phù hợp, thường thêm load balancer; không coi public bucket URL là
domain HTTPS hoàn chỉnh. [Google Cloud static hosting](https://docs.cloud.google.com/storage/docs/hosting-static-website).

Giữ nguyên URL demo hiện tại trước Demo Day. Lần phát hành landing đầu dùng
URL preview riêng; `VITE_DEMO_URL` phải trỏ đến demo thật đã xác minh, không giữ
`demoHref="/"` nếu `/` đã trở thành landing. Tài liệu đang ghi fallback app
`https://roadwatch-web-bx6lfekcba-as.a.run.app`; kiểm tra lại lúc release.

Sau khi duyệt mới đề xuất root `https://c3-roadwatch-162.io.vn` cho landing và
subdomain `demo.c3-roadwatch-162.io.vn` cho app, hoặc giữ app URL gốc. Đây chỉ là
topology đề xuất; chưa có xác nhận DNS quyền quản lý hoặc mapping. Không tự
đổi URL đang nộp hội đồng. Không tạo service worker landing ở scope `/` trên
origin app: tránh cache/đè bundle HMI. P0 không cần service worker cho landing.

Landing không polling `/api/status`, mở MJPEG/WebSocket, gọi SLM/TTS hoặc đánh
thức inference trong nền. Hover CTA không prewarm model. CORS bucket media chỉ
cấp cho origin cần dùng; public asset tách khỏi dữ liệu/model/upload riêng.

## 9. Evidence và quy tắc truyền thông

| Nội dung | Cách được phép trình bày | Nguồn và giới hạn |
|---|---|---|
| Runtime snapshot 2026-08-29 | Processed 11.28 FPS; Display 23.07 FPS; E2E P50/P95 89.96/149.91ms | `PERFORMANCE_STREAMING_OPTIMIZATION_2026-08-29.md`, `reports/benchmark-performance-release-20260829.json`; Windows AMD, test_video10, audio off; chưa rerun trong phiên này |
| Gate runtime | Mục tiêu R1 ≥12 processed FPS; P95≤150ms | Gate là mục tiêu. 11.28 FPS chưa đạt gate FPS; không tuyên bố R1 đã pass |
| Traffic sign | mAP50 0.98741; mAP50-95 0.83217 | `ROADWATCH_TECHNICAL_REPORT.md` và artifact nguồn; nêu dataset/split khi publish; không gọi “98.7% chính xác toàn RoadWatch” |
| Speed classifier | Top-1 0.98254 | Metric classifier riêng, không phải thành công cảnh báo E2E |
| Object candidate | Baseline retained; V3 Full chưa promote | Locked event recall 0.60 so với baseline 0.80 trong report; không suy rộng mọi đường phố |
| SLM | Giải thích optional cho Engineer, có deterministic fallback | Không quyết định emergency, không hứa trả lời tức thời |
| Offline | Local chạy khi model/voice/UI đã tải và nguồn video/camera sẵn | Landing qua Internet và GCP demo không tự có khả năng offline |
| AAOS/Jetson/VinFast | HMI emulator, edge target, cần OEM/calibration/hardware | Không dùng ảnh OEM hay logo VinFast trong hàng “đối tác” nếu chưa được phép |

Các snapshot lịch sử dùng điều kiện khác nhau không vẽ thành chart A/B chứng
minh cải tiến phần trăm. Mỗi record evidence có `id`, `metric`, `value`, `unit`,
`scope`, `dataset_or_window`, `hardware`, `runtime`, `audio_enabled`, `date`,
`report`, `release_id`, `status`. Status: measured / target / unavailable.

Không công bố tỷ lệ ngăn tai nạn, 30 FPS mọi thiết bị, “production-ready”,
thành công ngã xe/ngã người tổng quát hoặc đối tác doanh nghiệp không có bằng
chứng. Trang giới hạn không giấu trong chữ nhỏ cuối footer.

## 10. Backlog thực thi

Tất cả task dưới đây **PLANNED**. “AI” nghĩa là có thể tự thực hiện phần mềm
trong quyền hiện có; không thay thế human review, quyền public media hoặc DNS.

| Task | Phụ thuộc | Thực hiện / phạm vi | Definition of Done và evidence | Phụ trách | Ước lượng |
|---|---|---|---|---|---|
| LP-00 · Freeze baseline | — | Snapshot/hash file nháp, build/config HMI, route và asset | Manifest trước sửa; working tree khác giữ nguyên; có cách khôi phục riêng | AI | 0.5–1h |
| LP-01 · Content/evidence | LP-00 | Rút thành 10 section; claim matrix; CTA và trạng thái thật | 100% metric có nguồn/điều kiện; không link giả; list giới hạn | AI; owner xác nhận contact | 1–2h |
| LP-02 · Visual direction | LP-01 | Capture references, tạo 3 hướng desktop/mobile rồi chọn một | 3 phương án, hero/playground/Driver–Engineer/mobile; owner duyệt một hướng | AI + owner chọn | 1–2h + chờ review |
| LP-03 · Build isolation | LP-02 | Config Vite landing riêng, tokens, layout, prerender, fonts | Dist landing riêng; không import HMI; routes/CTA đúng; shell đọc được khi JS lỗi | AI | 1.5–2.5h |
| LP-04 · Media/evidence pack | LP-01, LP-02 | Chọn/cắt video, record UI thật, xuất fixture/WAV, optimize/blur | A01–A10 cần dùng có manifest, rights/privacy; tối thiểu 3 clip thật + 2 ảnh UI + 3 audio | AI; owner quyền công bố | 2–4h |
| LP-05 · Interactive story | LP-03, LP-04 | I01–I06; timeline, tab, evidence, audio controller | Mọi nút có hành vi; switching/seek reset; một audio source; không inference API nền | AI | 2–3h |
| LP-06 · Motion/a11y | LP-05 | Reveal/sticky/focus/reduced-motion/mobile | Keyboard đủ luồng; no scroll trap; video không méo; reduced-motion đủ nội dung | AI | 1–2h |
| LP-07 · Perf/security/SEO | LP-05 | Lazy media; bundle audit; CSP/media origins; meta/OG/sitemap | Đạt §11; không secrets/PII; không public runtime report thô | AI | 1–2h |
| LP-08 · Human story gate | LP-06, LP-07 | 5 người thử quy trình và trả lời câu hỏi | Ghi kết quả §1/§11, lỗi ưu tiên và quyết định; không AI tự xác nhận người đã nghe | AI chuẩn bị, human thực hiện | 0.5–1h + người review |
| LP-09 · Preview/release | LP-08 | Build image landing riêng; URL preview; kiểm tra cold/warm/DNS khi có quyền | HTTPS, media range/seek, app CTA, performance; rollback artifact; không đụng service inference | AI; human DNS nếu cần | 1–2h + thời gian cloud/DNS |
| LP-10 · Handoff | LP-09 | Runbook, phiên bản, content map và update instructions | Manifest/version; report QA; cách đổi clip/copy/metrics và rollback | AI | 0.5–1h |

Tổng ước lượng kỹ thuật **12–22 giờ**, không gồm chờ người duyệt, quyền media,
chụp lại video khi lỗi model, DNS hoặc công việc sửa pipeline không thuộc scope.
Đây là dự toán dựa trên việc đã có bản nháp, không phải cam kết thời gian chạy.

Nếu cần demo trong một ngày: P0 mục tiêu 8–12 giờ sau khi có hướng thiết kế và
media được duyệt: VI, hero, 3 scenario replay, Driver/Engineer tour, evidence,
FAQ, CTA, responsive, audio và fallback. Giữ pipeline ở sơ đồ click đơn giản;
hoãn EN hoàn chỉnh, chart nâng cao, nhiều clip và CDN tùy chỉnh sang P1.
Không bỏ rights/privacy, nhãn simulation, performance hoặc audio QA để kịp giờ.

## 11. Acceptance gates

### Performance và cô lập

| Gate | Mục tiêu | Cách xác minh |
|---|---|---|
| Core Web Vitals | LCP≤2.5s; INP≤200ms; CLS≤0.1 ở p75 khi đủ dữ liệu field | Lab trước release; real-user measurement sau release, tách mobile/desktop |
| Lab | Lighthouse performance≥90 desktop, ≥85 mobile; a11y≥95 và manual QA | 3 lượt cold-cache cấu hình ghi rõ; median; không gọi lab là field pass |
| Payload ban đầu | HTML/CSS/JS/fonts/poster ≤1 MB compressed; JS đầu ≤200 KB gzip | Network log fresh visit trước tải video |
| Chuyển động | Mục tiêu 60Hz device: ≥95% animation frames ≤20ms trong 30s scroll | Chrome trace trên AMD local và thiết bị mobile test xác định; không suy ra model FPS |
| Layout | Không horizontal overflow ở 360/390/768/1024/1440/1920px | Screenshot/keyboard QA; typography tiếng Việt đủ dấu |
| Audio | 0 overlap, 0 duplicate trong 30 lượt click/tab/seek nhanh | Log controller và human listen; capture lý do suppress |
| Isolation | 0 call model/session/status/stream/TTS/SLM chỉ từ lượt đọc landing | Network log 60s; app không bị khởi tạo tự động |
| App regression | Same-window inference P95/display FPS không lệch quá 10% median khi mở landing tab nền | 3 run baseline + 3 run test cùng config/video/warmup; nếu nhiễu rerun, không sửa model để đạt |

Ngưỡng Web Vitals là tham chiếu Google, không phải số đã đạt của landing:
[Web Vitals](https://web.dev/articles/vitals). Các budget khác là mục tiêu nội
bộ cần đo. Cold start hosting, tải media và E2E inference là ba số khác nhau.

### Chức năng và an toàn

1. Tắt mạng backend inference: landing vẫn đọc được và playground asset cached
   hoặc đã tải vẫn chạy; không claim toàn landing offline lần đầu.
2. Seek/chuyển scenario/pause: event, video và audio không lẫn phiên.
3. Chặn autoplay, thiếu clip/audio, mất mạng: poster/transcript và retry rõ ràng;
   không đổi qua Web Speech tiếng Anh, không hiện playback thành công giả.
4. Keyboard/reduced-motion/zoom 200%: nội dung, CTA và controls vẫn dùng được.
5. Demo URL/auth không đổi; về từ demo không tự phát tiếng hoặc reset phiên HMI.
6. Dataset/report public không chứa secret, dữ liệu upload hay danh tính không được phép.
7. Metric có đơn vị và source; simulation có nhãn ngay trên player; không logo đối tác giả.
8. Footer links, VI/EN nếu bật, báo cáo PDF, repo, contact đều có đích thật.
9. Chưa có contact thật thì bỏ form/liên hệ, dùng báo cáo + repo; không hiện thông báo “đã gửi” khi chưa có backend nhận.

Human comprehension gate gồm sáu câu: (1) RoadWatch giúp gì? (2) Có tự phanh
không? (3) Vì sao đường đông có lúc không đọc? (4) Driver/Engineer khác gì?
(5) Replay landing khác demo AI trực tiếp thế nào? (6) Cần gì để thử trên xe thật?
Tiêu chí đạt như §1; không tạo câu trả lời hoặc pass thay người thử.

## 12. Rollout, fallback và cập nhật

1. Không đổi `dist-ui-v4`, Piper, Traffic Context v1, model hoặc ngưỡng để phục
   vụ marketing. Sửa lỗi app phát hiện trong QA phải có task riêng.
2. Landing chạy preview/build riêng trước, không takeover `/` của app đang nộp.
3. Khóa manifest content/media cùng build ID; cùng release giữ model profile,
   evidence report và asset hash tương thích. File nặng được version bằng GCS.
4. Nếu animation hoặc video gây lag: tắt motion/hero autoplay, chuyển poster,
   giữ CTA và transcript. Fallback này không chặn người vào app thật.
5. Nếu landing release lỗi: chuyển traffic service landing về revision trước;
   giữ URL app nguyên. Nếu đã đổi DNS thì dùng record backup với TTL được ghi
   nhận; không xóa revision/asset còn được bản trước tham chiếu.
6. Mỗi khi RoadWatch đổi model/copy/UI: cập nhật claim matrix và screenshots,
   render lại fixture/WAV cần thiết, chạy visual/audio check, giữ revision cũ.
7. Ghi ngày cập nhật trên evidence và changelog; nếu số đo cũ khác điều kiện
   hiện tại, gắn “historical snapshot”, không âm thầm đổi tên thành kết quả mới.

Mẫu handoff mỗi task: Task ID / thay đổi / file / bằng chứng / pass-fail-blocked /
giới hạn / rollback / bước tiếp theo. Tài liệu này là blueprint để agent triển
khai theo LP-00→LP-10 ở phiên sau; mọi task chưa làm giữ `PLANNED`.

## 13. Nguồn và phạm vi phiên lập kế hoạch

Nguồn nội bộ: [README](../README.md),
[báo cáo kỹ thuật](ROADWATCH_TECHNICAL_REPORT.md),
[Master Action Plan](MASTER_ACTION_PLAN.md),
[performance 2026-08-29](PERFORMANCE_STREAMING_OPTIMIZATION_2026-08-29.md),
[kiến trúc deployment](UNIFIED_DEPLOYMENT_ARCHITECTURE.md),
[landing nháp](../frontend/src/landing/README.md),
`frontend/src/landing/{LandingPage.tsx,content.ts,landing.css}`, `configs/default.json`.

Nguồn công khai đã đọc 2026-08-30 được đặt cạnh quyết định tương ứng trong tài
liệu. Không dùng số liệu/safety claim của hãng tham khảo để chứng minh RoadWatch.
Skill Product Design giúp chốt brief, kế thừa source hiện có và đặt visual
selection trước implementation. Đây là plan bằng văn bản theo yêu cầu, chưa
tạo mockup mới, tải stock, dựng website, cài dependency, deploy hoặc chỉnh DNS.

| Version | Ngày | Thay đổi |
|---|---|---|
| 1.0 | 2026-08-30 | Blueprint đầu tiên: 10 section, 6 tương tác, media inventory, LP-00–LP-10, quality gates và rollback |
