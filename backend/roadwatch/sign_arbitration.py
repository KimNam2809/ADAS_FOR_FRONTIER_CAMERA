from __future__ import annotations

from typing import Any

from .alert_copy import combined_speed_limit_message, validate_alert_message


SEVERITY_RANK = {"informational": 0, "advisory": 1, "warning": 2, "critical": 3}
LANE_BINDING_MIN_CONFIDENCE = 0.75


def lane_binding_metadata(candidate: dict[str, Any]) -> dict[str, Any]:
    """Normalize optional evidence linking a sign to the ego lane.

    A sign detector normally knows only the sign class. It must not be allowed
    to assert that a lane-specific speed applies to the ego vehicle without an
    explicit lane/arrow/road-geometry binding supplied by an upstream module.
    """

    nested = candidate.get("evidence")
    evidence = nested if isinstance(nested, dict) else {}
    status = str(
        candidate.get("lane_binding_status")
        or evidence.get("lane_binding_status")
        or ""
    ).strip().lower()
    aliases = {
        "ego": "ego_lane",
        "ego_lane": "ego_lane",
        "same_lane": "ego_lane",
        "other": "other_lane",
        "other_lane": "other_lane",
        "adjacent_lane": "other_lane",
        "all": "all_lanes",
        "all_lanes": "all_lanes",
        "unknown": "unknown",
    }
    status = aliases.get(status, "unknown")
    applies = candidate.get(
        "applies_to_ego_lane",
        evidence.get("applies_to_ego_lane"),
    )
    if isinstance(applies, str):
        normalized = applies.strip().lower()
        if normalized in {"true", "yes", "1", "ego", "ego_lane"}:
            applies = True
        elif normalized in {"false", "no", "0", "other", "other_lane"}:
            applies = False
        else:
            applies = None
    elif not isinstance(applies, bool):
        applies = None
    if applies is True:
        status = "ego_lane"
    elif applies is False and status == "unknown":
        status = "other_lane"
    confidence_value = candidate.get(
        "lane_binding_confidence",
        evidence.get("lane_binding_confidence", 0.0),
    )
    try:
        confidence = max(0.0, min(1.0, float(confidence_value)))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "lane_binding_status": status,
        "lane_binding_confidence": round(confidence, 4),
        "applies_to_ego_lane": applies,
        "lane_index": candidate.get("lane_index", evidence.get("lane_index")),
    }


def is_ego_lane_bound(candidate: dict[str, Any]) -> bool:
    """Return true only for explicit, sufficiently confident ego-lane evidence."""

    metadata = lane_binding_metadata(candidate)
    return (
        metadata["lane_binding_status"] in {"ego_lane", "all_lanes"}
        and metadata["lane_binding_confidence"] >= LANE_BINDING_MIN_CONFIDENCE
    )


def sign_family(candidate: dict[str, Any]) -> str:
    if candidate.get("event_type") == "speed_sign":
        return "speed_limit"
    evidence = candidate.get("evidence", {})
    return str(evidence.get("sign_kind") or evidence.get("sign_family") or candidate.get("cooldown_key", "unknown"))


def is_speed_candidate(candidate: dict[str, Any]) -> bool:
    """Recognize speed signs even when an upstream adapter uses traffic_sign."""

    if candidate.get("event_type") == "speed_sign":
        return True
    evidence = candidate.get("evidence")
    if not isinstance(evidence, dict):
        return False
    return str(evidence.get("sign_kind", "")).lower() in {
        "speed_limit",
        "speed_limit_maximum",
        "speed_limit_minimum",
    } or str(evidence.get("speed_role", "")).lower() in {"maximum", "minimum"}


def sign_rank(candidate: dict[str, Any]) -> tuple[int, float, float, str]:
    """Return a total ordering so input permutations cannot change the result."""

    return (
        SEVERITY_RANK.get(str(candidate.get("severity")), 0),
        float(candidate.get("road_relevance", 1.0)),
        float(candidate.get("risk_score", 0.0)),
        str(candidate.get("cooldown_key", "")),
    )


def arbitrate_sign_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep one deterministic candidate per semantic sign family.

    Different sign families remain available for HUD display. The AlertGovernor
    selects at most one audio winner after road-user hazards have been ranked.
    """

    speed_candidates = [item for item in candidates if is_speed_candidate(item)]
    speed_by_role: dict[str, list[dict[str, Any]]] = {"maximum": [], "minimum": []}
    for item in speed_candidates:
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        role = str(evidence.get("speed_role") or "maximum").lower()
        speed_by_role.setdefault(role, []).append(item)
    pre_suppressed: list[dict[str, Any]] = []
    selected_speed: dict[str, dict[str, Any]] = {}
    ambiguous_roles: set[str] = set()
    for role, role_candidates in speed_by_role.items():
        if not role_candidates:
            continue
        values = {
            item.get("evidence", {}).get("speed_value")
            for item in role_candidates
        } - {None}
        bound = [item for item in role_candidates if is_ego_lane_bound(item)]
        if len(values) > 1 and not bound:
            ambiguous_roles.add(role)
            pre_suppressed.extend(role_candidates)
            continue
        if bound:
            best_bound = max(
                bound,
                key=lambda item: float(
                    item.get("evidence", {}).get("lane_binding_confidence", 0.0)
                ),
            )
            selected_speed[role] = best_bound
            pre_suppressed.extend(item for item in role_candidates if item is not best_bound)
        else:
            selected_speed[role] = max(role_candidates, key=sign_rank)
            pre_suppressed.extend(item for item in role_candidates if item is not selected_speed[role])

    # Two different speed roles are safe to combine only when both are proven
    # to regulate the ego lane. Without that evidence, do not invent a combined
    # sentence that could apply to an adjacent lane.
    maximum = selected_speed.get("maximum")
    minimum = selected_speed.get("minimum")
    if ambiguous_roles or (
        maximum is not None
        and minimum is not None
        and not (is_ego_lane_bound(maximum) and is_ego_lane_bound(minimum))
    ):
        template = max(speed_candidates, key=sign_rank)
        ambiguity_role = "minimum" if ambiguous_roles == {"minimum"} else "maximum"
        ambiguity = {
            **template,
            "event_type": "traffic_sign",
            "severity": "advisory",
            "message": validate_alert_message(
                "Nhiều biển tốc độ tối thiểu; xem làn mình."
                if ambiguity_role == "minimum"
                else "Nhiều biển giới hạn tốc độ; xem làn mình."
            ),
            "risk_score": 0.48,
            "cooldown_key": "traffic_sign:speed_limit_lane_ambiguous",
            "audio_eligible": False,
            "evidence": {
                **template.get("evidence", {}),
                "speed_value": None,
                "speed_values": sorted(
                    {
                        item.get("evidence", {}).get("speed_value")
                        for item in speed_candidates
                        if item.get("evidence", {}).get("speed_value") is not None
                    }
                ),
                "sign_kind": "speed_limit_lane_ambiguous",
                "lane_binding_status": "unknown",
                "lane_binding_confidence": 0.0,
                "orientation_audio_suppressed": True,
            },
        }
        candidates = [item for item in candidates if not is_speed_candidate(item)] + [ambiguity]
        pre_suppressed.extend(
            item for item in (maximum, minimum) if item is not None and item not in pre_suppressed
        )
    elif maximum is not None and minimum is not None:
        max_value = maximum.get("evidence", {}).get("speed_value")
        min_value = minimum.get("evidence", {}).get("speed_value")
        combined = {
            **maximum,
            "message": validate_alert_message(
                combined_speed_limit_message(int(max_value), int(min_value))
            ),
            "cooldown_key": f"speed_sign:combined:{max_value}:{min_value}",
            "evidence": {
                **maximum.get("evidence", {}),
                "speed_role": "combined",
                "maximum_speed_value": max_value,
                "minimum_speed_value": min_value,
                "lane_binding_status": "ego_lane",
                "lane_binding_confidence": min(
                    float(maximum.get("evidence", {}).get("lane_binding_confidence", 0.0)),
                    float(minimum.get("evidence", {}).get("lane_binding_confidence", 0.0)),
                ),
            },
        }
        selected_speed = {"combined": combined}
        pre_suppressed.extend(
            item
            for item in speed_candidates
            if item is not maximum and item is not minimum
        )
        pre_suppressed.extend([minimum])
        candidates = [item for item in candidates if not is_speed_candidate(item)] + [combined]
    else:
        candidates = [item for item in candidates if not is_speed_candidate(item)] + list(selected_speed.values())

    selected: dict[str, dict[str, Any]] = {}
    suppressed: list[dict[str, Any]] = list(pre_suppressed)
    non_signs: list[dict[str, Any]] = []
    for candidate in candidates:
        if not (candidate.get("is_traffic_sign") or candidate.get("event_type") == "speed_sign"):
            non_signs.append(candidate)
            continue
        family = sign_family(candidate)
        current = selected.get(family)
        if current is None or sign_rank(candidate) > sign_rank(current):
            if current is not None:
                suppressed.append(current)
            selected[family] = candidate
        else:
            suppressed.append(candidate)
    ordered_signs = sorted(selected.values(), key=sign_rank, reverse=True)
    return non_signs + ordered_signs, suppressed
