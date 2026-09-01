from __future__ import annotations

import argparse
from collections import Counter
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

from roadwatch.ground_truth import events_for_source, score_events, validate_ground_truth  # noqa: E402
from roadwatch.regression import (  # noqa: E402
    aggregate_results,
    render_markdown,
    sha256_file,
    validate_manifest,
    truth_for_scenario,
)
from scripts.run_regression import run_tests  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Rescore an immutable RW-03 inference artifact")
    parser.add_argument("--input", default="reports/rw03-regression-latest.json")
    parser.add_argument("--manifest", default="configs/regression_manifest.json")
    parser.add_argument("--output", default="reports/rw03-regression-final.json")
    parser.add_argument("--markdown", default="reports/rw03-regression-final.md")
    parser.add_argument("--evidence", default="evaluation/rw03_baseline_evidence.json")
    args = parser.parse_args()

    input_path = PROJECT_ROOT / args.input
    manifest_path = PROJECT_ROOT / args.manifest
    source_report = json.loads(input_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    integrity = validate_manifest(manifest, PROJECT_ROOT, verify_hashes=True)
    if integrity["status"] != "pass":
        print(json.dumps(integrity, ensure_ascii=False, indent=2))
        return 2

    truth_path = PROJECT_ROOT / manifest["ground_truth"]
    ground_truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth_errors = validate_ground_truth(ground_truth)
    if truth_errors:
        raise SystemExit("Invalid regression ground truth: " + "; ".join(truth_errors))

    results = source_report["results"]
    for result in results:
        scenario = result["scenario"]
        start = float(scenario.get("start_seconds", 0.0))
        end = start + float(scenario["duration_seconds"])
        video_truth = events_for_source(ground_truth, str(scenario["source"]))
        clip_truth = truth_for_scenario(video_truth, start, end)
        metric = score_events(result.get("events", []), clip_truth)
        mandatory = result["mandatory_metrics"]
        mandatory["timestamp_event_metrics"] = metric
        mandatory["time_to_warning"] = {
            "status": metric["status"],
            "matches": metric.get("matches", []),
            "deadline_success_rate": metric.get("deadline_success_rate"),
        }
        mandatory["false_alerts_per_minute"].update(
            {
                "status": metric["status"],
                "value": metric.get("false_alerts_per_minute"),
                "qualification": metric.get("qualification"),
            }
        )
        mandatory["repeated_alert_rate"] = metric.get("duplicate_alert_rate")

    summary = aggregate_results(results, set(manifest["event_taxonomy"]), integrity)
    automated_tests = run_tests()
    gates = {**summary["gates"], "automated_tests": automated_tests["status"] == "pass"}
    report = {
        **source_report,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "manifest": {"path": args.manifest, "sha256": sha256_file(manifest_path)},
        "ground_truth": {"path": manifest["ground_truth"], "sha256": sha256_file(truth_path)},
        "integrity": integrity,
        "automated_tests": automated_tests,
        "gates": gates,
        "summary": summary,
        "results": results,
        "rescore_provenance": {
            "parent_inference_artifact": args.input,
            "parent_inference_sha256": sha256_file(input_path),
            "reason": "Correct verified-negative measurement denominator without rerunning inference",
            "inference_events_unchanged": True,
        },
    }
    output = PROJECT_ROOT / args.output
    markdown = PROJECT_ROOT / args.markdown
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown.write_text(render_markdown(report), encoding="utf-8")
    event_counts = Counter(
        str(event.get("event_type"))
        for result in results
        for event in result.get("events", [])
    )
    false_positive_counts = Counter(
        str(event.get("event_type"))
        for result in results
        for event in result["mandatory_metrics"]["timestamp_event_metrics"].get(
            "false_predictions", []
        )
    )
    evidence = {
        "schema_version": 1,
        "task_id": "RW-03",
        "generated_at": report["generated_at"],
        "status": report["status"],
        "release_id": report["release_id"],
        "manifest": report["manifest"],
        "ground_truth": report["ground_truth"],
        "config_sha256": report["config_sha256"],
        "effective_config": report["effective_config"],
        "determinism": report["determinism"],
        "gates": gates,
        "summary": summary,
        "events_by_type": dict(event_counts),
        "false_positives_by_type": dict(false_positive_counts),
        "full_report": {
            "path": args.output,
            "sha256": sha256_file(output),
            "git_policy": "local generated artifact; regenerate with scripts/run_regression.py",
        },
        "rescore_provenance": report["rescore_provenance"],
    }
    evidence_path = PROJECT_ROOT / args.evidence
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "gates": gates, "summary": summary}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
