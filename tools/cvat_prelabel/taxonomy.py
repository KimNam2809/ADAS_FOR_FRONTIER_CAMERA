from __future__ import annotations

from typing import Any


DROP_PREFIX = "unused_speed_head_"

EXACT_LABEL_MAP = {
    "No Entry": "no_entry",
    "Stop": "stop",
    "Pedestrian Crossing": "pedestrian_crossing",
    "Pedestrian Lane": "pedestrian_crossing",
    "Children Crossing": "children_crossing",
    "Road Work Ahead": "road_work",
    "Slippery Road": "slippery_road",
    "Accident area": "accident_area",
    "Obstacle on the Road": "obstacle",
    "Level Crossing with Barriers": "level_crossing",
    "Roundabout": "roundabout",
    "Sharp Left Turn": "sharp_left",
    "Sharp Right Turn": "sharp_right",
    "Red Light": "red_light",
    "Green Light": "traffic_light",
    "Traffic light ahead": "traffic_light",
    "End of 50km/h speed limit": "speed_limit_end",
    "End of all prohibition": "speed_zone_end",
}

PROHIBITION_LABELS = {
    "No Trucks and Bus",
    "No Trucks",
    "No Cars",
    "No Moto",
    "No Horns",
    "No Left Turn",
    "No Right Turn",
    "No U-Turn",
    "No U-Turn and No Left Turn",
    "No U-Turn and No Right Turn",
    "No U-Turn for Cars",
    "No bus",
    "No Overtaking",
    "No Motobike Left Turn",
    "No Two or Three-wheeled Vehicles",
    "No Stopping & No Parking",
    "No Parking",
    "No Straight and Right Turn",
    "No Left or Right Turn",
    "No U-Turn and Left Turn for Cars",
    "No left turn for cars",
    "No Parking on Odd Days",
    "No Parking on Even Days",
}

MANDATORY_LABELS = {
    "Turn Right Only",
    "Turn Left Only",
    "Lane Allocation",
    "Keep left",
    "One way street",
    "Turn Left",
    "Turn Right",
}

INFORMATION_LABELS = {
    "Road with Surveillance Camera",
    "U-Turn Area",
    "Parking",
    "Bus Stop",
    "Hospital",
    "Residential area",
    "sparsely populated area",
    "Dual carriageway",
}

WARNING_LABELS = {
    "Low Clearance",
    "Danger",
    "Slow Down",
    "Double curve first to right",
    "Height Limit",
    "Intersection with a Minor Road",
    "Intersection with Equal Roads",
    "Intersection with a Priority Road",
    "Narrow Road Left Side",
    "Narrow Road Right Side",
    "Narrow road both sides",
    "Speed Bump",
    "Steep ascent",
    "Narrow bridge",
    "Uneven road",
}


def canonical_label(detector_label: str, speed_value: int | None = None) -> str | None:
    """Map the 82-class production detector to the locked CVAT taxonomy."""
    label = detector_label.strip()
    if label.startswith(DROP_PREFIX):
        return None
    if label == "speed_limit" or speed_value is not None or label.isdigit():
        return "speed_limit_max"
    if label in EXACT_LABEL_MAP:
        return EXACT_LABEL_MAP[label]
    if label in PROHIBITION_LABELS:
        return "prohibition"
    if label in MANDATORY_LABELS:
        return "mandatory"
    if label in INFORMATION_LABELS:
        return "information"
    if label in WARNING_LABELS:
        return "warning"
    return "unknown_sign"


def default_speed_attributes(speed_value: int | None) -> dict[str, str]:
    """Fail closed on lane applicability; a detector cannot infer lane scope."""
    return {
        "speed_value": str(speed_value) if speed_value is not None else "unknown",
        "scope": "uncertain",
        "relative_lane": "unknown",
        "mounting": "unknown",
        "visibility": "clear",
        "orientation": "uncertain",
        "temporary": "false",
        "ignore_training": "false",
        "uncertain": "true" if speed_value is None else "false",
    }


def cvat_attributes(
    label_spec: dict[str, Any], values: dict[str, str]
) -> list[dict[str, Any]]:
    specs = {item["name"]: item for item in label_spec.get("attributes", [])}
    resolved: list[dict[str, Any]] = []
    for name, value in values.items():
        spec = specs.get(name)
        if spec is None:
            continue
        allowed = [str(item) for item in spec.get("values", [])]
        if spec.get("input_type") == "select" and value not in allowed:
            value = "unknown" if "unknown" in allowed else spec.get("default_value", allowed[0])
        resolved.append({"spec_id": int(spec["id"]), "value": str(value)})
    return resolved

