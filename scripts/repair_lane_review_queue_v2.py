from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_review_queue_v2.json"
DEFAULT_REPORT = ROOT / "evaluation/rw10_lane_review_repair_report.json"
DEFAULT_BACKUP_DIR = ROOT / "evaluation/backups"
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
SCALE_CANDIDATES = ((1.0, 1.0), (1.0, 1.0 / 3.0), (1.0 / 3.0, 1.0), (1.0 / 3.0, 1.0 / 3.0))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def points(record: dict[str, Any]) -> list[list[float]]:
    return list(record.get("ego_left_boundary") or []) + list(record.get("ego_right_boundary") or [])


def in_bounds(point: list[float], width: int = FRAME_WIDTH, height: int = FRAME_HEIGHT) -> bool:
    return len(point) == 2 and 0 <= float(point[0]) <= width and 0 <= float(point[1]) <= height


def transformed(point: list[float], sx: float, sy: float) -> list[int]:
    return [round(float(point[0]) * sx), round(float(point[1]) * sy)]


def valid_transforms(record: dict[str, Any]) -> list[tuple[float, float]]:
    raw = points(record)
    if not raw:
        return [(1.0, 1.0)]
    x_scales = (1.0,) if all(0 <= float(point[0]) <= FRAME_WIDTH for point in raw) else (1.0 / 3.0,)
    y_scales = (1.0,) if all(0 <= float(point[1]) <= FRAME_HEIGHT for point in raw) else (1.0 / 3.0,)
    return [
        (sx, sy)
        for sx in x_scales
        for sy in y_scales
        if all(in_bounds(transformed(point, sx, sy)) for point in raw)
    ]


def apply_scale(record: dict[str, Any], sx: float, sy: float) -> None:
    for key in ("ego_left_boundary", "ego_right_boundary"):
        record[key] = [transformed(point, sx, sy) for point in record.get(key, [])]


def repair_record(record: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(record)
    actions: list[str] = []
    raw_points = points(updated)
    if raw_points and not all(in_bounds(point) for point in raw_points):
        # Do not transform a mixture of already-in-frame and out-of-frame points:
        # that pattern is ambiguous and requires a reviewer, not a guessed scale.
        inside = [in_bounds(point) for point in raw_points]
        candidates = valid_transforms(updated)
        if not all(inside) and not any(inside) and len(candidates) == 1 and candidates[0] != (1.0, 1.0):
            sx, sy = candidates[0]
            apply_scale(updated, sx, sy)
            actions.append(f"scale_x={sx:g};scale_y={sy:g}")
        else:
            updated["review_status"] = "needs_recheck"
            actions.append("ambiguous_coordinate_scale")
    if int(updated.get("ground_truth_lane_count") or 0) == 0 and points(updated):
        updated["review_status"] = "needs_recheck"
        actions.append("zero_lane_count_with_polyline")
    if actions:
        updated["repair_status"] = "auto_repaired" if updated.get("review_status") == "verified" else "needs_recheck"
        existing = str(updated.get("review_notes") or "").strip()
        repair_note = "Automatic queue audit: " + ", ".join(actions) + "."
        updated["repair_notes"] = repair_note
        updated["review_notes"] = f"{existing} {repair_note}".strip()
    return updated


def validate_post(queue: dict[str, Any]) -> dict[str, Any]:
    records = queue.get("records", [])
    issues: list[str] = []
    for record in records:
        status = record.get("review_status")
        if status not in {"pending", "verified", "needs_recheck"}:
            issues.append(f"{record.get('id')}:invalid_status")
        if status == "verified":
            for point in points(record):
                if not in_bounds(point):
                    issues.append(f"{record.get('id')}:out_of_frame_point")
            if int(record.get("ground_truth_lane_count") or 0) == 0 and points(record):
                issues.append(f"{record.get('id')}:zero_lane_polyline")
    split_sources: dict[str, set[str]] = {}
    for record in records:
        split_sources.setdefault(str(record.get("split")), set()).add(str(record.get("source")))
    split_values = list(split_sources.values())
    overlap = any(split_values[i] & split_values[j] for i in range(len(split_values)) for j in range(i + 1, len(split_values)))
    if overlap:
        issues.append("source_split_overlap")
    return {
        "status": "pass" if not issues else "fail",
        "records": len(records),
        "verified": sum(record.get("review_status") == "verified" for record in records),
        "pending": sum(record.get("review_status") == "pending" for record in records),
        "needs_recheck": sum(record.get("review_status") == "needs_recheck" for record in records),
        "split_source_overlap": overlap,
        "issues": issues,
    }


def run(queue_path: Path, report_path: Path, backup_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    original_bytes = queue_path.read_bytes()
    original = json.loads(original_bytes.decode("utf-8"))
    repaired = copy.deepcopy(original)
    actions = {"coordinate_scale_repairs": 0, "needs_recheck": 0, "unchanged": 0}
    for index, record in enumerate(original.get("records", [])):
        updated = repair_record(record)
        repaired["records"][index] = updated
        if updated == record:
            actions["unchanged"] += 1
        elif updated.get("review_status") == "needs_recheck":
            actions["needs_recheck"] += 1
        else:
            actions["coordinate_scale_repairs"] += 1
    validation = validate_post(repaired)
    backup_path = backup_dir / f"{queue_path.stem}.pre_repair_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    report = {
        "schema_version": 1,
        "task_id": "RW-10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queue": str(queue_path),
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "actions": actions,
        "post_validation": validation,
        "backup": str(backup_path),
        "repair_policy": {
            "frame_size": [FRAME_WIDTH, FRAME_HEIGHT],
            "scale_candidates": [[sx, sy] for sx, sy in SCALE_CANDIDATES],
            "ambiguous_coordinates_are_not_clipped": True,
            "semantic_conflicts_are_not_guessed": True,
        },
    }
    if validation["status"] != "pass":
        report["status"] = "aborted_validation_failed"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise RuntimeError(f"Repair validation failed; queue not overwritten: {validation}")
    if dry_run:
        report["status"] = "dry_run_pass"
    else:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(queue_path, backup_path)
        fd, temp_name = tempfile.mkstemp(prefix=f"{queue_path.stem}_", suffix=".json", dir=queue_path.parent)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            temp_path.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp_path, queue_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        report["status"] = "applied"
        report["repaired_sha256"] = sha256(queue_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely repair RW-10 lane review coordinates")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = run(args.queue, args.report, args.backup_dir, args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
