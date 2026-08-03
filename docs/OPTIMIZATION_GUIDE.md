# 🚀 ADAS Object Detection Optimization Guide for Edge Devices

## **Mục Lục**
1. [Giới Thiệu](#giới-thiệu)
2. [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
3. [Tối Ưu Hóa Độ Trễ (Latency)](#tối-ưu-hóa-độ-trễ-latency)
4. [Tối Ưu Hóa Băng Thông và Tài Nguyên](#tối-ưu-hóa-băng-thông-và-tài-nguyên)
5. [Cải Thiện Hiệu Suất và Trải Nghiệm Người Dùng](#cải-thiện-hiệu-suất-và-trải-nghiệm-người-dùng)
6. [Cấu Hình Cho AWS EC2 (ARM64)](#cấu-hình-cho-aws-ec2-arm64)
7. [Cấu Hình Cho Jetson Nano](#cấu-hình-cho-jetson-nano)
8. [Benchmark và Đánh Giá](#benchmark-và-đánh-giá)
9. [Khắc Phục Sự Cố](#khắc-phục-sự-cố)

---

## **📌 Giới Thiệu**

Module **Object Detection** của **RoadWatch Copilot** được thiết kế đặc biệt cho **Edge Devices** (như AWS EC2 ARM64, Jetson Nano) với mục tiêu:

✅ **Giảm độ trễ** (Latency < 50ms)
✅ **Tối ưu băng thông và tài nguyên** (CPU/GPU/Memory)
✅ **Cải thiện hiệu suất** (FPS ≥ 25)
✅ **Trải nghiệm người dùng mượt mà**

Module sử dụng **YOLOv8-nano** với **ONNX Runtime** để đạt hiệu suất tối ưu trên **AWS EC2 G5G.xlarge (ARM64)**.

---

## **💻 Yêu Cầu Hệ Thống**

### **1. AWS EC2 G5G.xlarge (ARM64)**
| **Thông Số** | **Giá Trị** | **Ghi Chú** |
|--------------|------------|-------------|
| **CPU** | 4 vCPU (ARM64) | |
| **GPU** | NVIDIA T4G (Ampere) | Không hỗ trợ CUDA truyền thống |
| **RAM** | 16GB | |
| **VRAM** | 8GB | |
| **Storage** | 60GB GP3 SSD | |
| **OS** | Ubuntu 26.04 LTS (ARM64) | |
| **ONNX Runtime** | 1.16.0+ | Chạy trên CPU/GPU |

### **2. Jetson Nano (ARM64)**
| **Thông Số** | **Giá Trị** | **Ghi Chú** |
|--------------|------------|-------------|
| **CPU** | Quad-core ARM Cortex-A57 @ 1.43 GHz | |
| **GPU** | NVIDIA Maxwell (128 CUDA Cores) | Hỗ trợ CUDA 10.2 |
| **RAM** | 4GB LPDDR4 | Shared với GPU |
| **OS** | Ubuntu 20.04 (ARM64) | JetPack 5.1.2 |
| **TensorRT** | 8.5.3 | |

---

## **⚡ Tối Ưu Hóa Độ Trễ (Latency)**

### **🎯 Mục Tiêu: Latency < 50ms**

### **🔧 Các Kỹ Thuật Tối Ưu**

#### **1. Chọn Model Phù Hợp**

| **Model** | **Size (MB)** | **FPS (AWS ARM64)** | **mAP** | **Latency (ms)** | **Khuyến Nghị** |
|-----------|--------------|----------------------|---------|------------------|------------------|
| YOLOv8n | ~3.2MB | **25-35** | 0.37 | **30-45** | ✅ **Tốt nhất cho AWS ARM64** |
| YOLOv8s | ~9.2MB | 15-20 | 0.45 | 50-70 | ⚠️ Chỉ dùng nếu cần độ chính xác cao |
| YOLOv8m | ~25.2MB | 5-10 | 0.50 | 100+ | ❌ Không phù hợp |

**→ Sử dụng `YOLOv8n` cho AWS EC2 ARM64 để đạt FPS cao nhất.**

**Cách cài đặt:**
```python
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    model_type='yolov8n'  # Model nhỏ nhất
)
```

---

#### **2. Input Size Tối Ưu**

| **Input Size** | **FPS (AWS ARM64)** | **mAP** | **Latency (ms)** | **Khuyến Nghị** |
|----------------|----------------------|---------|------------------|------------------|
| 320x320 | **30-35** | 0.30 | **25-35** | ✅ **Tốt nhất cho tốc độ** |
| 480x480 | 20-25 | 0.35 | 40-50 | ⚠️ Cân bằng tốc độ/chất lượng |
| 640x640 | 10-15 | 0.37 | 60-80 | ❌ Chậm trên AWS ARM64 |

**→ Sử dụng `320x320` cho AWS EC2 ARM64 để giảm latency.**

**Cách cài đặt:**
```python
detector.config.input_size = 320
```

---

#### **3. Quantization (Lượng Tử Hóa)**

**⚠️ LƯU Ý:** Trên AWS EC2 ARM64 (T4G), **TensorRT không hỗ trợ đầy đủ**, nên chúng ta sử dụng **ONNX Runtime** với **FP16/INT8** thông qua **ONNX Runtime's optimization**.

| **Precision** | **Size (MB)** | **FPS** | **mAP Loss** | **Latency** | **Khuyến Nghị** |
|--------------|--------------|---------|--------------|-------------|------------------|
| FP32 | ~3.2MB | 25 | 0% | ~40ms | ❌ Không tối ưu |
| FP16 | ~1.6MB | **30-35** | <1% | **~30ms** | ✅ **Tốt nhất cho AWS ARM64** |
| INT8 | ~0.8MB | **35-40** | ~2-3% | **~25ms** | ✅ **Tốt nhất nếu chấp nhận mất độ chính xác nhẹ** |

**Cách bật quantization:**
```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()

# Quantize sang FP16
fp16_model = optimizer.quantize_onnx(
    "models/yolov8n.onnx",
    quantization_type="fp16"
)

# Sử dụng model FP16
detector.config.model_path = fp16_model
```

---

#### **4. ONNX Runtime Optimization**

ONNX Runtime hỗ trợ **các tối ưu sau** trên ARM64:

```python
from src.detection import YOLODetector
import onnxruntime as ort

# Cấu hình ONNX Runtime session options
options = ort.SessionOptions()
options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

# Sử dụng CPU Execution Provider (không có CUDA trên AWS ARM64)
session = ort.InferenceSession("models/yolov8n.onnx", providers=['CPUExecutionProvider'], sess_options=options)
```

---

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

# Sử dụng 2 luồng (tối ưu cho AWS ARM64)
with ThreadPoolExecutor(max_workers=2) as executor:
    results = list(executor.map(process_frame, frames))
```

---

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

---

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
| 75 | ~30% | ~90% | ✅ **Tốt nhất cho AWS ARM64** |
| 50 | ~15% | ~80% | ⚠️ Chất lượng thấp |

---

#### **2. Batch Processing**

Xử lý **nhiều frame cùng lúc** để tận dụng CPU hiệu quả.

**Cài đặt:**
```python
from src.config import DetectorConfig

config = DetectorConfig(
    batch_size=2  # Xử lý 2 frame cùng lúc (tối ưu cho AWS ARM64)
)
```

**Lưu ý:**
- **AWS ARM64**: `batch_size=2` (tối ưu)
- **Jetson Nano**: `batch_size=1` (không đủ RAM)

---

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

---

#### **4. Dynamic Resolution Scaling**

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
elif monitor.get_average_metrics().fps > 35:
    detector.config.input_size = 480  # Tăng lên 480x480
```

---

#### **5. Selective Processing**

Chỉ xử lý **các vùng quan tâm (ROI)** thay vì toàn bộ frame.

**Ví dụ:**
```python
from src.detection import YOLODetector

detector = YOLODetector()

# Chỉ xử lý 1/4 frame (góc trên bên trái)
roi = frame[0:240, 0:320]  # ROI: (y1:y2, x1:x2)
result = detector.detect(roi)
```

---

#### **6. Early Stopping**

Dừng xử lý sớm nếu **không có chuyển động**.

**Ví dụ:**
```python
from src.detection import YOLODetector

detector = YOLODetector()

# Chỉ xử lý nếu có chuyển động (sử dụng Motion Detection)
def has_motion(frame1, frame2):
    # So sánh 2 frame
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return len(contours) > 0

# Sử dụng
prev_frame = None
if prev_frame is None or has_motion(prev_frame, frame):
    result = detector.detect(frame)
    prev_frame = frame
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

---

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

# Sử dụng post-processor
context_result = post_processor.process(detection_result)
```

---

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

---

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

---

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

---

## **⚙️ Cấu Hình Cho AWS EC2 (ARM64)**

### **Cấu Hình Tối Ưu**

```python
from src.detection import DetectorFactory

# Tạo detector tối ưu cho AWS EC2 ARM64
detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    use_tensorrt=False,  # Không dùng TensorRT trên ARM64 AWS
    target_fps=30
)

# Cấu hình chi tiết
detector.config.model_type = "yolov8n"
detector.config.input_size = 320
detector.config.use_half_precision = False  # ONNX Runtime sẽ tự tối ưu
detector.config.use_int8 = False
detector.config.batch_size = 2  # Xử lý 2 frame cùng lúc
```

**Dự kiến hiệu suất:**
- **FPS**: 25-35
- **Latency**: 30-45ms
- **Memory Usage**: ~1.5-2GB
- **CPU Usage**: ~60-80%

---

## **⚙️ Cấu Hình Cho Jetson Nano**

### **Cấu Hình Tối Ưu**

```python
from src.detection import DetectorFactory

# Tạo detector tối ưu cho Jetson Nano
detector = DetectorFactory.create_detector(
    device_type='jetson_nano',
    use_tensorrt=True,  # Dùng TensorRT trên Jetson
    target_fps=30
)

# Cấu hình chi tiết
detector.config.model_type = "yolov8n"
detector.config.input_size = 320
detector.config.use_half_precision = True
detector.config.use_int8 = True  # Bật INT8 quantization
detector.config.batch_size = 1
```

**Dự kiến hiệu suất:**
- **FPS**: 35-45
- **Latency**: 20-30ms
- **Memory Usage**: ~1.2-1.5GB
- **GPU Usage**: ~80-95%

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

---

### **2. Kết Quả Dự Kiến**

| **Thiết Bị** | **Model** | **Input Size** | **Precision** | **FPS** | **Latency (ms)** | **mAP** |
|-------------|-----------|---------------|--------------|---------|------------------|---------|
| AWS ARM64 | YOLOv8n | 320x320 | FP32 | 25-30 | 33-40 | 0.37 |
| AWS ARM64 | YOLOv8n | 320x320 | FP16 | **30-35** | **30-35** | 0.36 |
| AWS ARM64 | YOLOv8n | 320x320 | INT8 | **35-40** | **25-30** | 0.34 |
| Jetson Nano | YOLOv8n | 320x320 | FP16 | **35-40** | **25-30** | 0.35 |
| Jetson Nano | YOLOv8n | 320x320 | INT8 | **40-45** | **20-25** | 0.33 |

---

## **🛠️ Khắc Phục Sự Cố**

### **1. Lỗi Thường Gặp Trên AWS EC2 (ARM64)**

#### **🔴 Lỗi: `ONNX Runtime not optimized for ARM64`**
**Nguyên nhân:** ONNX Runtime chưa được tối ưu cho ARM64.

**Giải pháp:**
```bash
# Sử dụng phiên bản ONNX Runtime mới nhất
pip install --upgrade onnxruntime
```

---

#### **🔴 Lỗi: `Low FPS on ARM64`**
**Nguyên nhân:** Model quá nặng cho ARM64.

**Giải pháp:**
```python
# Dùng model nhỏ nhất
detector.config.model_type = "yolov8n"

# Giảm input size
detector.config.input_size = 320

# Bật frame cache
detector.config.enable_frame_cache = True
```

---

#### **🔴 Lỗi: `High CPU Usage`**
**Nguyên nhân:** Xử lý quá nhiều frame cùng lúc.

**Giải pháp:**
```python
# Giảm batch size
detector.config.batch_size = 1

# Giảm số luồng
detector.config.num_inference_threads = 1
```

---

#### **🔴 Lỗi: `Out of Memory`**
**Nguyên nhân:** Model quá lớn.

**Giải pháp:**
```python
# Dùng model nhỏ hơn
detector.config.model_type = "yolov8n"

# Giảm input size
detector.config.input_size = 320
```

---

## **📚 Tài Liệu Tham Khảo**

1. [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com/)
2. [ONNX Runtime Documentation](https://onnxruntime.ai/)
3. [AWS EC2 G5G Instance Guide](https://aws.amazon.com/ec2/instance-types/g5g/)
4. [NVIDIA T4G GPU Documentation](https://docs.nvidia.com/jetson/archives/r35.1/DeveloperGuide/text/SD/Jetsons/T4GTX1.html)
5. [ONNX Runtime Performance Tuning](https://onnxruntime.ai/docs/performance/tune_performance.html)

---

## **🎯 Kết Luận**

Để đạt được **hiệu suất tối ưu** trên **AWS EC2 ARM64 (G5G.xlarge)**, bạn nên:

1. ✅ **Sử dụng YOLOv8n** (model nhỏ nhất)
2. ✅ **Input size 320x320** (giảm độ phân giải)
3. ✅ **Bật FP16/INT8 quantization** (giảm kích thước model)
4. ✅ **Sử dụng ONNX Runtime** (tối ưu cho ARM64)
5. ✅ **Bật frame cache** (giảm xử lý lặp lại)
6. ✅ **Sử dụng multi-threading** (tận dụng CPU)
7. ✅ **Bật temporal smoothing** (giảm false positive)
8. ✅ **Ưu tiên xử lý vật thể quan trọng** (người, xe, biển báo)

Với các tối ưu trên, **AWS EC2 G5G.xlarge có thể đạt 25-35 FPS với latency 30-45ms**, đáp ứng yêu cầu real-time cho **RoadWatch Copilot**.

---

**🚀 Chúc bạn tối ưu thành công!**
