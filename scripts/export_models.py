from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = PROJECT_ROOT / "models"


def export(model_name: str, image_size: int, half: bool) -> Path:
    from ultralytics import YOLO

    source = MODEL_ROOT / model_name
    if not source.exists():
        raise FileNotFoundError(source)
    model = YOLO(str(source))
    exported = Path(
        model.export(format="onnx", imgsz=image_size, simplify=True, dynamic=False, half=half)
    )
    target = MODEL_ROOT / f"{source.stem}.onnx"
    if exported.resolve() != target.resolve():
        exported.replace(target)
    names = {str(key): value for key, value in model.names.items()}
    target.with_suffix(".names.json").write_text(
        json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Export RoadWatch detectors to ONNX")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--half", action="store_true", help="Chỉ dùng khi runtime hỗ trợ FP16")
    parser.add_argument("--objects-only", action="store_true")
    parser.add_argument(
        "--object-model",
        default="yolo11n.pt",
        help="Tên checkpoint object detector trong roadwatch/models",
    )
    args = parser.parse_args()
    print(export(args.object_model, args.imgsz, args.half))
    if not args.objects_only:
        print(export("yolo11s_vietnam_traffic.pt", args.imgsz, args.half))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
