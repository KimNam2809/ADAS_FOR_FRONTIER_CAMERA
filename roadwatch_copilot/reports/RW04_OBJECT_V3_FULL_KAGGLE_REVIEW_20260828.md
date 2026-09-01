# RW-04 — Object V3 Full Fine-tune Kaggle review

## Kết luận

**Không promote; giữ `baseline_coco`.** Kaggle output là một full training
artifact hợp lệ về mặt kỹ thuật, nhưng candidate fail event-level safety gate:
event recall giảm từ `0.8000` xuống `0.6000`. Vì vậy `configs/model_registry.json`
vẫn không thay đổi.

## Remote và credential evidence

- Kernel: `lekimnam/roadwatch-object-detector-v3-full-fine-tune`.
- Run: `345504146`; private; owner page hiển thị `Le Kim Nam`; remote status
  `complete_candidate_not_promoted`.
- `roadwatch/.env` vẫn có đủ hai key Account 1/2; chỉ kiểm tra metadata an toàn,
  không đọc/ghi hoặc in giá trị token. CLI Account 1 bị Kaggle trả
  `Authentication required`; Account 2 xác thực được nhưng không có quyền đọc
  kernel private. Owner browser session mới là bằng chứng truy cập dùng để tải
  artifact, không phải bằng chứng token đã được thay đổi.

## Artifact integrity

| File | SHA-256 | Kiểm tra |
|---|---|---|
| `artifacts/kaggle/object_v3_full_output/best.pt` | `8425c24ca33cc55a015f14cddd4dc9f8b567e6e9f864e2787678614878c328ca` | khớp `artifact_hashes.json`; Ultralytics load PASS |
| `artifacts/kaggle/object_v3_full_output/best.onnx` | `57c1822cd397f6732175e3a3bd83238a6659a26f42d284b320f5a666a5f11e9e` | khớp `artifact_hashes.json`; ONNX checker/ORT CPU PASS |

Output root còn `yolo26n.pt` (SHA-256
`9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`); file
này không phải đường dẫn `best.pt` mà `job_status.json` khai báo nên không dùng
cho candidate/promotion.

Taxonomy khớp 7 lớp RoadWatch: `person`, `rider`, `bicycle`, `motorcycle`,
`car`, `bus`, `truck`. Checkpoint có `2,591,205` parameters; ONNX contract là
input `1x3x640x640`, output `1x11x8400`. Same-frame smoke trên frame 0 cho
2 boxes ở cả PyTorch và ONNX, class set giống nhau; box-coordinate L1 mean
`0.1900` (khác biệt preprocessing/rounding, không phải mAP parity).

## Kaggle training/data gate

Kaggle preflight `PASS`, CUDA/T4 path được dùng, `training_local=false`,
`production_model_unchanged=true`, và `validation_or_test_modified=false`.
Pseudo-label gate tự động đạt: `7,935` sampled images, `6,509` accepted
positive images, `472` person, `1,126` motorcycle, `9,853` car instances,
mean confidence `0.8259`. Tuy nhiên remote vẫn đặt
`promotion_allowed=false` vì pseudo-label target-domain bắt buộc Human review.

Held-out metrics từ `job_status.json`:

| Metric | Candidate |
|---|---:|
| Precision | 0.62393 |
| Recall | 0.44158 |
| mAP50 | 0.48756 |
| mAP50-95 | 0.28465 |

## RoadWatch locked regression

Chạy cùng 6 locked media scenarios, cùng ground truth SHA-256
`C27E3C265F0CA0713268FE5D68955B4400838D3C2C080DE67A4E0DF4BCD6E815`:
baseline được rerun ngay trước candidate bằng cùng code/runtime; chi tiết ở
`reports/rw04-baseline-current-locked-regression.json`.

| Metric | Baseline COCO | Object V3 Full | Gate |
|---|---:|---:|---|
| TP / FP / FN | 8 / 4 / 2 | 6 / 5 / 4 | fail (miss/FP tăng) |
| Event precision | 0.6667 | 0.5455 | thông tin |
| Event recall | 0.8000 | 0.6000 | **fail** |
| False alerts/min | 3.0769 | 3.8462 | **fail (+25%)** |
| Object latency P95 mean | 33.785 ms | 32.105 ms | pass |

Promotion evaluator: `automated_pass=false`, `decision=keep_baseline` (event
recall và FAR đều fail). Full
backend `pytest tests -q` pass (exit code `0`, one deprecation warning); the
candidate regression itself was rerun with the automated-test gate enabled.
V3 candidate bỏ sót FCW/fallen-rider trong các locked windows và replay
diagnostic cho thấy presence `person`/`motorcycle` giảm mạnh ở
`dashcam_vietnam_traffic_multi.mp4` trong khi `rider` tăng; đây là rủi ro
taxonomy/recall cần remediation, không được che bằng threshold.

## Bằng chứng và rollback

- Metadata: `artifacts/kaggle/object_v3_full_output/artifact_manifest.json`.
- Locked regression: `reports/rw04-v3-full-locked-regression.json` và `.md`.
- Promotion decision: `reports/rw04-v3-full-promotion.json`.
- Diagnostic replay: `reports/object_v3_full_dashcam_replay_20260828.json`.
- Rollback/default: không thay `configs/model_registry.json`, không ghi đè
  `models/yolo11n.pt`/ONNX; candidate chỉ nằm trong thư mục artifact riêng.

## Bước tiếp theo để có thể promote

1. Human adjudicate tối thiểu 50 FP/FN mẫu target-domain và ghi provenance;
   không dùng `ai_provisional` thay Human review.
2. Remediate class mapping/VRU sampling để `person`/`motorcycle` không suy giảm;
   submit Kaggle version mới, giữ val/test khóa.
3. Lặp held-out metrics + locked RW-03 event regression; chỉ khi event recall
   và VRU recall không thấp hơn baseline, FAR không tăng quá 10%, latency P95
   trong 125% và Human gate đạt mới được cập nhật registry.
