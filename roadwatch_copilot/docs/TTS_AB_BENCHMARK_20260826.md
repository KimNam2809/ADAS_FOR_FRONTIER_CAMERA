# TTS A/B benchmark — 2026-08-26

## Kết luận release

VieNeu-TTS v3 Turbo đã đạt static/performance gate trên máy phát triển Windows
AMD, nhưng **chưa được promote** vì chưa có human listening gate. Piper vẫn là
provider release và rollback mặc định.

Hardware/runtime: Windows 11, Python 3.12.13, AMD64/AMD Ryzen 5 7535HS, ONNX
Runtime CPU. VieNeu dùng `backend=onnx`, `precision=int8`, preset voice
`Minh Triết`. Cả hai provider dùng cùng corpus 149 câu và cache budget 256.

## Kết quả đo được

| Chỉ số | Piper baseline | VieNeu candidate | Gate |
|---|---:|---:|---:|
| Canonical success | 149/149 | 149/149 | 149/149 |
| WAV hợp lệ | 149/149 | 149/149 | 149/149 |
| Uncached P50 | 110.045 ms | 736.683 ms | ≤ 2.000 ms |
| Uncached P95 | 158.327 ms | 1110.677 ms | ≤ 2.000 ms |
| Cached start P50 | 0.006 ms | 0.004 ms | ≤ 750 ms |
| Cached start P95 | 0.011 ms | 0.012 ms | ≤ 750 ms |
| RSS trong process benchmark | 286.32 MB | 868.05 MB | ≤ 2 GiB |
| Error | 0 | 0 | 0 |

VieNeu first run model/session load: `105.401 s`; first gateway synthesis sau
OS/model cache: `8.987 s`, trong đó `8.983 s` là synthesis path. Đây là cold-load
evidence cần hiển thị riêng, không được cộng vào realtime alert claim. Khi model
đã warm và câu đã cache, đường phát cảnh báo nhanh hơn đáng kể.

Raw evidence local (được `.gitignore` để không commit artifact):

- `reports/tts-ab-vieneu-latest.json`
- `reports/tts-ab-piper-latest.json`

## Promotion decision

Static/performance: `PASS` cho cả baseline và candidate.

Human listening: `PENDING`; cần tối thiểu 3 người Việt nghe các câu có hướng,
hành động và số `40/50/60/80`, điểm trung bình tối thiểu `4/5`, đồng thời xác
nhận không mất âm đầu và không sai nghĩa.

Vì vậy:

```text
active release provider = Piper
VieNeu = candidate / local A-B only
Cloud Run + AAOS promotion = chưa thực hiện
```

## Bằng chứng implementation

- `backend/roadwatch/tts.py`: `TTSProvider`, gateway, fallback và telemetry.
- `backend/roadwatch/tts_vieneu.py`: adapter VieNeu ONNX CPU/int8, preset voice,
  WAV validation và bounded cache.
- `backend/roadwatch/audio.py`: native speaker có thể thử candidate local nhưng
  fallback về Piper nếu candidate lỗi.
- `scripts/benchmark_tts_ab.py`: benchmark cùng corpus, uncached/cached pass và
  report promotion pending human.
- `tests/test_tts.py`: adapter/cache/fallback/API contract tests.

## Giới hạn và rollback

Benchmark chạy trên CPU laptop; không suy diễn thành Jetson Orin hoặc xe thật.
Không có người nghe độc lập trong phiên này nên không được gọi VieNeu là release
provider. Rollback không cần xóa model/cache:

```powershell
$env:ROADWATCH_TTS_PROVIDER = "piper"
```

Sau khi restart backend, kiểm tra `/api/health` có
`requested_provider: piper`, `mode: local` hoặc `dedicated_cloud_service`.
