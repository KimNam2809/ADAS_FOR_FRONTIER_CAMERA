from __future__ import annotations

from typing import Any


SEVERITY_RANK = {"informational": 0, "advisory": 1, "warning": 2, "critical": 3}


def sign_family(candidate: dict[str, Any]) -> str:
    if candidate.get("event_type") == "speed_sign":
        return "speed_limit"
    evidence = candidate.get("evidence", {})
    return str(evidence.get("sign_kind") or evidence.get("sign_family") or candidate.get("cooldown_key", "unknown"))


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

    speed_candidates = [
        item for item in candidates if item.get("event_type") == "speed_sign"
    ]
    speed_values = {
        item.get("evidence", {}).get("speed_value") for item in speed_candidates
    } - {None}
    lane_bound = [
        item
        for item in speed_candidates
        if float(item.get("evidence", {}).get("lane_binding_confidence", 0.0)) >= 0.75
    ]
    pre_suppressed: list[dict[str, Any]] = []
    if len(speed_values) > 1 and not lane_bound:
        # Without lane-instance geometry, selecting one of several simultaneous
        # lane-specific limits is unsafe. Keep an explicit ambiguity advisory
        # instead of asserting the wrong active limit.
        template = max(speed_candidates, key=sign_rank)
        ambiguity = {
            **template,
            "event_type": "traffic_sign",
            "severity": "advisory",
            "message": "Phát hiện nhiều biển tốc độ theo làn. Hãy quan sát biển áp dụng cho làn đang đi.",
            "risk_score": 0.48,
            "cooldown_key": "traffic_sign:speed_limit_lane_ambiguous",
            "evidence": {
                **template.get("evidence", {}),
                "speed_value": None,
                "speed_values": sorted(speed_values),
                "sign_kind": "speed_limit_lane_ambiguous",
                "lane_binding_status": "unresolved",
            },
        }
        candidates = [
            item for item in candidates if item.get("event_type") != "speed_sign"
        ] + [ambiguity]
        pre_suppressed.extend(speed_candidates)
    elif lane_bound:
        best_bound = max(
            lane_bound,
            key=lambda item: float(
                item.get("evidence", {}).get("lane_binding_confidence", 0.0)
            ),
        )
        candidates = [
            item for item in candidates if item.get("event_type") != "speed_sign"
        ] + [best_bound]
        pre_suppressed.extend(item for item in speed_candidates if item is not best_bound)

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
