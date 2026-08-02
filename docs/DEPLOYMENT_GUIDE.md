# 🚀 ADAS Object Detection Deployment Guide

## **Mục Lục**
1. [Giới Thiệu](#giới-thiệu)
2. [Yêu Cầu Trước Khi Triển Khai](#yêu-cầu-trước-khi-triển-khai)
3. [Triển Khai Trên Jetson Nano](#triển-khai-trên-jetson-nano)
4. [Triển Khai Trên AWS EC2](#triển-khai-trên-aws-ec2)
5. [Triển Khai Trên Laptop AMD](#triển-khai-trên-laptop-amd)
6. [Cấu Hình Môi Trường](#cấu-hình-môi-trường)
7. [Chạy Ứng Dụng](#chạy-ứng-dụng)
8. [Giám Sát Hiệu Suất](#giám-sát-hiệu-suất)
9. [Khắc Phục Sự Cố](#khắc-phục-sự-cố)
10. [Cập Nhật và Bảo Trì](#cập-nhật-và-bảo-trì)

---

## **📋 Giới Thiệu**

Hướng dẫn này sẽ giúp bạn **triển khai module Object Detection** của **RoadWatch Copilot** trên các nền tảng khác nhau:

- **Jetson Nano** (Edge Device - ARM64)
- **AWS EC2 G5G.xlarge** (Cloud - x86_64)
- **Laptop AMD** (Local Development - x86_64)

Module sử dụng **YOLOv8-nano** với **ONNX Runtime** và **TensorRT** để đạt hiệu suất tối ưu trên Edge Devices.

---

## **✅ Yêu Cầu Trước Khi Triển Khai**

### **1. Phần Cứng**

| **Nền Tảng** | **Yêu Cầu Tối Thiểu** | **Khuyến Nghị** |
|--------------|----------------------|------------------|
| **Jetson Nano** | 4GB RAM, 16GB Storage | Jetson Nano 2GB/4GB |
| **AWS EC2** | 4 vCPU, 8GB RAM, 1 GPU | G5G.xlarge (NVIDIA T4G) |
| **Laptop AMD** | 8GB RAM, AMD GPU (RDNA 2+) | Ryzen 7 7735HS+ |

### **2. Phần Mềm**

| **Nền Tảng** | **OS** | **CUDA** | **TensorRT** | **Python** |
|--------------|--------|----------|--------------|------------|
| **Jetson Nano** | Ubuntu 20.04 (ARM64) | 10.2 | 8.5.3 | 3.8+ |
| **AWS EC2** | Ubuntu 22.04 (x86_64) | 11.8 | 8.5.3 | 3.10+ |
| **Laptop AMD** | Ubuntu 22.04 / Windows 11 | - | - | 3.10+ |

### **3. Thư Viện Cần Thiết**

- **PyTorch** (cho training)
- **ONNX Runtime** (cho inference)
- **TensorRT** (tùy chọn, cho tối ưu)
- **OpenCV** (xử lý ảnh)
- **NumPy** (tính toán)
- **Ultralytics YOLOv8** (model)

---

## **🎯 Triển Khai Trên Jetson Nano**

### **Bước 1: Cài Đặt JetPack SDK**

JetPack SDK cung cấp **CUDA, cuDNN, TensorRT** cho Jetson Nano.

```bash
# Download JetPack SDK từ NVIDIA
wget https://developer.download.nvidia.com/embedded/jetpack/5.1.2/JetPack-5.1.2-Linux-JETSON_NANO-devkit.tar.gz

# Flash JetPack vào Jetson Nano
# (Tham khảo: https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit)
```

**Lưu ý:** Quá trình flash có thể mất **30-60 phút**.

---

### **Bước 2: Cài Đặt Thư Viện**

#### **Cài Đặt Python 3.8+**
```bash
sudo apt update
sudo apt install -y python3.8 python3.8-venv python3.8-dev
```

#### **Cài Đặt OpenCV**
```bash
sudo apt install -y python3-opencv
```

#### **Cài Đặt PyTorch cho ARM64**
```bash
# Cài PyTorch cho Jetson Nano
pip install torch==2.0.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html
```

**Lưu ý:** PyTorch cho ARM64 có sẵn trên [PyTorch for Jetson](https://forums.developer.nvidia.com/t/pytorch-for-jetson-version-2-0-1-now-available/223916).

---

#### **Cài Đặt ONNX Runtime**
```bash
pip install onnxruntime-gpu==1.16.0
```

---

#### **Cài Đặt TensorRT**
TensorRT đã được cài đặt sẵn với JetPack SDK. Bạn chỉ cần cài đặt **Python bindings**:

```bash
pip install nvidia-pyindex nvidia-tensorrt==8.5.3.1
```

---

#### **Cài Đặt PyCUDA**
```bash
pip install pycuda
```

---

### **Bước 3: Clone Repository**

```bash
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection
```

---

### **Bước 4: Cài Đặt Dependencies**

```bash
pip install -r requirements.txt
```

---

### **Bước 5: Download Model**

#### **Tùy Chọn 1: Download Model Đã Train Sẵn**
```bash
# Tạo thư mục models
mkdir -p models

# Download YOLOv8n ONNX model
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx
```

#### **Tùy Chọn 2: Export Model Từ PyTorch**
```bash
python -c "
import torch
from src.utils import ModelOptimizer

# Load YOLOv8n model
model = torch.hub.load('ultralytics/yolov8', 'yolov8n')

# Export to ONNX
optimizer = ModelOptimizer()
optimizer.export_to_onnx(model, input_shape=(1, 3, 320, 320), onnx_path='models/yolov8n.onnx')
"
```

---

### **Bước 6: Build TensorRT Engine**

```bash
python -c "
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()
optimizer.optimize_for_tensorrt(
    'models/yolov8n.onnx',
    engine_path='models/yolov8n.engine',
    fp16_mode=True,
    int8_mode=False,
    max_batch_size=1
)
"
```

**Lưu ý:** Quá trình build TensorRT engine có thể mất **5-10 phút**.

---

### **Bước 7: Cấu Hình Detector**

```python
from src.detection import DetectorFactory

# Tạo detector tối ưu cho Jetson Nano
detector = DetectorFactory.create_detector(
    device_type="jetson_nano",
    use_tensorrt=True,
    target_fps=30
)
```

---

### **Bước 8: Chạy Demo**

#### **Chạy Với Camera**
```bash
python -c "
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(device_type='jetson_nano')

# Mở camera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Phát hiện vật thể
    result = detector.detect(frame)
    
    # Vẽ kết quả
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Hiển thị
    cv2.imshow('ADAS Object Detection', frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
"
```

#### **Chạy Với Video**
```bash
python -c "
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(device_type='jetson_nano')

# Mở video
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
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Hiển thị
    cv2.imshow('ADAS Object Detection', frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
"
```

---

## **☁️ Triển Khai Trên AWS EC2**

### **Bước 1: Tạo EC2 Instance**

1. Đăng nhập vào **AWS Console** → **EC2**
2. Chọn **Launch Instance**
3. Chọn **AMI**: `Ubuntu Server 22.04 LTS (x86_64)`
4. Chọn **Instance Type**: `g5g.xlarge` (NVIDIA T4G GPU)
5. Chọn **Storage**: 60GB GP3 SSD
6. Chọn **Security Group**: Mở port **22 (SSH), 80 (HTTP), 8000 (API)**
7. **Launch Instance**

---

### **Bước 2: Kết Nối Đến Instance**

```bash
# Kết nối qua SSH
ssh -i your-key.pem ubuntu@<public-ip>
```

---

### **Bước 3: Cài Đặt Driver và CUDA**

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài NVIDIA Driver (T4G)
sudo ubuntu-drivers autoinstall

# Cài CUDA Toolkit 11.8
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2204-11-8-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt update
sudo apt install -y cuda-11-8

# Thêm CUDA vào PATH
echo 'export PATH=/usr/local/cuda-11.8/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

---

### **Bước 4: Cài Đặt TensorRT**

```bash
# Download TensorRT 8.5.3
wget https://developer.download.nvidia.com/compute/redist/tensorrt/8.5.3.1/tensorrt-8.5.3.1.linux.x86_64.cuda-11.8.tar.gz

# Giải nén
tar -xzvf tensorrt-8.5.3.1.linux.x86_64.cuda-11.8.tar.gz

# Cài đặt
sudo cp -r TensorRT-8.5.3.1/* /usr/local/
echo 'export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

---

### **Bước 5: Cài Đặt Thư Viện Python**

```bash
# Cài Python 3.10
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# Tạo virtual environment
python3.10 -m venv ~/adas_venv
source ~/adas_venv/bin/activate

# Cài dependencies
pip install --upgrade pip
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2 -f https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

---

### **Bước 6: Clone Repository và Setup**

```bash
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection

# Download model
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8s.onnx -O models/yolov8s.onnx

# Build TensorRT engine
python -c "
from src.utils import ModelOptimizer
optimizer = ModelOptimizer()
optimizer.optimize_for_tensorrt(
    'models/yolov8s.onnx',
    engine_path='models/yolov8s.engine',
    fp16_mode=True,
    max_batch_size=4
)
"
```

---

### **Bước 7: Chạy Ứng Dụng**

```bash
# Chạy detector
python -c "
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(
    device_type='aws_g5g',
    use_tensorrt=True,
    target_fps=60
)

# Test với một frame
import cv2
import numpy as np

frame = np.zeros((480, 640, 3), dtype=np.uint8)
result = detector.detect(frame)
print(f'FPS: {result.fps:.2f}, Latency: {result.latency:.2f}ms')
"
```

---

## **💻 Triển Khai Trên Laptop AMD**

### **Bước 1: Cài Đặt ROCm**

ROCm là **thay thế cho CUDA** trên AMD GPU.

```bash
# Thêm ROCm repository
sudo apt update && sudo apt install -y wget
wget https://repo.radeon.com/amdgpu-install/5.7/ubuntu/jammy/amdgpu-install_5.7.50700-1_all.deb
sudo apt install ./amdgpu-install_5.7.50700-1_all.deb

# Cài ROCm
sudo amdgpu-install --usecase=rocm,hip,mllib --no-dkms
```

**Lưu ý:** ROCm 5.7+ hỗ trợ **Ryzen 7000 series** (RDNA 2+).

---

### **Bước 2: Cài Đặt Thư Viện Python**

```bash
# Cài Python 3.10
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# Tạo virtual environment
python3.10 -m venv ~/adas_venv
source ~/adas_venv/bin/activate

# Cài dependencies
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install onnxruntime-rocm  # ONNX Runtime cho ROCm
pip install -r requirements.txt
```

---

### **Bước 3: Clone Repository và Setup**

```bash
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection

# Download model
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8s.onnx -O models/yolov8s.onnx
```

---

### **Bước 4: Chạy Ứng Dụng**

```bash
# Chạy detector (không dùng TensorRT)
python -c "
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(
    device_type='laptop_amd',
    use_tensorrt=False,
    target_fps=30
)

# Test với một frame
import cv2
import numpy as np

frame = np.zeros((480, 640, 3), dtype=np.uint8)
result = detector.detect(frame)
print(f'FPS: {result.fps:.2f}, Latency: {result.latency:.2f}ms')
"
```

---

## **⚙️ Cấu Hình Môi Trường**

### **1. Cấu Hình Detector**

Bạn có thể cấu hình detector thông qua **`DetectorConfig`**:

```python
from src.config import DetectorConfig

config = DetectorConfig(
    model_type="yolov8n",  # Model: n, s, m, l, x
    model_path="models/yolov8n.onnx",
    engine_path="models/yolov8n.engine",
    conf_threshold=0.5,  # Ngưỡng confidence
    iou_threshold=0.45,  # Ngưỡng IoU cho NMS
    input_size=320,  # Kích thước input
    use_tensorrt=True,  # Sử dụng TensorRT
    use_half_precision=True,  # Sử dụng FP16
    use_int8=False,  # Sử dụng INT8
    batch_size=1,  # Batch size
    target_classes=["person", "car", "motorcycle", "bus", "truck"]  # Lọc class
)

detector = YOLODetector(config=config)
```

---

### **2. Cấu Hình Hiệu Suất**

```python
from src.config import PerformanceConfig

config = PerformanceConfig(
    target_latency=50,  # Mục tiêu latency (ms)
    max_latency=100,  # Latency tối đa (ms)
    target_fps=30,  # Mục tiêu FPS
    min_fps=15,  # FPS tối thiểu
    enable_compression=True,  # Nén frame
    compression_quality=75,  # Chất lượng nén (0-100)
    enable_batch_processing=False,  # Xử lý batch
    num_inference_threads=1,  # Số luồng inference
    priority_classes=["person", "car", "motorcycle"]  # Class ưu tiên
)
```

---

### **3. Cấu Hình Cho Jetson Nano**

```python
from src.detection import DetectorFactory

# Tự động cấu hình cho Jetson Nano
detector = DetectorFactory.create_detector(
    device_type="jetson_nano",
    use_tensorrt=True,
    target_fps=30
)

# Hoặc cấu hình thủ công
detector.config.model_type = "yolov8n"
detector.config.input_size = 320
detector.config.use_half_precision = True
detector.config.use_int8 = True
```

---

## **▶️ Chạy Ứng Dụng**

### **1. Chạy Với Camera**

```bash
python -c "
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(device_type='jetson_nano')

# Mở camera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Phát hiện vật thể
    result = detector.detect(frame)
    
    # Vẽ kết quả
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Hiển thị FPS và Latency
    cv2.putText(frame, f'FPS: {result.fps:.1f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Latency: {result.latency:.1f}ms', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Hiển thị
    cv2.imshow('ADAS Object Detection', frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
"
```

---

### **2. Chạy Với Video**

```bash
python -c "
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(device_type='jetson_nano')

# Mở video
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
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Hiển thị
    cv2.imshow('ADAS Object Detection', frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
"
```

---

### **3. Chạy Với API (FastAPI)**

Tạo file `api/main.py`:

```python
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from src.detection import DetectorFactory
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

app = FastAPI()

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo detector
detector = DetectorFactory.create_detector(device_type='jetson_nano')

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
                "x1": det.bbox[0],
                "y1": det.bbox[1],
                "x2": det.bbox[2],
                "y2": det.bbox[3]
            },
            "is_priority": det.is_priority
        })
    
    return {
        "frame_id": result.frame_id,
        "fps": result.fps,
        "latency": result.latency,
        "detections": detections
    }

@app.get("/health")
async def health():
    return {"status": "OK"}
```

Chạy API:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Test API:

```bash
# Test với curl
curl -X POST -F "file=@test_image.jpg" http://localhost:8000/detect

# Hoặc dùng Python
import requests

with open("test_image.jpg", "rb") as f:
    response = requests.post("http://localhost:8000/detect", files={"file": f})
    print(response.json())
```

---

## **📊 Giám Sát Hiệu Suất**

### **1. Sử Dụng PerformanceMonitor**

```python
from src.utils import PerformanceMonitor

monitor = PerformanceMonitor(
    window_size=10,
    target_fps=30,
    max_latency=50
)

# Trong vòng lặp xử lý frame
start = monitor.start_frame()
result = detector.detect(frame)
monitor.end_frame(start)

# Lấy metrics
metrics = monitor.get_current_metrics()
print(f"FPS: {metrics['fps']:.1f}")
print(f"Latency: {metrics['latency_ms']:.1f}ms")
print(f"CPU Usage: {metrics['cpu_usage_percent']:.1f}%")
print(f"Memory Usage: {metrics['memory_usage_percent']:.1f}%")
```

---

### **2. Sử Dụng Prometheus + Grafana**

Cài đặt **Prometheus** và **Grafana** để giám sát hiệu suất từ xa.

#### **Cài Đặt Prometheus**

```bash
# Tạo file prometheus.yml
cat > prometheus.yml <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'adas'
    static_configs:
      - targets: ['localhost:9090']
EOF

# Chạy Prometheus
docker run -d -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
```

#### **Cài Đặt Grafana**

```bash
# Chạy Grafana
docker run -d -p 3000:3000 grafana/grafana
```

#### **Tích Hợp Với ADAS**

```python
from prometheus_client import start_http_server, Counter, Gauge

# Khởi tạo metrics
FPS_GAUGE = Gauge('adas_fps', 'Frames per second')
LATENCY_GAUGE = Gauge('adas_latency_ms', 'Processing latency in milliseconds')
CPU_USAGE_GAUGE = Gauge('adas_cpu_usage_percent', 'CPU usage percentage')
MEMORY_USAGE_GAUGE = Gauge('adas_memory_usage_percent', 'Memory usage percentage')

# Start HTTP server
start_http_server(8000)

# Cập nhật metrics
FPS_GAUGE.set(metrics['fps'])
LATENCY_GAUGE.set(metrics['latency_ms'])
CPU_USAGE_GAUGE.set(metrics['cpu_usage_percent'])
MEMORY_USAGE_GAUGE.set(metrics['memory_usage_percent'])
```

---

## **🛠️ Khắc Phục Sự Cố**

### **1. Lỗi Thường Gặp**

#### **🔴 Lỗi: `ModuleNotFoundError: No module named 'tensorrt'`**
**Nguyên nhân:** TensorRT Python bindings chưa được cài đặt.

**Giải pháp:**
```bash
pip install nvidia-pyindex nvidia-tensorrt==8.5.3.1
```

---

#### **🔴 Lỗi: `CUDA out of memory`**
**Nguyên nhân:** Model quá lớn cho GPU.

**Giải pháp:**
```python
# Dùng model nhỏ hơn
detector.config.model_type = "yolov8n"

# Giảm input size
detector.config.input_size = 320

# Giảm batch size
detector.config.batch_size = 1
```

---

#### **🔴 Lỗi: `ONNX model not found`**
**Nguyên nhân:** Model ONNX chưa được download hoặc export.

**Giải pháp:**
```bash
# Download model
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx
```

---

#### **🔴 Lỗi: `TensorRT engine not found`**
**Nguyên nhân:** TensorRT engine chưa được build.

**Giải pháp:**
```python
from src.utils import ModelOptimizer

optimizer = ModelOptimizer()
optimizer.optimize_for_tensorrt(
    'models/yolov8n.onnx',
    engine_path='models/yolov8n.engine',
    fp16_mode=True
)
```

---

#### **🔴 Lỗi: `Low FPS`**
**Nguyên nhân:** Model quá nặng hoặc input size quá lớn.

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
**Nguyên nhân:** Xử lý đồng bộ hoặc không bật quantization.

**Giải pháp:**
```python
# Bật quantization
detector.config.use_half_precision = True
detector.config.use_int8 = True

# Bật frame cache
from src.config import PerformanceConfig
config = PerformanceConfig(enable_frame_cache=True)
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

## **🔄 Cập Nhật và Bảo Trì**

### **1. Cập Nhật Model**

```bash
# Download model mới
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx

# Build lại TensorRT engine
python -c "
from src.utils import ModelOptimizer
optimizer = ModelOptimizer()
optimizer.optimize_for_tensorrt(
    'models/yolov8n.onnx',
    engine_path='models/yolov8n.engine',
    fp16_mode=True
)
"
```

---

### **2. Cập Nhật Dependencies**

```bash
# Cập nhật requirements.txt
pip install --upgrade -r requirements.txt
```

---

### **3. Backup Model**

```bash
# Backup models
mkdir -p backup/models
cp -r models/* backup/models/

# Backup config
mkdir -p backup/config
cp -r src/config/* backup/config/
```

---

### **4. Log Rotation**

Cấu hình **log rotation** để tránh log file quá lớn:

```python
from src.utils import setup_logger

# Setup logger với rotation
logger = setup_logger(
    name="adas",
    log_level=logging.INFO,
    log_file="adas.log",
    max_file_size=10 * 1024 * 1024,  # 10MB
    backup_count=3  # Giữ 3 file backup
)
```

---

## **📚 Tài Liệu Tham Khảo**

1. [NVIDIA Jetson Nano Developer Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit)
2. [AWS EC2 G5G Instance Guide](https://aws.amazon.com/ec2/instance-types/g5g/)
3. [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com/)
4. [ONNX Runtime Documentation](https://onnxruntime.ai/)
5. [TensorRT Documentation](https://developer.nvidia.com/tensorrt)
6. [ROCm Documentation](https://docs.amd.com/)

---

## **🎯 Kết Luận**

Bạn đã hoàn thành việc **triển khai module Object Detection** trên các nền tảng khác nhau. Với các cấu hình và tối ưu hóa phù hợp, hệ thống có thể đạt:

| **Nền Tảng** | **FPS** | **Latency** | **Memory Usage** | **GPU Usage** |
|--------------|---------|-------------|-----------------|---------------|
| Jetson Nano | 30-40 | 25-35ms | ~1.5GB | ~80-90% |
| AWS G5G | 80-100 | 10-20ms | ~3GB | ~70-80% |
| Laptop AMD | 20-30 | 30-50ms | ~2GB | ~60-70% |

**🚀 Chúc bạn triển khai thành công!**
