# RoadWatch RW-04 → RW-07 Execution Report

Ngày thực thi: 2026-08-21. Mức phát hành giữ nguyên: **R0 — Research demo**.

## Kết luận điều hành

| Task | Trạng thái | Kết luận có thể công bố |
|---|---|---|
| RW-04 | Complete — candidate rejected | Giữ `baseline_coco`; candidate chưa đủ điều kiện promote. |
| RW-05 | Partial — model/data blocked | Logic hướng, chống lặp và critical false-alert đạt; maneuver Recall chưa đạt. |
| RW-06 | R0 software gate pass | Relative FCW/Lead Braking đạt gate video hiện có; chưa phải vận tốc/TTC vật lý. |
| RW-07 | Software complete, hardware blocked | Validator/evaluator sẵn sàng; metric TTC vẫn bị khóa cho đến calibration + closed course. |

## RW-04 — Object detector promotion

- Baseline event Recall: `0.7083`; candidate: `0.5833`.
- Baseline FP: `491`; candidate FP: `529`.
- Candidate object P95 mean: `36.964 ms`, đạt latency gate nhưng không bù được suy giảm Recall/FAR.
- Quyết định: không thay profile đang chạy; `baseline_coco` tiếp tục là active object profile.
- Evidence: `evaluation/rw04_object_promotion.json`.

## RW-05 — VRU, cut-in và cross-traffic

Đã triển khai:

- track association có center/size recovery và semantic family `rider↔motorcycle`;
- robust temporal motion, EMA và displacement dài hạn;
- camera lateral-motion compensation khi có đủ track ổn định;
- ego-path projection, path conflict, origin-side và direction evidence;
- temporal confirmation, semantic cooldown và strict object/direction scoring;
- critical gate yêu cầu proximity `>=0.75` và approach `>=0.30`.

Kết quả nghiêm ngặt trên 37 scenario/388 giây verified coverage:

- maneuver Recall: `8/18 = 0.4444` — **fail** so với `>=0.90`;
- left/right semantic accuracy: `8/8 = 1.0000` — pass;
- duplicate event rate: `15/460 = 0.0326` — pass;
- false critical: `0`, tương đương `0.0/min` — pass.

Phân tích lỗi cho thấy nhiều miss gắn với detector phát sai semantic class
(`motorcycle→person`, `car→bus/truck`) hoặc không tạo đúng track qua occlusion. Không
hạ thêm ngưỡng vì sẽ phá false-alert gate. RW-05 chỉ được đóng hoàn toàn sau khi object
model vượt RW-04 promotion gate trên chính bộ 18 maneuver events.

Evidence: `evaluation/rw05_quality_gate_v4.json`,
`reports/rw05-regression-v4.json`, `scripts/diagnose_rw05.py`.

## RW-06 — FCW và Lead Braking không telemetry

Đã triển khai `MonocularKinematics` luôn xuất telemetry tương đối:

- `relative_scale_px`;
- `relative_closing_rate_per_s` từ slope log-height;
- `relative_closing_acceleration_per_s2`;
- `relative_ttc_proxy_seconds` chỉ là image-space proxy;
- mọi evidence ghi `kinematics_space=image_space` và
  `relative_kinematics_role=advisory_image_space_only`.

Lead Braking hợp nhất paired-red-lamp cue và relative scale acceleration. Một cue phải
tồn tại ít nhất 3 frame; FCW cũng không được kích hoạt từ một frame đơn.

Kết quả gate hiện tại:

- verified FCW/Lead Braking Recall: `2/2 = 1.0`;
- no single-frame trigger: pass;
- lead-brake confirmation `>=3` frame: pass;
- image-space evidence labeling: pass.

Sau vòng siết projected ego-path, width và relative closing gates, kết quả v2 là:

- emitted FCW/Lead events giảm từ `92` xuống `8`;
- false events giảm từ `84` xuống `6` trên `388 s`;
- FAR giảm từ `12.9897/min` xuống `0.9278/min`, đạt gate R0 `<=1/min`;
- hai verified Lead Braking events vẫn được match (`2/2`).

Hai event là cỡ mẫu quá nhỏ và FAR đang sát ngưỡng. Đây là R0 pass, không phải tuyên
bố production Recall hay độ an toàn closed-course. Evidence chính:
`evaluation/rw06_quality_gate_v2.json`, `reports/rw06-regression-v2.json`.

## RW-07 — Metric distance/TTC

Đã triển khai:

- calibration schema validator: camera ID, resolution, intrinsics, distortion,
  `>=12` valid image, RMS `<1 px`, SHA-256 từng ảnh;
- calibration artifact không thể tự cấp quyền bật metric TTC;
- evaluator measured-distance/TTC cho 5/10/15/20/30/40 m, day + night;
- pass chỉ khi distance median error `<=10%`, P95 `<=20%`, TTC median absolute
  error `<=0.5 s`.

Trạng thái hiện tại là `blocked` đúng thiết kế vì chưa có
`configs/camera_calibration.json`, measured-distance samples và closed-course safety
driver. `metric_ttc_alerting_allowed=false` được giữ nguyên.

Evidence/tooling: `evaluation/rw07_calibration_gate.json`,
`backend/roadwatch/calibration.py`, `scripts/calibrate_camera.py`,
`scripts/validate_calibration.py`, `scripts/evaluate_metric_ttc.py`.

## Xác minh chung

- Full automated suite: `85 passed`.
- RW-03 deterministic regression: `37/37` scenario complete; integrity/taxonomy/
  ground-truth/tests đều pass.
- Release preflight: `24/24` checks pass.
- Active release vẫn là `roadwatch-r0-2026-08-21`, object profile
  `baseline_coco`, không có model candidate bị promote ngầm.

## Công việc tiếp theo được phép bắt đầu

1. RW-08 Fallen Rider dataset gate có thể bắt đầu độc lập.
2. RW-05 chỉ tiếp tục bằng object-model/data improvement rồi chạy lại RW-04; không
   tuning ngưỡng mù.
3. RW-07 cần Human cung cấp calibration images cùng chính camera/mount và measured
   closed-course data; trước đó không bật metric TTC.
4. RW-10 lane-instance/count có thể bắt đầu bằng benchmark phần mềm, nhưng final gate
   vẫn cần target lane labels và edge hardware.
