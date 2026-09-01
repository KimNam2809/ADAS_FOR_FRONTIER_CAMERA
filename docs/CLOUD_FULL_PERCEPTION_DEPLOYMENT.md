# RoadWatch Cloud Full-Perception Deployment

Ngày nghiệm thu: 2026-08-24  
GCP project: `c3-roadwatch-162`  
Cloud Run service: `roadwatch-web`  
Revision full-perception gốc: `roadwatch-web-00016-wkd`  
Revision on-demand hiện hành: `roadwatch-web-00021-qd4`  
Fallback URL: <https://roadwatch-web-bx6lfekcba-as.a.run.app>

## 1. Mục tiêu và quyết định kiến trúc

Cloud demo trước đây dùng object-only profile để khắc phục E2E khoảng 31 giây.
Revision này khôi phục traffic sign, lane, hazard, TTS tiếng Việt và beep mà
không đưa optional model vào critical latency path.

- Object/risk/annotation chạy ở pipeline chính.
- Traffic sign và YOLOP chạy trong hai latest-frame worker độc lập, có session
  generation và staleness cap để không rò kết quả khi seek/đổi video.
- Sign chạy mỗi processed frame; lane chạy mỗi bốn processed frame và dùng cache
  giữa hai lần inference.
- Cloud Run dùng 8 vCPU/8 GiB và session affinity. API client
  phải giữ affinity cookie giữa start/status/stream; trình duyệt thực hiện việc
  này tự động.
- Container không phát loa server. Browser dùng Web Audio cho beep và Web Speech
  `vi-VN` cho TTS, lấy trực tiếp `spoken_message` từ canonical alert event.

## 2. Model thực tế trên Cloud

| Head | Artifact | Nguồn quyết định | Runtime |
|---|---|---|---|
| Road user | `yolo11n_320.onnx` | Baseline COCO thắng Object V2 ở event recall/FAR | ONNX CPU, 320 |
| Traffic sign | `roadwatch_detector_v2_416.onnx` | Runtime export 416 từ weights Traffic Sign Phase 2 đã promote | ONNX CPU, 416 |
| Speed value | `roadwatch_speed_digits_v2.onnx` | Classifier Phase 2 đã promote | ONNX CPU, 160 crop |
| Lane/drivable | `yolop_lane_detection_640.onnx` | Release lane hiện hành; UFLDv2 chưa đạt edge FPS gate | ONNX CPU, 640 |

Không dùng Object V2 đã rejected, UFLDv2 candidate fail edge FPS gate hoặc Fallen
Rider candidate chưa qua dataset gate. Export 416 không phải model mới được train;
đó là cùng weights sign Phase 2 với input resolution dành riêng cho Cloud CPU.

Artifact runtime mới:

- `roadwatch_detector_v2_416.onnx`: SHA-256
  `6CFCD2C09F750C3828AAFF7387FEB4ED89DA46A1608339C1095BBE75B1ACAFDA`.
- `roadwatch_speed_digits_v2.onnx`: SHA-256
  `B26B89E8692CB694B869EF4C62269FA0AFA29C76BC5006F4FD6A8A7D3E9D8ECF`.

Hai artifact được phân phối qua GCS allowlist, không qua Git. `.gitignore` chỉ
ngăn file nặng vào repository và không được dùng để loại runtime asset khỏi GCP.

## 3. Quality gate của sign runtime export

- `test_video10`, 2–7 giây: 4 frame nhận đúng 60; temporal risk tạo speed-60
  candidate và canonical message đúng.
- `test_video11`, 31,5–35,5 giây: 6 frame nhận đúng 80. Cửa sổ có cả biển theo
  lane 60/80; lane-binding vẫn là limitation riêng, không được tùy tiện chọn một
  giới hạn khi không chắc lane relevance.
- `video_test`, negative window 34–67 giây: 124 sample, `0` speed-sign candidate.
- Không giảm `sign_confidence`, classifier confidence hoặc confirmation hits.
  Temporal association được sửa theo screen velocity/thời gian, có distance cap.

## 4. Public acceptance evidence

### Speed sign → hazard → TTS

`test_video10`, 2–7 giây, giữ Cloud Run affinity cookie:

- Start API: `78 ms`; first frame: `613 ms`.
- Detector: speed 60 confidence `0,9136`.
- Speed classifier: confidence `0,9806`.
- Event: `speed_sign`, source time `4,133 s`, `hits=3`.
- `display_message == spoken_message`:
  `Tối đa 60 ki-lô-mét/giờ.`
- `audio_action=tts`.
- Processed FPS `5,00`; E2E p50 `56,20 ms`, p95 `83,42 ms`.

### Lane/drivable overlay

`test_video10`, 8–16 giây:

- Max lane quality `1,00`; final lane quality `0,9688`.
- Lane quality coverage `0,60` trên cửa sổ.
- Processed FPS `5,10`; E2E p50 `62,74 ms`, p95 `84,18 ms`.
- Model health: object/sign/speed/lane đều loaded, CPU provider, error `null`.

`/api/health.status` vẫn có thể là `degraded` vì edge R0 release manifest yêu cầu
PT/hash artifact không được đóng gói trong Cloud container. Đây là cloud-profile
manifest mismatch đã biết; provider health ở trên mới là bằng chứng runtime cho
public replay. Không được diễn giải `degraded` thành model inference đang lỗi,
nhưng cũng chưa được đổi thành tuyên bố production-ready.

### FCW → beep + TTS

`test_video10`, 14–19 giây:

- Critical FCW tại source time `15,333 s`, risk `0,96`.
- `display_message == spoken_message == Cảnh báo va chạm phía trước!`.
- `audio_action=beep_tts`.
- Processed FPS `4,85`; E2E p95 `117,44 ms`.

### Browser smoke

- Driver HUD phát hiện speed 60 và hiển thị canonical message trong evidence
  timeline.
- Browser audio chuyển từ `Chạm để bật` sang `Web Speech vi-VN` sau user gesture
  và utterance start.
- Engineer Console hiển thị ba perception head `HEALTHY/Loaded`.
- Lane overlay xuất hiện trong MJPEG; không có browser console warning/error.
- E2E p95 quan sát trên UI khoảng `87 ms` trong phiên dài hơn.

## 5. Verification và release/rollback

- Python regression: `152/152` pass.
- Targeted cloud/sign/risk tests: `24/24` pass.
- Python compile, TypeScript và Vite production build: pass.
- Final Cloud Build: `c79fc08c-fbaf-447a-b784-c470a7613cd5`, status `SUCCESS`.
- Final revision: `roadwatch-web-00016-wkd`, 100% traffic.
- Rollback nhanh: chuyển traffic về `roadwatch-web-00010-rbk` để lấy object-only
  low-latency profile; source rollback checkpoint trước GCP vẫn được giữ.

## 6. Giới hạn còn lại

- Đây là public replay/evaluation plane, không phải benchmark Jetson hoặc bằng
  chứng an toàn xe thật.
- Browser TTS phụ thuộc voice `vi-VN` của trình duyệt/OS và cần user gesture để
  vượt autoplay policy. Local/AAOS vẫn dùng Piper/offline audio path riêng.
- Từ 2026-08-25, Web và Piper chuyển sang `min=0,max=1`: không còn compute idle
  24/7 nhưng cold start tăng. UI dùng `/api/startup` để hiển thị rõ GCP/model/TTS
  đang khởi động; warm latency phải được báo riêng với startup elapsed.
- YOLOP có thể reject frame mờ/tối và trả lane quality 0; đây là fail-safe để
  khóa LDW, không phải luôn vẽ lane bằng mọi giá.
- Multi-lane sign binding 60/80, calibration, CAN/radar và closed-course safety
  validation vẫn chưa đủ để tuyên bố production-ready trên xe thật.

## 7. On-demand startup cho giai đoạn chấm bài

- FastAPI yield sớm và chạy GCS/model/Piper bootstrap trong background để HTML
  không bị chặn bởi download/load model.
- Chỉ bốn model active được tải lúc startup; bốn video mẫu (~252 MB) chỉ tải từ
  GCS khi được chọn. Library metadata vẫn hiển thị đầy đủ trước khi tải video.
- Full-screen gate tiếng Việt giải thích lần đầu thường cần 1–3 phút, công bố
  stage GCP/Dữ liệu/Model AI/TTS và tự poll 2 giây/lần.
- `/api/session/start` fail-closed với HTTP 503/Retry-After khi chưa ready.
- Đây là cost/UX mode, không phải thay đổi model, ngưỡng risk hoặc safety claim.

### 7.1. Cấu hình và bằng chứng phát hành 2026-08-25

- Web `roadwatch-web-00021-qd4` và TTS `roadwatch-tts-00004-kdv` nhận 100%
  traffic; cả hai service dùng service-level `min=0,max=1`.
- Web vẫn giữ 8 vCPU/8 GiB, TTS giữ 2 vCPU/2 GiB và CPU always allocated trong
  thời gian instance tồn tại. Vì `min=0`, instance được phép scale về 0 khi idle;
  đây là on-demand mode, không phải lịch bật/tắt thủ công.
- Web image dùng `Dockerfile.cloud`/`requirements-cloud.txt`, chỉ chứa dependency
  ONNX/FastAPI/OpenCV/GCS cần cho Cloud. PyTorch, Ultralytics và CUDA local không
  còn nằm trong image này; bốn model runtime vẫn được tải từ GCS allowlist.
- Cloud Build Web gọn: `6d0770f6-8d65-4da7-bd6c-cd45266826dd`, digest
  `sha256:0e3430d08a940cee86ffb7e524af13159d65f9aaa6c71ad6b5dd75ecb3622f8b`.
- Cloud Build TTS: `2dadf250-fb46-4cb4-bac7-2666102f48c5`.
- Public startup API sau deploy: `ready=true`, startup nội bộ `5,0 s`; HTTP
  request kiểm tra `450,55 ms`. Đây là lần nghiệm thu sau deploy, không được coi
  là phép đo cold start sau 15 phút idle.
- Fresh run `test_video10` tải lazy lần đầu: start `1.562,42 ms`. Run warm 15 s:
  57 frame, end-to-end P50/P95 `56,26/77,23 ms`, object P95 `24,22 ms`, không
  pipeline error/degraded reason.
- Model health: object `yolo11n_320.onnx`, sign
  `roadwatch_detector_v2_416.onnx`, speed classifier
  `roadwatch_speed_digits_v2.onnx` và lane `yolop_lane_detection_640.onnx` đều
  `loaded=true` trên ONNX CPU.
- FCW canonical event phát `beep_tts`; Piper trả WAV HTTP 200, 56.364 byte,
  provider `piper/vi_VN-vais1000-medium`, public cache-hit round-trip `197,91 ms`.
- Regression hiện hành `162/162` pass; Python compile, TypeScript và Vite
  production build đều pass.

### 7.2. Rollback

- Runtime rollback nhanh: chuyển Web về `roadwatch-web-00019-x8h`, TTS về
  `roadwatch-tts-00003-rt7` và đặt lại `min=1` nếu cần phiên demo luôn-warm.
- Không xóa revision, GCS model/video hoặc Piper voice khi rollback.
- Bản on-demand giảm chi phí compute idle nhưng người chấm đầu tiên sau idle sẽ
  thấy startup gate. Khoảng chờ thực tế phụ thuộc image pull, GCS và quota; UI
  chủ động thông báo ước lượng 1–3 phút và tự chuyển khi API báo ready.
