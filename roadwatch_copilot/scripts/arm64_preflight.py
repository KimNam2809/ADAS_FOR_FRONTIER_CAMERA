from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def collect() -> dict:
    try:
        import torch

        cuda = bool(torch.cuda.is_available())
        gpu = torch.cuda.get_device_name(0) if cuda else None
        torch_version = torch.__version__
    except Exception as exc:  # pragma: no cover - depends on target runtime
        cuda, gpu, torch_version = False, None, f"error:{exc}"
    architecture = platform.machine().lower()
    checks = {
        "architecture_is_aarch64": architecture in {"aarch64", "arm64"},
        "cuda_available": cuda,
        "gpu_is_t4g": bool(gpu and "T4G" in gpu.upper()),
    }
    return {
        "schema_version": 1,
        "task_id": "RW-13",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(checks.values()) else "not_on_target",
        "checks": checks,
        "architecture": architecture,
        "gpu": gpu,
        "torch": torch_version,
        "scope": "ARM64 cloud packaging/CUDA parity; not Jetson Orin validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="RW-13 ARM64 cloud preflight")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/rw13-arm64-preflight.json")
    args = parser.parse_args()
    report = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
