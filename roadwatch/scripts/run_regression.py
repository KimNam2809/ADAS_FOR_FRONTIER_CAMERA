from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["ROADWATCH_DISABLE_AUDIO"] = "1"

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.ground_truth import validate_ground_truth  # noqa: E402
from roadwatch.regression import (  # noqa: E402
    aggregate_results,
    render_markdown,
    seed_everything,
    sha256_file,
    sha256_json,
    validate_manifest,
)
from scripts.evaluate import run_scenario  # noqa: E402


def run_tests() -> dict:
    command = [sys.executable, "-m", "pytest", "tests", "-q"]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "status": "pass" if completed.returncode == 0 else "fail",
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic RoadWatch RW-03 regression")
    parser.add_argument("--manifest", default="configs/regression_manifest.json")
    parser.add_argument("--suite", choices=["locked_media", "dashcam_sample"])
    parser.add_argument("--scenario", action="append")
    parser.add_argument(
        "--object-profile",
        help="Override manifest object profile for a recorded promotion-candidate run",
    )
    parser.add_argument("--max-wall-seconds", type=float, default=900.0)
    parser.add_argument("--skip-hashes", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--output", default="reports/rw03-regression-latest.json")
    parser.add_argument("--markdown", default="reports/rw03-regression-latest.md")
    args = parser.parse_args()

    manifest_path = PROJECT_ROOT / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    integrity = validate_manifest(manifest, PROJECT_ROOT, verify_hashes=not args.skip_hashes)
    if integrity["status"] != "pass":
        print(json.dumps(integrity, ensure_ascii=False, indent=2))
        return 2

    scenarios = list(manifest["scenarios"])
    if args.suite:
        scenarios = [item for item in scenarios if item["suite"] == args.suite]
    if args.scenario:
        wanted = set(args.scenario)
        scenarios = [item for item in scenarios if item["id"] in wanted]
    if not scenarios:
        raise SystemExit("No regression scenarios selected")

    ground_truth_path = PROJECT_ROOT / manifest["ground_truth"]
    ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    truth_errors = validate_ground_truth(ground_truth)
    if truth_errors:
        raise SystemExit("Invalid regression ground truth: " + "; ".join(truth_errors))

    determinism = seed_everything(int(manifest["seed"]))
    object_profile = args.object_profile or manifest["object_profile"]
    runtime_path = PROJECT_ROOT / "configs" / "__regression_runtime__.json"
    config_manager = ConfigManager(runtime_path=runtime_path)
    config_manager.update(
        {
            "app": {
                "loop_video": False,
                "pace_replay": False,
                "max_processed_fps": float(manifest["max_processed_fps"]),
            },
            "audio": {"enabled": False},
            "inference": {"object_profile": object_profile},
        },
        persist=False,
    )
    effective_config = config_manager.snapshot()

    results = []
    for index, scenario in enumerate(scenarios, start=1):
        print(f"[{index}/{len(scenarios)}] {scenario['id']}", flush=True)
        results.append(
            run_scenario(
                scenario,
                max_wall_seconds=args.max_wall_seconds,
                object_profile=object_profile,
                ground_truth=ground_truth,
            )
        )

    summary = aggregate_results(results, set(manifest["event_taxonomy"]), integrity)
    automated_tests = (
        {"status": "skipped", "reason": "--skip-tests"} if args.skip_tests else run_tests()
    )
    gates = {
        **summary["gates"],
        "automated_tests": automated_tests["status"] == "pass",
    }
    report = {
        "schema_version": 1,
        "task_id": "RW-03",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "release_id": manifest["release_id"],
        "object_profile": object_profile,
        "manifest": {
            "path": args.manifest,
            "sha256": sha256_file(manifest_path),
        },
        "ground_truth": {
            "path": manifest["ground_truth"],
            "sha256": sha256_file(ground_truth_path),
        },
        "config_sha256": sha256_json(effective_config),
        "effective_config": effective_config,
        "determinism": determinism,
        "integrity": integrity,
        "automated_tests": automated_tests,
        "gates": gates,
        "summary": summary,
        "results": results,
    }
    output = PROJECT_ROOT / args.output
    markdown = PROJECT_ROOT / args.markdown
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "gates": gates, "summary": summary}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
