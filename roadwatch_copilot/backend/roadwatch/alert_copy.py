"""Shared guardrails for short, driver-facing RoadWatch alert copy."""

from __future__ import annotations

import os


# RoadWatch lexical budgets are compatibility/safety guards, not legal or OEM
# standards. The old profile keeps the seven-token invariant; vNext uses the
# researched information-unit and duration rules, with a wider hard stop only
# for malformed/external messages.
MAX_ALERT_WORDS = 7
VNEXT_HARD_MAX_ALERT_WORDS = 12
ALERT_COPY_PROFILE_ENV = "ROADWATCH_ALERT_COPY_PROFILE"
DEFAULT_ALERT_COPY_PROFILE = "vnext"
LEGACY_ALERT_COPY_PROFILE = "legacy"


def alert_copy_profile() -> str:
    """Return the selected copy profile, defaulting to the researched vNext catalog.

    The process must be restarted after changing the environment variable because
    sign policies are constructed at import time. ``legacy`` is intentionally kept
    as the rollback profile for the previously tested seven-word catalog.
    """

    requested = os.getenv(ALERT_COPY_PROFILE_ENV, DEFAULT_ALERT_COPY_PROFILE).strip().lower()
    return LEGACY_ALERT_COPY_PROFILE if requested in {"legacy", "legacy_7word", "baseline"} else DEFAULT_ALERT_COPY_PROFILE


def profile_message(vnext: str, legacy: str) -> str:
    """Select a canonical message without creating separate HUD/TTS variants."""

    return legacy if alert_copy_profile() == LEGACY_ALERT_COPY_PROFILE else vnext


def alert_word_limit() -> int:
    """Return the hard validation ceiling for the active copy profile."""

    return MAX_ALERT_WORDS if alert_copy_profile() == LEGACY_ALERT_COPY_PROFILE else VNEXT_HARD_MAX_ALERT_WORDS


def alert_word_count(message: str) -> int:
    """Count the words used by the driver-facing alert budget."""

    return len(str(message).strip().split())


def validate_alert_message(message: str) -> str:
    """Return *message* or fail fast when a canonical alert is too long."""

    value = " ".join(str(message).split())
    if not value:
        raise ValueError("Câu cảnh báo không được để trống")
    count = alert_word_count(value)
    limit = alert_word_limit()
    if count > limit:
        raise ValueError(
            f"Câu cảnh báo vượt ngân sách {limit} từ: "
            f"{count} từ — {value!r}"
        )
    return value


def short_location(location: str) -> str:
    """Compress a camera-relative location without dropping left/right."""

    value = str(location).lower()
    if "bên trái" in value:
        return "bên trái"
    if "bên phải" in value:
        return "bên phải"
    return "phía trước"


def short_crossing_direction(movement_direction: str) -> str:
    """Return a compact Vietnamese direction phrase for cross-traffic TTS."""

    if movement_direction == "left_to_right":
        return "trái sang phải"
    return "phải sang trái"


def crossing_side(origin_side: str) -> str:
    """Return the camera-relative conflict side used by the vNext copy."""

    if origin_side == "left":
        return "bên trái"
    if origin_side == "right":
        return "bên phải"
    return "phía trước"


def fcw_message(label: str, location: str, *, critical: bool = False) -> str:
    """Build the profile-aware FCW message."""

    if critical:
        return profile_message("Cảnh báo va chạm", "Cảnh báo va chạm phía trước!")
    return profile_message(
        f"{label} {short_location(location)}; giảm tốc độ.",
        f"{label} {short_location(location)}; tiến gần.",
    )


def lead_braking_message(label: str) -> str:
    """Describe a lead vehicle's image-space deceleration cue."""

    return profile_message(
        f"{label} phía trước đang giảm tốc. Hãy chú ý.",
        f"{label} phía trước; giảm tốc.",
    )


def vulnerable_message(label: str, location: str) -> str:
    """Build the VRU warning while preserving the camera-relative location."""

    return profile_message(
        f"{label} {short_location(location)}; giảm tốc độ.",
        f"{label} {short_location(location)}; giảm tốc.",
    )


def cut_in_message(label: str, origin_location: str) -> str:
    """Describe an object entering from a camera-relative side."""

    return profile_message(
        f"{label} nhập làn từ {origin_location}. Hãy chú ý.",
        f"{label} {origin_location}; nhập làn.",
    )


def cross_traffic_message(label: str, origin_side: str, movement_direction: str) -> str:
    """Prefer conflict-side wording; retain the old motion wording on rollback."""

    if alert_copy_profile() != LEGACY_ALERT_COPY_PROFILE and label.strip().lower() in {
        "người đi bộ",
        "person",
    }:
        if movement_direction in {"left_to_right", "right_to_left"}:
            return f"{label} đang cắt ngang từ {short_crossing_direction(movement_direction)}."
        return f"{label} đang cắt ngang phía trước."
    return profile_message(
        f"{label} cắt ngang từ {crossing_side(origin_side)}.",
        f"{label} cắt {short_crossing_direction(movement_direction)}.",
    )


def ldw_message(side: str) -> str:
    """Build the profile-aware lane-departure warning."""

    return profile_message(
        f"Cảnh báo lệch làn bên {side}.",
        f"Lệch làn bên {side}.",
    )


def speed_limit_message(speed: int, *, minimum: bool = False) -> str:
    """Build a speed-sign message while retaining the legacy maximum wording."""

    if minimum:
        return f"Tối thiểu {speed} ki-lô-mét/giờ phía trước."
    return profile_message(
        f"Giới hạn {speed} ki-lô-mét/giờ phía trước.",
        f"Tối đa {speed} ki-lô-mét/giờ.",
    )


def combined_speed_limit_message(maximum: int, minimum: int) -> str:
    """Describe a maximum/minimum pair proven to apply to the ego lane."""

    return profile_message(
        f"Giới hạn {maximum} ki-lô-mét/giờ và tối thiểu {minimum} ki-lô-mét/giờ.",
        f"Tối đa {maximum}; tối thiểu {minimum}.",
    )


def ambiguous_speed_message(*, minimum: bool = False) -> str:
    """Avoid asserting a lane-specific limit when lane binding is unresolved."""

    if minimum:
        return profile_message(
            "Nhiều biển tốc độ tối thiểu; xem làn mình.",
            "Nhiều biển tốc độ; xem làn mình.",
        )
    return profile_message(
        "Nhiều biển giới hạn tốc độ; xem làn mình.",
        "Nhiều biển tốc độ; xem làn mình.",
    )
