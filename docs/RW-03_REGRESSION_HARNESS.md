# RW-03 — Deterministic Regression Harness

## Kết luận

**RW-03 software/harness gate: PASS.** 37/37 scenario được chạy bằng pipeline
thật, không dùng mock inference. Manifest integrity, taxonomy, measured ground
truth và automated tests đều pass.

**Baseline quality: FAIL cho production.** Technical PASS chỉ chứng minh hệ
thống đo và chặn regression hoạt động; nó không có nghĩa model/risk logic hiện
tại đủ an toàn.

## Phạm vi đã khóa

| Suite | Scenario | Chính sách chọn |
|---|---:|---|
| Locked media | 6 | Toàn bộ clip legacy có timestamp ground truth verified |
| Dashcam Việt Nam | 31 | 16 positive windows + 15 negative windows, seed 162 |
| Tổng | 37 | Replay không pace, 6 processed FPS, audio disabled |

Mỗi scenario chứa SHA-256 nguồn video. Manifest còn khóa release contract,
default config, regression ground truth và code của pipeline/risk/alert/scorer.
Thay đổi âm thầm bất kỳ artifact nào làm preflight fail trước inference.

## Kết quả baseline đo được

| Chỉ số | Giá trị |
|---|---:|
| Scenario completed | 37/37 |
| True positive | 17 |
| False positive | 491 |
| False negative | 7 |
| Precision | 0,0335 |
| Recall | 0,7083 |
| Miss rate | 0,2917 |
| Unexpected event type | 0 |

False positive tập trung ở `fcw=188`, `vulnerable_road_user=137`,
`cross_traffic=106`, `lead_vehicle_braking=20`, `traffic_sign=21`, `cut_in=18`
và `speed_sign=1`. Đây là bằng chứng định lượng để ưu tiên temporal confirmation,
track stability, risk calibration và anti-alert overload ở RW-04/RW-05/RW-12.

## Lỗi được phát hiện trong lúc triển khai

1. RW-02 gọi lane event là `lane_departure`, runtime API dùng `ldw`. Regression
   taxonomy đã chuẩn hóa sang `ldw`, có mapping khi chuyển ground truth.
2. Scorer cũ không coi verified negative-only window là measured coverage. Scorer
   mới lấy hợp các khoảng exhaustive và negative, tránh đếm trùng denominator.
3. Baseline phát nhiều cảnh báo lặp/sai trên dashcam negative. Harness giữ nguyên
   kết quả này thay vì điều chỉnh threshold để làm đẹp báo cáo.

## Cách chạy

Tạo lại manifest khi chủ động thay golden truth hoặc locked code:

```powershell
.venv/Scripts/python.exe scripts/build_regression_manifest.py
```

Chạy full regression cho một release:

```powershell
.venv/Scripts/python.exe scripts/run_regression.py
```

Nếu chỉ sửa scorer mà giữ nguyên inference events, có thể rescore với provenance:

```powershell
.venv/Scripts/python.exe scripts/rescore_regression.py
```

Không được rebuild manifest để né một hash mismatch ngoài quy trình review. Mọi
thay đổi golden truth vẫn cần chủ dự án phê duyệt.

## Artifact

- `configs/regression_manifest.json`: scenario, seed, taxonomy và locked hashes.
- `evaluation/regression_ground_truth.json`: golden event-level truth hợp nhất.
- `evaluation/rw03_baseline_evidence.json`: evidence JSON gọn, có effective config.
- `reports/rw03-regression-final.json`: full local artifact chứa từng event.
- `reports/rw03-regression-final.md`: báo cáo scenario-level.
- `scripts/run_regression.py`: full runner.
- `scripts/rescore_regression.py`: scorer-only replay có parent artifact hash.

## Điều kiện cho RW-04

Candidate object detector không được promote chỉ vì mAP tốt hơn. Nó phải chạy
cùng manifest và không làm giảm event recall/VRU recall, không tăng FAR quá 10%,
đồng thời đáp ứng latency P95 theo DoD RW-04. Baseline hiện tại có chất lượng
thấp nên mục tiêu đầu tiên là giảm FP mạnh mà không làm recall giảm dưới 0,7083.
