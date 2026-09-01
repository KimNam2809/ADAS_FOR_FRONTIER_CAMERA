from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

import torch


class OnnxOutputWrapper(torch.nn.Module):
    """Convert UFLDv2's dictionary output into stable named ONNX outputs."""

    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, image: torch.Tensor) -> tuple[torch.Tensor, ...]:
        output = self.model(image)
        return (
            output["loc_row"],
            output["loc_col"],
            output["exist_row"],
            output["exist_col"],
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export official UFLDv2 CULane R18 to ONNX")
    parser.add_argument("--repo", type=Path, default=Path(".cache/ufldv2"))
    parser.add_argument("--checkpoint", type=Path, default=Path("models/ufldv2_culane_res18.pth"))
    parser.add_argument(
        "--output", type=Path, default=Path("models/ufldv2_culane_res18_320x1600.onnx")
    )
    parser.add_argument("--opset", type=int, default=17)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    checkpoint_path = args.checkpoint.resolve()
    output_path = args.output.resolve()
    if not repo.exists():
        raise FileNotFoundError(f"Missing official UFLDv2 repository: {repo}")
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Missing UFLDv2 checkpoint: {checkpoint_path}")

    sys.path.insert(0, str(repo))
    # The upstream utility module imports NVIDIA DALI even when only model
    # construction is needed. Provide its small initialization helper locally
    # so CPU-only export does not require the training-only DALI dependency.
    common_stub = types.ModuleType("utils.common")

    def initialize_weights(*models: torch.nn.Module) -> None:
        def initialize(module: torch.nn.Module) -> None:
            if isinstance(module, torch.nn.Conv2d):
                torch.nn.init.kaiming_normal_(module.weight, nonlinearity="relu")
                if module.bias is not None:
                    torch.nn.init.constant_(module.bias, 0)
            elif isinstance(module, torch.nn.Linear):
                module.weight.data.normal_(0.0, std=0.01)
            elif isinstance(module, torch.nn.BatchNorm2d):
                torch.nn.init.constant_(module.weight, 1)
                torch.nn.init.constant_(module.bias, 0)
            else:
                for child in module.children():
                    initialize(child)

        for candidate in models:
            initialize(candidate)

    common_stub.initialize_weights = initialize_weights
    sys.modules["utils.common"] = common_stub
    from model.model_culane import parsingNet

    model = parsingNet(
        pretrained=False,
        backbone="18",
        num_grid_row=200,
        num_cls_row=72,
        num_grid_col=100,
        num_cls_col=81,
        num_lane_on_row=4,
        num_lane_on_col=4,
        use_aux=False,
        input_height=320,
        input_width=1600,
        fc_norm=True,
    )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    state_dict = checkpoint.get("model", checkpoint)
    compatible = {
        (key[7:] if key.startswith("module.") else key): value
        for key, value in state_dict.items()
    }
    incompatible = model.load_state_dict(compatible, strict=False)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise RuntimeError(
            "Checkpoint is incompatible: "
            f"missing={incompatible.missing_keys}, unexpected={incompatible.unexpected_keys}"
        )

    wrapper = OnnxOutputWrapper(model.eval().cpu())
    dummy = torch.zeros((1, 3, 320, 1600), dtype=torch.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with torch.inference_mode():
        torch.onnx.export(
            wrapper,
            dummy,
            output_path,
            input_names=["images"],
            output_names=["loc_row", "loc_col", "exist_row", "exist_col"],
            opset_version=args.opset,
            do_constant_folding=True,
            dynamo=False,
        )

    result = {
        "status": "exported",
        "checkpoint": str(checkpoint_path),
        "output": str(output_path),
        "size_mb": round(output_path.stat().st_size / 1024**2, 2),
        "input": [1, 3, 320, 1600],
        "outputs": {
            "loc_row": [1, 200, 72, 4],
            "loc_col": [1, 100, 81, 4],
            "exist_row": [1, 2, 72, 4],
            "exist_col": [1, 2, 81, 4],
        },
        "opset": args.opset,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
