from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

import numpy as np


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def seed_everything(seed: int) -> dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)
    torch_status = "not_installed"
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if hasattr(torch, "use_deterministic_algorithms"):
            torch.use_deterministic_algorithms(True, warn_only=True)
        torch_status = "seeded"
    except ImportError:
        pass
    return {"seed": seed, "python": "seeded", "numpy": "seeded", "torch": torch_status}


def validate_manifest(
    manifest: dict[str, Any], project_root: Path, verify_hashes: bool = True
) -> dict[str, Any]:
    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    source_hash_cache: dict[Path, str] = {}
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    taxonomy = set(manifest.get("event_taxonomy", []))
    if not taxonomy:
        errors.append("event_taxonomy is required")
    scenario_ids: set[str] = set()
    for scenario in manifest.get("scenarios", []):
        scenario_id = str(scenario.get("id", ""))
        if not scenario_id or scenario_id in scenario_ids:
            errors.append(f"duplicate/missing scenario id: {scenario_id!r}")
        scenario_ids.add(scenario_id)
        source = project_root / "media" / str(scenario.get("source", ""))
        expected_hash = str(scenario.get("source_sha256", "")).upper()
        status = "pass"
        actual_hash = None
        if not source.is_file():
            status = "fail"
            errors.append(f"{scenario_id}: source missing: {source.name}")
        elif verify_hashes:
            if source not in source_hash_cache:
                source_hash_cache[source] = sha256_file(source)
            actual_hash = source_hash_cache[source]
            if actual_hash != expected_hash:
                status = "fail"
                errors.append(f"{scenario_id}: source SHA-256 mismatch")
        checks.append(
            {
                "kind": "media",
                "scenario_id": scenario_id,
                "path": f"media/{source.name}",
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "status": status,
            }
        )
        start = float(scenario.get("start_seconds", -1))
        duration = float(scenario.get("duration_seconds", -1))
        if start < 0 or duration <= 0:
            errors.append(f"{scenario_id}: invalid time bounds")
        unknown_expected = set(scenario.get("expected_event_types", [])) - taxonomy
        if unknown_expected:
            errors.append(f"{scenario_id}: unknown expected event types {sorted(unknown_expected)}")

    for artifact in manifest.get("locked_artifacts", []):
        relative = Path(str(artifact.get("path", "")))
        path = project_root / relative
        expected_hash = str(artifact.get("sha256", "")).upper()
        status = "pass"
        actual_hash = None
        if not path.is_file():
            status = "fail"
            errors.append(f"locked artifact missing: {relative.as_posix()}")
        elif verify_hashes:
            actual_hash = sha256_file(path)
            if actual_hash != expected_hash:
                status = "fail"
                errors.append(f"locked artifact SHA-256 mismatch: {relative.as_posix()}")
        checks.append(
            {
                "kind": "artifact",
                "path": relative.as_posix(),
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "status": status,
            }
        )
    return {"status": "pass" if not errors else "fail", "checks": checks, "errors": errors}


def truth_for_scenario(video_truth: dict[str, Any] | None, start: float, end: float) -> dict[str, Any] | None:
    if not video_truth:
        return None

    def overlaps(item: dict[str, Any]) -> bool:
        return float(item["end_seconds"]) >= start and float(item["start_seconds"]) <= end

    def clipped(item: dict[str, Any]) -> dict[str, Any]:
        copy = dict(item)
        copy["start_seconds"] = max(start, float(item["start_seconds"]))
        copy["end_seconds"] = min(end, float(item["end_seconds"]))
        return copy

    return {
        **{key: value for key, value in video_truth.items() if key not in {"events", "coverage", "negative_windows"}},
        "events": [dict(item) for item in video_truth.get("events", []) if overlaps(item)],
        "coverage": [clipped(item) for item in video_truth.get("coverage", []) if overlaps(item)],
        "negative_windows": [
            clipped(item) for item in video_truth.get("negative_windows", []) if overlaps(item)
        ],
    }


def aggregate_results(
    results: list[dict[str, Any]], taxonomy: set[str], integrity: dict[str, Any]
) -> dict[str, Any]:
    observed = {
        str(event.get("event_type"))
        for result in results
        for event in result.get("events", [])
    }
    unexpected = sorted(observed - taxonomy)
    completed = sum(bool(result.get("completed")) for result in results)
    timestamp = [
        result.get("mandatory_metrics", {}).get("timestamp_event_metrics", {})
        for result in results
    ]
    totals = {
        key: sum(int(item.get(key, 0) or 0) for item in timestamp)
        for key in ("true_positive", "false_positive", "false_negative")
    }
    tp, fp, fn = totals["true_positive"], totals["false_positive"], totals["false_negative"]
    gates = {
        "manifest_and_hash_integrity": integrity.get("status") == "pass",
        "all_scenarios_completed": completed == len(results) and bool(results),
        "no_unexpected_event_type": not unexpected,
        "all_scenarios_have_measured_ground_truth": all(
            item.get("status") == "measured" for item in timestamp
        ),
    }
    return {
        "status": "pass" if all(gates.values()) else "fail",
        "gates": gates,
        "scenario_count": len(results),
        "completed_scenarios": completed,
        "observed_event_types": sorted(observed),
        "unexpected_event_types": unexpected,
        **totals,
        "precision": round(tp / max(tp + fp, 1), 4),
        "recall": round(tp / max(tp + fn, 1), 4),
        "miss_rate": round(fn / max(tp + fn, 1), 4),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# RoadWatch Regression Report",
        "",
        f"- Status: **{report['status'].upper()}**",
        f"- Release: `{report['release_id']}`",
        f"- Seed: `{report['determinism']['seed']}`",
        f"- Config SHA-256: `{report['config_sha256']}`",
        f"- Scenarios: {summary['completed_scenarios']}/{summary['scenario_count']} completed",
        f"- Event precision/recall: {summary['precision']:.4f} / {summary['recall']:.4f}",
        f"- Unexpected event types: {summary['unexpected_event_types'] or 'none'}",
        "",
        "## Gates",
        "",
        "| Gate | Result |",
        "|---|---|",
    ]
    lines.extend(
        f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
        for name, passed in report["gates"].items()
    )
    lines.extend(["", "## Scenarios", "", "| ID | Completed | Events | TP | FP | FN |", "|---|---:|---:|---:|---:|---:|"])
    for item in report["results"]:
        metric = item["mandatory_metrics"]["timestamp_event_metrics"]
        lines.append(
            f"| `{item['scenario']['id']}` | {'yes' if item['completed'] else 'no'} | "
            f"{len(item.get('events', []))} | {metric.get('true_positive', 0)} | "
            f"{metric.get('false_positive', 0)} | {metric.get('false_negative', 0)} |"
        )
    lines.extend(
        [
            "",
            "> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; "
            "RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, "
            "không tự động promote model khi metric thấp.",
            "",
        ]
    )
    return "\n".join(lines)
