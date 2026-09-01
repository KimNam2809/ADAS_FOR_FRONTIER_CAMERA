from __future__ import annotations

from typing import Any


ALLOWED_SOURCE_STATES = {
    "quarantined",
    "pretraining_only",
    "temporal_pretraining_only",
    "hard_negatives_and_candidate_mining_only",
    "synthetic_supplement_only",
    "target_training_candidate",
}
TARGET_CLASSES = {"fallen_person", "fallen_two_wheeler"}
SPLITS = ("train", "val", "test")
SCENARIO_GROUP_FIELDS = (
    "source_video_id", "scenario_family", "carla_town", "scenario_seed",
    "capture_session", "camera_configuration",
)


def _scenario_identity(group: Any) -> tuple[str, ...]:
    if isinstance(group, str):
        return (group,)
    if not isinstance(group, dict):
        return ()
    explicit = str(group.get("group_id", "")).strip()
    values = tuple(str(group.get(field, "")).strip() for field in SCENARIO_GROUP_FIELDS)
    if any(values):
        return values
    return (explicit,) if explicit else ()


def _split_has_no_leakage(groups: Any) -> bool:
    if not isinstance(groups, dict):
        return False
    identities: list[set[tuple[str, ...]]] = []
    for split in SPLITS:
        values = groups.get(split, [])
        if not isinstance(values, list) or not values:
            return False
        normalized = {_scenario_identity(value) for value in values}
        if () in normalized or not normalized:
            return False
        identities.append(normalized)
    return not any(
        identities[left] & identities[right]
        for left in range(len(identities))
        for right in range(left + 1, len(identities))
    )


def _provenance_is_complete(sources: Any) -> bool:
    if not isinstance(sources, list) or not sources:
        return False
    required = ("slug", "license", "provenance_url", "permission_type")
    return all(
        isinstance(source, dict)
        and all(str(source.get(field, "")).strip() for field in required)
        for source in sources
    )


def validate_source_catalog(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    taxonomy = payload.get("target_taxonomy", {})
    classes = set(taxonomy.get("specialist_detection_classes", []))
    if classes != TARGET_CLASSES:
        errors.append("specialist taxonomy must be fallen_person + fallen_two_wheeler")
    if taxonomy.get("temporal_event") != "fallen_rider":
        errors.append("fallen_rider must remain a temporal event, not an image class")
    seen: set[str] = set()
    for source in payload.get("sources", []):
        slug = str(source.get("slug", ""))
        if not slug or slug in seen:
            errors.append(f"duplicate or missing source slug: {slug!r}")
        seen.add(slug)
        if source.get("status") not in ALLOWED_SOURCE_STATES:
            errors.append(f"{slug}: invalid source status")
        if not source.get("license"):
            errors.append(f"{slug}: license field is required")
        if source.get("status") == "target_training_candidate" and source.get(
            "license"
        ) in {"unknown", "unverified", "requires_official_release_review"}:
            errors.append(f"{slug}: unverified license cannot enter target training")
    required = payload.get("required_target_dataset", {})
    if set(required.get("classes", [])) != TARGET_CLASSES:
        errors.append("required target dataset classes do not match taxonomy")
    if required.get("split_rule") != "group by original video before frame extraction":
        errors.append("video-group split is mandatory")
    return errors


def dataset_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    classes = manifest.get("instances", {})
    positive_images = int(manifest.get("positive_images", 0))
    negatives = int(manifest.get("negative_images", 0))
    total_clips = int(manifest.get("clip_count", 0))
    adverse_clips = int(manifest.get("night_or_adverse_clips", 0))
    scenario_groups = manifest.get("scenario_groups", manifest.get("video_groups", {}))
    val_real = int(manifest.get("validation_real_positives", 0))
    val_total = int(manifest.get("validation_total_positives", 0))
    test_source_types = {str(value).strip() for value in manifest.get("test_source_types", [])}
    gates = {
        "instances_per_class_at_least_250": all(
            int(classes.get(label, 0)) >= 250 for label in TARGET_CLASSES
        ),
        "negative_images_to_positive_images_at_least_2": positive_images > 0 and negatives / positive_images >= 2.0,
        "night_or_adverse_at_least_20_percent": adverse_clips / max(total_clips, 1) >= 0.20,
        "scenario_group_split_has_no_leakage": _split_has_no_leakage(scenario_groups),
        "licenses_approved": bool(manifest.get("licenses_approved", False)),
        "forward_dashcam_test_set_present": bool(
            manifest.get("forward_dashcam_test_set_present", False)
        ),
        "real_data_in_validation_at_least_30_percent": val_total > 0 and val_real / val_total >= 0.30,
        "test_set_is_100_percent_real_dashcam": (
            int(manifest.get("test_synthetic_count", -1)) == 0
            and test_source_types == {"real_dashcam"}
        ),
        "provenance_tracked_per_source": _provenance_is_complete(manifest.get("source_provenance", [])),
    }
    return {
        "status": "pass" if all(gates.values()) else "blocked",
        "gates": gates,
        "instances": {label: int(classes.get(label, 0)) for label in sorted(TARGET_CLASSES)},
        "negative_images_to_positive_images_ratio": round(negatives / max(positive_images, 1), 4),
        "validation_real_positive_fraction": round(val_real / max(val_total, 1), 4),
        "night_or_adverse_fraction": round(adverse_clips / max(total_clips, 1), 4),
    }
