# Object detector model promotion

## Trạng thái hiện tại

- Production/default: `baseline_coco` (`yolo11n.pt`/`yolo11n.onnx`).
- Candidate: `roadwatch_objects_v1` (`roadwatch_objects_v1.pt`/ONNX).
- Latest candidate: `roadwatch_objects_v1_1` (Phase 2.1 VRU balancing).
- Candidate taxonomy: `person, rider, bicycle, motorcycle, car, bus, truck`.
- Registry và checksum: `configs/model_registry.json`.
- BARD vẫn bị cách ly; chỉ BDD100K + DAWN đã qua Human Quality Gate.

## Object V3 Full — 2026-08-28

Kaggle full fine-tune `lekimnam/roadwatch-object-detector-v3-full-fine-tune`
(run `345504146`) đã được tải và kiểm tra hash/ONNX. Artifact đạt technical
preflight nhưng **không được promote**: locked event recall `0.6000` thấp hơn
`baseline_coco=0.8000`, dù FAR và object P95 latency không tăng. Pseudo-label
remote cũng giữ `promotion_allowed=false` cho tới khi Human review hoàn tất.
Chi tiết evidence và rollback nằm tại
`reports/RW04_OBJECT_V3_FULL_KAGGLE_REVIEW_20260828.md`.

Hai model có class ID khác nhau. Vì vậy phải chọn bằng `object_profile`; không
được chỉ thay tên checkpoint. Profile tự gắn đúng class IDs và tránh làm mất
`car`/`truck` của model mới.

## Chạy A/B

```powershell
.\.venv\Scripts\python.exe .\scripts\compare_object_models.py
```

Report mặc định: `reports/ab-object-models.json`. Cả hai profile dùng cùng video,
sampling, risk rules, lane/sign models và audio-off evaluation mode. Các metric:

- scenario-presence recall và semantic recall;
- alerts/minute;
- thời điểm cảnh báo đầu tiên tính từ đầu clip;
- object inference latency P50/P95;
- HUD/TTS payload consistency;
- unexpected event type/minute (chỉ là proxy).

Timestamp Ground Truth hiện nằm ở `evaluation/event_ground_truth.json`. Các cửa
sổ đã xác minh được dùng để tính event precision/recall, false alerts/min và
deadline warning. Các cửa sổ `provisional` không được tính như bằng chứng chính
thức cho tới khi người kiểm thử đổi trạng thái sang `verified`.

## Promotion gate

Candidate chỉ được đổi thành mặc định khi đồng thời:

1. mọi scenario hoàn tất;
2. presence recall không thấp hơn baseline;
3. semantic recall không thấp hơn baseline;
4. object latency P95 không quá 125% baseline;
5. alert density không tăng quá 10% trước manual review;
6. người kiểm thử xác nhận false alerts/min và cảnh báo sai class/side không xấu hơn;
7. VRU recall (`rider`, `bicycle`, `motorcycle`) trên held-out test tăng hoặc không giảm.

Calibrated v1.1 đã giảm timestamp false alerts/min từ 10.3846 xuống 5.7692,
nhưng timestamp event recall giảm từ 0.5000 xuống 0.3750. Vì gate số 2 không đạt,
production vẫn giữ `baseline_coco`.

Nếu bất kỳ gate nào không đạt, giữ `baseline_coco`; candidate vẫn có thể dùng qua
feature flag để debug.

## Phase 2.1 trên Kaggle

Kernel: `lekimnam/roadwatch-object-detector-phase-2-1`.

- khởi tạo từ Phase-2 `best.pt`;
- tiếp tục 20 epoch với learning rate thấp;
- chỉ nhân bản ảnh train chứa rider/motorcycle (3x) hoặc bicycle (2x);
- validation/test giữ nguyên tuyệt đối;
- BARD hard-quarantine;
- xuất balance report, checkpoint, plots và held-out test metrics.

Phase 2.1 đã hoàn tất. Checkpoint đã được xác minh SHA-256, export ONNX và đăng ký
dưới profile `roadwatch_objects_v1_1`. A/B regression phải hoàn tất trước khi cập
nhật `active_object_profile`.
