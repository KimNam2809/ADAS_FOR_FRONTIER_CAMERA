from __future__ import annotations

import argparse
import hashlib
import json
import sys
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "third_party" / "twinlitenetplus"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_model(checkpoint: Path, config: str):
    import torch
    from model.model import TwinLiteNetPlus

    model = TwinLiteNetPlus(Namespace(config=config))
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model.load_state_dict(state)
    model.eval()
    return model


def compare_outputs(torch_outputs, ort_outputs) -> dict[str, float | list[int]]:
    max_abs = 0.0
    mean_abs = 0.0
    shapes: list[list[int]] = []
    for torch_output, ort_output in zip(torch_outputs, ort_outputs):
        torch_array = torch_output.detach().cpu().numpy()
        ort_array = np.asarray(ort_output)
        shapes.append(list(ort_array.shape))
        difference = np.abs(torch_array - ort_array)
        max_abs = max(max_abs, float(difference.max(initial=0.0)))
        mean_abs = max(mean_abs, float(difference.mean()))
    return {
        "max_abs": max_abs,
        "mean_abs": mean_abs,
        "output_shapes": shapes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export TwinLiteNet+ Medium to ONNX and verify parity.")
    parser.add_argument(
        "--checkpoint",
        default=str(PROJECT_ROOT / "models" / "twinlitenetplus_medium.pth"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "models" / "twinlitenetplus_medium.onnx"),
    )
    parser.add_argument("--config", default="medium", choices=["nano", "small", "medium", "large"])
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument(
        "--height",
        type=int,
        default=384,
        help="Static input height; 384 matches 16:9 dashcam letterbox output.",
    )
    args = parser.parse_args()

    import onnx
    import onnxruntime as ort
    import torch

    checkpoint = Path(args.checkpoint).resolve()
    output_path = Path(args.output).resolve()
    if not checkpoint.exists():
        raise FileNotFoundError(checkpoint)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = load_model(checkpoint, args.config)
    dummy = torch.rand(1, 3, args.height, args.width, dtype=torch.float32)
    torch.onnx.export(
        model,
        (dummy,),
        str(output_path),
        input_names=["images"],
        output_names=["drivable_logits", "lane_logits"],
        opset_version=args.opset,
        do_constant_folding=True,
        dynamo=False,
    )
    onnx_model = onnx.load(str(output_path))
    onnx.checker.check_model(onnx_model)

    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    parity: dict[str, dict[str, float | list[int]]] = {}
    with torch.inference_mode():
        test_input = torch.rand(1, 3, args.height, args.width, dtype=torch.float32)
        torch_outputs = model(test_input)
        ort_outputs = session.run(None, {input_name: test_input.numpy()})
        parity[f"{args.height}x{args.width}"] = compare_outputs(torch_outputs, ort_outputs)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha256(checkpoint),
        "output": str(output_path),
        "output_sha256": sha256(output_path),
        "config": args.config,
        "opset": args.opset,
        "input_contract": {
            "shape": [1, 3, args.height, args.width],
            "format": "RGB float32 tensor, NCHW, values in [0, 1]",
            "spatial_axes": "static; re-export for another target aspect ratio",
        },
        "output_contract": ["drivable_logits", "lane_logits"],
        "parameters": int(sum(parameter.numel() for parameter in model.parameters())),
        "onnxruntime_providers": session.get_providers(),
        "parity": parity,
        "gate": {
            "onnx_checker": "PASS",
            "onnxruntime_load": "PASS",
            "parity_rule": "max_abs <= 1e-4 on the exported static shape",
            "parity_pass": all(
                float(item["max_abs"]) <= 1e-4 for item in parity.values()
            ),
        },
    }
    report_path = output_path.with_suffix(".export.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["gate"]["parity_pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
