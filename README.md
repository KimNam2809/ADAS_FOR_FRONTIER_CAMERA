# Universal YOLO Counter

One Python source tree for Windows, Linux, macOS Intel/Apple Silicon, NVIDIA CUDA, and headless ARM64 servers. The environment is platform-specific; the application code is shared.

## 1. Add assets

- Copy your trained model to `models/best.pt`.
- Copy a test video or image into `media/`.

## 2. Desktop setup

Use Python 3.10 or 3.11.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

For NVIDIA, install a CUDA-enabled PyTorch build appropriate to the driver before installing `requirements.txt`. For Apple Silicon, the program automatically chooses MPS when PyTorch reports it available. AMD Windows safely falls back to CPU.

## Export model to ONNX format

```bash
yolo export `
  model=models/yolov10n.pt `
  format=onnx `
  imgsz=512 `
  simplify=True `
  dynamic=False `
  batch=1
```

```bash
yolo export model=models/yolov10n_test.onnx format=engine imgsz=640 simplify=True dynamic=False batch=1 device=0

```

yolov10n_640.onnx
yolov10_traffic_sign.pt
yolov10n_vietnam_traffic.pt

## 3. Run visually

Video:

```bash
python run.py --source media/traffic.mp4 --model models/best.pt --show --save
```

Image:

```bash
python run.py --source media/test.jpg --model models/best.pt --output outputs/test.jpg --show
```

Webcam:

```bash
python run.py --source 0 --model models/best.pt --show --no-save
```

Count selected classes only:

```bash
python run.py --source media/traffic.mp4 --classes car motorcycle bus truck
```

Low-resource mode:

```bash
python run.py --source media/traffic.mp4 --device cpu --imgsz 416 --frame-skip 1
```

Move the counting line with `--line`, from 0 at the top to 1 at the bottom:

```bash
python run.py --source media/traffic.mp4 --line 0.65
```

## 4. Headless ARM64 EC2

Use an ARM64 Ubuntu/NVIDIA image whose driver and CUDA-enabled ARM64 PyTorch installation are already compatible with NVIDIA T4G. Verify first:

```bash
uname -m
nvidia-smi
python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
```

Then install server dependencies and run without GUI:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements-server.txt
python run.py --source media/traffic.mp4 --device 0 --no-show --save
```

For RTSP:

```bash
python run.py --source 'rtsp://user:password@host/stream' --device 0 --no-show --save
```

Do not put camera credentials in source control. Use environment variables or a secret manager.

## Notes

- Image mode counts objects visible in one image.
- Video mode uses tracking IDs and counts line crossings, not bounding boxes per frame.
- Test class names with your own model. They must match `model.names` exactly.
- Source code is portable, but PyTorch/CUDA/ROCm wheels are hardware and OS specific. Do not copy a virtual environment between platforms.
