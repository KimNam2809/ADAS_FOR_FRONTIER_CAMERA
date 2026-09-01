# YOLOP vs TwinLiteNet+ — All RoadWatch Videos Replay

Generated: `2026-08-28T05:25:22.481317+00:00`  
Runtime: `directml`  
Videos: `16`; processed samples: `96`

> Đây là benchmark replay không có ground-truth. Quality proxy, temporal IoU và mask agreement chỉ dùng để hỗ trợ quyết định demo; không phải accuracy/mIoU.

## Tổng hợp

| Model | Samples | P50 (ms) | P95 (ms) | Mean quality proxy | Temporal IoU |
|---|---:|---:|---:|---:|---:|
| `yolop` | 96 | 56.575 | 61.159 | 0.6346 | 0.0525 |
| `twinlitenetplus_medium_onnx` | 96 | 32.928 | 34.902 | 0.6972 | 0.1129 |

## Quyết định an toàn

- Không tự động promote model nào.
- YOLOP vẫn là fallback production.
- TwinLiteNet+ chỉ có thể là demo candidate sau khi kiểm tra ảnh overlay; muốn thay production vẫn cần ground-truth và LDW regression.
- Ảnh overlay nằm tại:
  `D:\AI_VinUni_Project_T162\SetUpModule\Object-Ditection-Manual\yolo-universal-counter\yolo-universal-counter\roadwatch\reports\review\twinlitenetplus-vs-yolop-all-videos`

## Theo từng video

- `dashcam_vietnam.mp4` — 6 samples; YOLOP P95 `61.8 ms`; TwinLiteNet+ P95 `35.078 ms`; lane agreement `0.3924`.
- `dashcam_vietnam_night.mp4` — 6 samples; YOLOP P95 `59.942 ms`; TwinLiteNet+ P95 `33.422 ms`; lane agreement `0.4629`.
- `dashcam_vietnam_rain+night.mp4` — 6 samples; YOLOP P95 `61.242 ms`; TwinLiteNet+ P95 `33.778 ms`; lane agreement `0.3418`.
- `dashcam_vietnam_traffic_multi.mp4` — 6 samples; YOLOP P95 `58.372 ms`; TwinLiteNet+ P95 `33.681 ms`; lane agreement `0.4607`.
- `test_video1.mp4` — 6 samples; YOLOP P95 `59.52 ms`; TwinLiteNet+ P95 `34.139 ms`; lane agreement `0.1798`.
- `test_video10.mp4` — 6 samples; YOLOP P95 `58.245 ms`; TwinLiteNet+ P95 `33.821 ms`; lane agreement `0.4663`.
- `test_video11.mp4` — 6 samples; YOLOP P95 `57.32 ms`; TwinLiteNet+ P95 `34.673 ms`; lane agreement `0.3359`.
- `test_video2.mp4` — 6 samples; YOLOP P95 `67.471 ms`; TwinLiteNet+ P95 `40.107 ms`; lane agreement `0.4871`.
- `test_video3.mp4` — 6 samples; YOLOP P95 `59.504 ms`; TwinLiteNet+ P95 `34.606 ms`; lane agreement `0.3964`.
- `test_video4.mp4` — 6 samples; YOLOP P95 `59.151 ms`; TwinLiteNet+ P95 `34.902 ms`; lane agreement `0.3523`.
- `test_video5.mp4` — 6 samples; YOLOP P95 `57.335 ms`; TwinLiteNet+ P95 `33.035 ms`; lane agreement `0.3704`.
- `test_video6.mp4` — 6 samples; YOLOP P95 `61.556 ms`; TwinLiteNet+ P95 `33.532 ms`; lane agreement `0.4059`.
- `test_video7.mp4` — 6 samples; YOLOP P95 `57.687 ms`; TwinLiteNet+ P95 `34.353 ms`; lane agreement `0.4601`.
- `test_video8.mp4` — 6 samples; YOLOP P95 `61.159 ms`; TwinLiteNet+ P95 `37.786 ms`; lane agreement `0.4556`.
- `test_video9.mp4` — 6 samples; YOLOP P95 `59.077 ms`; TwinLiteNet+ P95 `34.628 ms`; lane agreement `0.6168`.
- `video_test.mp4` — 6 samples; YOLOP P95 `56.85 ms`; TwinLiteNet+ P95 `34.995 ms`; lane agreement `0.1531`.
