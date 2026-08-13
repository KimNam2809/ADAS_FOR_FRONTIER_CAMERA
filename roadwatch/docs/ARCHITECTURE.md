# Kiến trúc RoadWatch

```text
Camera / video replay
        │ frame_id + monotonic timestamp + drop policy
        ▼
Perception adapters
  ├─ YOLO11n road users
  ├─ YOLO11s VN traffic signs
  └─ YOLOP ONNX lane + drivable area
        │ normalized detections/masks
        ▼
Temporal evidence
  ├─ IoU track IDs and history
  ├─ lane/drivable association
  └─ stability + image expansion/lateral motion
        ▼
Risk Engine ──► candidate events + evidence packet
        ▼
Alert Governor (deterministic)
  ├─ confirmation / quality gates
  ├─ severity / cooldown / escalation
  └─ one audio winner; all accepted events remain on HUD
        ├────────► beep + cached Piper Vietnamese TTS
        ├────────► SQLite event/audit log
        └────────► FastAPI/WebSocket/MJPEG ► React HMI
```

## Process boundary

MVP chạy pipeline trong worker thread của edge service để đơn giản hóa demo. UI/WebSocket không nằm trong vòng quyết định; đóng trình duyệt không dừng inference/audio. Bản production nên tách `roadwatch-core` và `roadwatch-api` thành process riêng qua IPC để watchdog độc lập.

## Dữ liệu cảnh báo

```json
{
  "event_type": "fcw",
  "severity": "warning",
  "object_id": 7,
  "location": "phía trước",
  "risk_score": 0.68,
  "confidence": 0.87,
  "cooldown_key": "fcw:7",
  "evidence": {
    "hits": 6,
    "in_ego_lane": true,
    "on_drivable": true,
    "expansion_rate": 0.21,
    "lane_quality": 0.74,
    "method": "image-space risk; không phải TTC theo mét"
  }
}
```

## Runtime scheduling

- Object detector: mỗi processed frame.
- YOLOP: mặc định mỗi 2 frame, dùng mask gần nhất giữa hai lần.
- Sign detector: mỗi 5 frame vì biển thay đổi chậm hơn FCW.
- Queue không tích lũy frame cũ; replay dùng stride để giữ dữ liệu mới.
- Batch luôn bằng 1.

## Giới hạn kỹ thuật hiện tại

- Tracker MVP là IoU temporal tracker, không phải ByteTrack đầy đủ. Interface/track schema cho phép thay adapter mà không đổi Risk Engine.
- FCW dùng image-space risk/box expansion, không tuyên bố khoảng cách mét hay metric TTC.
- LDW bị khóa nếu YOLOP không tạo được cặp lane geometry đủ tin cậy.
- Không có ego speed, turn-signal, yaw rate hoặc camera calibration; các dữ liệu này chỉ được thêm dưới dạng read-only adapter sau thử nghiệm an toàn.

