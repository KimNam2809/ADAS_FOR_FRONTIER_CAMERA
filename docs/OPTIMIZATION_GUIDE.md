# 🚀 ADAS Object Detection Optimization Guide for Edge Devices

## **Mục Lục**
1. [Giới Thiệu](#giới-thiệu)
2. [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
3. [Tối Ưu Hóa Độ Trễ (Latency)](#tối-ưu-hóa-độ-trễ-latency)
4. [Tối Ưu Hóa Băng Thông và Tài Nguyên](#tối-ưu-hóa-băng-thông-và-tài-nguyên)
5. [Cải Thiện Hiệu Suất và Trải Nghiệm Người Dùng](#cải-thiện-hiệu-suất-và-trải-nghiệm-người-dùng)
6. [Cấu Hình Cho Từng Thiết Bị](#cấu-hình-cho-từng-thiết-bị)
7. [Benchmark và Đánh Giá](#benchmark-và-đánh-giá)
8. [Khắc Phục Sự Cố](#khắc-phục-sự-cố)

---

## **📋 Giới Thiệu**

Module **Object Detection** của **RoadWatch Copilot** được thiết kế đặc biệt cho **Edge Devices** (như Jetson Nano) với mục tiêu:

✅ **Giảm độ trễ** (Latency < 50ms)
✅ **Tối ưu băng thông và tài nguyên** (CPU/GPU/Memory)
✅ **Cải thiện hiệu suất** (FPS ≥ 30)
✅ **Trải nghiệm người dùng mượt mà**

Module sử dụng **YOLOv8-nano** với **ONNX Runtime** và **TensorRT** để đạt hiệu suất tối ưu trên Jetson Nano.

---

## **💻 Yêu Cầu Hệ Thống**

### **1. Jetson Nano (ARM64)**
| **Thông Số** | **Giá Trị** | **Ghi Chú** |
|--------------|------------|-------------|
| CPU | Quad-core ARM Cortex-A57 @ 1.43 GHz | |
| GPU | NVIDIA Maxwell (128 CUDA Cores) | Hỗ trợ CUDA 10.2 |
| RAM | 4GB LPDDR4 | Shared với GPU |
| Storage | 16GB eMMC / microSD | Khuyến nghị dùng SSD |
| OS | Ubuntu 20.04 (ARM64) | JetPack 5.1.2 |
| CUDA | 10.2 | |
| TensorRT | 8.5.3 | |

### **2. AWS EC2 G5G.xlarge (x86_64)**
| **Thông Số** | **Giá Trị** | **Ghi Chú** |
|--------------|------------|-------------|
| CPU | Intel Xeon Scalable (4 vCPU) | |
| GPU | NVIDIA T4G (Ampere, 2560 CUDA Cores) | |
| RAM | 16GB | |
| VRAM | 8GB GDDR6 | |
| OS | Ubuntu 22.04 | |
| CUDA | 11.8 | |
| TensorRT | 8.5.3 | |

### **3. Laptop AMD (x86_64)**
| **Thông Số** | **Giá Trị** | **Ghi Chú** |
|--------------|------------|-------------|
| CPU | AMD Ryzen 7 7735HS (8C/16T) | |
| GPU | AMD Radeon 680M (RDNA 2) | Không hỗ trợ CUDA |
| RAM | 16GB DDR5 | |
| OS | Ubuntu 22.04 / Windows 11 | |
| ROCm | 5.7+ | Thay thế CUDA |

---

## **⚡ Tối Ưu Hóa Độ Trễ (Latency)**

### **🎯 Mục Tiêu**
- **Độ trễ xử lý < 50ms** (từ khi nhận frame đến khi output kết quả)
- **FPS ≥ 30** (để đảm bảo real-time)

### **🔧 Các Kỹ Thuật Tối Ưu**

#### **1. Chọn Model Phù Hợp**
| **Model** | **Size (MB)** | **FPS (Jetson Nano)** | **mAP** | **Latency (ms)** | **Khuyến Nghị** |
|-----------|--------------|----------------------|---------|------------------|------------------|
| YOLOv8n | ~3.2MB | 30-40 | 0.37 | ~30-40 | ✅ **Tốt nhất cho Jetson Nano** |
| YOLOv8s | ~9.2MB | 20-25 | 0.45 | ~40-50 | ⚠️ Chỉ dùng nếu cần độ chính xác cao |
| YOLOv8m | ~25.2MB | 10-15 | 0.50 | ~60-80 | ❌ Không phù hợp |

**→ Sử dụng `YOLOv8n` cho Jetson Nano để đạt FPS cao nhất.**

#### **2. Input Size Tối Ưu**
| **Input Size** | **FPS (Jetson Nano)** | **mAP** | **Latency (ms)** | **Khuyến Nghị** |
|----------------|----------------------|---------|------------------|------------------|
| 320x320 | 40-50 | 0.30 | ~20-30 | ✅ **Tốt nhất cho tốc độ** |
| 480x480 | 30-35 | 0.35 | ~30-40 | ⚠️ Cân bằng tốc độ/chất lượng |
| 640x640 | 20-25 | 0.37 | ~40-50 | ❌ Chậm trên Jetson Nano |

**→ Sử dụng `320x320` cho Jetson Nano để giảm latency.**

#### **3. Quantization (Lượng Tử Hóa)**
| **Precision** | **Size (MB)** | **FPS** | **mAP Loss** | **Latency** | **Khuyến Nghị** |
|--------------|--------------|---------|--------------|-------------|------------------|
| FP32 | ~3.2MB | 30 | 0% | ~40ms | ❌ Không tối ưu |
| FP16 | ~1.6MB | 35-40 | <1% | ~30ms | ✅ **Tốt nhất cho Jetson** |
| INT8 | ~0.8MB | 40-45 | ~2-3% | ~25ms | ✅ **Tốt nhất nếu chấp nhận mất độ chính xác nhẹ** |

**→ Sử dụng `FP16` hoặc `INT8` để giảm latency và tăng FPS.**

**Cách bật quantization:**
```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()

# Quantize sang FP16
fp16_model = optimizer.quantize_onnx("yolov8n.onnx", "fp16")

# Quantize sang INT8 (cần calibration data)
int8_model = optimizer.quantize_onnx("yolov8n.onnx", "int8", calibration_data)
```

#### **4. TensorRT Optimization**
TensorRT có thể **tăng tốc độ lên 2-3 lần** so với ONNX Runtime thuần.

**Cách bật TensorRT:**
```python
from src.detection import DetectorFactory

# Tạo detector với TensorRT
detector = DetectorFactory.create_detector(
    device_type="jetson_nano",
    use_tensorrt=True
)
```

**Build TensorRT Engine:**
```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()
engine_path = optimizer.optimize_for_tensorrt(
    "yolov8n.onnx",
    fp16_mode=True,
    int8_mode=False,
    max_batch_size=1
)
```

#### **5. Multi-Threading**
Sử dụng **luồng riêng biệt** cho:
- **Preprocessing** (resize, normalize)
- **Inference** (model prediction)
- **Post-processing** (NMS, filtering)

**Ví dụ:**
```python
from concurrent.futures import ThreadPoolExecutor
from src.detection import YOLODetector

detector = YOLODetector()

def process_frame(frame):
    return detector.detect(frame)

# Sử dụng 3 luồng
with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(process_frame, frames))
```

#### **6. Frame Caching (Bộ Đệm Frame)**
Giảm thiểu việc xử lý lặp lại các frame giống nhau.

**Cài đặt:**
```python
from src.config import PerformanceConfig

config = PerformanceConfig(
    enable_frame_cache=True,
    cache_size=5  # Lưu 5 frame gần nhất
)
```

#### **7. Asynchronous Processing**
Xử lý **không đồng bộ** để tránh chặn luồng chính.

**Ví dụ:**
```python
import asyncio
from src.detection import YOLODetector

detector = YOLODetector()

async def detect_async(frame):
    return await asyncio.to_thread(detector.detect, frame)

# Chạy song song
results = await asyncio.gather(*[detect_async(f) for f in frames])
```

---

## **📊 Tối Ưu Hóa Băng Thông và Tài Nguyên**

### **🎯 Mục Tiêu**
- **Giảm băng thông** (compression, batch processing)
- **Giảm sử dụng CPU/GPU** (model nhẹ, quantization)
- **Giảm sử dụng RAM** (memory pooling, garbage collection)

### **🔧 Các Kỹ Thuật Tối Ưu**

#### **1. Frame Compression**
Nén frame trước khi xử lý để **giảm băng thông**.

**Cài đặt:**
```python
from src.utils import FrameProcessor

processor = FrameProcessor(
    target_size=320,
    enable_compression=True,
    compression_quality=75  # Chất lượng 75% (cân bằng giữa chất lượng và kích thước)
)
```

**Ảnh hưởng:**
| **Compression Quality** | **File Size** | **Processing Time** | **Khuyến Nghị** |
|------------------------|---------------|---------------------|------------------|
| 100 (No compression) | 100% | 100% | ❌ Không tối ưu |
| 90 | ~50% | ~95% | ⚠️ Tốt cho chất lượng cao |
| 75 | ~30% | ~90% | ✅ **Tốt nhất cho Jetson** |
| 50 | ~15% | ~80% | ⚠️ Chất lượng thấp |

#### **2. Batch Processing**
Xử lý **nhiều frame cùng lúc** để tận dụng GPU hiệu quả.

**Cài đặt:**
```python
from src.config import DetectorConfig

config = DetectorConfig(
    batch_size=4  # Xử lý 4 frame cùng lúc
)
```

**Lưu ý:**
- **Jetson Nano**: `batch_size=1` (không đủ VRAM)
- **AWS G5G**: `batch_size=4-8` (đủ VRAM)

#### **3. Memory Pooling**
Tái sử dụng bộ nhớ để **giảm thiểu allocation/deallocation**.

**Cài đặt:**
```python
from src.config import PerformanceConfig

config = PerformanceConfig(
    enable_memory_pool=True,
    memory_pool_size=10  # 10MB
)
```

#### **4. Model Pruning (Cắt Tỉa Model)**
Loại bỏ các **weights không quan trọng** để giảm kích thước model.

**Cách thực hiện:**
```python
import torch
from src.utils import ModelOptimizer

# Load model
model = torch.hub.load('ultralytics/yolov8', 'yolov8n')

# Prune 30% of weights
optimizer = ModelOptimizer()
pruned_model = optimizer.prune_model(model, amount=0.3)

# Export to ONNX
optimizer.export_to_onnx(pruned_model, input_shape=(1, 3, 320, 320))
```

**Ảnh hưởng:**
| **Pruning Amount** | **Model Size** | **FPS** | **mAP Loss** | **Khuyến Nghị** |
|-------------------|---------------|---------|--------------|------------------|
| 0% | 100% | 100% | 0% | ❌ Không prune |
| 20% | ~80% | ~110% | <1% | ✅ **Tốt nhất** |
| 30% | ~70% | ~120% | ~2% | ⚠️ Cân nhắc |
| 50% | ~50% | ~150% | ~5-10% | ❌ Mất độ chính xác nhiều |

#### **5. Dynamic Resolution Scaling**
Thay đổi **kích thước input** dựa trên tải hệ thống.

**Ví dụ:**
```python
from src.detection import YOLODetector
from src.utils import PerformanceMonitor

detector = YOLODetector()
monitor = PerformanceMonitor()

# Giảm resolution nếu FPS thấp
if monitor.get_average_metrics().fps < 20:
    detector.config.input_size = 320  # Giảm xuống 320x320
elif monitor.get_average_metrics().fps > 40:
    detector.config.input_size = 640  # Tăng lên 640x640
```

#### **6. Selective Processing**
Chỉ xử lý **các vùng quan tâm (ROI)** thay vì toàn bộ frame.

**Ví dụ:**
```python
from src.detection import YOLODetector

detector = YOLODetector()

# Chỉ xử lý 1/4 frame (góc trên bên trái)
roi = frame[0:240, 0:320]  # ROI: (y1:y2, x1:x2)
result = detector.detect(roi)
```

#### **7. Early Stopping**
Dừng xử lý sớm nếu **không có vật thể quan trọng**.

**Ví dụ:**
```python
from src.detection import YOLODetector

detector = YOLODetector()

# Chỉ xử lý nếu có chuyển động
if has_motion(frame):
    result = detector.detect(frame)
else:
    result = None  # Skip processing
```

---

## **🎮 Cải Thiện Hiệu Suất và Trải Nghiệm Người Dùng**

### **🎯 Mục Tiêu**
- **Hiệu suất ổn định** (không giật lag)
- **Trải nghiệm mượt mà** (không false positive)
- **Cảnh báo kịp thời** (ưu tiên theo mức độ nguy hiểm)

### **🔧 Các Kỹ Thuật Cải Thiện**

#### **1. Priority-Based Processing**
Ưu tiên xử lý **các vật thể quan trọng** (người, xe, biển báo).

**Cài đặt:**
```python
from src.config import DetectorConfig

config = DetectorConfig(
    target_classes=["person", "car", "motorcycle", "bus", "truck", "stop sign", "traffic light"]
)
```

**Priority Classes:**
| **Class** | **Priority** | **Mức Độ Nguy Hiểm** |
|-----------|-------------|---------------------|
| person | 1 | ⭐⭐⭐⭐⭐ |
| car | 2 | ⭐⭐⭐⭐ |
| motorcycle | 2 | ⭐⭐⭐⭐ |
| bus | 2 | ⭐⭐⭐⭐ |
| truck | 2 | ⭐⭐⭐⭐ |
| bicycle | 3 | ⭐⭐⭐ |
| stop sign | 1 | ⭐⭐⭐⭐⭐ |
| traffic light | 1 | ⭐⭐⭐⭐⭐ |

#### **2. Temporal Smoothing**
Làm mượt kết quả trên **nhiều frame** để giảm false positive.

**Cài đặt:**
```python
from src.detection import DetectionPostProcessor

post_processor = DetectionPostProcessor(
    max_track_age=2.0,  # Theo dõi vật thể trong 2 giây
    iou_threshold=0.5,  # IoU threshold cho tracking
    min_detection_confidence=0.4  # Confidence tối thiểu để tracking
)
```

**Cách hoạt động:**
1. **Tracking**: Theo dõi vật thể qua nhiều frame.
2. **Filtering**: Loại bỏ các detection **không ổn định** (nháy nháy).
3. **Averaging**: Lấy trung bình vị trí của vật thể trên nhiều frame.

#### **3. Confidence Threshold Dynamic Adjustment**
Điều chỉnh **ngưỡng confidence** dựa trên tình huống.

**Ví dụ:**
```python
from src.detection import YOLODetector

detector = YOLODetector()

# Tăng confidence nếu có nhiều false positive
if false_positive_rate > 0.1:  # >10% false positive
    detector.config.conf_threshold = 0.6  # Tăng ngưỡng
elif false_positive_rate < 0.05:  # <5% false positive
    detector.config.conf_threshold = 0.4  # Giảm ngưỡng
```

#### **4. Non-Maximum Suppression (NMS) Tối Ưu**
Loại bỏ **các bounding box trùng lặp** hiệu quả.

**Cài đặt:**
```python
from src.config import DetectorConfig

config = DetectorConfig(
    iou_threshold=0.45  # IoU threshold cho NMS
)
```

**Ảnh hưởng:**
| **IoU Threshold** | **Số Lượng Box** | **False Positive** | **Khuyến Nghị** |
|------------------|------------------|-------------------|------------------|
| 0.3 | Nhiều | Cao | ❌ Quá thấp |
| 0.45 | Trung bình | Trung bình | ✅ **Tốt nhất** |
| 0.6 | Ít | Thấp | ⚠️ Có thể bỏ sót vật thể |
| 0.7 | Rất ít | Rất thấp | ❌ Có thể bỏ sót nhiều |

#### **5. Adaptive Frame Rate**
Điều chỉnh **FPS** dựa trên tải hệ thống.

**Ví dụ:**
```python
from src.utils import PerformanceMonitor
import time

monitor = PerformanceMonitor()

# Giảm FPS nếu hệ thống quá tải
if monitor.get_average_metrics().cpu_usage > 90:
    time.sleep(0.1)  # Giảm FPS xuống ~10fps
elif monitor.get_average_metrics().cpu_usage > 80:
    time.sleep(0.05)  # Giảm FPS xuống ~20fps
```

#### **6. User Feedback Integration**
Cho phép người dùng **điều chỉnh ngưỡng** dựa trên trải nghiệm.

**Ví dụ:**
```python
from src.config import DetectorConfig

# Người dùng muốn ít cảnh báo hơn
config.conf_threshold = 0.7  # Tăng ngưỡng confidence

# Người dùng muốn nhiều cảnh báo hơn
config.conf_threshold = 0.3  # Giảm ngưỡng confidence
```

#### **7. Context-Aware Alerts**
Cảnh báo **thông minh** dựa trên ngữ cảnh.

**Ví dụ:**
```python
from src.detection import DetectionPostProcessor

post_processor = DetectionPostProcessor()

# Cài đặt lane boundaries (từ module Lane Detection)
post_processor.set_lane_boundaries(lane_boundaries)

# Xử lý kết quả
context_result = post_processor.process(detection_result)

# Kiểm tra cảnh báo
for warning in context_result.collision_warnings:
    print(f"Cảnh báo va chạm: {warning['class']} - TTC: {warning['ttc']:.2f}s")

for warning in context_result.lane_violation_warnings:
    print(f"Cảnh báo lệch làn: {warning['class']}")

for warning in context_result.speed_violation_warnings:
    print(f"Cảnh báo vượt tốc độ: {warning['class']} - {warning['estimated_speed']:.1f} km/h")
```

---

## **⚙️ Cấu Hình Cho Từng Thiết Bị**

### **1. Jetson Nano (ARM64)**
```python
from src.detection import DetectorFactory

# Tạo detector tối ưu cho Jetson Nano
detector = DetectorFactory.create_detector(
    device_type="jetson_nano",
    use_tensorrt=True,
    target_fps=30
)

# Cấu hình chi tiết
detector.config.model_type = "yolov8n"
detector.config.input_size = 320
detector.config.use_half_precision = True
detector.config.use_int8 = True  # Nếu chấp nhận mất độ chính xác nhẹ
```

**Dự kiến hiệu suất:**
- **FPS**: 30-40
- **Latency**: 25-35ms
- **Memory Usage**: ~1.5GB
- **GPU Usage**: ~80-90%

---

### **2. AWS EC2 G5G.xlarge (x86_64)**
```python
from src.detection import DetectorFactory

# Tạo detector tối ưu cho AWS G5G
detector = DetectorFactory.create_detector(
    device_type="aws_g5g",
    use_tensorrt=True,
    target_fps=60
)

# Cấu hình chi tiết
detector.config.model_type = "yolov8s"
detector.config.input_size = 640
detector.config.batch_size = 4  # Xử lý 4 frame cùng lúc
detector.config.use_half_precision = True
```

**Dự kiến hiệu suất:**
- **FPS**: 80-100
- **Latency**: 10-20ms
- **Memory Usage**: ~3GB
- **GPU Usage**: ~70-80%

---

### **3. Laptop AMD (x86_64)**
```python
from src.detection import DetectorFactory

# Tạo detector tối ưu cho Laptop AMD
detector = DetectorFactory.create_detector(
    device_type="laptop_amd",
    use_tensorrt=False,  # Không hỗ trợ TensorRT
    target_fps=30
)

# Cấu hình chi tiết
detector.config.model_type = "yolov8s"
detector.config.input_size = 640
detector.config.use_half_precision = False  # Không hỗ trợ FP16 trên AMD
```

**Dự kiến hiệu suất:**
- **FPS**: 20-30 (CPU) / 40-50 (GPU ROCm)
- **Latency**: 30-50ms
- **Memory Usage**: ~2GB
- **GPU Usage**: ~60-70%

---

## **📈 Benchmark và Đánh Giá**

### **1. Cách Chạy Benchmark**
```python
from src.detection import YOLODetector
from src.utils import PerformanceMonitor
import cv2
import time

# Load detector
detector = YOLODetector()

# Load test video
cap = cv2.VideoCapture("test_video.mp4")

# Initialize performance monitor
monitor = PerformanceMonitor()

# Run benchmark
frame_count = 0
start_time = time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # Process frame
    start = monitor.start_frame()
    result = detector.detect(frame)
    monitor.end_frame(start)
    
    frame_count += 1
    
    # Display metrics every 10 frames
    if frame_count % 10 == 0:
        metrics = monitor.get_average_metrics()
        print(f"Frame {frame_count}: FPS={metrics.fps:.1f}, Latency={metrics.latency:.1f}ms")

cap.release()

# Print final results
end_time = time.time()
total_time = end_time - start_time
avg_fps = frame_count / total_time

print(f"\n=== Benchmark Results ===")
print(f"Total Frames: {frame_count}")
print(f"Total Time: {total_time:.2f}s")
print(f"Average FPS: {avg_fps:.2f}")
print(f"Average Latency: {monitor.get_average_metrics().latency:.2f}ms")
```

### **2. Kết Quả Dự Kiến**

| **Thiết Bị** | **Model** | **Input Size** | **Precision** | **FPS** | **Latency (ms)** | **mAP** |
|-------------|-----------|---------------|--------------|---------|------------------|---------|
| Jetson Nano | YOLOv8n | 320x320 | FP16 | 35-40 | 25-30 | 0.35 |
| Jetson Nano | YOLOv8n | 320x320 | INT8 | 40-45 | 20-25 | 0.33 |
| Jetson Nano | YOLOv8s | 640x640 | FP16 | 20-25 | 40-50 | 0.43 |
| AWS G5G | YOLOv8s | 640x640 | FP16 | 80-100 | 10-20 | 0.45 |
| AWS G5G | YOLOv8m | 640x640 | FP16 | 50-60 | 15-25 | 0.50 |
| Laptop AMD | YOLOv8s | 640x640 | FP32 | 20-30 | 30-50 | 0.45 |

### **3. Đánh Giá Chất Lượng**

| **Metric** | **Mục Tiêu** | **Cách Đo** | **Kết Quả Dự Kiến** |
|------------|-------------|-------------|---------------------|
| **mAP** | ≥ 0.35 | COCO evaluation | 0.35-0.45 |
| **FPS** | ≥ 30 | Benchmark | 30-40 (Jetson) |
| **Latency** | < 50ms | Benchmark | 25-35ms (Jetson) |
| **False Positive Rate** | < 5% | Manual review | < 3% |
| **Memory Usage** | < 2GB | `psutil` | ~1.5GB (Jetson) |
| **CPU Usage** | < 80% | `psutil` | ~60-70% (Jetson) |
| **GPU Usage** | < 90% | `pynvml` | ~80-90% (Jetson) |

---

## **🛠️ Khắc Phục Sự Cố**

### **1. Lỗi Thường Gặp**

#### **🔴 Lỗi: `CUDA out of memory`**
**Nguyên nhân:**
- Model quá lớn cho GPU.
- Batch size quá lớn.

**Giải pháp:**
```python
# Giảm batch size
detector.config.batch_size = 1

# Dùng model nhỏ hơn
detector.config.model_type = "yolov8n"

# Giảm input size
detector.config.input_size = 320
```

---

#### **🔴 Lỗi: `TensorRT engine not found`**
**Nguyên nhân:**
- Chưa build TensorRT engine.
- Đường dẫn không đúng.

**Giải pháp:**
```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()

# Build TensorRT engine
engine_path = optimizer.optimize_for_tensorrt(
    "yolov8n.onnx",
    fp16_mode=True
)

# Cập nhật config
detector.config.engine_path = engine_path
detector.config.use_tensorrt = True
```

---

#### **🔴 Lỗi: `ONNX model not found`**
**Nguyên nhân:**
- Chưa export model sang ONNX.
- Đường dẫn không đúng.

**Giải pháp:**
```python
from src.utils import ModelOptimizer
import torch

# Load PyTorch model
model = torch.hub.load('ultralytics/yolov8', 'yolov8n')

# Export to ONNX
optimizer = ModelOptimizer()
onnx_path = optimizer.export_to_onnx(model, input_shape=(1, 3, 320, 320))

# Cập nhật config
detector.config.model_path = onnx_path
```

---

#### **🔴 Lỗi: `Low FPS`**
**Nguyên nhân:**
- Model quá nặng.
- Input size quá lớn.
- Không bật TensorRT.

**Giải pháp:**
```python
# Dùng model nhỏ hơn
detector.config.model_type = "yolov8n"

# Giảm input size
detector.config.input_size = 320

# Bật TensorRT
detector.config.use_tensorrt = True

# Bật FP16
detector.config.use_half_precision = True
```

---

#### **🔴 Lỗi: `High Latency`**
**Nguyên nhân:**
- Xử lý đồng bộ.
- Không bật quantization.
- Frame cache không hiệu quả.

**Giải pháp:**
```python
# Bật quantization
detector.config.use_half_precision = True
detector.config.use_int8 = True

# Bật frame cache
from src.config import PerformanceConfig
config = PerformanceConfig(enable_frame_cache=True)

# Sử dụng async processing
import asyncio
async def detect_async(frame):
    return await asyncio.to_thread(detector.detect, frame)
```

---

#### **🔴 Lỗi: `False Positive Quá Nhiều`**
**Nguyên nhân:**
- Confidence threshold quá thấp.
- Không bật temporal smoothing.

**Giải pháp:**
```python
# Tăng confidence threshold
detector.config.conf_threshold = 0.6

# Bật temporal smoothing
from src.detection import DetectionPostProcessor
post_processor = DetectionPostProcessor(
    max_track_age=2.0,
    min_detection_confidence=0.5
)
```

---

### **2. Debugging Tools**

#### **🔍 Kiểm Tra GPU Usage**
```python
import pynvml

pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

# GPU Usage
gpu_usage = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
print(f"GPU Usage: {gpu_usage}%")

# Memory Usage
mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
print(f"GPU Memory: {mem_info.used / 1024**2:.1f}MB / {mem_info.total / 1024**2:.1f}MB")
```

---

#### **🔍 Kiểm Tra CPU/Memory Usage**
```python
import psutil

# CPU Usage
cpu_usage = psutil.cpu_percent(interval=1)
print(f"CPU Usage: {cpu_usage}%")

# Memory Usage
mem_usage = psutil.virtual_memory().percent
print(f"Memory Usage: {mem_usage}%")
```

---

#### **🔍 Kiểm Tra Latency**
```python
from src.utils import PerformanceMonitor

monitor = PerformanceMonitor()

# Sau khi xử lý một số frame
metrics = monitor.get_average_metrics()
print(f"Average Latency: {metrics.latency:.2f}ms")
print(f"Average FPS: {metrics.fps:.2f}")
```

---

#### **🔍 Log Debug**
```python
from src.utils import setup_logger

# Setup logger với level DEBUG
logger = setup_logger("adas", log_level=logging.DEBUG)

# Log chi tiết
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

---

## **📚 Tài Liệu Tham Khảo**

1. [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com/)
2. [ONNX Runtime Documentation](https://onnxruntime.ai/)
3. [TensorRT Documentation](https://developer.nvidia.com/tensorrt)
4. [NVIDIA Jetson Nano Developer Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit)
5. [PyTorch Quantization Guide](https://pytorch.org/docs/stable/quantization.html)
6. [OpenCV Documentation](https://docs.opencv.org/4.x/)

---

## **🎯 Kết Luận**

Để đạt được **hiệu suất tối ưu** trên **Edge Devices** (như Jetson Nano), bạn nên:

1. ✅ **Sử dụng YOLOv8n** (model nhỏ nhất)
2. ✅ **Input size 320x320** (giảm độ phân giải)
3. ✅ **Bật FP16/INT8 quantization** (giảm kích thước model)
4. ✅ **Bật TensorRT** (tăng tốc độ inference)
5. ✅ **Bật frame cache** (giảm xử lý lặp lại)
6. ✅ **Sử dụng multi-threading** (tận dụng CPU/GPU)
7. ✅ **Bật temporal smoothing** (giảm false positive)
8. ✅ **Ưu tiên xử lý vật thể quan trọng** (người, xe, biển báo)

Với các tối ưu trên, **Jetson Nano có thể đạt 30-40 FPS với latency < 50ms**, đáp ứng yêu cầu real-time cho **RoadWatch Copilot**.

---

**🚀 Chúc bạn triển khai thành công!**
