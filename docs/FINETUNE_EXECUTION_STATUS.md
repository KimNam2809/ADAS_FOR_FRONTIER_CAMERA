# RoadWatch Fine-tune Execution Status

## Trạng thái hiện tại

- Kế hoạch: `RW-OBJECT-V2`.
- Trạng thái: `OBJECT V2 VERSION 4 REJECTED; BASELINE RETAINED`.
- Kaggle Job: <https://www.kaggle.com/code/lekimnam/roadwatch-object-detector-v2-target-domain>
- Credential mới đã xác thực thành công. Script submit hỗ trợ cả giá trị `.env` có và không có dấu nháy.

## Object V3 Full Fine-tune — review ngày 2026-08-28

- Kernel: <https://www.kaggle.com/code/lekimnam/roadwatch-object-detector-v3-full-fine-tune/output>
  (owner browser run `345504146`, private).
- Remote state: `complete_candidate_not_promoted`; preflight `PASS`; không có
  training error; val/test không bị sửa; không train local.
- Artifact đã thu riêng tại
  `artifacts/kaggle/object_v3_full_output/` và hash khớp remote:
  `best.pt=8425c24ca33cc55a015f14cddd4dc9f8b567e6e9f864e2787678614878c328ca`,
  `best.onnx=57c1822cd397f6732175e3a3bd83238a6659a26f42d284b320f5a666a5f11e9e`.
- Held-out: precision `0.62393`, recall `0.44158`, mAP50 `0.48756`,
  mAP50-95 `0.28465`; pseudo-label gate tự động đạt nhưng remote vẫn khóa
  promote vì Human review bắt buộc.
- Locked RW-03 (6 scenarios, baseline rerun ngay trước candidate): baseline
  `8/4/2`, recall `0.8000`, FAR `3.0769/min`, object P95 `33.785 ms`; V3 Full
  `6/5/4`, recall `0.6000`, FAR `3.8462/min`, object P95 `32.105 ms`. Full
  `pytest tests -q` exit code `0` (một deprecation warning).
- Promotion decision: `keep_baseline`; `configs/model_registry.json` vẫn để
  `active_object_profile=baseline_coco`. Chi tiết tại
  `reports/RW04_OBJECT_V3_FULL_KAGGLE_REVIEW_20260828.md` và
  `reports/rw04-v3-full-promotion.json`.

## Lịch sử Object V2

- **Version 1 — ERROR:** BDD100K/DAWN và checkpoint mount thành công, nhưng Google Drive folder thiếu bốn video target-domain mới. Không bắt đầu training.
- **Khắc phục:** tạo Kaggle Dataset private `lekimnam/roadwatch-target-domain-videos-v1`, xác minh đủ 7/7 video và 1.603.258.100 byte. Kernel ưu tiên dataset attached thay vì Drive; có alias cho tên file chứa dấu `+` bị Kaggle chuẩn hóa.
- **Version 2 — STARTED:** submit thành công với private target-domain dataset ngày 2026-08-22.
- **Version 2 — ERROR/QUALITY GATE STOP:** pseudo-label hoàn tất 1.763 frame nhưng video dài `dashcam_vietnam.mp4` dùng AV1 không decode được bằng OpenCV trên Kaggle. Gate frame, person và motorcycle không đạt; training không chạy.
- **Khắc phục:** xác nhận codec local (`dashcam_vietnam.mp4=AV01`, sáu video còn lại H.264), thêm FFmpeg AV1→H.264 preprocessing trên Kaggle. Quality Gate fail giờ kết thúc có kiểm soát và giữ artifact để audit.
- **Version 3 — RUNNING:** submit thành công với AV1 preprocessing và gate artifact preservation ngày 2026-08-22.
- **Version 3 — COMPLETE / NO TRAINING:** AV1 preprocessing thành công, lấy đủ
  4.120 frame. Gate đạt 5/6; `person=227/300` không đạt. Training không chạy,
  không có checkpoint và không promote. Xem `evaluation/object_v2_v3_quality_gate.json`.
- **Version 4 remediation:** tăng background sampling 1→2 FPS nhưng giữ nguyên
  confidence/gate; mục tiêu tăng coverage person mà không hạ chuẩn chất lượng.
- **Version 4 — RUNNING:** submit thành công ngày 2026-08-23; pre-submit test
  2/2 pass, lịch nền dự kiến 7.635 frame trước hard-window additions.
- **Version 4 — COMPLETE CANDIDATE:** Quality Gate 6/6 pass; 7.935 sampled,
  `person=472`, `motorcycle=1.126`, `car=9.853`, mean confidence 0,8259.
  Held-out precision 0,6239, recall 0,4416, mAP50 0,4876, mAP50-95 0,2846.
  Candidate chưa promote do cần Human pseudo-label review + event regression.
- **Artifact export Version 1 — RUNNING:** CPU-only kernel
  `lekimnam/roadwatch-object-v2-artifact-export` đang tách model/report khỏi
  archive nguồn 9,98 GB. Future transient data đã chuyển sang `/kaggle/temp`.
- **Artifact export Version 1 — ERROR:** downstream kernel không mount được file
  tree của archive nguồn. Fallback HTTP Range đã tải đúng 9 artifact allowlisted
  (~16,9 MB), có SHA-256, không tải full archive.
- **Promotion — REJECTED:** static recall 0,4416 < 0,60 và mAP50-95 0,2846 <
  0,32. Locked event recall giảm 0,80→0,60; false alerts/min tăng
  3,8462→4,6154. Latency P95 mean cải thiện 34,017→29,392 ms nhưng không đủ.
  Active profile vẫn `baseline_coco`; Object V2 chỉ giữ làm diagnostic artifact.
- Không có quá trình train nào được chạy trên máy local.
- Gói Kaggle, script submit và resource profile đã hoàn thành.

## Chuỗi thực thi bắt buộc

1. **Credential preflight**
   - Đọc `KAGGLE_API_TOKEN` từ `.env` mà không in giá trị ra log.
   - Xác minh danh tính Kaggle và quyền push kernel.
2. **Submit Object V2 Quality Gate**
   - Kernel: `lekimnam/roadwatch-object-detector-v2-target-domain`.
   - Accelerator bắt buộc: NVIDIA T4/P100; dừng ngay nếu không có CUDA.
   - Gắn BDD100K, DAWN, Phase 2.1 checkpoint và tải video target-domain đã được chủ dự án phê duyệt.
3. **Chuẩn bị dữ liệu target-domain**
   - Lấy mẫu nền ở 1 FPS và cửa sổ khó ở 5 FPS.
   - Pseudo-label với checkpoint Phase 2.1 và ngưỡng confidence theo lớp.
   - Chỉ thêm dữ liệu vào train; tuyệt đối không thay đổi val/test khóa.
4. **Automated Quality Gate**
   - Tổng frame lấy mẫu >= 2.500.
   - Positive pseudo-label >= 750.
   - `person >= 300`, `motorcycle >= 300`, `car >= 1.000`.
   - Mean confidence >= 0,75.
   - Xuất ảnh overlay và manifest để human review.
5. **Object V2 training**
   - Khởi tạo từ Phase 2.1 checkpoint.
   - 20 epochs, image size 640, dùng GPU Kaggle.
   - Xuất PyTorch checkpoint, ONNX và metrics held-out test.
6. **Promotion gate**
   - Candidate luôn ở trạng thái chờ duyệt sau training.
   - Chỉ promote khi human pseudo-label review đạt và event regression RoadWatch không suy giảm các tình huống critical.
7. **Lane V2**
   - Object V2 đã có quyết định reject và artifact ổn định; Lane V2 được phép bắt đầu.
   - Ưu tiên UFLDv2/ResNet-18; đánh giá lane count, lane-boundary stability, LDW event precision/recall và FPS.

## Artifact đã sẵn sàng

- `kaggle/train_object_v2/roadwatch_train_object_v2.py`
- `kaggle/train_object_v2/kernel-metadata.json`
- `scripts/submit_object_v2.ps1`
- `scripts/profile_object_v2_resources.py`
- `reports/object-v2-resource-profile.json`
- `configs/finetune_object_v2.json`
- `configs/finetune_lane_v2.json`

### Lane V2 Phase 1 (2026-08-24)

- Kaggle Version 1 đã được submit và quan sát ở trạng thái `RUNNING`:
  <https://www.kaggle.com/code/lekimnam/roadwatch-lane-v2-target-quality-gate>.
- Input đã xác minh trước submit: 1,603,258,100 byte target videos và
  825,199,044 byte UFLDv2 ONNX; tổng 2.262 GiB.
- Job chỉ sinh 600 `candidate_unverified` và contact sheet; không train local,
  không fine-tune trên Kaggle và không thay YOLOP baseline.
- Fine-tune vẫn block cho tới gate 3,000 verified polyline frames. Chi tiết và
  ETA nằm trong `reports/LANE_V2_PHASE1_LAUNCH.md`.
- Version 1 hoàn tất nhưng machine gate fail: 420/600 frames, thiếu day source,
  candidate coverage `0.3595`, night candidates `28/120`. Root cause là OpenCV
  seek không decode được `dashcam_vietnam.mp4`; Version 2 đã bổ sung FFmpeg
  fallback và fail-fast cho source rỗng.
- Version 2 đã được submit lên cùng Kaggle kernel và đang `RUNNING`; mục tiêu
  là xác minh ingestion correction trước khi mở rộng annotation/fine-tune.
- Version 2 kết thúc `ERROR` sau GPU preflight tại `cv2.imdecode(!buf.empty())`:
  FFmpeg fallback trả buffer rỗng ở một timestamp. Đây là lỗi guard của
  ingestion; Version 3 đã thêm empty-buffer/cv2-error handling, không liên quan
  CUDA hay model.
- Version 3 `COMPLETE`: ingestion đủ `599/600`, đủ 4 source condition, nhưng
  candidate coverage chỉ `0.3623` và night candidate `28/120`; machine gate fail.
  Đã tạo queue review `evaluation/rw10_lane_review_queue_v2.json` với `599`
  pending records. Fine-tune vẫn block bởi verified-polyline gate.
- Queue repair ngày 2026-08-25 đã backup và quét toàn bộ 599 record; sau khi
  quarantine một record semantic conflict còn `19 verified`, `579 pending`,
  `1 needs_recheck`. Chưa đủ 300 pilot verified và chưa được fine-tune.

## Dự toán

- Video target-domain local: 1,493 GB.
- Base dataset: 70.796 train / 10.104 val / 20.101 test.
- Frame target-domain dự kiến: 4.120.
- Working disk Kaggle: 28-40 GB.
- ETA đến Quality Gate: 0,8-1,8 giờ.
- Object V2 training: 5-8 GPU-hours trên T4x2, phụ thuộc quota và hàng đợi Kaggle.

## Lịch sử gỡ chặn credential

Chủ dự án đã tạo Kaggle API token mới và thêm vào `roadwatch/.env`:

```dotenv
KAGGLE_API_TOKEN=<new-token>
```

Token không được gửi qua chat và không được commit. Credential preflight và kernel push đã thành công ngày 2026-08-22; trạng thái ngay sau submit là `KernelWorkerStatus.RUNNING`.
