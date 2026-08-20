from __future__ import annotations

import re
from dataclasses import dataclass


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


_SPEED_RE = re.compile(r"^Speed limit (\d+)km/h$", re.IGNORECASE)
_NUMERIC_SPEEDS = {"10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "110", "120"}
_GENERIC_SPEED_LABELS = {"speed_limit", "speed limit", "speed-limit"}


# Safety/action signs are spoken. Low-urgency facilities and parking signs are
# intentionally HUD-only to avoid alert fatigue.
_POLICIES: dict[str, SignPolicy] = {
    "No Entry": SignPolicy(
        "prohibition",
        "advisory",
        "Phát hiện biển cấm đi vào. Hãy kiểm tra biển có áp dụng cho hướng đang đi.",
        0.48,
    ),
    "Stop": SignPolicy("stop", "warning", "Cảnh báo biển dừng lại phía trước.", 0.76),
    "Red Light": SignPolicy("traffic_light", "warning", "Cảnh báo đèn đỏ phía trước.", 0.82),
    "Traffic light ahead": SignPolicy("warning", "advisory", "Phía trước có đèn tín hiệu giao thông.", 0.42),
    "Pedestrian Crossing": SignPolicy("vulnerable_zone", "warning", "Cảnh báo khu vực người đi bộ sang đường.", 0.66),
    "Pedestrian Lane": SignPolicy("vulnerable_zone", "warning", "Cảnh báo làn đường dành cho người đi bộ.", 0.62),
    "Children Crossing": SignPolicy("vulnerable_zone", "warning", "Cảnh báo khu vực trẻ em qua đường. Hãy giảm tốc.", 0.72),
    "Road Work Ahead": SignPolicy("local_hazard", "warning", "Cảnh báo công trường phía trước. Hãy giảm tốc.", 0.70),
    "Accident area": SignPolicy("local_hazard", "warning", "Cảnh báo khu vực tai nạn phía trước. Hãy giảm tốc.", 0.78),
    "Obstacle on the Road": SignPolicy("local_hazard", "warning", "Cảnh báo có chướng ngại vật trên đường.", 0.76),
    "Slippery Road": SignPolicy("local_hazard", "warning", "Cảnh báo đường trơn trượt. Hãy giảm tốc.", 0.72),
    "Speed Bump": SignPolicy("local_hazard", "advisory", "Phía trước có gờ giảm tốc.", 0.48),
    "Uneven road": SignPolicy("local_hazard", "advisory", "Cảnh báo mặt đường không bằng phẳng.", 0.46),
    "Danger": SignPolicy("local_hazard", "warning", "Cảnh báo nguy hiểm phía trước. Hãy chú ý.", 0.70),
    "Slow Down": SignPolicy("local_hazard", "warning", "Cảnh báo giảm tốc phía trước.", 0.68),
    "Level Crossing with Barriers": SignPolicy("rail_crossing", "warning", "Cảnh báo giao cắt đường sắt có rào chắn.", 0.76),
    "Narrow bridge": SignPolicy("road_geometry", "warning", "Cảnh báo cầu hẹp phía trước.", 0.62),
    "Narrow Road Left Side": SignPolicy("road_geometry", "advisory", "Phía trước đường hẹp bên trái.", 0.46),
    "Narrow Road Right Side": SignPolicy("road_geometry", "advisory", "Phía trước đường hẹp bên phải.", 0.46),
    "Narrow road both sides": SignPolicy("road_geometry", "advisory", "Phía trước đường hẹp cả hai bên.", 0.48),
    "Sharp Left Turn": SignPolicy("road_geometry", "advisory", "Phía trước có khúc cua gấp bên trái.", 0.48),
    "Sharp Right Turn": SignPolicy("road_geometry", "advisory", "Phía trước có khúc cua gấp bên phải.", 0.48),
    "Double curve first to right": SignPolicy("road_geometry", "advisory", "Phía trước có nhiều khúc cua, đầu tiên về bên phải.", 0.48),
    "Steep ascent": SignPolicy("road_geometry", "advisory", "Phía trước có đoạn đường dốc lên.", 0.42),
    "No Overtaking": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm vượt.", 0.42),
    "No Left Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm rẽ trái.", 0.42),
    "No Right Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm rẽ phải.", 0.42),
    "No U-Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm quay đầu.", 0.42),
    "No U-Turn and No Left Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm quay đầu và cấm rẽ trái.", 0.44),
    "No U-Turn and No Right Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm quay đầu và cấm rẽ phải.", 0.44),
    "No U-Turn for Cars": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm ô tô quay đầu.", 0.42),
    "No left turn for cars": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm ô tô rẽ trái.", 0.42),
    "No Motobike Left Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm xe máy rẽ trái.", 0.42),
    "No Two or Three-wheeled Vehicles": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm xe hai và ba bánh.", 0.42),
    "No Cars": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm ô tô.", 0.42),
    "No Trucks": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm xe tải.", 0.42),
    "No Trucks and Bus": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm xe tải và xe buýt.", 0.42),
    "Low Clearance": SignPolicy("clearance", "warning", "Cảnh báo giới hạn chiều cao phía trước.", 0.64),
    "Height Limit": SignPolicy("clearance", "warning", "Cảnh báo giới hạn chiều cao phía trước.", 0.64),
    "Turn Left Only": SignPolicy("mandatory", "advisory", "Hướng bắt buộc rẽ trái phía trước.", 0.38),
    "Turn Right Only": SignPolicy("mandatory", "advisory", "Hướng bắt buộc rẽ phải phía trước.", 0.38),
    "Turn Left": SignPolicy("mandatory", "advisory", "Hướng đi bên trái phía trước.", 0.36),
    "Turn Right": SignPolicy("mandatory", "advisory", "Hướng đi bên phải phía trước.", 0.36),
    "Keep left": SignPolicy("mandatory", "advisory", "Hãy đi về bên trái theo biển chỉ dẫn.", 0.38),
    "Roundabout": SignPolicy("mandatory", "advisory", "Phía trước có vòng xuyến.", 0.38),
    "Lane Allocation": SignPolicy("mandatory", "advisory", "Chú ý biển phân làn phía trước.", 0.38),
    "One way street": SignPolicy("mandatory", "advisory", "Đã nhận diện đường một chiều.", 0.36),
    "End of all prohibition": SignPolicy("restriction_end", "advisory", "Đã hết các lệnh cấm trước đó.", 0.32),
    "End of 50km/h speed limit": SignPolicy("speed_end", "advisory", "Đã hết giới hạn tốc độ 50 ki-lô-mét một giờ.", 0.34),
    "Parking": SignPolicy("information", "informational", "Đã nhận diện khu vực đỗ xe.", 0.15, False),
    "Bus Stop": SignPolicy("information", "informational", "Đã nhận diện điểm dừng xe buýt.", 0.15, False),
    "Hospital": SignPolicy("information", "informational", "Đã nhận diện bệnh viện.", 0.15, False),
    "Green Light": SignPolicy("information", "informational", "Đèn xanh phía trước.", 0.15, False),
}


_POLICIES.update(
    {
        "No Moto": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm xe máy.", 0.40),
        "No bus": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm xe buýt.", 0.40),
        "No Horns": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm sử dụng còi.", 0.36),
        "No Straight and Right Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm đi thẳng và rẽ phải.", 0.42),
        "No Left or Right Turn": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm rẽ trái và rẽ phải.", 0.42),
        "No U-Turn and Left Turn for Cars": SignPolicy("prohibition", "advisory", "Đã nhận diện biển cấm ô tô quay đầu và rẽ trái.", 0.42),
        "Intersection with a Priority Road": SignPolicy("intersection", "advisory", "Chú ý giao nhau với đường ưu tiên phía trước.", 0.38),
        "Intersection with Equal Roads": SignPolicy("intersection", "advisory", "Chú ý giao nhau với đường đồng cấp phía trước.", 0.38),
        "Intersection with a Minor Road": SignPolicy("intersection", "advisory", "Chú ý giao nhau với đường nhánh phía trước.", 0.36),
        "Residential area": SignPolicy("zone", "advisory", "Đã vào khu vực đông dân cư.", 0.34),
        "sparsely populated area": SignPolicy("zone", "advisory", "Đã ra khỏi khu vực đông dân cư.", 0.32),
        "Dual carriageway": SignPolicy("road_geometry", "advisory", "Phía trước bắt đầu đường đôi.", 0.34),
        "U-Turn Area": SignPolicy("information", "informational", "Phía trước có khu vực quay đầu.", 0.18, False),
        "Road with Surveillance Camera": SignPolicy("information", "informational", "Phía trước có camera giám sát.", 0.16, False),
        "No Stopping & No Parking": SignPolicy("parking_restriction", "informational", "Đã nhận diện biển cấm dừng và đỗ xe.", 0.18, False),
        "No Parking": SignPolicy("parking_restriction", "informational", "Đã nhận diện biển cấm đỗ xe.", 0.18, False),
        "No Parking Odd Days": SignPolicy("parking_restriction", "informational", "Đã nhận diện biển cấm đỗ xe ngày lẻ.", 0.18, False),
        "Even Days": SignPolicy("parking_restriction", "informational", "Đã nhận diện biển hạn chế đỗ xe ngày chẵn.", 0.18, False),
    }
)


def policy_for_label(label: str) -> SignPolicy | None:
    match = _SPEED_RE.match(label)
    if match:
        speed = int(match.group(1))
        return SignPolicy(
            "speed_limit",
            "advisory",
            f"Đã nhận diện biển giới hạn tốc độ {speed} ki-lô-mét một giờ.",
            0.30,
            True,
            True,
        )
    if label in _NUMERIC_SPEEDS:
        speed = int(label)
        return SignPolicy(
            "speed_limit",
            "advisory",
            f"Đã nhận diện biển giới hạn tốc độ {speed} ki-lô-mét một giờ.",
            0.30,
            True,
            True,
        )
    return _POLICIES.get(label)


def speed_value(label: str) -> int | None:
    match = _SPEED_RE.match(label)
    if match:
        return int(match.group(1))
    return int(label) if label in _NUMERIC_SPEEDS else None


def is_speed_limit_label(label: str) -> bool:
    """Return true for either a numeric or collapsed generic speed-sign label."""

    return speed_value(label) is not None or label.strip().lower() in _GENERIC_SPEED_LABELS
