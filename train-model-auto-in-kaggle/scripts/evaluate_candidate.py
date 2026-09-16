from __future__ import annotations

import argparse
from pathlib import Path

from common import load_json, utc_now, write_json


def evaluate(metrics: dict, gates: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for key, threshold in gates["static_metrics"].items():
        metric_key = key.removesuffix("_min")
        value = metrics.get(metric_key)
        if value is None or float(value) < float(threshold):
            failures.append(f"{metric_key}:{value}<{threshold}")
    return not failures, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--gates", default="train-model-auto-in-kaggle/configs/sign_release_gates.yaml")
    parser.add_argument("--output", default="build/evaluation.json")
    args = parser.parse_args()
    metrics, gates = load_json(Path(args.metrics)), load_json(Path(args.gates))
    passed, failures = evaluate(metrics, gates)
    report = {
        "status": "PASS_PENDING_HUMAN_GATE" if passed else "REJECT",
        "evaluated_at": utc_now(),
        "failures": failures,
        "human_gate_required": True,
        "promotion_allowed": False,
    }
    write_json(Path(args.output), report)
    print(report["status"])
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
