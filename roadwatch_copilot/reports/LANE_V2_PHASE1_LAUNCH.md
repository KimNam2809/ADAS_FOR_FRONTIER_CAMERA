# Lane V2 Phase 1 — Kaggle launch

- Task: `RW-10`.
- Kernel: `lekimnam/roadwatch-lane-v2-target-quality-gate`, Version 1.
- URL: <https://www.kaggle.com/code/lekimnam/roadwatch-lane-v2-target-quality-gate>
- Trạng thái quan sát ngay sau submit: `RUNNING`.
- Accelerator bắt buộc: Kaggle GPU T4.

## Mục tiêu

Job lấy mẫu 600 frame target-domain theo bốn điều kiện day, dense traffic,
night và rain+night. UFLDv2 tạo lane polyline ứng viên; geometry và temporal
filters loại boundary thiếu, giao nhau, sai chiều rộng hoặc nhảy vị trí bất
thường. Frame cùng source không được chia sang nhiều split.

Đây là quality-gate pilot, không phải training job. Mọi nhãn sinh tự động mang
trạng thái `candidate_unverified`; job luôn giữ `training_blocked=true` và không
thay YOLOP runtime mặc định.

## Resource profile trước submit

| Thành phần | Dung lượng |
|---|---:|
| Target videos đã xác minh bằng Kaggle API | 1,603,258,100 byte |
| UFLDv2 teacher ONNX đã xác minh bằng Kaggle API | 825,199,044 byte |
| Tổng input | 2,428,457,144 byte (2.262 GiB) |
| Output ước tính | 0.10–0.25 GiB |

ETA đến quality gate là 15–35 phút, tương đương khoảng 0.25–0.60 GPU-hour.
Đây là ước tính cho inference 600 frame, video seek, contact-sheet và startup;
không bao gồm fine-tune.

## Gate và giới hạn

Pilot cần ít nhất 300 polyline frame được review để đánh giá chính sách nhãn.
Fine-tune target-domain vẫn bị chặn cho tới khi đạt gate cấu hình đầy đủ: 3,000
verified frames, gồm 500 night, 400 rain, 1,000 multi-lane, 400 faded/missing
marking và 300 frame double-review với disagreement không quá 5%.

Version 1 có mô tả nhầm ngưỡng 300 frame là điều kiện unblock train trong JSON
output. Giá trị này chỉ là pilot review gate; source đã được sửa cho version kế
tiếp và nguồn sự thật vẫn là `configs/finetune_lane_v2.json`.

## Version 1 postmortem

Version 1 chỉ có 420 record thay vì 600: `dashcam_vietnam.mp4` tồn tại trên
Kaggle nhưng OpenCV không đọc được frame khi seek. Vì phiên bản đầu không có
fallback và cũng chưa fail-fast theo source, job vẫn hoàn tất với machine gate
fail. Version 2 bổ sung FFmpeg single-frame fallback và dừng lỗi nếu source bắt
buộc sinh ra 0 frame; đây là ingestion correction, không phải model promotion.

Version 2 đã qua GPU preflight nhưng dừng ở frame decode vì FFmpeg trả về
`stdout` rỗng và code gọi `cv2.imdecode()` mà chưa kiểm tra buffer. Version 3
bổ sung empty-buffer guard và coi frame đó là decode-miss có kiểm soát.
