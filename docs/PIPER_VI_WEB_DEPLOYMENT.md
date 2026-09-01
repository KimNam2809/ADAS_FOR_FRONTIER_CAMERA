# RoadWatch Public Web — Piper tiếng Việt

## 1. Kết quả

Public Web không còn dùng `window.speechSynthesis`. TTS được cố định thành
Piper `vi_VN-vais1000-medium`, tổng hợp thành WAV ở dịch vụ Cloud Run riêng và
phát bằng Web Audio trên Driver HUD. Beep vẫn được sinh tức thời tại browser.

- Public URL: `https://roadwatch-web-bx6lfekcba-as.a.run.app`
- Web revision hiện hành: `roadwatch-web-00021-qd4`
- TTS revision hiện hành: `roadwatch-tts-00004-kdv`
- Provider hiển thị trên HUD: `piper/vi_VN-vais1000-medium`
- Language metadata: `vi_VN`, Vietnamese, Vietnam
- Sample rate: `22.050 Hz`; quality: `medium`; một người nói nữ.

## 2. Nguyên nhân lỗi trước đây

`SpeechSynthesisUtterance.lang = "vi-VN"` chỉ là yêu cầu lựa chọn ngôn ngữ. Nếu
máy chấm/demo không cài voice tiếng Việt, browser có thể fallback sang voice
tiếng Anh. Vì vậy “Hãy chú ý” bị phát âm như tiếng Anh dù chuỗi Unicode đúng.

Không thể khắc phục chắc chắn bằng cách đổi `rate`, `pitch` hoặc tiếp tục tìm
voice trong `speechSynthesis.getVoices()`: danh sách này phụ thuộc máy khách.

## 3. Voice được chọn và tính pháp lý

Voice chính thức là `vi_VN-vais1000-medium` từ `rhasspy/piper-voices`:

- Model: <https://huggingface.co/rhasspy/piper-voices/blob/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx>
- Config: <https://huggingface.co/rhasspy/piper-voices/blob/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json>
- Model card: <https://huggingface.co/rhasspy/piper-voices/blob/main/vi/vi_VN/vais1000/medium/MODEL_CARD>
- Dataset: VAIS-1000; license ghi trong model card: CC BY 4.0.
- Piper runtime: <https://github.com/OHF-Voice/piper1-gpl>, GPL-3.0.

Không chọn `vi_VN-25hours_single-low` vì giấy phép dataset/model chưa rõ ràng.
Tài liệu và source RoadWatch phải giữ attribution này khi phân phối sản phẩm.

## 4. Quản lý artifact

Hai file voice không nằm trong Git. Chúng được upload vào:

```text
gs://c3-roadwatch-162-roadwatch-assets/voices/vi_VN-vais1000-medium.onnx
gs://c3-roadwatch-162-roadwatch-assets/voices/vi_VN-vais1000-medium.onnx.json
```

| Artifact | Size | SHA-256 | GCS/local MD5 |
|---|---:|---|---|
| ONNX | 63.201.294 B | `ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab` | `XkJCjE9hMfdVV88VbJwVJg==` |
| JSON | 4.860 B | `fafb9da1354ed4b77c31af228ed41fb41cd825c14cffa105454b25e6ae751ee0` | `XslmklNUHWS6l/YOQi8a0A==` |

`configs/cloud_assets.json` là allowlist; `asset_bootstrap.py` xác minh SHA-256
trước khi dùng. `.gitignore` chỉ ngăn GitHub nhận file nặng, không loại asset
khỏi GCP.

## 5. Luồng thực thi

1. Risk/Alert Governor sinh `spoken_message` và `audio_action` như trước.
2. Frontend nhận event qua `/api/status`.
3. Beep `beep_tts` được phát ngay bằng Web Audio.
4. Frontend yêu cầu `/api/tts/events/{event_id}.wav` với token đăng nhập.
5. Web backend chỉ chấp nhận event do server đã sinh; không nhận arbitrary text
   từ public client.
6. Web service gọi private `roadwatch-tts` bằng Cloud Run identity token.
7. TTS service trả WAV Piper; browser decode và phát sau beep.

TTS chạy ở Cloud Run 2 CPU/2 GiB riêng, concurrency 4, `min=0,max=1`. Piper
không tranh CPU với object/sign/lane perception 8 CPU và không phát sinh compute
idle 24/7.

## 6. Chống cold start và quá tải

- TTS warm-up chạy graph và Vietnamese phonemizer trong startup.
- On-demand startup tải voice, chạy graph/phonemizer với câu prime duy nhất;
  không pre-cache 149 câu để giảm cold start. Cache runtime vẫn giới hạn `256`.
- Web lấy IAM token và gọi private `/health` trong startup gate, vì vậy gate chỉ
  chuyển ready sau khi Piper container đã thức dậy.
- Browser không fallback về voice tiếng Anh. Nếu Piper lỗi, HUD báo lỗi thay vì
  đọc sai ngôn ngữ.
- HTTP web concurrency tăng từ 8 lên 80 vì mỗi MJPEG stream giữ một slot. TTS
  concurrency vẫn là 4 và chỉ có một synthesizer lock, không tăng inference song
  song ngoài kiểm soát.

## 7. Bằng chứng acceptance

### API/public

- FCW: `audio_action=beep_tts`, message `Cảnh báo va chạm phía trước!`.
- Piper: cache hit, synthesis `0,000 ms`, public TTS round-trip `308,16 ms`.
- Perception: E2E p50 `63,89 ms`, p95 `94,02 ms`; object p95 trong gate trước
  `25,50 ms`; processed FPS `4,39`; `tts_failed=0`.
- Sau tăng concurrency: 12/12 health requests HTTP 200, 0 response 429.

### Browser

- HUD chuyển sang `Sẵn sàng · piper/vi_VN-vais1000-medium · hit`.
- FCW banner hiện đúng; FPS `5,16`; UI P95 `84,3 ms`.
- Browser console: không có warning/error.
- Source frontend không còn `speechSynthesis`/`SpeechSynthesisUtterance`.

### Regression

- Python full regression hiện hành: `162/162` pass.
- TypeScript và Vite production build: pass.
- Voice WAV có header `RIFF/WAVE`; local unseen phrase sau warm-up khoảng
  `142,5 ms`; cache lookup khoảng `0,03 ms`.

## 8. Hạn chế và rollback

- Cần một user gesture (“Chạm để bật”) do autoplay policy của browser; đây là
  hạn chế trình duyệt, không phải thiếu voice.
- Chất lượng `medium` phù hợp câu ADAS ngắn, chưa thay thế quality gate nghe bởi
  nhiều người Việt ở cabin/loa ô tô.
- TTS `min=0` có cold start sau giai đoạn idle. Web startup gate đánh thức Piper
  trước khi cho phép phân tích; nếu phiên để mở quá lâu trước cảnh báo đầu tiên,
  request TTS vẫn có thể chịu một cold start mới và HUD sẽ báo lỗi thay vì dùng
  voice tiếng Anh.
- Rollback web: chuyển traffic về `roadwatch-web-00018-hkt` hoặc `00017-czw`.
- Rollback TTS: chuyển traffic về `roadwatch-tts-00002-5bn`; không xóa voice GCS.

## 9. On-demand acceptance 2026-08-25

- Cả Web và TTS dùng `min=0,max=1`; Web startup gate gọi private TTS `/health`
  nên người chấm chỉ vào màn hình đăng nhập sau khi Piper sẵn sàng.
- TTS không pre-cache 149 câu lúc khởi động (`ROADWATCH_TTS_PRECACHE=0`); một câu
  prime vẫn kiểm tra graph và Vietnamese phonemizer.
- Public FCW smoke trên revision hiện hành trả WAV HTTP 200, 56.364 byte,
  provider `piper/vi_VN-vais1000-medium`, cache hit và round-trip `197,91 ms`.
- Build TTS hiện hành: `2dadf250-fb46-4cb4-bac7-2666102f48c5`; build Web:
  `6d0770f6-8d65-4da7-bd6c-cd45266826dd`.
- Rollback on-demand gần nhất: Web `roadwatch-web-00019-x8h`, TTS
  `roadwatch-tts-00003-rt7`, đồng thời đặt lại `min=1` nếu cần luôn-warm.
