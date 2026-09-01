# RoadWatch Fine-tune Quality Gate Runbook

Tài liệu này là hướng dẫn xác minh bắt buộc cho các job fine-tune RoadWatch.
Mỗi candidate phải được kiểm tra độc lập trước khi chuyển sang bước kế tiếp.

## 1. FT-00 — Kaggle Preflight

### Triển khai ở đâu

- Local preflight: `scripts/finetune_preflight.ps1`.
- Remote preflight: phần log đầu tiên của Kaggle Kernel.
- Bằng chứng local: `reports/finetune_preflight_20260827.json`.

### Cần kiểm tra

- Kaggle token có mặt nhưng không xuất hiện trong log.
- Kernel bật `GPU`.
- Dataset sources được khai báo trong `kernel-metadata.json`.
- Không có bước training local.
- Lane queue không được coi là đủ điều kiện nếu chưa có 3.000 frame verified.

### Cách thực hiện

1. Mở Kernel Kaggle đúng version.
2. Chọn `Settings` và xác nhận `Accelerator = GPU`.
3. Mở `Logs` và đọc các dòng đầu tiên.
4. Tìm `GPU preflight`, `CUDA available` và tên `Tesla T4` hoặc `P100`.
5. Đảm bảo không có `Missing attached Kaggle inputs`, `CUDA unavailable` hoặc
   `CPU training`.

### Pass criteria

```text
GPU count >= 1
All declared inputs mounted
preflight status = PASS
No secret in logs
```

## 2. RW-04.1 — Object pilot 1 epoch

### Triển khai ở đâu

- Kernel: `lekimnam/roadwatch-object-detector-v3-pilot`.
- Output folder: `/kaggle/working/roadwatch_object_v3_pilot/`.
- Local code: `kaggle/train_object_v3_pilot/`.

### Cần kiểm tra

```text
preflight.json
dataset_manifest.json
training_results.csv
job_status.json
best.pt
best.onnx
artifact_hashes.json
```

### Cách thực hiện

1. Trong `Logs`, xác nhận job chạy `pilot_1_epoch` và hoàn tất epoch 1.
2. Mở `job_status.json`, xác nhận `status = complete_pilot` và
   `training_error = null`.
3. Mở `training_results.csv`; không chấp nhận loss/metric là `NaN`.
4. Xác nhận `best.pt` và `best.onnx` tồn tại.
5. Mở các ảnh prediction/contact sheet nếu kernel đã sinh output.
6. Kiểm tra taxonomy chỉ gồm bảy lớp canonical:
   `person, rider, bicycle, motorcycle, car, bus, truck`.

### Pass criteria

- GPU preflight PASS.
- Đúng một epoch hoàn tất.
- Không OOM, NaN hoặc dataloader error.
- Checkpoint load được và ONNX inference được.
- Candidate không ghi đè baseline production.
- Không được coi đây là bằng chứng model đã tốt hơn baseline.

### Phản hồi của chủ dự án

Đạt:

```text
PASS OBJECT PILOT
```

Không đạt:

```text
REJECT OBJECT PILOT
Lý do: <mô tả log hoặc artifact lỗi>
```

Không có phản hồi `PASS OBJECT PILOT` thì không chạy pilot 3–5 epoch hoặc full.

## 3. RW-04.1 — Object pilot 3–5 epochs

### Cần kiểm tra

- `results.png` có đường loss hữu hạn và không tăng vô hạn.
- `confusion_matrix.png` không cho thấy một class bị mất hoàn toàn.
- `val_batch*.jpg` có prediction hợp lý trên ô tô, xe máy, người, night/rain
  và dense traffic.
- Validation hoàn tất, không memory leak hoặc OOM.

### Lưu ý

Pilot chỉ xác minh độ ổn định của pipeline. Không dùng mAP pilot để promote.
Sau gate này phải dừng tiếp để chờ xác nhận trước full fine-tune.

## 4. RW-04.2 — Object full fine-tune

### Cần kiểm tra ở đâu

Trong Kaggle output:

```text
metrics.json
event_regression.json
best.pt
best.onnx
artifact_hashes.json
```

### Pass criteria

```text
mAP50-95 >= 0.32
Recall >= 0.60
VRU recall >= 0.55
Critical event recall >= baseline
False alerts <= 3/minute
Latency P95 <= 1.25 * baseline
```

Phải đối chiếu FCW, VRU, cut-in, cross-traffic, night, rain, dense motorcycle
và false-alert trên cùng locked video/timestamp. Chỉ cần một critical gate fail
thì giữ baseline và đánh dấu candidate `rejected`.

## 5. RW-10.1 — Lane queue review

### Triển khai ở đâu

- Queue: `evaluation/rw10_lane_review_queue_v2.json`.
- Frame: đường dẫn `image` trong từng record.
- Validator: các script repair/validation lane hiện có.

### Cách review một record

1. Mở ảnh frame.
2. Đếm lane cùng chiều với ego vehicle.
3. Vẽ `ego_left_boundary` và `ego_right_boundary` nếu nhìn rõ.
4. Nếu tối, mưa, phản chiếu, mờ hoặc bị che: đặt `uncertain = true` và ghi chú.
5. Chọn `marking_type`, `visibility`, `road_direction`.
6. Chỉ đặt `review_status = verified` khi người review bảo vệ được nhãn.

Không được copy `model_proposal` thành ground truth.

### Điều kiện mở khóa lane training

```text
verified frames >= 3000
night >= 500
rain >= 400
multi-lane >= 1000
faded/missing markings >= 400
double-review >= 300
disagreement <= 5%
```

## 6. RW-10.3 — Lane fine-tune

Chỉ chạy sau khi lane data gate PASS. Kiểm tra riêng day/night/rain/multi-lane:

```text
lane count accuracy >= 0.95
ego-boundary F1 >= 0.90
night/rain recall >= 0.85
LDW false alerts <= 1/minute
AMD full-pipeline FPS >= 12
E2E P95 <= 150 ms
```

Nếu chưa có Jetson thật, chỉ báo cáo benchmark AMD/EC2; không tuyên bố đạt gate
Jetson 30 FPS.

## 7. Quy tắc fallback

- Object fallback: `yolo11n.onnx`.
- Lane fallback: `yolop_lane_detection_640.onnx`.
- Candidate lỗi, thiếu input, OOM, NaN hoặc fail critical metric đều không được
  promote.
- Model/video/dataset/checkpoint lớn không commit vào Git.
