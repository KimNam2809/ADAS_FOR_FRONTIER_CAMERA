# RoadWatch — TTS duplicate playback fix

## Kết quả

RoadWatch local Web dùng một audio owner duy nhất: browser. Backend chỉ tạo và
trả WAV Piper; nó không phát loa server trong chế độ này. Native/AAOS vẫn có thể
dùng owner `server` một cách tường minh.

Voice release được khóa vào:

```text
piper/vi_VN-vais1000-medium
voice alias: Trúc Ly
sample rate: 22.050 Hz
num speakers: 1
cache namespace: piper-v3
```

`Trúc Ly` là tên hiển thị của RoadWatch. Metadata Piper xác nhận model có một
speaker, vì vậy đây không phải là một `speaker_id` riêng trong model.

## Vì sao câu bị lặp

Piper trực tiếp sinh câu bình thường. Hiện tượng như `Cảnh cảnh báo báo va va
chạm chạm` là dấu hiệu audio bị phát chồng hoặc WAV cũ bị dùng lại, không phải
lỗi phát âm tiếng Việt của model.

Các lớp bảo vệ hiện tại:

- Backend claim một `event_id` một lần và dedupe cùng canonical audio key.
- Browser claim event, khóa một speech playback trong session và không phát
  trùng cùng message trong cửa sổ ngắn.
- `beep_tts` có một beep sequence và một WAV duy nhất.
- Cache key chứa provider, SHA-256 model, SHA-256 config và canonical message.
- Token lặp liền kề được chuẩn hóa trước khi gửi vào Piper.
- Không có fallback sang `window.speechSynthesis`, `pyttsx3` hoặc voice Windows.

## Kiểm tra sau khi cập nhật

```powershell
cd roadwatch
.\scripts\setup.ps1
.\scripts\start.ps1 -Port 8019
```

Mở một tab mới hoặc hard reload, sau đó kiểm tra `http://127.0.0.1:8019/api/health`.
Các giá trị cần thấy:

```text
frontend_release.bundle = dist-ui-v4
tts.provider = piper/vi_VN-vais1000-medium
tts.voice_name = Trúc Ly
audio.output_owner = browser
audio.playback_mode = single_owner
audio.server_playback = false
tts.cache_namespace = piper-v3
```

Trong DevTools → Network, một cảnh báo chỉ được có một request:

```text
/api/tts/events/{event_id}.wav
```

Trong Console không được xuất hiện `speechSynthesis` hoặc lỗi JavaScript.

## Bằng chứng local đã chạy

- Python unit suite: toàn bộ test pass; chỉ còn warning deprecation của
  `starlette.testclient`.
- `compileall`: pass.
- Vite/TypeScript build vào `frontend/dist-ui-v4`: pass.
- Piper direct smoke: WAV `RIFF/WAVE`, mono, `22.050 Hz`, model SHA-256:
  `ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab`.
- API smoke trên port `8019`: health `ready`, bundle `dist-ui-v4`, owner
  `browser`, server playback `false`, policy `enforce`.
- Replay `test_video10.mp4`: event biển giới hạn 60 được tạo; endpoint TTS trả
  HTTP `200`, `audio/wav`, provider Piper và đúng model fingerprint.

Kiểm tra nghe bằng tai trong trình duyệt vẫn là human gate: mở tab mới/hard
reload, chạm một lần để bật audio, chạy video có FCW và xác nhận một câu chỉ
được nghe một lần.

## Fallback

- UI cũ vẫn giữ nguyên và có thể chọn bằng `-FrontendDist`.
- Piper vẫn là release baseline; VieNeu không tự động được promote.
- `-AudioOwner server` dành cho native/AAOS khi cần phát qua thiết bị âm thanh
  của edge.
- Cache cũ không bị xóa; namespace `piper-v3` khiến WAV cũ không được tái dùng.
