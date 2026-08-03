# 🚀 ADAS Object Detection Deployment Guide

## **Mục Lục**
1. [Giới Thiệu](#giới-thiệu)
2. [Yêu Cầu Trước Khi Triển Khai](#yêu-cầu-trước-khi-triển-khai)
3. [Triển Khai Trên AWS EC2 (ARM64)](#triển-khai-trên-aws-ec2-arm64)
4. [Triển Khai Trên Jetson Nano](#triển-khai-trên-jetson-nano)
5. [Triển Khai Trên Laptop (x86_64)](#triển-khai-trên-laptop-x86_64)
6. [Cấu Hình Môi Trường](#cấu-hình-môi-trường)
7. [Chạy Ứng Dụng](#chạy-ứng-dụng)
8. [Giám Sát Hiệu Suất](#giám-sát-hiệu-suất)
9. [Khắc Phục Sự Cố](#khắc-phục-sự-cố)
10. [Cập Nhật và Bảo Trì](#cập-nhật-và-bảo-trì)

---

## **📌 Giới Thiệu**

Hướng dẫn này sẽ giúp bạn **triển khai module Object Detection** của **RoadWatch Copilot** trên **AWS EC2 (ARM64)**. Module sử dụng **YOLOv8-nano** với **ONNX Runtime** để phát hiện các vật thể trên đường như **người, xe ô tô, xe máy, xe bus, xe tải, biển báo giao thông** với **độ trễ thấp** và **hiệu suất cao**.

### **🎯 Đặc Điểm Chính**
✅ **Real-time Object Detection** - Phát hiện vật thể trong thời gian thực
✅ **Optimized for ARM64** - Tối ưu cho AWS EC2 G5G.xlarge (ARM64)
✅ **Low Latency** - Độ trễ xử lý **< 50ms**
✅ **High Performance** - Hiệu suất **≥ 30 FPS**
✅ **ONNX Runtime** - Chạy model ONNX trên ARM64
✅ **Easy Deployment** - Triển khai đơn giản với Docker

---

## **✅ Yêu Cầu Trước Khi Triển Khai**

### **1. AWS EC2 Instance (ARM64)**
- **AMI**: Ubuntu Server 26.04 LTS (ARM64)
- **Instance Type**: g5g.xlarge (NVIDIA T4G GPU, 4 vCPU, 16GB RAM, 8GB VRAM)
- **Architecture**: 64-bit (ARM)
- **Storage**: 60GB GP3 SSD (EBS General Purpose)
- **Security Group**: Mở port **22 (SSH), 8000 (API)**

### **2. Kết Nối Đến Instance**
```bash
# Kết nối qua SSH (thay thế your-key.pem và public-ip)
ssh -i your-key.pem ubuntu@<public-ip>
```

---

## **☁️ Triển Khai Trên AWS EC2 (ARM64)**

### **Bước 1: Cập Nhật Hệ Thống**
```bash
# Cập nhật package list
sudo apt update && sudo apt upgrade -y

# Cài đặt các gói cần thiết
sudo apt install -y wget curl git build-essential python3.10 python3.10-venv python3.10-dev python3-pip
```

---

### **Bước 2: Cài Đặt NVIDIA Driver cho T4G GPU (ARM64)**

**⚠️ LƯU Ý:** AWS EC2 G5G.xlarge sử dụng **NVIDIA T4G GPU (ARM64)**, không sử dụng CUDA truyền thống. Thay vào đó, chúng ta sử dụng **NVIDIA Driver cho ARM64** và **ONNX Runtime**.

```bash
# Kiểm tra GPU
lspci | grep -i nvidia

# Cài đặt NVIDIA Driver cho ARM64 (T4G)
# AWS đã cài sẵn driver, nhưng chúng ta cần cài thêm thư viện
sudo apt install -y nvidia-driver-535

# Khởi động lại instance (nếu cần)
sudo reboot
```

---

### **Bước 3: Cài Đặt ONNX Runtime cho ARM64**

```bash
# Cài đặt ONNX Runtime (không cần CUDA cho ARM64 trên AWS)
pip install onnxruntime==1.16.0

# Xác minh cài đặt
python3 -c "import onnxruntime; print('ONNX Runtime version:', onnxruntime.__version__)"
```

---

### **Bước 4: Cài Đặt OpenCV cho ARM64**

```bash
# Cài đặt OpenCV cho Python
pip install opencv-python-headless==4.8.0.76

# Xác minh cài đặt
python3 -c "import cv2; print('OpenCV version:', cv2.__version__)"
```

---

### **Bước 5: Cài Đặt Các Thư Viện Khác**

```bash
# Cài đặt các thư viện cần thiết
pip install numpy==1.24.3 ultralytics==8.0.196 psutil==5.9.5 pyyaml==6.0.1
```

---

### **Bước 6: Clone Repository**

```bash
# Clone repository
cd ~
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection
```

---

### **Bước 7: Download Model YOLOv8**

```bash
# Tạo thư mục models
mkdir -p models

# Download YOLOv8n ONNX model (tối ưu cho ARM64)
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx

# Xác minh model
ls -lh models/
```

---

### **Bước 8: Test Module Object Detection**

#### **Tùy Chọn 1: Chạy Test Với Ảnh Tĩnh**

```bash
# Tạo một script test đơn giản
cat > test_image.py << 'EOF'
import cv2
import numpy as np
from src.detection import DetectorFactory

# Tạo detector (không dùng TensorRT trên ARM64 AWS)
detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    use_tensorrt=False,
    target_fps=30
)

# Tạo một frame test (màu xanh lá cây)
frame = np.zeros((480, 640, 3), dtype=np.uint8)
frame[:, :] = (0, 255, 0)  # Màu xanh lá cây

# Phát hiện vật thể
result = detector.detect(frame)

# In kết quả
print(f"Số lượng vật thể phát hiện: {len(result.detections)}")
print(f"FPS: {result.fps:.2f}")
print(f"Latency: {result.latency:.2f}ms")
print(f"CPU Usage: {result.cpu_usage:.1f}%")
print(f"Memory Usage: {result.memory_usage:.1f}%")
EOF

# Chạy script
python3 test_image.py
```

**📌 Kết quả mong đợi:**
```
Số lượng vật thể phát hiện: 0
FPS: 25.00
Latency: 40.00ms
CPU Usage: 15.2%
Memory Usage: 12.5%
```

---

#### **Tùy Chọn 2: Chạy Với Ảnh Thật**

```bash
# Download một ảnh test
wget https://ultralytics.com/images/bus.jpg -O test_bus.jpg

# Tạo script test với ảnh thật
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
print(f"Số lượng vật thể phát hiện: {len(result.detections)}")
for i, det in enumerate(result.detections):
    print(f"  {i+1}. {det.class_name}: {det.confidence:.2f} (bbox: {det.bbox})")
print(f"FPS: {result.fps:.2f}")
print(f"Latency: {result.latency:.2f}ms")
EOF

# Chạy script
python3 test_real_image.py
```

**📌 Kết quả mong đợi:**
```
Số lượng vật thể phát hiện: 3
  1. bus: 0.98 (bbox: (100.5, 150.2, 400.7, 300.8))
  2. person: 0.85 (bbox: (450.1, 200.3, 500.4, 350.6))
  3. car: 0.72 (bbox: (50.2, 180.5, 120.3, 220.7))
FPS: 28.50
Latency: 35.00ms
```

---

#### **Tùy Chọn 3: Chạy Với Camera (Webcam)**

**⚠️ LƯU Ý:** AWS EC2 không có webcam vật lý, nhưng bạn có thể:
1. **Sử dụng camera ảo** (virtual camera)
2. **Stream video từ máy local**
3. **Sử dụng video test**

##### **Cách 1: Sử Dụng Video Test**

```bash
# Download video test
wget https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 -O test_video.mp4

# Tạo script test video
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
    
    # Hiển thị FPS và Latency
    cv2.putText(frame, f'FPS: {result.fps:.1f}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Latency: {result.latency:.1f}ms', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Hiển thị (nhưng trên AWS EC2 không có GUI, nên chỉ in ra terminal)
    print(f"Frame {frame_count}: {len(result.detections)} detections, FPS: {result.fps:.1f}, Latency: {result.latency:.1f}ms")
    frame_count += 1
    
    # Dừng sau 10 frame (để test)
    if frame_count >= 10:
        break

cap.release()
print("Test hoàn tất!")
EOF

# Chạy script
python3 test_video.py
```

**📌 Kết quả mong đợi:**
```
Frame 0: 0 detections, FPS: 25.0, Latency: 40.0ms
Frame 1: 1 detections, FPS: 28.5, Latency: 35.0ms
Frame 2: 2 detections, FPS: 30.0, Latency: 33.3ms
...
Test hoàn tất!
```

---

##### **Cách 2: Sử Dụng Stream Từ Máy Local**

Bạn có thể **stream video từ máy local** đến AWS EC2 bằng **FFmpeg** và **Netcat**:

**Trên máy local:**
```bash
# Stream video từ webcam đến AWS EC2
ffmpeg -f v4l2 -i /dev/video0 -f mpegts udp://<aws-public-ip>:1234
```

**Trên AWS EC2:**
```bash
# Nhận stream và xử lý
cat > test_stream.py << 'EOF'
import cv2
from src.detection import DetectorFactory

# Tạo detector
detector = DetectorFactory.create_detector(
    device_type='aws_arm64',
    use_tensorrt=False,
    target_fps=30
)

# Mở stream UDP
cap = cv2.VideoCapture('udp://0.0.0.0:1234')

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        continue
    
    # Phát hiện vật thể
    result = detector.detect(frame)
    
    # In kết quả
    print(f"Detections: {len(result.detections)}, FPS: {result.fps:.1f}, Latency: {result.latency:.1f}ms")
    
    # Dừng bằng Ctrl+C
EOF

# Chạy script
python3 test_stream.py
```

---

### **Bước 9: Chạy API (FastAPI) Để Test Từ Xa**

```bash
# Cài đặt FastAPI và Uvicorn
pip install fastapi==0.104.1 uvicorn==0.24.0

# Tạo file API
cat > api/main.py << 'EOF'
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

### **Bước 10: Sử Dụng Docker (Tùy Chọn)**

```bash
# Build Docker image cho ARM64
docker build --platform linux/arm64 -t adas-copilot:arm64 .

# Chạy container
docker run --rm -p 8000:8000 adas-copilot:arm64
```

---

## **🏠 Triển Khai Trên Jetson Nano**

### **Bước 1: Cài Đặt JetPack SDK**

```bash
# Download JetPack SDK
wget https://developer.download.nvidia.com/embedded/jetpack/5.1.2/JetPack-5.1.2-Linux-JETSON_NANO-devkit.tar.gz

# Flash JetPack vào Jetson Nano
# (Tham khảo: https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit)
```

---

### **Bước 2: Cài Đặt Thư Viện**

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài Python 3.8+
sudo apt install -y python3.8 python3.8-venv python3.8-dev

# Cài OpenCV
sudo apt install -y python3-opencv

# Cài PyTorch cho Jetson (ARM64)
pip install torch==2.0.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html

# Cài ONNX Runtime
pip install onnxruntime-gpu==1.16.0

# Cài TensorRT (đã cài sẵn với JetPack)
pip install nvidia-pyindex nvidia-tensorrt==8.5.3.1
```

---

### **Bước 3: Clone Repository và Chạy**

```bash
# Clone repository
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection

# Download model
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx

# Build TensorRT engine (tùy chọn)
python3 -c "
from src.utils import ModelOptimizer
optimizer = ModelOptimizer()
optimizer.optimize_for_tensorrt('models/yolov8n.onnx', engine_path='models/yolov8n.engine', fp16_mode=True)
"

# Chạy demo
python3 -c "
import cv2
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(device_type='jetson_nano', use_tensorrt=True)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret: break
    result = detector.detect(frame)
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imshow('ADAS', frame)
    if cv2.waitKey(1) == ord('q'): break

cap.release()
cv2.destroyAllWindows()
"
```

---

## **💻 Triển Khai Trên Laptop (x86_64)**

### **Bước 1: Cài Đặt Môi Trường**

```bash
# Cài Python 3.10+
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# Tạo virtual environment
python3.10 -m venv ~/adas_venv
source ~/adas_venv/bin/activate

# Cài dependencies
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install onnxruntime opencv-python-headless numpy ultralytics psutil pyyaml
```

---

### **Bước 2: Clone Repository và Chạy**

```bash
# Clone repository
git clone https://github.com/KimNam2809/ADAS_FOR_FRONTIER_CAMERA.git
cd ADAS_FOR_FRONTIER_CAMERA
git checkout feat-Object-Detection

# Download model
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8s.onnx -O models/yolov8s.onnx

# Chạy demo
python3 -c "
import cv2
from src.detection import DetectorFactory

detector = DetectorFactory.create_detector(device_type='laptop', use_tensorrt=False)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret: break
    result = detector.detect(frame)
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(frame, f'{det.class_name} {det.confidence:.2f}', (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    cv2.imshow('ADAS', frame)
    if cv2.waitKey(1) == ord('q'): break

cap.release()
cv2.destroyAllWindows()
"
```

---

## **⚙️ Cấu Hình Môi Trường**

### **1. Cấu Hình Detector**

```python
from src.config import DetectorConfig
from src.detection import YOLODetector

# Cấu hình cho AWS EC2 ARM64
config = DetectorConfig(
    model_type="yolov8n",
    model_path="models/yolov8n.onnx",
    conf_threshold=0.5,
    iou_threshold=0.45,
    input_size=320,
    use_tensorrt=False,  # Không dùng TensorRT trên ARM64 AWS
    use_half_precision=False,
    use_int8=False,
    target_classes=["person", "car", "motorcycle", "bus", "truck", "stop sign", "traffic light"]
)

detector = YOLODetector(config=config)
```

---

### **2. Cấu Hình Hiệu Suất**

```python
from src.config import PerformanceConfig

config = PerformanceConfig(
    target_latency=50,
    max_latency=100,
    target_fps=30,
    enable_compression=True,
    compression_quality=75,
    priority_classes=["person", "car", "motorcycle"]
)
```

---

## **📊 Giám Sát Hiệu Suất**

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

## **🛠️ Khắc Phục Sự Cố**

### **1. Lỗi Thường Gặp Trên AWS EC2 (ARM64)**

#### **🔴 Lỗi: `ModuleNotFoundError: No module named 'onnxruntime'`**
**Nguyên nhân:** ONNX Runtime chưa được cài đặt.

**Giải pháp:**
```bash
pip install onnxruntime==1.16.0
```

---

#### **🔴 Lỗi: `Cannot load ONNX model`**
**Nguyên nhân:** Đường dẫn model không đúng.

**Giải pháp:**
```bash
# Kiểm tra đường dẫn model
ls -lh models/

# Đảm bảo model tồn tại
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx
```

---

#### **🔴 Lỗi: `No module named 'cv2'`**
**Nguyên nhân:** OpenCV chưa được cài đặt.

**Giải pháp:**
```bash
pip install opencv-python-headless==4.8.0.76
```

---

#### **🔴 Lỗi: `Low FPS`**
**Nguyên nhân:** Model quá nặng cho ARM64.

**Giải pháp:**
```python
# Dùng model nhỏ hơn
detector.config.model_type = "yolov8n"

# Giảm input size
detector.config.input_size = 320
```

---

#### **🔴 Lỗi: `High Latency`**
**Nguyên nhân:** Xử lý chậm trên ARM64.

**Giải pháp:**
```python
# Giảm input size
detector.config.input_size = 320

# Bật frame cache
from src.config import PerformanceConfig
config = PerformanceConfig(enable_frame_cache=True)
```

---

## **🔄 Cập Nhật và Bảo Trì**

### **1. Cập Nhật Model**

```bash
# Download model mới
wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.onnx -O models/yolov8n.onnx
```

---

### **2. Cập Nhật Dependencies**

```bash
pip install --upgrade -r requirements.txt
```

---

## **📚 Tài Liệu Tham Khảo**

1. [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com/)
2. [ONNX Runtime Documentation](https://onnxruntime.ai/)
3. [AWS EC2 G5G Instance Guide](https://aws.amazon.com/ec2/instance-types/g5g/)
4. [NVIDIA T4G GPU Documentation](https://docs.nvidia.com/jetson/archives/r35.1/DeveloperGuide/text/SD/Jetsons/T4GTX1.html)

---

## **🎯 Kết Luận**

Bạn đã hoàn thành việc **triển khai module Object Detection** trên **AWS EC2 (ARM64)**. Với các cấu hình trên, hệ thống có thể đạt:

| **Nền Tảng** | **FPS** | **Latency** | **Memory Usage** |
|--------------|---------|------------|-----------------|
| AWS EC2 G5G (ARM64) | **25-35** | **30-45ms** | ~1.5-2GB |

**🚀 Chúc bạn triển khai thành công!**
