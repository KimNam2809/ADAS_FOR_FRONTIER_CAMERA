# RoadWatch v0.2 — Reliability, Evaluation & Edge Readiness

## Đã triển khai

- Event lifecycle có UUID, frame/source time, expiry, trạng thái lifecycle/audio và suppression reason.
- Audio TTL, supersede theo event key, stale-event dropping và beep pattern dễ chịu hơn.
- Sign state xác nhận theo thời gian; một speed sign mới thay thế event cũ trong queue.
- HUD dùng active event; màu box phân biệt observed/candidate/suppressed/active.
- SQLite migration lưu được decision/audio trace.
- Scenario Evaluation Suite và manifest từ nhật ký kiểm thử thực tế.
- Metric runtime: P50/P95, FPS, drop ratio, lane coverage, event type, suppression và stale audio.
- YOLO ONNX adapter hỗ trợ DirectML/CUDA/CPU; script export giữ names mapping.
- Adaptive sign cadence, predicted-box association, lane-offset smoothing.
- Cross-traffic event và brake-light cue thử nghiệm; brake-light mặc định tắt đến khi có ground truth.
- Camera-calibration gate, read-only vehicle adapter và edge preflight. Không có actuator API.

## Chưa được phép tuyên bố hoàn thành

- mAP/precision/recall detection: chưa có bounding-box ground truth RoadWatch.
- Event-level precision/recall và time-to-warning: manifest chưa có timestamp chuẩn.
- Biển 60 trên `test_video10`: model v0.2 vẫn dự đoán class 40; cần fine-tune dữ liệu biển Việt Nam.
- Jetson/TensorRT, CAN và closed-course: có profile/gate nhưng chưa được kiểm chứng phần cứng.
- Metric TTC: bị khóa vì `camera_calibration.json` chưa có và `calibrated=false`.

## Lệnh xác minh

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe scripts\export_models.py
.\.venv\Scripts\python.exe scripts\evaluate.py --scenario test-video10-speed-lane
.\.venv\Scripts\python.exe scripts\edge_preflight.py
```

Mọi report runtime nằm trong `reports/` và bị Git ignore vì chứa thông tin máy/phiên chạy.
