from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "objects_baseline": ("yolo11n.onnx", "images:1x3x640x640"),
    "objects_v1_1": ("roadwatch_objects_v1_1.onnx", "images:1x3x640x640"),
    "traffic_sign": ("yolo11s_vietnam_traffic.onnx", "images:1x3x640x640"),
    "yolop": ("yolop_lane_detection_640.onnx", "input:1x3x640x640"),
    "ufldv2": ("ufldv2_culane_res18_320x1600.onnx", "images:1x3x320x1600"),
}


def parse_metric(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and benchmark FP16 TensorRT engines on Jetson")
    parser.add_argument("--trtexec", default="/usr/src/tensorrt/bin/trtexec")
    parser.add_argument("--model", action="append", choices=sorted(MODELS))
    parser.add_argument("--workspace-mib", type=int, default=2048)
    parser.add_argument("--duration", type=int, default=20)
    parser.add_argument("--output", default="reports/jetson-tensorrt-benchmark.json")
    args = parser.parse_args()
    trtexec = shutil.which(args.trtexec) or (args.trtexec if Path(args.trtexec).exists() else None)
    if trtexec is None:
        raise FileNotFoundError("trtexec not found; run this script inside a JetPack/TensorRT Jetson image")
    selected = args.model or list(MODELS)
    rows = []
    engines = PROJECT_ROOT / "models" / "engines"
    engines.mkdir(parents=True, exist_ok=True)
    for name in selected:
        model_name, shape = MODELS[name]
        onnx = PROJECT_ROOT / "models" / model_name
        if not onnx.exists():
            rows.append({"model": name, "status": "missing", "path": str(onnx)})
            continue
        engine = engines / f"{onnx.stem}.fp16.engine"
        command = [
            str(trtexec), f"--onnx={onnx}", f"--saveEngine={engine}", "--fp16",
            f"--shapes={shape}", f"--memPoolSize=workspace:{args.workspace_mib}",
            f"--duration={args.duration}", "--warmUp=1000", "--useSpinWait",
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        log = completed.stdout + "\n" + completed.stderr
        log_path = PROJECT_ROOT / "reports" / f"trtexec-{name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(log, encoding="utf-8")
        rows.append(
            {
                "model": name,
                "status": "ok" if completed.returncode == 0 else "failed",
                "onnx_mb": round(onnx.stat().st_size / 1024**2, 2),
                "engine_mb": round(engine.stat().st_size / 1024**2, 2) if engine.exists() else None,
                "throughput_fps": parse_metric(log, r"Throughput:\s+([0-9.]+)\s+qps"),
                "gpu_compute_mean_ms": parse_metric(log, r"GPU Compute Time:.*?mean = ([0-9.]+) ms"),
                "latency_p95_ms": parse_metric(log, r"Latency:.*?percentile\(95%\) = ([0-9.]+) ms"),
                "return_code": completed.returncode,
                "log": str(log_path),
            }
        )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "models": rows,
        "acceptance": {
            "object_p95_ms_max": 35,
            "sign_p95_ms_max": 50,
            "lane_p95_ms_max": 80,
            "pipeline_fps_min": 12,
            "power_mode": "record nvpmodel mode and tegrastats separately",
            "runtime_integration": "blocked until every selected engine passes and TensorRT adapters are validated",
        },
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if rows and all(row["status"] == "ok" for row in rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
