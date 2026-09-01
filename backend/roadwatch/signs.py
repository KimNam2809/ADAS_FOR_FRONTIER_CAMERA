from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .alert_copy import (
    alert_copy_profile,
    profile_message,
    speed_limit_message,
    validate_alert_message,
)


@dataclass(frozen=True)
class SignPolicy:
    """Driver-facing policy for a traffic-sign detector label.

    The detector taxonomy is intentionally kept separate from HMI policy: not
    every detected sign should interrupt the driver with speech.
    """

    kind: str
    severity: str
    message: str
    risk_score: float
    audio_eligible: bool = True
    require_red_ring: bool = False

    def __post_init__(self) -> None:
        # Every sign policy is a canonical message consumed by both the HUD
        # and TTS. Reject an overlong policy at import/configuration time
        # instead of silently truncating a safety instruction.
        validate_alert_message(self.message)


_SPEED_RE = re.compile(r"^Speed limit (\d+)km/h$", re.IGNORECASE)
_MIN_SPEED_RE = re.compile(
    r"^(?:minimum speed(?: limit)?|minimum_speed|min speed|speed minimum)[\s_-]*(\d+)\s*(?:km/?h)?$",
    re.IGNORECASE,
)
_NUMERIC_SPEEDS = {"10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "110", "120"}
_GENERIC_SPEED_LABELS = {"speed_limit", "speed limit", "speed-limit"}


# Safety/action signs are spoken. Low-urgency facilities and parking signs are
# intentionally HUD-only to avoid alert fatigue.
_POLICIES: dict[str, SignPolicy] = {
    "No Entry": SignPolicy(
        "prohibition",
        "advisory",
        "Biển cấm đi vào; kiểm tra hướng.",
        0.48,
        # Camera-only perception cannot establish whether this sign applies to
        # the ego direction. vNext keeps it visual-only until orientation
        # evidence is supplied; legacy preserves the previous spoken behavior.
        alert_copy_profile() == "legacy",
    ),
    "Stop": SignPolicy("stop", "warning", "Biển dừng phía trước.", 0.76),
    "Red Light": SignPolicy("traffic_light", "warning", "Đèn đỏ phía trước.", 0.82),
    "Traffic light ahead": SignPolicy("warning", "advisory", "Đèn tín hiệu phía trước.", 0.42),
    "Pedestrian Crossing": SignPolicy(
        "vulnerable_zone",
        "warning",
        profile_message("Lối sang đường phía trước.", "Người đi bộ sang đường."),
        0.66,
    ),
    "Pedestrian Lane": SignPolicy("vulnerable_zone", "warning", "Làn người đi bộ phía trước.", 0.62),
    "Children Crossing": SignPolicy(
        "vulnerable_zone",
        "warning",
        profile_message("Khu vực trẻ em; giảm tốc.", "Trẻ em sang đường; giảm tốc."),
        0.72,
    ),
    "Road Work Ahead": SignPolicy("local_hazard", "warning", "Công trường phía trước; giảm tốc.", 0.70),
    "Accident area": SignPolicy("local_hazard", "warning", "Khu vực tai nạn; giảm tốc.", 0.78),
    "Obstacle on the Road": SignPolicy(
        "local_hazard",
        "warning",
        profile_message(
            "Chướng ngại vật phía trước; giảm tốc.",
            "Chướng ngại vật phía trước.",
        ),
        0.76,
    ),
    "Slippery Road": SignPolicy("local_hazard", "warning", "Đường trơn; giảm tốc.", 0.72),
    "Speed Bump": SignPolicy("local_hazard", "advisory", "Gờ giảm tốc phía trước.", 0.48),
    "Uneven road": SignPolicy("local_hazard", "advisory", "Mặt đường gồ ghề.", 0.46),
    "Danger": SignPolicy("local_hazard", "warning", "Nguy hiểm phía trước.", 0.70),
    "Slow Down": SignPolicy("local_hazard", "warning", "Giảm tốc phía trước.", 0.68),
    "Level Crossing with Barriers": SignPolicy("rail_crossing", "warning", "Giao cắt đường sắt; giảm tốc.", 0.76),
    "Narrow bridge": SignPolicy("road_geometry", "warning", "Cầu hẹp phía trước.", 0.62),
    "Narrow Road Left Side": SignPolicy("road_geometry", "advisory", "Đường hẹp bên trái.", 0.46),
    "Narrow Road Right Side": SignPolicy("road_geometry", "advisory", "Đường hẹp bên phải.", 0.46),
    "Narrow road both sides": SignPolicy("road_geometry", "advisory", "Đường hẹp hai bên.", 0.48),
    "Sharp Left Turn": SignPolicy("road_geometry", "advisory", "Cua gấp bên trái.", 0.48),
    "Sharp Right Turn": SignPolicy("road_geometry", "advisory", "Cua gấp bên phải.", 0.48),
    "Double curve first to right": SignPolicy("road_geometry", "advisory", "Nhiều cua; đầu tiên bên phải.", 0.48),
    "Steep ascent": SignPolicy("road_geometry", "advisory", "Dốc lên phía trước.", 0.42),
    "No Overtaking": SignPolicy("prohibition", "advisory", "Cấm vượt phía trước.", 0.42),
    "No Left Turn": SignPolicy("prohibition", "advisory", "Cấm rẽ trái.", 0.42),
    "No Right Turn": SignPolicy("prohibition", "advisory", "Cấm rẽ phải.", 0.42),
    "No U-Turn": SignPolicy("prohibition", "advisory", "Cấm quay đầu.", 0.42),
    "No U-Turn and No Left Turn": SignPolicy("prohibition", "advisory", "Cấm quay đầu, rẽ trái.", 0.44),
    "No U-Turn and No Right Turn": SignPolicy("prohibition", "advisory", "Cấm quay đầu, rẽ phải.", 0.44),
    "No U-Turn for Cars": SignPolicy("prohibition", "advisory", "Cấm ô tô quay đầu.", 0.42),
    "No left turn for cars": SignPolicy("prohibition", "advisory", "Cấm ô tô rẽ trái.", 0.42),
    "No Motobike Left Turn": SignPolicy("prohibition", "advisory", "Cấm xe máy rẽ trái.", 0.42),
    "No Two or Three-wheeled Vehicles": SignPolicy("prohibition", "advisory", "Cấm xe hai, ba bánh.", 0.42),
    "No Cars": SignPolicy("prohibition", "advisory", "Cấm ô tô.", 0.42),
    "No Trucks": SignPolicy("prohibition", "advisory", "Cấm xe tải.", 0.42),
    "No Trucks and Bus": SignPolicy("prohibition", "advisory", "Cấm xe tải, xe buýt.", 0.42),
    "Low Clearance": SignPolicy(
        "clearance",
        "warning",
        profile_message("Chiều cao giới hạn phía trước.", "Giới hạn chiều cao phía trước."),
        0.64,
    ),
    "Height Limit": SignPolicy(
        "clearance",
        "warning",
        profile_message("Chiều cao giới hạn phía trước.", "Giới hạn chiều cao phía trước."),
        0.64,
    ),
    "Turn Left Only": SignPolicy(
        "mandatory", "advisory", profile_message("Chỉ rẽ trái.", "Bắt buộc rẽ trái."), 0.38
    ),
    "Turn Right Only": SignPolicy(
        "mandatory", "advisory", profile_message("Chỉ rẽ phải.", "Bắt buộc rẽ phải."), 0.38
    ),
    "Turn Left": SignPolicy("mandatory", "advisory", "Hướng đi bên trái.", 0.36),
    "Turn Right": SignPolicy("mandatory", "advisory", "Hướng đi bên phải.", 0.36),
    "Keep left": SignPolicy(
        "mandatory", "advisory", profile_message("Giữ bên trái.", "Đi về bên trái."), 0.38
    ),
    "Roundabout": SignPolicy("mandatory", "advisory", "Vòng xuyến phía trước.", 0.38),
    "Lane Allocation": SignPolicy(
        "mandatory",
        "advisory",
        profile_message("Biển phân làn phía trước.", "Chú ý biển phân làn phía trước."),
        0.38,
    ),
    "One way street": SignPolicy("mandatory", "advisory", "Đường một chiều phía trước.", 0.36),
    "End of all prohibition": SignPolicy("restriction_end", "advisory", "Hết các lệnh cấm.", 0.32),
    "End of 50km/h speed limit": SignPolicy("speed_end", "advisory", "Hết giới hạn 50 ki-lô-mét/giờ.", 0.34),
    "Parking": SignPolicy("information", "informational", "Khu vực đỗ xe.", 0.15, False),
    "Bus Stop": SignPolicy("information", "informational", "Điểm dừng xe buýt.", 0.15, False),
    "Hospital": SignPolicy("information", "informational", "Bệnh viện phía trước.", 0.15, False),
    "Green Light": SignPolicy("information", "informational", "Đèn xanh phía trước.", 0.15, False),
}


_POLICIES.update(
    {
        "No Moto": SignPolicy("prohibition", "advisory", "Cấm xe máy.", 0.40),
        "No bus": SignPolicy("prohibition", "advisory", "Cấm xe buýt.", 0.40),
        "No Horns": SignPolicy("prohibition", "advisory", "Cấm dùng còi.", 0.36),
        "No Straight and Right Turn": SignPolicy("prohibition", "advisory", "Cấm đi thẳng, rẽ phải.", 0.42),
        "No Left or Right Turn": SignPolicy("prohibition", "advisory", "Cấm rẽ trái, rẽ phải.", 0.42),
        "No U-Turn and Left Turn for Cars": SignPolicy("prohibition", "advisory", "Cấm ô tô quay đầu, rẽ trái.", 0.42),
        "Intersection with a Priority Road": SignPolicy("intersection", "advisory", "Giao nhau đường ưu tiên.", 0.38),
        "Intersection with Equal Roads": SignPolicy("intersection", "advisory", "Giao nhau đường đồng cấp.", 0.38),
        "Intersection with a Minor Road": SignPolicy("intersection", "advisory", "Giao nhau đường nhánh.", 0.36),
        "Residential area": SignPolicy("zone", "advisory", "Vào khu đông dân cư.", 0.34),
        "sparsely populated area": SignPolicy("zone", "advisory", "Rời khu đông dân cư.", 0.32),
        "Dual carriageway": SignPolicy("road_geometry", "advisory", "Bắt đầu đường đôi.", 0.34),
        "U-Turn Area": SignPolicy("information", "informational", "Khu vực quay đầu phía trước.", 0.18, False),
        "Road with Surveillance Camera": SignPolicy("information", "informational", "Camera giám sát phía trước.", 0.16, False),
        "No Stopping & No Parking": SignPolicy("parking_restriction", "informational", "Cấm dừng và đỗ.", 0.18, False),
        "No Parking": SignPolicy("parking_restriction", "informational", "Cấm đỗ xe.", 0.18, False),
        "No Parking Odd Days": SignPolicy("parking_restriction", "informational", "Cấm đỗ ngày lẻ.", 0.18, False),
        "Even Days": SignPolicy("parking_restriction", "informational", "Hạn chế đỗ ngày chẵn.", 0.18, False),
    }
)


# These signs describe a road rule or a lane/maneuver option.  With no GPS,
# steering intent or map context, speaking them as if RoadWatch were directing
# the driver is unnecessarily intrusive.  Keep them visible for the driver
# and auditable for the engineer, but route them to HUD-only.
HUD_ONLY_DIRECTION_SIGN_LABELS = frozenset(
    {
        "Turn Left",
        "Turn Right",
        "Turn Left Only",
        "Turn Right Only",
        "Keep left",
        "No Left Turn",
        "No Right Turn",
        "No U-Turn",
        "No U-Turn and No Left Turn",
        "No U-Turn and No Right Turn",
        "No U-Turn for Cars",
        "No left turn for cars",
        "No Motobike Left Turn",
        "No Straight and Right Turn",
        "No Left or Right Turn",
        "No U-Turn and Left Turn for Cars",
    }
)
for _label in HUD_ONLY_DIRECTION_SIGN_LABELS:
    _policy = _POLICIES.get(_label)
    if _policy is not None:
        _POLICIES[_label] = replace(_policy, audio_eligible=False)


def policy_for_label(label: str) -> SignPolicy | None:
    minimum_match = _MIN_SPEED_RE.match(label.strip())
    if minimum_match:
        speed = int(minimum_match.group(1))
        return SignPolicy(
            "speed_limit_minimum",
            "advisory",
            speed_limit_message(speed, minimum=True),
            0.30,
            True,
            False,
        )
    match = _SPEED_RE.match(label)
    if match:
        speed = int(match.group(1))
        return SignPolicy(
            "speed_limit",
            "advisory",
            speed_limit_message(speed),
            0.30,
            True,
            True,
        )
    if label in _NUMERIC_SPEEDS:
        speed = int(label)
        return SignPolicy(
            "speed_limit",
            "advisory",
            speed_limit_message(speed),
            0.30,
            True,
            True,
        )
    return _POLICIES.get(label)


def resolve_sign_message(label: str, sign: dict[str, object]) -> tuple[str, bool, dict[str, object]]:
    """Resolve driver-facing sign copy and audio eligibility.

    The No Entry sign is intentionally conservative in vNext. A detector
    confidence score proves the class, not the direction in which the sign
    applies. Optional orientation metadata can enable a precise spoken variant
    only after an upstream lane/map/OEM component has supplied evidence.
    """

    policy = policy_for_label(label)
    if policy is None:
        raise KeyError(f"Không có sign policy cho nhãn: {label}")
    if label != "No Entry" or alert_copy_profile() == "legacy":
        return policy.message, policy.audio_eligible, {}

    nested = sign.get("evidence")
    evidence = nested if isinstance(nested, dict) else {}
    status = str(sign.get("orientation_status") or evidence.get("orientation_status") or "").strip().lower()
    confidence_value = sign.get("orientation_confidence", evidence.get("orientation_confidence", 0.0))
    try:
        orientation_confidence = float(confidence_value)
    except (TypeError, ValueError):
        orientation_confidence = 0.0
    orientation_aliases = {
        "opposite": "opposite_direction",
        "opposite_direction": "opposite_direction",
        "reverse": "opposite_direction",
        "same": "ego_direction",
        "same_direction": "ego_direction",
        "ego": "ego_direction",
        "ego_direction": "ego_direction",
    }
    resolved = orientation_aliases.get(status)
    if resolved and orientation_confidence >= 0.85:
        message = (
            "Cấm đi vào chiều đối diện."
            if resolved == "opposite_direction"
            else "Cấm đi vào chiều này."
        )
        return message, True, {
            "orientation_status": resolved,
            "orientation_confidence": round(orientation_confidence, 4),
        }
    return policy.message, False, {
        "orientation_status": "unknown",
        "orientation_confidence": round(orientation_confidence, 4),
        "orientation_audio_suppressed": True,
    }


def speed_value(label: str) -> int | None:
    match = _SPEED_RE.match(label)
    if match:
        return int(match.group(1))
    return int(label) if label in _NUMERIC_SPEEDS else None


def minimum_speed_value(label: str) -> int | None:
    """Return a parsed minimum-speed value when the detector exposes one."""

    match = _MIN_SPEED_RE.match(label.strip())
    return int(match.group(1)) if match else None


def is_speed_limit_label(label: str) -> bool:
    """Return true for either a numeric or collapsed generic speed-sign label."""

    return speed_value(label) is not None or label.strip().lower() in _GENERIC_SPEED_LABELS


def is_minimum_speed_label(label: str) -> bool:
    """Return true for a detector label describing a minimum speed sign."""

    return minimum_speed_value(label) is not None


def spoken_sign_messages() -> tuple[str, ...]:
    """Canonical spoken sign corpus used to warm the deterministic Piper cache."""

    messages = {
        policy.message for policy in _POLICIES.values() if policy.audio_eligible
    }
    messages.update(
        policy_for_label(speed).message
        for speed in sorted(_NUMERIC_SPEEDS, key=int)
        if policy_for_label(speed) is not None
    )
    return tuple(sorted(messages))
