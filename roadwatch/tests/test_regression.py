import json
from pathlib import Path

from roadwatch.regression import (
    aggregate_results,
    sha256_file,
    sha256_json,
    truth_for_scenario,
    validate_manifest,
)


def test_hashes_are_stable(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_bytes(b"roadwatch")
    assert sha256_file(path) == sha256_file(path)
    assert sha256_json({"b": 2, "a": 1}) == sha256_json({"a": 1, "b": 2})


def test_truth_is_limited_to_scenario_window() -> None:
    truth = {
        "source": "clip.mp4",
        "events": [
            {"id": "inside", "start_seconds": 12, "end_seconds": 14},
            {"id": "outside", "start_seconds": 30, "end_seconds": 31},
        ],
        "coverage": [
            {"start_seconds": 0, "end_seconds": 20, "exhaustive": True}
        ],
        "negative_windows": [{"start_seconds": 5, "end_seconds": 11}],
    }
    clipped = truth_for_scenario(truth, 10, 20)
    assert [item["id"] for item in clipped["events"]] == ["inside"]
    assert clipped["coverage"][0]["start_seconds"] == 10
    assert clipped["negative_windows"][0]["start_seconds"] == 10


def test_manifest_rejects_hash_mismatch(tmp_path: Path) -> None:
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "clip.mp4").write_bytes(b"video")
    manifest = {
        "schema_version": 1,
        "event_taxonomy": ["fcw"],
        "scenarios": [
            {
                "id": "scenario",
                "source": "clip.mp4",
                "source_sha256": "00" * 32,
                "start_seconds": 0,
                "duration_seconds": 1,
                "expected_event_types": ["fcw"],
            }
        ],
        "locked_artifacts": [],
    }
    report = validate_manifest(manifest, tmp_path)
    assert report["status"] == "fail"
    assert any("SHA-256 mismatch" in error for error in report["errors"])


def test_aggregate_blocks_unexpected_taxonomy() -> None:
    result = {
        "completed": True,
        "events": [{"event_type": "made_up_event"}],
        "mandatory_metrics": {
            "timestamp_event_metrics": {
                "status": "measured",
                "true_positive": 0,
                "false_positive": 1,
                "false_negative": 0,
            }
        },
    }
    summary = aggregate_results([result], {"fcw"}, {"status": "pass"})
    assert summary["status"] == "fail"
    assert summary["unexpected_event_types"] == ["made_up_event"]


def test_tracked_manifest_has_locked_hashes() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "configs" / "regression_manifest.json").read_text())
    assert len(manifest["scenarios"]) == 37
    locked_paths = {item["path"] for item in manifest["locked_artifacts"]}
    assert len(locked_paths) >= 10
    assert "evaluation/regression_ground_truth.json" in locked_paths
    assert "backend/roadwatch/risk.py" in locked_paths
    assert "scripts/run_regression.py" in locked_paths
