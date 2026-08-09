# RoadWatch Copilot — Layer Contracts & Integration Guide

> Tài liệu tích hợp chung cho team 4 người.
>
> Mục tiêu: các thành viên phụ trách Tầng 1, Tầng 2, Tầng 3 và Tầng 4 có thể phát triển độc lập, chạy test bằng dữ liệu giả lập, sau đó tích hợp mà không phải tự đoán format dữ liệu của nhau.

---

## 1. Mục tiêu hệ thống

RoadWatch Copilot là hệ thống hỗ trợ cảnh báo người lái trên edge. Hệ thống chỉ cảnh báo, không tự phanh, không tự đánh lái và không gửi lệnh điều khiển xe.

```text
Video/Camera
    ↓
Tầng 1 — Perception
    ↓
Tầng 2 — Kinematics
    ↓
Tầng 3 — Decision Matrix
    ├── Beep/Cảnh báo tức thì
    ├── TTS
    └── HUD/Backend/Logs
    ↓
Tầng 4 — Async Context, TTS, API, UI, Metrics
```

### Nguyên tắc bắt buộc

1. Tầng 3 là nơi quyết định mức độ cảnh báo.
2. FCW Critical không được chờ TTS hoặc SLM.
3. Tầng 4 không được tự tắt hoặc hạ mức cảnh báo Critical.
4. Mỗi frame phải có `frame_id` và `timestamp_ms`.
5. Mỗi cảnh báo phải có `reason` để giải thích.
6. Input quá cũ phải được đánh dấu `System-Degraded`.
7. Các tầng phải chạy được bằng mock JSON trước khi tích hợp camera/model thật.
8. Đây là prototype nghiên cứu, không phải hệ thống ADAS thương mại hoặc hệ thống tự lái được chứng nhận.

---

## 2. Cấu trúc repository chuẩn

Từ thư mục gốc repository, cấu trúc cần thống nhất như sau:

```text
roadwatch-copilot/
├── layer1/
│   ├── __init__.py
│   ├── perception.py
│   ├── detector.py
│   ├── lane_detector.py
│   ├── model_runner.py
│   ├── adapter.py
│   └── tests/
│
├── layer2/
│   ├── __init__.py
│   ├── tracker.py
│   ├── ttc.py
│   ├── cut_in.py
│   ├── adapter.py
│   └── tests/
│
├── layer3/
│   ├── __init__.py
│   ├── contracts.py
│   ├── config.py
│   ├── cooldown.py
│   ├── rules.py
│   ├── engine.py
│   ├── replay.py
│   ├── audio_adapter.py
│   └── tests/
│
├── layer4/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── tts_worker.py
│   ├── api.py
│   ├── hud.py
│   ├── metrics.py
│   └── tests/
│
├── contracts/
│   ├── __init__.py
│   └── contracts.py
│
├── config/
│   └── policy.json
│
├── scenarios/
│   ├── normal.json
│   ├── fcw_warning.json
│   ├── fcw_critical.json
│   ├── cut_in.json
│   ├── ldw.json
│   ├── conflict.json
│   └── stale_frame.json
│
├── tests/
│   ├── test_contracts.py
│   ├── test_pipeline_smoke.py
│   └── test_layer_integration.py
│
├── requirements.txt
├── requirements-layer3.txt
├── docker-compose.yml
└── README.md
```

### Quy tắc đặt code

- `contracts/`: contract dùng chung giữa các layer.
- `layer1/`: không chứa rule quyết định cảnh báo.
- `layer2/`: không phát âm thanh và không gọi TTS.
- `layer3/`: quyết định cảnh báo, priority, cooldown và safety rule.
- `layer4/`: audio, TTS, UI, API, metrics và các xử lý bất đồng bộ.
- `scenarios/`: input chuẩn để replay và regression test.
- `tests/`: test theo layer và test tích hợp.

Nếu repository hiện tại đang đặt `contracts.py` trong `layer3/`, team có thể giữ cách này trong MVP. Tuy nhiên, khi cả bốn tầng cùng dùng, nên chuyển sang `contracts/contracts.py` để tránh import vòng và thể hiện rõ đây là tài sản dùng chung.

---

## 3. Thiết lập môi trường chung

### 3.1. Tạo virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 3.2. Cài dependencies

Tạo `requirements.txt`:

```txt
pydantic>=2.7,<3
pytest>=8.0,<9
PyYAML>=6.0
numpy>=1.26
```

Cài đặt:

```bash
pip install -r requirements.txt
```

Tầng 1 có thể cài thêm:

```bash
pip install ultralytics onnx onnxruntime opencv-python
```

Nếu dùng NVIDIA GPU và ONNX Runtime GPU, cài package phù hợp với CUDA trên máy đích. Không commit hoặc hard-code CUDA provider trong contract.

### 3.3. Kiểm tra import

```bash
python -c "from layer3.contracts import Layer2_KinematicsOutput, Layer3_DecisionOutput; print('contracts: OK')"
```

---

## 4. Contract dùng chung

File hiện tại của team có thể nằm ở:

```text
layer3/contracts.py
```

Khi các layer khác dùng, import bằng:

```python
from layer3.contracts import Layer1_PerceptionOutput
from layer3.contracts import Layer2_KinematicsOutput
from layer3.contracts import Layer3_DecisionOutput
```

Khi chuyển sang thư mục dùng chung, import bằng:

```python
from contracts.contracts import Layer1_PerceptionOutput
```

Không được copy riêng một bản `contracts.py` vào từng layer. Nếu mỗi layer có một schema khác nhau, tích hợp sẽ tạo ra lỗi khó phát hiện.

---

## 5. Công dụng từng tầng

### 5.1. Tầng 1 — Unified Perception

Tầng 1 nhận frame ảnh và chỉ trả về nhận thức tĩnh:

- object class;
- confidence;
- bounding box;
- depth tương đối hoặc ước lượng;
- lane geometry;
- scene understanding.

Tầng 1 không được trả về quyết định “phát beep” hoặc “cảnh báo Critical”.

Output tối thiểu:

```json
{
  "frame_metadata": {
    "frame_id": 100,
    "timestamp_ms": 4000,
    "frame_age_ms": 10
  },
  "objects": [],
  "lanes": {
    "detected": true,
    "departure_probability": 0.2
  }
}
```

### 5.2. Tầng 2 — Kinematics

Tầng 2 nhận output Tầng 1 và tính:

- track ID;
- vận tốc tương đối;
- TTC;
- object có tiến lại gần không;
- object có cut-in không;
- quan hệ với lane;
- số frame track ổn định.

Tầng 2 không được phát âm thanh, không gọi TTS và không tự mute Tầng 4.

### 5.3. Tầng 3 — Decision Matrix

Tầng 3 nhận output Tầng 2 và quyết định:

- event nào đang hoạt động;
- mức `critical`, `warning`, `info`;
- urgent beep/chime/none;
- overlay màu gì;
- TTS có được phép hay không;
- candidate nào bị suppress;
- lý do của quyết định.

### 5.4. Tầng 4 — Async Context & Delivery

Tầng 4 nhận output Tầng 3 và thực hiện:

- phát beep;
- đưa câu cảnh báo vào TTS queue;
- hiển thị HUD;
- ghi metrics;
- cung cấp FastAPI/WebSocket;
- chạy context assistant hoặc SLM nếu có.

Tầng 4 không được thay đổi `priority_level` hoặc hạ Critical xuống Warning.

---

## 6. Toàn bộ chỉnh sửa trong `contracts.py`

### 6.1. Bổ sung `timestamp_ms` và `frame_age_ms`

Bản cũ:

```python
class FrameMetadata(BaseModel):
    frame_id: int
    timestamp: float
```

Bản mới:

```python
class FrameMetadata(BaseModel):
    frame_id: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    frame_age_ms: int = Field(default=0, ge=0)
```

Lý do:

- `timestamp_ms` dễ so sánh giữa các layer;
- `frame_age_ms` giúp Tầng 3 phát hiện dữ liệu stale;
- tránh nhầm giữa giây, mili-giây và timestamp Unix.

### 6.2. Thêm giá trị `unknown` cho scene

Bản cũ chỉ có `clear`, `rainy`, `foggy` và `day`, `night`, `twilight`.

Bản mới thêm `unknown` vì model có thể không xác định được thời tiết hoặc ánh sáng. Không nên ép model phải đoán một giá trị giả.

### 6.3. Validate bounding box

Bbox phải có đúng dạng:

```text
[x1, y1, x2, y2]
```

và phải thỏa:

```text
x2 > x1
x4 > y1
```

Nếu không validate ở contract, Tầng 2 có thể nhận box lỗi và tính sai tâm object, vận tốc hoặc TTC.

### 6.4. `depth_z` chuyển thành Optional

Bản cũ bắt buộc:

```python
depth_z: float = Field(ge=0.0)
```

Bản mới:

```python
depth_z: Optional[float] = Field(default=None, ge=0.0)
```

Lý do: depth model có thể không trả về giá trị hợp lệ ở một frame. `None` tốt hơn việc gửi giá trị giả `0.0`.

### 6.5. Sửa TTC

Không dùng `ttc: float = Field(ge=0.0)` nếu chưa thống nhất cách biểu diễn vô hạn.

Nên dùng:

```python
ttc_sec: Optional[float] = Field(default=None, ge=0.0)
```

Quy ước:

- `None`: không đủ dữ liệu hoặc không có nguy cơ tiến gần;
- số dương: TTC hợp lệ;
- không truyền số âm;
- không dùng `0` để biểu diễn thiếu dữ liệu.

### 6.6. Bổ sung tracking quality

Tầng 3 cần các trường:

```python
stable_frames: int
occluded: bool
confidence: float
lane_relation: str
```

Nếu chỉ có TTC mà không có track stability, hệ thống dễ phát cảnh báo từ detection nhiễu một frame.

### 6.7. Bổ sung `Lanes` vào Tầng 2

Tầng 3 cần lane output để quyết định LDW. Vì vậy `Layer2_KinematicsOutput` nên có:

```python
lanes: Lanes
```

với:

```python
departure_probability: Optional[float]
vehicle_offset_m: Optional[float]
```

### 6.8. Mở rộng output Tầng 3

Bản cũ chỉ có `active_event`. Bản mới thêm:

```python
selected_alert: Optional[AlertCandidate]
candidates: List[AlertCandidate]
```

Lý do: cần biết candidate nào được chọn và candidate nào bị suppress.

### 6.9. Đổi `mute_slm`

Nên đổi:

```python
mute_slm: bool
```

thành:

```python
suppress_lower_priority: bool
```

Lý do: Tầng 3 chỉ chặn cảnh báo ưu tiên thấp hơn; SLM không được xem là thành phần có quyền an toàn ngang với Decision Matrix.

---

## 7. Các scenario chuẩn

Mỗi file trong `scenarios/` là một input hợp lệ của Tầng 2 đưa vào Tầng 3. Các file này phải được commit vào Git để mọi người có cùng dữ liệu test.

### 7.1. `normal.json`

Mục đích: chạy xe bình thường, không có nguy cơ.

Kỳ vọng:

```text
active_event = none
audio = none
selected_alert = null
```

### 7.2. `fcw_warning.json`

Mục đích: xe phía trước đang tiến gần nhưng chưa Critical.

Điều kiện mẫu:

```text
ttc_sec = 2.0
is_approaching = true
relative_velocity_z_mps = -3.0
lane_relation = same_lane
stable_frames >= 4
```

Kỳ vọng:

```text
active_event = FCW
active_severity = warning
priority_level = 2
audio = chime hoặc TTS được phép
tts_allowed = true
```

### 7.3. `fcw_critical.json`

Mục đích: kiểm tra cảnh báo khẩn cấp.

Điều kiện mẫu:

```text
ttc_sec = 0.9
is_approaching = true
relative_velocity_z_mps = -7.0
lane_relation = same_lane
stable_frames >= 4
```

Kỳ vọng:

```text
active_event = FCW
active_severity = critical
priority_level = 1
audio = urgent_beep
beep_immediate = true
tts_allowed = false
suppress_lower_priority = true
```

### 7.4. `cut_in.json`

Mục đích: xe máy hoặc xe khác tạt vào làn trước xe.

Điều kiện mẫu:

```text
is_cut_in = true
ttc_sec <= 2.5
stable_frames >= 5
class_name = motorcycle hoặc car hoặc person
```

Kỳ vọng:

```text
active_event = Cut-in
active_severity = warning
tts_allowed = true
```

### 7.5. `ldw.json`

Mục đích: kiểm tra lệch làn có persistence.

Nếu dùng một frame, `departure_probability` cao chưa đủ để chứng minh LDW. Test thực tế nên dùng nhiều frame liên tiếp:

```text
frame 1: departure_probability = 0.80
frame 2: departure_probability = 0.83
frame 3: departure_probability = 0.86
...
```

Tổng thời gian vượt ngưỡng phải lớn hơn `persistence_ms`, ví dụ 800 ms.

Kỳ vọng:

```text
active_event = LDW
active_severity = warning
```

### 7.6. `conflict.json`

Mục đích: đồng thời có FCW và LDW hoặc Cut-in.

Kỳ vọng:

```text
FCW Critical thắng các cảnh báo thấp hơn
Các candidate còn lại có suppressed = true
suppression_reason có giá trị
```

### 7.7. `stale_frame.json`

Mục đích: kiểm tra input quá cũ.

Điều kiện mẫu:

```text
frame_age_ms = 500
max_frame_age_ms = 250
```

Kỳ vọng:

```text
active_event = System-Degraded
không phát FCW dựa trên frame stale
tts_allowed = false
```

---

## 8. Mẫu nội dung scenario còn thiếu

### 8.1. `scenarios/fcw_warning.json`

```json
{
  "frame_metadata": {
    "frame_id": 50,
    "timestamp_ms": 2000,
    "frame_age_ms": 10
  },
  "scene_understanding": {
    "weather": "clear",
    "lighting": "day"
  },
  "tracked_objects": [
    {
      "track_id": 5,
      "class_name": "car",
      "confidence": 0.91,
      "bbox": [400, 250, 510, 420],
      "depth_z": 18.0,
      "kinematics": {
        "relative_velocity_z_mps": -3.0,
        "ttc_sec": 2.0,
        "is_approaching": true,
        "is_cut_in": false,
        "lane_relation": "same_lane",
        "stable_frames": 10,
        "occluded": false,
        "confidence": 0.91
      }
    }
  ],
  "lanes": {
    "detected": true,
    "left_lane": [],
    "right_lane": [],
    "departure_probability": 0.12,
    "vehicle_offset_m": 0.05
  },
  "system_alerts": {
    "trigger_fcw": true,
    "trigger_ldw": false
  }
}
```

### 8.2. `scenarios/stale_frame.json`

```json
{
  "frame_metadata": {
    "frame_id": 300,
    "timestamp_ms": 10000,
    "frame_age_ms": 500
  },
  "scene_understanding": {
    "weather": "unknown",
    "lighting": "unknown"
  },
  "tracked_objects": [],
  "lanes": {
    "detected": false,
    "left_lane": [],
    "right_lane": [],
    "departure_probability": null,
    "vehicle_offset_m": null
  },
  "system_alerts": {
    "trigger_fcw": false,
    "trigger_ldw": false
  }
}
```

### 8.3. `scenarios/ldw.json`

```json
{
  "frame_metadata": {
    "frame_id": 80,
    "timestamp_ms": 4000,
    "frame_age_ms": 10
  },
  "scene_understanding": {
    "weather": "clear",
    "lighting": "day"
  },
  "tracked_objects": [],
  "lanes": {
    "detected": true,
    "left_lane": [[100, 700], [300, 400]],
    "right_lane": [[900, 700], [700, 400]],
    "departure_probability": 0.92,
    "vehicle_offset_m": 0.65
  },
  "system_alerts": {
    "trigger_fcw": false,
    "trigger_ldw": true
  }
}
```

Lưu ý: file `ldw.json` một frame phù hợp để kiểm tra contract. Để kiểm tra persistence 800 ms, cần một file dạng mảng frame hoặc một test gọi engine nhiều lần với timestamp tăng dần.

---

## 9. Quy trình làm việc của Tầng 1

### Folder

```text
layer1/
├── __init__.py
├── detector.py
├── lane_detector.py
├── model_runner.py
├── adapter.py
└── tests/
```

### Trách nhiệm

- Load YOLO/ONNX/TensorRT.
- Nhận frame.
- Trả `Layer1_PerceptionOutput`.
- Validate bbox, confidence và frame metadata.
- Không tạo `AlertCandidate`.

### Adapter tối thiểu

```python
from layer3.contracts import Layer1_PerceptionOutput


def run_perception(frame) -> Layer1_PerceptionOutput:
    # TODO: thay bằng YOLO/lane/depth thật
    return Layer1_PerceptionOutput.model_validate({
        "frame_metadata": {
            "frame_id": 0,
            "timestamp_ms": 0,
            "frame_age_ms": 0
        },
        "scene_understanding": {
            "weather": "unknown",
            "lighting": "unknown"
        },
        "objects": [],
        "lanes": {
            "detected": False,
            "left_lane": [],
            "right_lane": [],
            "departure_probability": None,
            "vehicle_offset_m": None
        }
    })
```

### Pass của Tầng 1

- Contract parse được 100% output.
- Bbox hợp lệ.
- Confidence nằm trong `[0, 1]`.
- Có `frame_id` và `timestamp_ms`.
- Không làm crash pipeline khi model không trả object.

### Fail của Tầng 1

- Bbox sai format.
- Dùng `depth_z = 0` để biểu diễn missing depth.
- Không có frame ID.
- Tự tạo FCW hoặc beep trong output.
- Model lỗi làm dừng toàn bộ pipeline.

---

## 10. Quy trình làm việc của Tầng 2

### Folder

```text
layer2/
├── __init__.py
├── tracker.py
├── ttc.py
├── cut_in.py
├── adapter.py
└── tests/
```

### Trách nhiệm

- Nhận `Layer1_PerceptionOutput`.
- Tạo track ID ổn định.
- Tính vận tốc tương đối.
- Tính TTC.
- Xác định `same_lane`.
- Xác định cut-in.
- Trả `Layer2_KinematicsOutput`.

### Quy ước TTC

```text
relative_velocity_z_mps < 0: vật thể đang tiến lại gần
relative_velocity_z_mps >= 0: không tiến lại gần
```

Nếu vật thể đang tiến lại gần:

```text
TTC = depth_z / abs(relative_velocity_z_mps)
```

Nếu không tiến lại gần hoặc thiếu depth:

```text
ttc_sec = null
```

### Pass của Tầng 2

- `track_id` ổn định qua các frame.
- TTC không âm.
- Không dùng TTC giả khi thiếu depth hoặc velocity.
- Có `stable_frames`.
- Có `lane_relation`.
- Không tự phát âm thanh.

### Fail của Tầng 2

- Đổi dấu vận tốc giữa các frame.
- TTC âm.
- Gửi `ttc = 0` khi không có nguy cơ.
- Gửi dữ liệu mà không có timestamp.
- Gán mọi object là `same_lane`.

---

## 11. Quy trình làm việc của Tầng 3

### Folder

```text
layer3/
├── contracts.py
├── config.py
├── cooldown.py
├── rules.py
├── engine.py
├── replay.py
├── audio_adapter.py
└── tests/
```

### Chạy replay

```bash
python -m layer3.replay \
  --input scenarios/fcw_warning.json \
  --policy config/policy.json
```

### Chạy unit test

```bash
pytest layer3/tests -q
```

### Pass của Tầng 3

- FCW, Cut-in, LDW có test.
- FCW Critical phát `urgent_beep`.
- FCW Critical có `tts_allowed = false`.
- Priority resolver chọn đúng cảnh báo cao nhất.
- Cảnh báo trùng bị cooldown.
- Frame stale trở thành `System-Degraded`.
- Mỗi cảnh báo có `reason`.
- Replay cùng input cho cùng output.

### Fail của Tầng 3

- SLM hoặc TTS được quyền thay đổi Critical.
- Một event phát lặp ở mọi frame.
- Không biết vì sao alert được phát.
- Frame stale vẫn phát cảnh báo nguy hiểm như dữ liệu mới.
- Unit test chỉ kiểm tra output mà không kiểm tra `reason` và `tts_allowed`.

---

## 12. Quy trình làm việc của Tầng 4

### Folder

```text
layer4/
├── __init__.py
├── pipeline.py
├── tts_worker.py
├── api.py
├── hud.py
├── metrics.py
└── tests/
```

### Trách nhiệm

- Nhận `Layer3_DecisionOutput`.
- Nếu `beep_immediate = true`, phát beep không qua TTS queue.
- Nếu `tts_allowed = true`, đưa message vào queue.
- Hiển thị HUD.
- Ghi metrics.
- Không block capture/inference loop.

### Adapter tối thiểu

```python
from layer3.contracts import Layer3_DecisionOutput


def consume_decision(
    output: Layer3_DecisionOutput,
) -> None:
    signals = output.decision_matrix.actuation_signals
    selected = output.decision_matrix.selected_alert

    if selected is None:
        return

    if signals.beep_immediate:
        print("URGENT BEEP")
        return

    if signals.tts_allowed:
        print(f"TTS: {selected.message_key}")
```

### Pass của Tầng 4

- TTS không block frame loop.
- Critical beep không chờ TTS.
- Queue có giới hạn.
- Có xử lý TTS lỗi.
- HUD hiển thị severity và event.
- Metrics có frame ID, timestamp và latency.

### Fail của Tầng 4

- Gọi Piper trực tiếp trong hàm xử lý frame.
- TTS queue vô hạn.
- Tầng 4 tự sửa `priority_level`.
- Tầng 4 tự tắt cảnh báo Critical.
- Audio lỗi làm crash perception loop.

---

## 13. Smoke test toàn pipeline

Tạo file `tests/test_pipeline_smoke.py`:

```python
import json
from pathlib import Path

from layer3.config import Policy
from layer3.contracts import Layer2_KinematicsOutput
from layer3.engine import DecisionEngine


ROOT = Path(__file__).resolve().parents[1]


def load_scenario(name: str):
    with open(ROOT / "scenarios" / name, "r", encoding="utf-8") as file:
        return Layer2_KinematicsOutput.model_validate(
            json.load(file)
        )


def test_smoke_fcw_warning():
    policy = Policy.from_json(ROOT / "config" / "policy.json")
    engine = DecisionEngine(policy)
    input_data = load_scenario("fcw_warning.json")

    output = engine.evaluate(input_data)

    assert output.decision_matrix.active_event == "FCW"
    assert output.decision_matrix.active_severity == "warning"
    assert output.decision_matrix.selected_alert is not None


def test_smoke_stale_frame():
    policy = Policy.from_json(ROOT / "config" / "policy.json")
    engine = DecisionEngine(policy)
    input_data = load_scenario("stale_frame.json")

    output = engine.evaluate(input_data)

    assert (
        output.decision_matrix.active_event
        == "System-Degraded"
    )
    assert (
        output.decision_matrix.actuation_signals.tts_allowed
        is False
    )
```

Chạy toàn bộ:

```bash
pytest -q
```

Chạy smoke test:

```bash
pytest tests/test_pipeline_smoke.py -q
```

Chạy replay tất cả scenario trên Linux/macOS:

```bash
for file in scenarios/*.json; do
  echo "===== $file ====="
  python -m layer3.replay \
    --input "$file" \
    --policy config/policy.json
 done
```

Windows PowerShell:

```powershell
Get-ChildItem scenarios\*.json | ForEach-Object {
    Write-Host "===== $($_.FullName) ====="
    python -m layer3.replay `
      --input $_.FullName `
      --policy config/policy.json
}
```

---

## 14. Bảng pass/fail chung cho team

### Contract

| Tiêu chí | Pass | Fail |
|---|---|---|
| Frame metadata | Có frame ID, timestamp, age | Thiếu hoặc sai đơn vị |
| Bbox | 4 giá trị, x2 > x1, y2 > y1 | Sai chiều hoặc thiếu giá trị |
| Confidence | `[0, 1]` | Ngoài khoảng |
| TTC | `null` hoặc số dương | Số âm hoặc dùng 0 giả |
| Lane | Có detected và probability | Không biết dữ liệu có hợp lệ |

### Functional

| Scenario | Kết quả pass |
|---|---|
| Normal | Không có audio alert |
| FCW warning | Warning, không Critical |
| FCW critical | Urgent beep, TTS bị chặn |
| Cut-in | Cut-in warning |
| LDW | Cảnh báo sau persistence |
| Conflict | Cảnh báo ưu tiên cao nhất thắng |
| Stale frame | System-Degraded |

### KPI MVP

```text
Contract validation pass rate       = 100%
Unit/integration test pass rate     = 100%
Critical recall trên scenario       >= 90%
Critical false positive             <= 1 / 10 phút
Duplicate alert rate                <= 5%
Critical bị TTS chặn                = 0
Alert có reason                      = 100%
Decision latency p95                 <= 50 ms
Unresolved critical bug              = 0
```

Các KPI trên là KPI của prototype. Không được trình bày chúng như tiêu chuẩn chứng nhận xe thương mại.

---

## 15. Quy tắc Git và phối hợp team

### Branch

```text
feature/layer1-perception
feature/layer2-kinematics
feature/layer3-decision
feature/layer4-platform
```

### Commit mẫu

```text
feat(layer3): add FCW priority rule
fix(contracts): allow nullable TTC
 test(scenarios): add stale frame case
feat(layer4): add non-blocking TTS adapter
```

### Pull request bắt buộc

Mỗi PR phải có:

- mô tả thay đổi;
- file contract bị ảnh hưởng nếu có;
- test command đã chạy;
- output test;
- ảnh/log nếu thay đổi HUD hoặc audio;
- ghi rõ có thay đổi schema hay không.

Không được tự ý sửa `contracts.py` mà không thông báo cho cả team. Contract thay đổi là thay đổi API nội bộ.

---

## 16. Definition of Done cuối cùng

Dự án được xem là đã tích hợp thông suốt khi chạy được:

```bash
pytest -q
```

và:

```bash
python -m layer3.replay \
  --input scenarios/fcw_critical.json \
  --policy config/policy.json
```

Kết quả phải chứng minh:

```text
- Tầng 1 có thể tạo perception output hợp lệ.
- Tầng 2 có thể tạo kinematics output hợp lệ.
- Tầng 3 chọn đúng alert và ghi rõ reason.
- Tầng 4 nhận được output mà không cần sửa schema.
- FCW Critical phát urgent beep độc lập với TTS.
- Scenario stale frame chuyển sang System-Degraded.
- Các candidate bị suppress vẫn được log.
- Toàn bộ pipeline có thể replay và tái hiện.
```

Nếu một thành viên chưa hoàn thiện model thật, người đó vẫn phải tạo adapter trả về mock output đúng contract. Nhờ vậy, cả team vẫn có thể chạy smoke test và tích hợp song song.
