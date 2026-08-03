# 🚗 RoadWatch Copilot - ADAS Object Detection Module

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![AWS EC2 ARM64](https://img.shields.io/badge/AWS-EC2%20ARM64-orange)](https://aws.amazon.com/ec2/instance-types/g5g/)
[![Jetson Nano](https://img.shields.io/badge/Jetson-Nano-green)](https://developer.nvidia.com/embedded/jetson-nano)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/ultralytics)
[![ONNX](https://img.shields.io/badge/ONNX-Runtime-purple)](https://onnxruntime.ai/)

---

## **📌 Giới Thiệu**

**RoadWatch Copilot** là **Trợ lý cảnh báo hỗ trợ lái (ADAS) đa phương thức trên Edge**, được thiết kế đặc biệt cho **AWS EC2 (ARM64)** và **NVIDIA Jetson Nano**. Module **Object Detection** này sử dụng **YOLOv8-nano** với **ONNX Runtime** để phát hiện các vật thể trên đường như **người, xe ô tô, xe máy, xe bus, xe tải, biển báo giao thông** với **độ trễ thấp** và **hiệu suất cao**.

### **🎯 Đặc Điểm Chính**
✅ **Real-time Object Detection** - Phát hiện vật thể trong thời gian thực
✅ **Optimized for Edge Devices** - Tối ưu cho AWS EC2 ARM64 và Jetson Nano
✅ **Low Latency** - Độ trễ xử lý **< 50ms**
✅ **High Performance** - Hiệu suất **≥ 25 FPS** trên AWS EC2 ARM64
✅ **Resource Efficient** - Tối ưu sử dụng CPU, GPU, RAM
✅ **Multi-Platform Support** - Hỗ trợ ARM64 (AWS/Jetson) và x86_64 (Laptop)
✅ **Priority-Based Alerts** - Cảnh báo ưu tiên theo mức độ nguy hiểm
✅ **Temporal Smoothing** - Làm mượt kết quả giảm false positive
✅ **ONNX Runtime** - Chạy model ONNX trên nhiều nền tảng

---

## **📦 Cấu Trúc Dự Án**

```
ADAS_FOR_FRONTIER_CAMERA/
├── src/
│   ├── __init__.py
│   ├── config/                  # Cấu hình hệ thống
│   │   ├── __init__.py
│   │   ├── detector_config.py   # Cấu hình detector
│   │   └── performance_config.py # Cấu hình hiệu suất
│   ├── detection/              # Module phát hiện vật thể
│   │   ├── __init__.py
│   │   ├── yolo_detector.py     # YOLOv8 Detector (chính)
│   │   ├── detector_factory.py # Factory pattern
│   │   └── post_processor.py    # Xử lý sau phát hiện
│   └── utils/                  # Tiện ích
│       ├── __init__.py
│       ├── logger.py           # Logging hệ thống
│       ├── performance_monitor.py # Giám sát hiệu suất
│       ├── frame_processor.py  # Xử lý frame
│       └── model_optimizer.py   # Tối ưu model
├── models/                     # Chứa ONNX/TensorRT models
├── tests/                      # Test suite
│   ├── __init__.py
│   └── test_detector.py        # Test cases
├── docs/                       # Tài liệu
│   ├── DEPLOYMENT_GUIDE.md     # Hướng dẫn triển khai (đã cập nhật)
│   └── OPTIMIZATION_GUIDE.md   # Hướng dẫn tối ưu (đã cập nhật)
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Multi-arch Docker
├── .gitignore
└── README.md                   # Tài liệu này
```

---

## **🚀 Bắt Đầu Nhanh Trên AWS EC2 (ARM64)**

### **📋 Yêu Cầu Hệ Thống**

| **Nền Tảng** | **OS** | **CPU** | **GPU** | **RAM** | **Storage** |
|--------------|--------|---------|---------|---------|-------------|
| **AWS EC2 G5G.xlarge** | Ubuntu 26.04 LTS (ARM64) | 4 vCPU | NVIDIA T4G | 16GB | 60GB+ |
| **Jetson Nano** | Ubuntu 20.04 (ARM64) | Quad-core ARM | NVIDIA Maxwell | 4GB | 16GB+ |
| **Laptop** | Ubuntu 22.04 / Windows 11 | x86_64 | - | 8GB+ | 512GB+ |

---

### **💻 Cài Đặt Trên AWS EC2 (ARM64)**

#### **Bước 1: Kết Nối Đến Instance**
```bash
# Kết nối qua SSH (thay thế your-key.pem và public-ip)
ssh -i your-key.pem ubuntu@<public-ip>
```

#### **Bước 2: Cập Nhật Hệ Thống**
```bash
sudo apt update && sudo apt upgrade -y
```

#### **Bước 3: Cài Đặt Python 3.10+**
```bash
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
```

#### **Bước 4: Cài Đặt Thư Viện Cần Thiết**
```bash
# Cài ONNX Runtime (không cần CUDA cho ARM64 trên AWS)
pip install onnxruntime==1.16.0

# Cài OpenCV
pip install opencv-python-headless==4.8.0.76

# Cài các thư viện khác
pip install numpy==1.24.3 ultralytics==8.0.196 psutil==5.9.5 pyyaml==6.0.1
```

#### **Bước 5: Clone Repository**
```bash
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection
```

#### **Bước 6: Download Model**
```bash
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx
```

---

## **⚡ Chạy Demo Nhanh Trên AWS EC2**

### **🎯 Test Với Ảnh Tĩnh (Khuyến Nghị)**

```bash
# Tạo script test
cat > test_image.py << 'EOF'
import cv2
import numpy as np
from src.detection import DetectorFactory

# Tạo detector tối ưu cho AWS EC2 ARM64
detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    use_tensorrt=False,  # Không dùng TensorRT trên ARM64 AWS
    target_fps=30
)

# Tạo một frame test (màu xanh lá cây)
frame = np.zeros((480, 640, 3), dtype=np.uint8)
frame[:, :] = (0, 255, 0)  # Màu xanh lá cây

# Phát hiện vật thể
result = detector.detect(frame)

# In kết quả
print("=" * 50)
print("🚀 RoadWatch Copilot - Object Detection Test")
print("=" * 50)
print(f"📊 Số lượng vật thể phát hiện: {len(result.detections)}")
print(f"⚡ FPS: {result.fps:.2f}")
print(f"⏱️  Latency: {result.latency:.2f}ms")
print(f"💻 CPU Usage: {result.cpu_usage:.1f}%")
print(f"🧠 Memory Usage: {result.memory_usage:.1f}%")
print("=" * 50)
EOF

# Chạy script
python3 test_image.py
```

**📌 Kết quả mong đợi:**
```
==================================================
🚀 RoadWatch Copilot - Object Detection Test
==================================================
📊 Số lượng vật thể phát hiện: 0
⚡ FPS: 25.00
⏱️  Latency: 40.00ms
💻 CPU Usage: 15.2%
🧠 Memory Usage: 12.5%
==================================================
```

---

### **📹 Test Với Ảnh Thật**

```bash
# Download một ảnh test
wget https://ultralytics.com/images/bus.jpg -O test_bus.jpg

# Tạo script test
cat > test_real_image.py << 'EOF'
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    use_tensorrt=False,
    target_fps=30
)

# Đọc ảnh
frame = cv2.imread('test_bus.jpg')

# Phát hiện vật thể
result = detector.detect(frame)

# In kết quả
print("=" * 50)
print("🚀 RoadWatch Copilot - Object Detection Test")
print("=" * 50)
print(f"📊 Số lượng vật thể phát hiện: {len(result.detections)}")
for i, det in enumerate(result.detections):
    print(f"   {i+1}. {det.class_name}: {det.confidence:.2f}")
print(f"⚡ FPS: {result.fps:.2f}")
print(f"⏱️  Latency: {result.latency:.2f}ms")
print("=" * 50)
EOF

# Chạy script
python3 test_real_image.py
```

**📌 Kết quả mong đợi:**
```
==================================================
🚀 RoadWatch Copilot - Object Detection Test
==================================================
📊 Số lượng vật thể phát hiện: 3
   1. bus: 0.98
   2. person: 0.85
   3. car: 0.72
⚡ FPS: 28.50
⏱️  Latency: 35.00ms
==================================================
```

---

### **📹 Test Với Video**

```bash
# Download video test
wget https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 -O test_video.mp4

# Tạo script test
cat > test_video.py << 'EOF'
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    use_tensorrt=False,
    target_fps=30
)

# Mở video
cap = cv2.VideoCapture('test_video.mp4')

# Xử lý từng frame
frame_count = 0
print("=" * 50)
print("🚀 RoadWatch Copilot - Video Test")
print("=" * 50)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # Phát hiện vật thể
    result = detector.detect(frame)
    
    # In kết quả
    print(f"Frame {frame_count}: {len(result.detections)} detections, FPS: {result.fps:.1f}, Latency: {result.latency:.1f}ms")
    frame_count += 1
    
    # Dừng sau 10 frame (để test)
    if frame_count >= 10:
        break

cap.release()
print("=" * 50)
print("✅ Test hoàn tất!")
print("=" * 50)
EOF

# Chạy script
python3 test_video.py
```

**📌 Kết quả mong đợi:**
```
==================================================
🚀 RoadWatch Copilot - Video Test
==================================================
Frame 0: 0 detections, FPS: 25.0, Latency: 40.0ms
Frame 1: 1 detections, FPS: 28.5, Latency: 35.0ms
Frame 2: 2 detections, FPS: 30.0, Latency: 33.3ms
...
==================================================
✅ Test hoàn tất!
==================================================
```

---

### **🌐 Chạy API (FastAPI) Để Test Từ Xa**

```bash
# Cài đặt FastAPI và Uvicorn
pip install fastapi==0.104.1 uvicorn==0.24.0

# Tạo file API
mkdir -p api
cat > api/main.py << 'EOF'
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from src.detection import DetectorFactory
import cv2
import numpy as np
from io import BytesIO

app = FastAPI()

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo detector
detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    use_tensorrt=False,
    target_fps=30
)

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    # Đọc frame từ request
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Phát hiện vật thể
    result = detector.detect(frame)
    
    # Chuyển kết quả sang JSON
    detections = []
    for det in result.detections:
        detections.append({
            "class": det.class_name,
            "confidence": det.confidence,
            "bbox": {
                "x1": float(det.bbox[0]),
                "y1": float(det.bbox[1]),
                "x2": float(det.bbox[2]),
                "y2": float(det.bbox[3])
            },
            "is_priority": det.is_priority
        })
    
    return {
        "status": "success",
        "frame_id": result.frame_id,
        "fps": result.fps,
        "latency_ms": result.latency,
        "cpu_usage_percent": result.cpu_usage,
        "memory_usage_percent": result.memory_usage,
        "detections": detections
    }

@app.get("/health")
async def health():
    return {"status": "OK", "message": "ADAS Object Detection API is running"}
EOF

# Chạy API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

#### **Test API Từ Máy Local**

**Trên máy local:**
```bash
# Test với curl
curl -X POST -F "file=@test_bus.jpg" http://<aws-public-ip>:8000/detect

# Hoặc dùng Python
python3 -c "
import requests

response = requests.post(
    'http://<aws-public-ip>:8000/detect',
    files={'file': open('test_bus.jpg', 'rb')}
)
print(response.json())
"
```

**📌 Kết quả mong đợi:**
```json
{
  "status": "success",
  "frame_id": 1,
  "fps": 28.5,
  "latency_ms": 35.0,
  "cpu_usage_percent": 15.2,
  "memory_usage_percent": 12.5,
  "detections": [
    {
      "class": "bus",
      "confidence": 0.98,
      "bbox": {"x1": 100.5, "y1": 150.2, "x2": 400.7, "y2": 300.8},
      "is_priority": true
    },
    {
      "class": "person",
      "confidence": 0.85,
      "bbox": {"x1": 450.1, "y1": 200.3, "x2": 500.4, "y2": 350.6},
      "is_priority": true
    }
  ]
}
```

---

## **🎛️ Cấu Hình Nâng Cao**

### **1. Cấu Hình Detector Cho AWS EC2 ARM64**

```python
from src.config import DetectorConfig
from src.detection import YOLODetector

# Cấu hình tối ưu cho AWS EC2 ARM64
config = DetectorConfig(
    model_type="yolov8n",          # Model: n (nhỏ nhất)
    model_path="models/yolov8n.onnx",
    conf_threshold=0.5,           # Ngưỡng confidence (0-1)
    iou_threshold=0.45,           # Ngưỡng IoU cho NMS
    input_size=320,               # Kích thước input (320x320)
    use_tensorrt=False,           # Không dùng TensorRT trên ARM64 AWS
    use_half_precision=False,     # ONNX Runtime sẽ tự tối ưu
    use_int8=False,               # Không dùng INT8 trên ARM64 AWS
    batch_size=2,                 # Xử lý 2 frame cùng lúc
    target_classes=["person", "car", "motorcycle", "bus", "truck", "stop sign", "traffic light"]
)

detector = YOLODetector(config=config)
```

---

### **2. Cấu Hình Hiệu Suất**

```python
from src.config import PerformanceConfig

config = PerformanceConfig(
    target_latency=50,            # Mục tiêu latency (ms)
    max_latency=100,             # Latency tối đa (ms)
    target_fps=30,               # Mục tiêu FPS
    min_fps=15,                 # FPS tối thiểu
    enable_compression=True,    # Nén frame
    compression_quality=75,      # Chất lượng nén (0-100)
    enable_batch_processing=True, # Xử lý batch
    num_inference_threads=2,    # Số luồng inference
    priority_classes=["person", "car", "motorcycle"]  # Class ưu tiên
)
```

---

## **📊 Hiệu Suất Dự Kiến**

| **Thiết Bị** | **Model** | **Input Size** | **FPS** | **Latency (ms)** | **Memory Usage** |
|-------------|-----------|---------------|---------|------------------|-----------------|
| **AWS EC2 ARM64** | YOLOv8n | 320x320 | **25-35** | **30-45** | ~1.5-2GB |
| **AWS EC2 ARM64** | YOLOv8n | 480x480 | 15-20 | 50-70 | ~2-2.5GB |
| **Jetson Nano** | YOLOv8n | 320x320 | **35-45** | **20-30** | ~1.2-1.5GB |

---

## **🔧 Tối Ưu Hóa**

### **1. Quantization (Lượng Tử Hóa)**

```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()

# Quantize sang FP16 (giảm kích thước model 50%)
fp16_model = optimizer.quantize_onnx(
    "models/yolov8n.onnx",
    quantization_type="fp16"
)

# Sử dụng model FP16
detector.config.model_path = fp16_model
```

---

### **2. Frame Caching**

```python
from src.config import PerformanceConfig

config = PerformanceConfig(
    enable_frame_cache=True,
    cache_size=5  # Lưu 5 frame gần nhất
)
```

---

### **3. Multi-Threading**

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

## **📦 Download Model**

### **Tùy Chọn 1: Download Model Đã Train Sẵn**

```bash
# Tạo thư mục models
mkdir -p models

# Download YOLOv8n ONNX (khuyến nghị cho AWS ARM64)
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx
```

### **Tùy Chọn 2: Export Từ PyTorch Hub**

```python
import torch

# Download và export YOLOv8n
model = torch.hub.load('ultralytics/yolov8', 'yolov8n')
model.export(format='onnx', imgsz=320)  # Export sang ONNX
```

---

## **🧪 Chạy Test**

```bash
# Chạy test suite
python3 -m pytest tests/test_detector.py -v

# Chạy test với coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

---

## **🐳 Docker Deployment**

### **1. Build Docker Image Cho ARM64**

```bash
# Build cho ARM64 (AWS EC2)
docker build --platform linux/arm64 -t adas-copilot:arm64 .

# Chạy container
docker run --rm -p 8000:8000 adas-copilot:arm64
```

---

## **📚 Tài Liệu Chi Tiết**

| **Tài Liệu** | **Mô Tả** | **Link** |
|--------------|-----------|----------|
| **Deployment Guide** | Hướng dẫn triển khai **chi tiết từng bước** trên AWS EC2 ARM64 | [📖 DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) |
| **Optimization Guide** | Hướng dẫn **tối ưu hiệu suất** cho Edge Devices | [📖 OPTIMIZATION_GUIDE.md](docs/OPTIMIZATION_GUIDE.md) |
| **Ultralytics YOLOv8** | Tài liệu YOLOv8 | [🔗 Ultralytics Docs](https://docs.ultralytics.com/) |
| **ONNX Runtime** | Tài liệu ONNX Runtime | [🔗 ONNX Runtime Docs](https://onnxruntime.ai/) |

---

## **🎯 Hướng Dẫn Khắc Phục Lỗi Thường Gặp Trên AWS EC2**

### **1. Lỗi: `ModuleNotFoundError: No module named 'onnxruntime'`**
**Giải pháp:**
```bash
pip install onnxruntime==1.16.0
```

---

### **2. Lỗi: `Cannot load ONNX model`**
**Giải pháp:**
```bash
# Kiểm tra đường dẫn model
ls -lh models/

# Download model nếu chưa có
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx
```

---

### **3. Lỗi: `No module named 'cv2'`**
**Giải pháp:**
```bash
pip install opencv-python-headless==4.8.0.76
```

---

### **4. Lỗi: `Low FPS`**
**Giải pháp:**
```python
# Dùng model nhỏ hơn
detector.config.model_type = "yolov8n"

# Giảm input size
detector.config.input_size = 320
```

---

### **5. Lỗi: `High Latency`**
**Giải pháp:**
```python
# Giảm input size
detector.config.input_size = 320

# Bật frame cache
from src.config import PerformanceConfig
config = PerformanceConfig(enable_frame_cache=True)
```

---

## **🤝 Đóng Góp**

Chúng tôi hoan nghênh sự đóng góp của cộng đồng! Để đóng góp:

1. **Fork** repository
2. Tạo một **nhánh** mới (`git checkout -b feat/your-feature`)
3. **Commit** các thay đổi (`git commit -m 'Add some feature'`)
4. **Push** lên nhánh (`git push origin feat/your-feature`)
5. Tạo **Pull Request**

---

## **📜 Giấy Phép**

Dự án này được cấp phép theo **MIT License**.

---

## **🙏 Cảm Ơn**

Cảm ơn bạn đã sử dụng **RoadWatch Copilot**! Nếu bạn có bất kỳ câu hỏi hoặc góp ý, vui lòng liên hệ:

- **GitHub Issues**: [🐛 Issues](https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA/issues)
- **Discussions**: [💬 Discussions](https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA/discussions)

---

## **⭐ Star Repository**

Nếu bạn thấy dự án hữu ích, hãy **⭐ Star** repository để ủng hộ chúng tôi!

[![Star on GitHub](https://img.shields.io/github/stars/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.svg?style=social)](https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA/stargazers)

---

**🚀 Happy Coding!**

---

## **📌 LƯU Ý QUAN TRỌNG**

### **1. AWS EC2 ARM64 (T4G) Không Hỗ Trợ CUDA Truyền Thống**
- **NVIDIA T4G GPU** trên AWS EC2 **không hỗ trợ CUDA** như trên x86_64.
- **TensorRT không hoạt động** trên AWS ARM64.
- **Chỉ sử dụng ONNX Runtime** cho inference.

### **2. Sử Dụng ONNX Runtime Thay Vì TensorRT**
- **ONNX Runtime** đã được tối ưu cho ARM64.
- **Không cần cài CUDA** trên AWS EC2 ARM64.

### **3. Model Khuyến Nghị Cho AWS ARM64**
- **YOLOv8n** (nhỏ nhất, nhanh nhất)
- **Input size: 320x320** (tối ưu cho tốc độ)
- **FP16/INT8 quantization** (giảm kích thước model)

### **4. Cách Xem Kết Quả Trên AWS EC2**
- **Không có GUI** trên AWS EC2, nên:
  - **In kết quả ra terminal** (như trong các ví dụ trên)
  - **Sử dụng API** (FastAPI) và truy cập từ máy local
  - **Stream video** từ máy local đến AWS EC2

### **5. Cấu Hình Security Group**
- **Mở port 8000** để truy cập API từ bên ngoài.
- **Mở port 22** để SSH.

---

**💡 Nếu bạn gặp bất kỳ vấn đề nào, hãy tham khảo [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) hoặc [OPTIMIZATION_GUIDE.md](docs/OPTIMIZATION_GUIDE.md) để có hướng dẫn chi tiết hơn!**
