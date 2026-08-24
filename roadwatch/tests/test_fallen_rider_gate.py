import json
from copy import deepcopy
from pathlib import Path

import pytest

from roadwatch.fallen_rider import dataset_gate, validate_source_catalog


ROOT = Path(__file__).resolve().parents[1]


def complete_manifest() -> dict:
    return {
        "instances": {"fallen_person": 300, "fallen_two_wheeler": 300},
        "positive_images": 500,
        "negative_images": 1000,
        "clip_count": 100,
        "night_or_adverse_clips": 20,
        "scenario_groups": {
            "train": [{"source_video_id": "a", "scenario_family": "fall"}],
            "val": [{"source_video_id": "b", "scenario_family": "fall"}],
            "test": [{"source_video_id": "c", "scenario_family": "fall"}],
        },
        "licenses_approved": True,
        "forward_dashcam_test_set_present": True,
        "validation_real_positives": 30,
        "validation_total_positives": 100,
        "test_synthetic_count": 0,
        "test_source_types": ["real_dashcam"],
        "source_provenance": [{
            "slug": "owner-capture",
            "license": "CC-BY-4.0",
            "provenance_url": "https://example.invalid/permission-record",
            "permission_type": "owner_release",
        }],
    }


def test_rw08_catalog_is_valid_and_temporal_event_is_separate() -> None:
    payload = json.loads((ROOT / "configs/fallen_rider_sources.json").read_text(encoding="utf-8"))
    assert validate_source_catalog(payload) == []


def test_rw08_dataset_gate_passes_complete_target_manifest() -> None:
    assert dataset_gate(complete_manifest())["status"] == "pass"


@pytest.mark.parametrize(
    ("mutation", "failed_gate"),
    [
        ({"negative_images": 999}, "negative_images_to_positive_images_at_least_2"),
        ({"validation_real_positives": 29}, "real_data_in_validation_at_least_30_percent"),
        ({"test_synthetic_count": 1}, "test_set_is_100_percent_real_dashcam"),
        ({"test_source_types": ["synthetic"]}, "test_set_is_100_percent_real_dashcam"),
        ({"source_provenance": []}, "provenance_tracked_per_source"),
    ],
)
def test_rw08_dataset_gate_blocks_invalid_evidence(mutation: dict, failed_gate: str) -> None:
    manifest = complete_manifest()
    manifest.update(mutation)
    result = dataset_gate(manifest)
    assert result["status"] == "blocked"
    assert result["gates"][failed_gate] is False


def test_rw08_dataset_gate_blocks_scenario_leakage() -> None:
    manifest = complete_manifest()
    manifest["scenario_groups"]["test"] = [
        {"source_video_id": "a", "scenario_family": "fall"}
    ]
    result = dataset_gate(manifest)
    assert result["status"] == "blocked"
    assert result["gates"]["scenario_group_split_has_no_leakage"] is False


def test_rw08_legacy_manifest_cannot_pass_without_new_evidence() -> None:
    manifest = deepcopy(complete_manifest())
    for key in (
        "positive_images", "validation_real_positives", "validation_total_positives",
        "test_synthetic_count", "test_source_types", "source_provenance",
    ):
        manifest.pop(key)
    assert dataset_gate(manifest)["status"] == "blocked"
