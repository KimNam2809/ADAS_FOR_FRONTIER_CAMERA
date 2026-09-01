# RoadWatch TTS Provider A/B và Quality Gate

## Mục đích

RoadWatch giữ Piper tiếng Việt làm release baseline vì đây là provider offline đã
được tích hợp và kiểm thử. VieNeu-TTS v3 Turbo chỉ là candidate để benchmark, không
tự động thay thế Piper và không được coi là đã được promote chỉ vì giọng nghe tự
nhiên hơn.

Kiến trúc dùng chung là:

```text
server-generated event ID
        ↓
canonical_message (banner == spoken_message)
        ↓
TTSProvider → Piper hoặc VieNeu candidate
        ↓
PCM WAV → Web/AAOS/native speaker
```

MOSS-Audio-Tokenizer-Nano-ONNX không phải TTS độc lập. Nó là audio codec/tokenizer
được VieNeu sử dụng bên dưới; RoadWatch không tải nó rồi gọi trực tiếp với text.
Tham khảo upstream: [VieNeu-TTS v3 Turbo](https://huggingface.co/pnnbao-ump/VieNeu-TTS-v3-Turbo)
và [MOSS Audio Tokenizer](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX).

## Cấu hình an toàn

Mặc định không cần cấu hình gì thêm:

```powershell
# Release baseline, local hoặc Piper Cloud Run hiện tại
$env:ROADWATCH_TTS_PROVIDER = "piper"
```

Chạy candidate local có fallback Piper:

```powershell
pip install -r requirements-tts-vieneu.txt
$env:ROADWATCH_TTS_PROVIDER = "vieneu"
$env:ROADWATCH_TTS_BACKEND = "onnx"
$env:ROADWATCH_TTS_PRECISION = "int8"
$env:ROADWATCH_TTS_VOICE_NAME = "Minh Triết"
```

VieNeu được lazy-load để default Piper không bị thêm thời gian import hoặc tải model.
Candidate chỉ chạy local trong giai đoạn A/B; `ROADWATCH_TTS_SERVICE_URL` không được
dùng để âm thầm chuyển candidate thành Cloud Run Piper. Nếu VieNeu lỗi khi phát một
cảnh báo, gateway dùng Piper local và công bố `fallbacks` cùng `last_fallback_reason`
trong `/api/health` hoặc `/api/status`.

Không đặt text tùy ý từ client vào đường phát cảnh báo. Endpoint public vẫn nhận
`event_id` của server-generated event và lấy `spoken_message` canonical từ storage.
Không dùng browser Web Speech vì giọng hệ thống có thể đọc tiếng Việt bằng phát âm
tiếng Anh.

## Chạy benchmark toàn bộ corpus đang bật

Benchmark tự lấy toàn bộ câu từ `default_alert_corpus()` của profile đang bật,
thay vì hard-code số lượng câu. Với catalog vNext hiện tại, corpus có thể khác
baseline cũ; report JSON luôn ghi `corpus_count` thực tế.

```powershell
cd roadwatch
.\.venv\Scripts\python.exe .\scripts\benchmark_tts_ab.py `
  --provider all `
  --output reports/tts-ab-latest.json
```

Có thể chạy riêng một provider:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_tts_ab.py --provider vieneu
```

Report không chứa WAV/model/secret và được ignore khỏi Git. Nếu package/model VieNeu
chưa sẵn sàng, benchmark ghi `dependency_missing_or_asset_unavailable` thay vì làm
hỏng Piper.

## Promotion gate

Candidate phải đạt đồng thời:

| Gate | Mức bắt buộc |
|---|---:|
| Canonical messages | `N/N` theo `corpus_count` thực tế |
| WAV | `N/N` RIFF/WAVE hợp lệ, không cắt âm đầu |
| Uncached short-alert P95 | `≤ 2.000 ms` |
| Cached start P95 | `≤ 750 ms` |
| Audio completion | `≥ 99%` |
| Memory | `≤ 2 GiB` cho service |
| Human listening | ≥ 3 người Việt, điểm trung bình `≥ 4/5` |
| Semantic listening | Không sai `trái/phải/phía trước`, hành động và số `40/50/60/80` |

`promotion_decision` của benchmark luôn bắt đầu là
`blocked_pending_human_listening`. Sau khi static/performance pass, cần lưu kết quả
nghe của ít nhất ba người độc lập. Chỉ khi toàn bộ gate pass mới được thay đổi
provider cho demo/Web/AAOS. Nếu fail, giữ Piper và sửa candidate.

## Rollback

```powershell
$env:ROADWATCH_TTS_PROVIDER = "piper"
Remove-Item Env:ROADWATCH_TTS_BACKEND -ErrorAction SilentlyContinue
Remove-Item Env:ROADWATCH_TTS_PRECISION -ErrorAction SilentlyContinue
```

Sau khi restart backend, `/api/health` phải báo `requested_provider: piper` và
`mode: local` hoặc `dedicated_cloud_service`. Không cần xóa VieNeu cache để rollback;
không xóa voice Piper baseline.

## Giới hạn triển khai

- VieNeu model card là nguồn thông tin upstream; số đo release phải lấy từ benchmark
  local trên phần cứng đã ghi rõ.
- Không dùng kết quả VieNeu trên laptop AMD để tuyên bố đạt realtime Jetson Orin.
- Không đưa candidate vào Cloud Run hoặc critical AAOS path trước local gate và human
  listening gate.
- TTS chỉ đọc cảnh báo đã được Alert Governor ủy quyền; quyết định FCW/VRU/LDW vẫn là
  deterministic rule engine, không phụ thuộc SLM.
