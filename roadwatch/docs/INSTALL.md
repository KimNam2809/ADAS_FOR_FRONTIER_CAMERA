# Cài đặt và vận hành

## 1. Windows AMD — profile phát triển hiện tại

1. Cài Python 3.10–3.12 x64, Node.js 20+, Git. Kiểm tra bằng `python --version`, `node --version`.
2. Copy model vào `roadwatch/models`, video vào `roadwatch/media`.
3. Chạy:

```powershell
cd roadwatch
.\scripts\setup.ps1 -PythonExe "C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe"
.\scripts\test.ps1
.\scripts\start.ps1
```

4. Truy cập `http://localhost:8000`. Dùng `-Lan` chỉ khi cần laptop hội đồng truy cập cùng mạng:

```powershell
$env:ROADWATCH_SECRET = "mot-chuoi-ngau-nhien-dai"
.\scripts\start.ps1 -Lan
```

Windows dùng `onnxruntime-directml` cho YOLOP. Hai model Ultralytics `.pt` chạy CPU trên máy AMD vì PyTorch/Ultralytics không dùng DirectML ổn định như ONNX Runtime; có thể export sang ONNX trong giai đoạn tối ưu tiếp theo.

## 2. Audio tiếng Việt offline

Setup tải `vi_VN-vais1000-medium` vào `voices/`. Hai file bắt buộc:

```text
vi_VN-vais1000-medium.onnx
vi_VN-vais1000-medium.onnx.json
```

Sinh trước audio template để tránh latency TTS lần đầu:

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_audio.py
```

Piper chạy trong worker bất đồng bộ; beep critical không đợi TTS. Voice/model mang giấy phép riêng, cần rà soát `MODEL_CARD` trước khi thương mại hóa.

## 3. Docker CPU

```powershell
docker compose config
docker compose build
docker compose up -d
docker compose logs -f roadwatch
```

Kiểm tra `http://localhost:8000/api/health`. Docker không chứa model/media trong image; chúng được mount read-only. Điều này giữ image nhỏ hơn và tránh đẩy dữ liệu nặng lên Git.

## 4. NVIDIA desktop / AWS EC2 g5g.xlarge

AMI đã có driver/PyTorch tương thích nên ưu tiên môi trường host hoặc `Dockerfile.nvidia`:

```bash
docker build -f Dockerfile.nvidia -t roadwatch:nvidia .
docker run --gpus all --rm -p 8000:8000 \
  -e ROADWATCH_DEVICE=0 -e ROADWATCH_RUNTIME=cuda \
  -v "$PWD/models:/app/models:ro" \
  -v "$PWD/media:/app/media:ro" \
  -v "$PWD/data:/app/data" roadwatch:nvidia
```

Trên EC2 ARM64 phải dùng wheel/container tương thích ARM64 và driver của AMI; không copy môi trường `.venv` Windows. Benchmark lại P50/P95 sau mỗi thay đổi provider.

## 5. Jetson Orin

1. Chọn base image L4T đúng với JetPack đang cài; sửa `L4T_PYTORCH_IMAGE` khi build.
2. Không cài generic PyPI `torch` đè bản NVIDIA JetPack.
3. Build:

```bash
docker build -f Dockerfile.jetson \
  --build-arg L4T_PYTORCH_IMAGE=<image-phu-hop-JetPack> \
  -t roadwatch:jetson .
```

4. Chạy với NVIDIA runtime, mount camera/video/model. TensorRT FP16 là bước tối ưu sau khi baseline CUDA/ONNX đã đúng; INT8 chỉ dùng khi có calibration set và báo cáo giảm chất lượng.

## 6. Cấu hình môi trường

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `ROADWATCH_SOURCE` | video local mặc định | `test_video10.mp4` |
| `ROADWATCH_DEVICE` | Ultralytics device (`cpu`, `0`) | `cpu` |
| `ROADWATCH_RUNTIME` | YOLOP (`auto`, `directml`, `cuda`, `cpu`) | `auto` |
| `ROADWATCH_MAX_FPS` | trần FPS xử lý | `12` |
| `ROADWATCH_DISABLE_AUDIO` | `1` để tắt audio | `0` |
| `ROADWATCH_SECRET` | khóa ký token local | demo default |

## 7. Sự cố thường gặp

- `python not found`: truyền đường dẫn đầy đủ vào `setup.ps1 -PythonExe`.
- DirectML biến mất sau cài Piper: chạy `pip install --force-reinstall --no-deps onnxruntime-directml`.
- UI không xuất hiện: chạy `npm.cmd run build` trong `frontend/` rồi restart backend.
- Model error nhưng API còn chạy: xem `degraded_reasons` và `/api/health`; đây là graceful degradation có chủ đích.
- Video chậm trên AMD: giảm `max_processed_fps`, tăng `lane_interval/sign_interval`, hoặc export YOLO `.pt` sang ONNX ở bản tối ưu tiếp theo.
