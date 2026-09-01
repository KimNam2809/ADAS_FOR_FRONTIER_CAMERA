from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune RoadWatch detector có version hóa")
    parser.add_argument("--data", required=True, help="YOLO data.yaml đã kiểm tra license/split")
    parser.add_argument("--model", default="models/yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--name", required=True, help="Tên version, ví dụ roadwatch-objects-v1")
    args = parser.parse_args()
    data = Path(args.data).resolve()
    model = (PROJECT_ROOT / args.model).resolve() if not Path(args.model).is_absolute() else Path(args.model)
    if not data.exists():
        raise FileNotFoundError(data)
    if not model.exists():
        raise FileNotFoundError(model)
    from ultralytics import YOLO

    result = YOLO(str(model)).train(
        data=str(data),
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=args.device,
        project=str(PROJECT_ROOT / "reports" / "training"),
        name=args.name,
        seed=2809,
        deterministic=True,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
