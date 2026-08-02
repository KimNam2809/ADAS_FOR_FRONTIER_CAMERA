# 🚗 RoadWatch Copilot - ADAS Object Detection Module

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Jetson Nano](https://img.shields.io/badge/Jetson-Nano-green)](https://developer.nvidia.com/embedded/jetson-nano)
[![YOLOv8](https://img.shields.io/badge/YOLO-v8-orange)](https://github.com/ultralytics/ultralytics)
[![ONNX](https://img.shields.io/badge/ONNX-Runtime-purple)](https://onnxruntime.ai/)
[![TensorRT](https://img.shields.io/badge/TensorRT-8.5-green)](https://developer.nvidia.com/tensorrt)

---

## **📌 Giới Thiệu**

**RoadWatch Copilot** là **Trợ lý cảnh báo hỗ trợ lái (ADAS) đa phương thức trên Edge**, được thiết kế đặc biệt cho **NVIDIA Jetson Nano** và các thiết bị Edge khác. Module **Object Detection** này sử dụng **YOLOv8-nano** với **ONNX Runtime** và **TensorRT** để phát hiện các vật thể trên đường như **người, xe ô tô, xe máy, xe bus, xe tải, biển báo giao thông** với **độ trễ thấp (< 50ms)** và **hiệu suất cao (≥ 30 FPS)**.

### **🎯 Đặc Điểm Chính**
✅ **Real-time Object Detection** - Phát hiện vật thể trong thời gian thực
✅ **Optimized for Edge Devices** - Tối ưu cho Jetson Nano, AWS EC2, Laptop AMD
✅ **Low Latency** - Độ trễ xử lý **< 50ms**
✅ **High Performance** - Hiệu suất **≥ 30 FPS** trên Jetson Nano
✅ **Resource Efficient** - Tối ưu sử dụng CPU, GPU, RAM
✅ **Multi-Platform Support** - Hỗ trợ ARM64 (Jetson) và x86_64 (AWS/Laptop)
✅ **Priority-Based Alerts** - Cảnh báo ưu tiên theo mức độ nguy hiểm
✅ **Temporal Smoothing** - Làm mượt kết quả giảm false positive
✅ **TensorRT Acceleration** - Tăng tốc inference với TensorRT
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
│   ├── DEPLOYMENT_GUIDE.md     # Hướng dẫn triển khai
│   └── OPTIMIZATION_GUIDE.md   # Hướng dẫn tối ưu
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Multi-arch Docker
├── .gitignore
└── README.md                   # Tài liệu này
```

---

## **🚀 Bắt Đầu Nhanh**

### **📋 Yêu Cầu Hệ Thống**

| **Nền Tảng** | **OS** | **CPU** | **GPU** | **RAM** | **Storage** |
|--------------|--------|---------|---------|---------|-------------|
| **Jetson Nano** | Ubuntu 20.04 (ARM64) | Quad-core ARM Cortex-A57 | NVIDIA Maxwell (128 CUDA Cores) | 4GB | 16GB+ |
| **AWS EC2 G5G** | Ubuntu 22.04 (x86_64) | Intel Xeon (4 vCPU) | NVIDIA T4G (2560 CUDA Cores) | 16GB | 60GB+ |
| **Laptop AMD** | Ubuntu 22.04 / Windows 11 | AMD Ryzen 7+ | AMD Radeon 680M+ | 16GB | 512GB+ |

### **💻 Cài Đặt**

#### **1. Clone Repository**
```bash
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection
```

#### **2. Cài Đặt Dependencies**

##### **Cho Jetson Nano (ARM64)**
```bash
# Cài Python 3.8+
sudo apt update
sudo apt install -y python3.8 python3.8-venv python3.8-dev python3-pip

# Cài OpenCV
sudo apt install -y python3-opencv

# Cài PyTorch cho Jetson (ARM64)
pip install torch==2.0.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html

# Cài các thư viện khác
pip install -r requirements.txt
```

##### **Cho AWS EC2 / Laptop (x86_64)**
```bash
# Cài Python 3.10+
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# Cài CUDA 11.8 (cho AWS EC2)
# Xem chi tiết trong DEPLOYMENT_GUIDE.md

# Tạo virtual environment
python3.10 -m venv ~/adas_venv
source ~/adas_venv/bin/activate

# Cài dependencies
pip install --upgrade pip
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2 -f https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

##### **Cho Laptop AMD (ROCm)**
```bash
# Cài ROCm 5.7+
wget https://repo.radeon.com/amdgpu-install/5.7/ubuntu/jammy/amdgpu-install_5.7.50700-1_all.deb
sudo apt install ./amdgpu-install_5.7.50700-1_all.deb
sudo amdgpu-install --usecase=rocm,hip,mllib --no-dkms

# Cài ONNX Runtime cho ROCm
pip install onnxruntime-rocm

# Cài các thư viện khác
pip install -r requirements.txt
```

---

## **⚡ Chạy Demo Nhanh**

### **🎥 Chạy Với Camera (Real-time)**

```bash
python -c "
import cv2
from src.detection import DetectorFactory

# Tạo detector tối ưu cho thiết bị của bạn
# Thay 'jetson_nano' bằng 'aws_g5g' hoặc 'laptop_amd' nếu cần
detector = DetectorFactory.create_detector(
    device_type='jetson_nano',
    use_tensorrt=True,
    target_fps=30
)

# Mở camera (sử dụng camera 0)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Phát hiện vật thể
    result = detector.detect(frame)
    
    # Vẽ kết quả lên frame
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        color = (0, 255, 0) if det.is_priority else (255, 0, 0)
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        cv2.putText(
            frame, 
            f'{det.class_name} {det.confidence:.2f}', 
            (int(x1), int(y1)-10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            color, 
            2
        )
    
    # Hiển thị FPS và Latency
    cv2.putText(frame, f'FPS: {result.fps:.1f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Latency: {result.latency:.1f}ms', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Hiển thị
    cv2.imshow('RoadWatch Copilot - Object Detection', frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
"
```

**💡 Lệnh rút gọn:**
```bash
# Chạy script demo camera
python examples/demo_camera.py
```

---

### **📹 Chạy Với Video**

```bash
python -c "
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(device_type='jetson_nano')

# Mở video (thay 'test_video.mp4' bằng đường dẫn video của bạn)
cap = cv2.VideoCapture('test_video.mp4')

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # Phát hiện vật thể
    result = detector.detect(frame)
    
    # Vẽ kết quả
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        color = (0, 255, 0) if det.is_priority else (255, 0, 0)
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
        cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Hiển thị
    cv2.imshow('RoadWatch Copilot - Object Detection', frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
"
```

---

### **🖼️ Chạy Với Ảnh Tĩnh**

```bash
python -c "
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(device_type='jetson_nano')

# Đọc ảnh
frame = cv2.imread('test_image.jpg')

# Phát hiện vật thể
result = detector.detect(frame)

# Vẽ kết quả
for det in result.detections:
    x1, y1, x2, y2 = det.bbox
    color = (0, 255, 0) if det.is_priority else (255, 0, 0)
    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
    cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

# Hiển thị
cv2.imshow('RoadWatch Copilot - Object Detection', frame)
cv2.waitKey(0)
cv2.destroyAllWindows()

# In kết quả
print(f'Phát hiện {len(result.detections)} vật thể')
print(f'FPS: {result.fps:.2f}')
print(f'Latency: {result.latency:.2f}ms')
for det in result.detections:
    print(f'  - {det.class_name}: {det.confidence:.2f}')
"
```

---

## **🎛️ Cấu Hình Nâng Cao**

### **1. Cấu Hình Detector**

```python
from src.config import DetectorConfig
from src.detection import YOLODetector

# Tạo cấu hình tùy chỉnh
config = DetectorConfig(
    model_type="yolov8n",          # Model: n, s, m, l, x
    model_path="models/yolov8n.onnx",
    engine_path="models/yolov8n.engine",
    conf_threshold=0.5,           # Ngưỡng confidence (0-1)
    iou_threshold=0.45,           # Ngưỡng IoU cho NMS
    input_size=320,               # Kích thước input (320, 480, 640)
    use_tensorrt=True,            # Sử dụng TensorRT
    use_half_precision=True,      # Sử dụng FP16
    use_int8=False,               # Sử dụng INT8
    batch_size=1,                 # Batch size
    target_classes=["person", "car", "motorcycle", "bus", "truck", "stop sign", "traffic light"]
)

# Tạo detector
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
    enable_batch_processing=False,  # Xử lý batch
    num_inference_threads=1,    # Số luồng inference
    priority_classes=["person", "car", "motorcycle"]  # Class ưu tiên
)
```

---

### **3. Cấu Hình Cho Từng Thiết Bị**

#### **Jetson Nano (ARM64)**
```python
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(
    device_type="jetson_nano",
    use_tensorrt=True,
    target_fps=30
)
```

#### **AWS EC2 G5G.xlarge (x86_64)**
```python
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(
    device_type="aws_g5g",
    use_tensorrt=True,
    target_fps=60
)
```

#### **Laptop AMD (x86_64)**
```python
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(
    device_type="laptop_amd",
    use_tensorrt=False,  # Không hỗ trợ TensorRT trên AMD
    target_fps=30
)
```

---

## **📊 Hiệu Suất Dự Kiến**

| **Thiết Bị** | **Model** | **Input Size** | **Precision** | **FPS** | **Latency** | **Memory** | **GPU Usage** |
|--------------|-----------|---------------|--------------|---------|------------|-----------|--------------|
| **Jetson Nano** | YOLOv8n | 320x320 | FP16 | **35-40** | **25-30ms** | ~1.5GB | ~80-90% |
| **Jetson Nano** | YOLOv8n | 320x320 | INT8 | **40-45** | **20-25ms** | ~1.2GB | ~85-95% |
| **AWS G5G** | YOLOv8s | 640x640 | FP16 | **80-100** | **10-20ms** | ~3GB | ~70-80% |
| **Laptop AMD** | YOLOv8s | 640x640 | FP32 | **20-30** | **30-50ms** | ~2GB | ~60-70% |

---

## **🔧 Tối Ưu Hóa**

### **1. Build TensorRT Engine**

```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()

# Build TensorRT engine từ ONNX
engine_path = optimizer.optimize_for_tensorrt(
    onnx_path='models/yolov8n.onnx',
    engine_path='models/yolov8n.engine',
    fp16_mode=True,      # Bật FP16
    int8_mode=False,     # Tắt INT8 (nếu không có calibration data)
    max_batch_size=1     # Batch size tối đa
)
```

---

### **2. Quantization (Lượng Tử Hóa)**

```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()

# Quantize sang FP16
fp16_model = optimizer.quantize_onnx(
    onnx_path='models/yolov8n.onnx',
    quantization_type='fp16'
)

# Quantize sang INT8 (cần calibration data)
# int8_model = optimizer.quantize_onnx(
#     onnx_path='models/yolov8n.onnx',
#     quantization_type='int8',
#     calibration_data=calibration_images
# )
```

---

### **3. Export Model Từ PyTorch**

```python
import torch
from src.utils import ModelOptimizer

# Load model YOLOv8
model = torch.hub.load('ultralytics/yolov8', 'yolov8n')

# Export sang ONNX
optimizer = ModelOptimizer()
onnx_path = optimizer.export_to_onnx(
    model,
    input_shape=(1, 3, 320, 320),  # Batch, Channels, Height, Width
    onnx_path='models/yolov8n.onnx'
)
```

---

## **📦 Download Model**

### **Tùy Chọn 1: Download Model Đã Train Sẵn**

```bash
# Tạo thư mục models
mkdir -p models

# Download YOLOv8n ONNX (khuyến nghị cho Jetson Nano)
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx

# Download YOLOv8s ONNX (cho AWS/Laptop)
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8s.onnx -O models/yolov8s.onnx
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
python -m pytest tests/test_detector.py -v

# Chạy test với coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

## **🐳 Docker Deployment**

### **1. Build Docker Image**

```bash
# Build cho ARM64 (Jetson Nano)
docker build --platform linux/arm64 -t adas-copilot:arm64 .

# Build cho x86_64 (AWS/Laptop)
docker build --platform linux/amd64 -t adas-copilot:amd64 .

# Build multi-arch (cả ARM64 và x86_64)
docker buildx build --platform linux/arm64,linux/amd64 -t adas-copilot:multiarch --push .
```

### **2. Chạy Docker Container**

```bash
# Chạy trên Jetson Nano (ARM64)
docker run --runtime nvidia --rm -p 8000:8000 adas-copilot:arm64

# Chạy trên AWS/Laptop (x86_64)
docker run --gpus all --rm -p 8000:8000 adas-copilot:amd64
```

---

## **📚 Tài Liệu Chi Tiết**

| **Tài Liệu** | **Mô Tả** | **Link** |
|--------------|-----------|----------|
| **Deployment Guide** | Hướng dẫn triển khai chi tiết | [📖 DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) |
| **Optimization Guide** | Hướng dẫn tối ưu hiệu suất | [📖 OPTIMIZATION_GUIDE.md](docs/OPTIMIZATION_GUIDE.md) |
| **Ultralytics YOLOv8** | Tài liệu YOLOv8 | [🔗 Ultralytics Docs](https://docs.ultralytics.com/) |
| **ONNX Runtime** | Tài liệu ONNX Runtime | [🔗 ONNX Runtime Docs](https://onnxruntime.ai/) |
| **TensorRT** | Tài liệu TensorRT | [🔗 TensorRT Docs](https://developer.nvidia.com/tensorrt) |

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

Dự án này được cấp phép theo **MIT License** - xem file [LICENSE](LICENSE) để biết chi tiết.

---

## **🙏 Cảm Ơn**

Cảm ơn bạn đã sử dụng **RoadWatch Copilot**! Nếu bạn có bất kỳ câu hỏi hoặc góp ý, vui lòng liên hệ:

- **Email**: [your-email@example.com](mailto:your-email@example.com)
- **GitHub Issues**: [🐛 Issues](https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA/issues)
- **Discussions**: [💬 Discussions](https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA/discussions)

---

## **⭐ Star Repository**

Nếu bạn thấy dự án hữu ích, hãy **⭐ Star** repository để ủng hộ chúng tôi!

[![Star on GitHub](https://img.shields.io/github/stars/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.svg?style=social)](https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA/stargazers)

---

**🚀 Happy Coding!**
