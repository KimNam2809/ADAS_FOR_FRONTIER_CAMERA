# YOLOP vs TwinLiteNet+ — All RoadWatch Videos Replay

Generated: `2026-08-28T05:29:20.372863+00:00`  
Runtime: `directml`  
Videos: `16`; processed samples: `192`

> Đây là benchmark replay không có ground-truth. Quality proxy, temporal IoU và mask agreement chỉ dùng để hỗ trợ quyết định demo; không phải accuracy/mIoU.

## Tổng hợp

| Model | Samples | P50 (ms) | P95 (ms) | Mean quality proxy | Temporal IoU |
|---|---:|---:|---:|---:|---:|
| `yolop` | 192 | 59.709 | 65.874 | 0.6438 | 0.0958 |
| `twinlitenetplus_medium_onnx` | 192 | 33.181 | 37.625 | 0.7238 | 0.1639 |

## Quyết định an toàn

- Không tự động promote model nào.
- YOLOP vẫn là fallback production.
- TwinLiteNet+ chỉ có thể là demo candidate sau khi kiểm tra ảnh overlay; muốn thay production vẫn cần ground-truth và LDW regression.
- Ảnh overlay nằm tại:
  `roadwatch\reports\review\twinlitenetplus-vs-yolop-all-videos-12`

## Theo từng video

- `dashcam_vietnam.mp4` — 12 samples; YOLOP P95 `59.819 ms`; TwinLiteNet+ P95 `33.812 ms`; lane agreement `0.3289`.
- `dashcam_vietnam_night.mp4` — 12 samples; YOLOP P95 `60.565 ms`; TwinLiteNet+ P95 `34.28 ms`; lane agreement `0.3326`.
- `dashcam_vietnam_rain+night.mp4` — 12 samples; YOLOP P95 `59.899 ms`; TwinLiteNet+ P95 `33.325 ms`; lane agreement `0.3656`.
- `dashcam_vietnam_traffic_multi.mp4` — 12 samples; YOLOP P95 `62.149 ms`; TwinLiteNet+ P95 `34.75 ms`; lane agreement `0.4812`.
- `test_video1.mp4` — 12 samples; YOLOP P95 `65.375 ms`; TwinLiteNet+ P95 `37.22 ms`; lane agreement `0.2245`.
- `test_video10.mp4` — 12 samples; YOLOP P95 `63.803 ms`; TwinLiteNet+ P95 `34.506 ms`; lane agreement `0.5525`.
- `test_video11.mp4` — 12 samples; YOLOP P95 `61.757 ms`; TwinLiteNet+ P95 `36.428 ms`; lane agreement `0.3317`.
- `test_video2.mp4` — 12 samples; YOLOP P95 `61.272 ms`; TwinLiteNet+ P95 `36.083 ms`; lane agreement `0.4518`.
- `test_video3.mp4` — 12 samples; YOLOP P95 `62.467 ms`; TwinLiteNet+ P95 `34.245 ms`; lane agreement `0.3886`.
- `test_video4.mp4` — 12 samples; YOLOP P95 `64.142 ms`; TwinLiteNet+ P95 `37.625 ms`; lane agreement `0.402`.
- `test_video5.mp4` — 12 samples; YOLOP P95 `69.78 ms`; TwinLiteNet+ P95 `38.756 ms`; lane agreement `0.3583`.
- `test_video6.mp4` — 12 samples; YOLOP P95 `61.144 ms`; TwinLiteNet+ P95 `35.818 ms`; lane agreement `0.4614`.
- `test_video7.mp4` — 12 samples; YOLOP P95 `62.113 ms`; TwinLiteNet+ P95 `37.332 ms`; lane agreement `0.4692`.
- `test_video8.mp4` — 12 samples; YOLOP P95 `59.675 ms`; TwinLiteNet+ P95 `33.174 ms`; lane agreement `0.4645`.
- `test_video9.mp4` — 12 samples; YOLOP P95 `63.885 ms`; TwinLiteNet+ P95 `34.652 ms`; lane agreement `0.5556`.
- `video_test.mp4` — 12 samples; YOLOP P95 `65.092 ms`; TwinLiteNet+ P95 `38.177 ms`; lane agreement `0.3295`.
