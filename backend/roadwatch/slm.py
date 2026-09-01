from __future__ import annotations

"""Asynchronous, evidence-grounded explanations for accepted RoadWatch alerts.

The SLM is deliberately downstream of ``RiskEngine`` and ``AlertGovernor``.
It can explain an accepted event, but it cannot create, change, suppress, or
escalate an alert.  The ONNX model and tokenizer are loaded lazily on a worker
thread so a missing model or a slow generation never blocks the perception,
audio, or HMI decision paths.
"""

import json
import logging
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import ConfigManager, MODEL_ROOT


LOGGER = logging.getLogger(__name__)

SUPPORTED_EVENTS = (
    "fcw",
    "lead_vehicle_braking",
    "vulnerable_road_user",
    "cut_in",
    "cross_traffic",
    "ldw",
    "speed_sign",
    "traffic_sign",
)


# Keep each system prompt short and event-specific.  The one-shot below teaches
# the desired Vietnamese sentence shape; the current JSON remains authoritative.
SYSTEM_PROMPTS: dict[str, str] = {
    "fcw": (
        "Giải thích event FCW bằng đúng một câu tiếng Việt. Nêu đối tượng, track, vị trí, "
        "xung đột quỹ đạo và mọi cặp giá trị-ngưỡng trong JSON. Chỉ dùng JSON; không dùng "
        "TTC, khoảng cách, tốc độ vật lý, tên khóa hoặc lời khuyên hành động."
    ),
    "lead_vehicle_braking": (
        "Giải thích event xe phía trước giảm tốc bằng đúng một câu tiếng Việt. Nêu đối "
        "tượng, track, vị trí, xung đột quỹ đạo và các evidence cùng giá trị-ngưỡng có trong "
        "JSON. Không tự thêm đèn phanh nếu JSON không có; không dùng tốc độ vật lý, TTC, "
        "tên khóa hoặc lời khuyên hành động."
    ),
    "vulnerable_road_user": (
        "Giải thích cảnh báo người tham gia giao thông dễ bị tổn thương bằng đúng một câu "
        "tiếng Việt. Nêu đối tượng, track, vị trí, xung đột quỹ đạo, risk score và ngưỡng, "
        "số frame xác nhận. Chỉ dùng JSON; không dùng TTC, khoảng cách, tốc độ vật lý, tên "
        "khóa hoặc lời khuyên hành động."
    ),
    "cut_in": (
        "Giải thích event phương tiện nhập làn bằng đúng một câu tiếng Việt. Nêu đối tượng, "
        "track, vị trí xuất phát, hướng vào quỹ đạo, độ chuyển động ngang, mức tiếp cận, "
        "risk score và các ngưỡng cùng số frame trong JSON. Không dùng TTC, khoảng cách, "
        "tốc độ vật lý, tên khóa hoặc lời khuyên hành động."
    ),
    "cross_traffic": (
        "Giải thích event vật thể cắt ngang bằng đúng một câu tiếng Việt. Nêu đối tượng, "
        "track, vị trí, hướng di chuyển, quỹ đạo bị cắt ngang, các giá trị-ngưỡng chuyển động "
        "và số frame trong JSON. Không dùng TTC, khoảng cách, tốc độ vật lý, tên khóa hoặc "
        "lời khuyên hành động."
    ),
    "ldw": (
        "Giải thích cảnh báo lệch làn bằng đúng một câu tiếng Việt. Nêu bên lệch, lane "
        "offset và ngưỡng, lane quality và ngưỡng, số frame xác nhận trong JSON. Không dùng "
        "TTC, khoảng cách, tốc độ vật lý, tên khóa hoặc lời khuyên hành động."
    ),
    "speed_sign": (
        "Giải thích xác nhận biển giới hạn tốc độ bằng đúng một câu tiếng Việt. Nêu giá trị "
        "km/h và các giá trị-ngưỡng thực sự có trong JSON, cùng số lần và thời gian xác nhận. "
        "Không suy diễn biển khác, không dùng tên khóa hoặc lời khuyên hành động."
    ),
    "traffic_sign": (
        "Giải thích xác nhận biển báo giao thông bằng đúng một câu tiếng Việt. Nêu loại biển, "
        "độ tin cậy nếu có, số lần phát hiện và thời gian xác nhận cùng ngưỡng trong JSON. "
        "Không suy diễn nội dung ngoài JSON, không dùng tên khóa hoặc lời khuyên hành động."
    ),
}

SHOT_INPUTS: dict[str, dict[str, Any]] = {
    "fcw": {
        "event": "fcw", "level": "warning", "object": "ô tô", "track": 128,
        "position": "phía trước", "conflict": True, "bbox_pct": 28,
        "bbox_min_pct": 18, "closing_rate_s": 0.43, "closing_min_s": 0.20,
        "risk": 0.73, "risk_min": 0.56, "frames": 3,
    },
    "lead_vehicle_braking": {
        "event": "lead_vehicle_braking", "level": "warning", "object": "ô tô",
        "track": 128, "position": "phía trước", "conflict": True, "bbox_pct": 26,
        "bbox_min_pct": 18, "closing_rate_s": 0.31, "closing_min_s": 0.15,
        "closing_accel_s2": 0.16, "accel_min_s2": 0.12, "brake_light": 0.58,
        "brake_min": 0.42, "frames": 3,
    },
    "vulnerable_road_user": {
        "event": "vulnerable_road_user", "level": "warning", "object": "người đi bộ",
        "track": 128, "position": "phía trước bên phải", "conflict": True,
        "risk": 0.67, "risk_min": 0.52, "frames": 3,
    },
    "cut_in": {
        "event": "cut_in", "level": "warning", "object": "ô tô", "track": 128,
        "position": "phía trước bên phải", "origin": "bên phải", "conflict": True,
        "trajectory_lateral": 0.08, "trajectory_lateral_min": 0.018,
        "approach": 0.06, "approach_min": 0.02, "risk": 0.68, "risk_min": 0.60,
        "frames": 2,
    },
    "cross_traffic": {
        "event": "cross_traffic", "level": "warning", "object": "xe máy", "track": 128,
        "position": "phía trước", "direction": "từ trái sang phải", "lateral_velocity": 0.06,
        "lateral_min": 0.028, "lateral_displacement": 0.12, "displacement_min": 0.025,
        "motion_observations": 6, "observations_min": 5, "path_crossing": True, "frames": 2,
    },
    "ldw": {
        "event": "ldw", "level": "warning", "side": "phải", "lane_offset": 0.41,
        "lane_offset_min": 0.34, "lane_quality": 0.72, "lane_quality_min": 0.48, "frames": 5,
    },
    "speed_sign": {
        "event": "speed_sign", "level": "advisory", "sign": "biển giới hạn tốc độ",
        "value": 50, "confidence": 0.91, "confidence_min": 0.72, "red_ring": 0.034,
        "red_ring_min": 0.018, "hits": 3, "hits_min": 3, "seconds": 0.32, "seconds_min": 0.25,
    },
    "traffic_sign": {
        "event": "traffic_sign", "level": "warning", "sign": "biển dừng", "label": "Stop",
        "confidence": 0.88, "hits": 3, "hits_min": 3, "seconds": 0.30,
        "seconds_min": 0.25, "stable": True,
    },
}

SHOT_OUTPUTS: dict[str, str] = {
    "fcw": (
        "FCW warning được kích hoạt cho ô tô thuộc track 128 ở phía trước vì đối tượng "
        "xung đột với quỹ đạo dự kiến, bounding box chiếm 28% chiều rộng frame vượt "
        "ngưỡng tối thiểu 18%, mức tiếp cận tương đối đạt 0,43/s vượt ngưỡng 0,20/s, "
        "risk score đạt 0,73 vượt ngưỡng 0,56 và điều kiện được duy trì trong 3 frame xác nhận."
    ),
    "lead_vehicle_braking": (
        "Cảnh báo xe phía trước giảm tốc: ô tô thuộc track 128 ở phía trước vì đối tượng "
        "xung đột với quỹ đạo dự kiến, bounding box chiếm 26% chiều rộng frame vượt ngưỡng "
        "18%, mức tiếp cận tương đối đạt 0,31/s vượt ngưỡng 0,15/s, gia tốc tiếp cận đạt "
        "0,16/s² vượt ngưỡng 0,12/s, điểm đèn phanh đạt 0,58 vượt ngưỡng 0,42 và điều kiện "
        "được duy trì trong 3 frame xác nhận."
    ),
    "vulnerable_road_user": (
        "Cảnh báo người đi bộ thuộc track 128 ở phía trước bên phải vì đối tượng xung đột "
        "với quỹ đạo dự kiến, risk score đạt 0,67 vượt ngưỡng 0,52 và điều kiện được duy "
        "trì trong 3 frame xác nhận."
    ),
    "cut_in": (
        "Cảnh báo ô tô thuộc track 128 từ phía trước bên phải có xu hướng nhập vào quỹ đạo "
        "vì độ chuyển động ngang hướng vào tâm đạt 0,08 vượt ngưỡng 0,018, mức tiếp cận "
        "tương đối đạt 0,06 vượt ngưỡng 0,02, risk score đạt 0,68 vượt ngưỡng 0,60 và "
        "điều kiện được duy trì trong 2 frame xác nhận."
    ),
    "cross_traffic": (
        "Cảnh báo xe máy thuộc track 128 đang cắt ngang từ trái sang phải phía trước vì "
        "quỹ đạo dự kiến bị cắt ngang, vận tốc ngang đạt 0,06 vượt ngưỡng 0,028, độ dịch "
        "chuyển ngang đạt 0,12 vượt ngưỡng 0,025, có 6 quan sát chuyển động vượt tối thiểu "
        "5 và điều kiện được duy trì trong 2 frame xác nhận."
    ),
    "ldw": (
        "Cảnh báo lệch làn bên phải vì lane offset đạt 0,41 vượt ngưỡng 0,34, lane quality "
        "đạt 0,72 vượt ngưỡng tối thiểu 0,48 và điều kiện được duy trì trong 5 frame xác nhận."
    ),
    "speed_sign": (
        "Đã xác nhận biển giới hạn tốc độ 50 km/h với độ tin cậy 0,91 vượt ngưỡng 0,72, "
        "điểm viền đỏ đạt 0,034 vượt ngưỡng 0,018, đủ 3 lần phát hiện và thời gian xác nhận "
        "0,32 giây vượt ngưỡng 0,25 giây."
    ),
    "traffic_sign": (
        "Đã xác nhận biển dừng với độ tin cậy 0,88, đủ 3 lần phát hiện ổn định và thời gian "
        "xác nhận 0,30 giây vượt ngưỡng 0,25 giây."
    ),
}


@dataclass(frozen=True)
class Generation:
    output: str
    prompt_tokens: int
    output_tokens: int
    latency_ms: float


@dataclass(frozen=True)
class SlmResult:
    status: str
    explanation: str | None = None
    latency_ms: float | None = None
    failure_reason: str | None = None
    quality_score: float | None = None
    prompt_tokens: int | None = None
    output_tokens: int | None = None


def _number_variants(value: float | int) -> set[str]:
    if isinstance(value, int) or float(value).is_integer() and abs(float(value)) >= 1:
        return {str(int(value))}
    number = float(value)
    values = {f"{number:.2f}", f"{number:.2f}".replace(".", ",")}
    values |= {f"{number:g}", f"{number:g}".replace(".", ",")}
    return values


def _has_number(output: str, value: float | int) -> bool:
    return any(
        re.search(rf"(?<!\d){re.escape(item)}(?!\d)", output)
        for item in _number_variants(value)
    )


def _clean_output(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.replace("<|im_end|>", "").strip()
    return " ".join(text.split())


def _vi_object(label: Any) -> str:
    return {
        "person": "người đi bộ",
        "rider": "người đi xe máy",
        "bicycle": "xe đạp",
        "motorcycle": "xe máy",
        "car": "ô tô",
        "bus": "xe buýt",
        "truck": "xe tải",
    }.get(str(label), str(label))


def _put(payload: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        payload[key] = value


def _rounded(value: Any, digits: int = 4) -> float | int | None:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    return bool(value)


def _event_threshold(config: dict[str, Any], key: str, default: float | int) -> float | int:
    try:
        value = config.get("risk", {}).get(key, default)
        return int(value) if isinstance(default, int) else float(value)
    except (TypeError, ValueError):
        return default


def build_payload(event: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Project a canonical event into a small, human-semantic JSON contract."""

    event_type = str(event.get("event_type", "")).lower()
    if event_type not in SUPPORTED_EVENTS:
        raise ValueError(f"SLM không hỗ trợ event: {event_type}")
    evidence = event.get("evidence") or {}
    payload: dict[str, Any] = {"event": event_type, "level": event.get("severity", "warning")}

    if event.get("object_id") is not None:
        payload["object"] = _vi_object(evidence.get("object_label", event.get("object_id")))
        payload["track"] = int(event["object_id"])
        _put(payload, "position", event.get("location"))
    if "path_conflict" in evidence:
        payload["conflict"] = _bool(evidence.get("path_conflict"))

    risk = event.get("risk_score")
    if event_type == "fcw":
        _put(payload, "bbox_pct", round(float(evidence.get("box_width_ratio", 0.0)) * 100))
        if evidence.get("emergency_near_field"):
            payload["mode"] = "emergency_near_field"
            _put(payload, "bbox_min_pct", round(float(_event_threshold(config, "emergency_width_ratio_min", 0.26)) * 100))
            _put(payload, "bbox_area_pct", round(float(evidence.get("bbox_area_ratio", 0.0)) * 100))
            _put(payload, "bbox_area_min_pct", round(float(_event_threshold(config, "emergency_bbox_area_ratio_min", 0.16)) * 100))
            _put(payload, "proximity", _rounded(evidence.get("proximity_score")))
            _put(payload, "proximity_min", _event_threshold(config, "emergency_proximity_min", 0.74))
            _put(payload, "confidence", _rounded(event.get("confidence")))
            _put(payload, "confidence_min", _event_threshold(config, "emergency_confidence_min", 0.55))
        else:
            _put(payload, "bbox_min_pct", round(float(_event_threshold(config, "fcw_width_ratio_min", 0.18)) * 100))
            _put(payload, "closing_rate_s", _rounded(evidence.get("relative_closing_rate_per_s")))
            _put(payload, "closing_min_s", _event_threshold(config, "fcw_relative_rate_min", 0.20))
        _put(payload, "risk", _rounded(risk))
        risk_key = "fcw_critical" if event.get("severity") == "critical" else "fcw_warning"
        _put(payload, "risk_min", _event_threshold(config, risk_key, 0.78 if risk_key == "fcw_critical" else 0.56))
        _put(payload, "frames", evidence.get("confirmation_frames_required"))
    elif event_type == "lead_vehicle_braking":
        _put(payload, "bbox_pct", round(float(evidence.get("box_width_ratio", 0.0)) * 100))
        if evidence.get("relative_kinematic_brake_cue"):
            _put(payload, "bbox_min_pct", round(float(_event_threshold(config, "lead_braking_width_ratio_min", 0.18)) * 100))
            _put(payload, "closing_rate_s", _rounded(evidence.get("relative_closing_rate_per_s")))
            _put(payload, "closing_min_s", _event_threshold(config, "lead_braking_relative_rate_min", 0.15))
            _put(payload, "closing_accel_s2", _rounded(evidence.get("relative_closing_acceleration_per_s2")))
            _put(payload, "accel_min_s2", _event_threshold(config, "lead_braking_relative_acceleration_min", 0.12))
            _put(payload, "kinematic_observations", evidence.get("relative_kinematics_observations"))
            _put(payload, "kinematic_observations_min", 4)
        elif evidence.get("paired_brake_lamp_cue"):
            _put(payload, "bbox_min_pct", round(float(_event_threshold(config, "lead_braking_lamp_width_ratio_min", 0.12)) * 100))
        if evidence.get("paired_brake_lamp_cue"):
            _put(payload, "brake_light", _rounded(evidence.get("brake_light_score")))
            _put(payload, "brake_min", _event_threshold(config, "brake_light_score_min", 0.42))
        _put(payload, "frames", evidence.get("confirmation_frames"))
    elif event_type == "vulnerable_road_user":
        _put(payload, "risk", _rounded(risk))
        if not evidence.get("vulnerable_fallback"):
            _put(payload, "risk_min", _event_threshold(config, "vulnerable_warning", 0.52))
        else:
            payload["gate"] = "vulnerable_fallback"
        _put(payload, "frames", _event_threshold(config, "hazard_confirmation_frames", 3))
    elif event_type == "cut_in":
        origin = {"left": "bên trái", "right": "bên phải"}.get(str(evidence.get("origin_side")), None)
        _put(payload, "origin", origin)
        _put(payload, "trajectory_lateral", abs(float(evidence.get("trajectory_lateral", 0.0))))
        _put(payload, "trajectory_lateral_min", 0.018)
        _put(payload, "approach", _rounded(evidence.get("approaching_score")))
        _put(payload, "approach_min", _event_threshold(config, "cut_in_approach_min", 0.02))
        _put(payload, "risk", _rounded(risk))
        if evidence.get("risk_gate") or not (
            evidence.get("vehicle_merge_override") or evidence.get("proximity_override")
        ):
            _put(payload, "risk_min", _event_threshold(config, "cut_in_warning", 0.60))
        else:
            payload["gate"] = "merge_or_proximity_override"
        _put(payload, "frames", _event_threshold(config, "trajectory_confirmation_frames", 2))
    elif event_type == "cross_traffic":
        direction = {
            "left_to_right": "từ trái sang phải",
            "right_to_left": "từ phải sang trái",
        }.get(str(evidence.get("movement_direction")))
        _put(payload, "direction", direction)
        _put(payload, "lateral_velocity", abs(float(evidence.get("relative_lateral_velocity", 0.0))))
        _put(payload, "lateral_min", _event_threshold(config, "cross_traffic_lateral_min", 0.028))
        _put(payload, "lateral_displacement", abs(float(evidence.get("relative_lateral_displacement", 0.0))))
        _put(payload, "displacement_min", _event_threshold(config, "cross_traffic_displacement_min", 0.025))
        _put(payload, "motion_observations", evidence.get("motion_observations"))
        _put(payload, "observations_min", evidence.get("motion_observations_min", _event_threshold(config, "cross_traffic_motion_observations_min", 5)))
        payload["path_crossing"] = True
        _put(payload, "frames", _event_threshold(config, "trajectory_confirmation_frames", 2))
    elif event_type == "ldw":
        _put(payload, "side", event.get("location"))
        _put(payload, "lane_offset", _rounded(evidence.get("lane_offset")))
        _put(payload, "lane_offset_min", _event_threshold(config, "ldw_offset_warning", 0.34))
        _put(payload, "lane_quality", _rounded(evidence.get("lane_quality")))
        _put(payload, "lane_quality_min", _event_threshold(config, "lane_quality_min", 0.48))
        _put(payload, "frames", evidence.get("confirmation_frames"))
    elif event_type == "speed_sign":
        payload["sign"] = "biển giới hạn tốc độ"
        _put(payload, "value", evidence.get("speed_value"))
        _put(payload, "confidence", _rounded(event.get("confidence")))
        visual_score = _rounded(evidence.get("visual_red_ring_score"))
        red_required = bool(config.get("risk", {}).get("speed_sign_visual_validation", True))
        if red_required:
            _put(payload, "red_ring", visual_score)
            _put(payload, "red_ring_min", _event_threshold(config, "speed_sign_red_ring_min", 0.018))
        _put(payload, "hits", evidence.get("hits"))
        _put(payload, "hits_min", _event_threshold(config, "speed_sign_confirmation_hits", 3))
        _put(payload, "seconds", _rounded(evidence.get("confirmation_seconds")))
        _put(payload, "seconds_min", _event_threshold(config, "speed_sign_confirmation_seconds", 0.25))
    elif event_type == "traffic_sign":
        label = str(evidence.get("label", "biển báo giao thông"))
        sign = {
            "Stop": "biển dừng", "Red Light": "biển đèn đỏ", "No Entry": "biển cấm đi vào",
            "Turn Left": "biển chỉ dẫn rẽ trái", "Turn Right": "biển chỉ dẫn rẽ phải",
        }.get(label, f"biển báo {label.lower()}")
        payload["sign"] = sign
        payload["label"] = label
        _put(payload, "confidence", _rounded(event.get("confidence")))
        _put(payload, "hits", evidence.get("hits"))
        _put(payload, "hits_min", _event_threshold(config, "traffic_sign_confirmation_hits", 3))
        _put(payload, "seconds", _rounded(evidence.get("confirmation_seconds")))
        _put(payload, "seconds_min", _event_threshold(config, "traffic_sign_confirmation_seconds", 0.25))
        payload["stable"] = True
    return payload


def compact_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def build_chat(event: dict[str, Any], config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    payload = build_payload(event, config)
    event_type = payload["event"]
    messages = (
        ("system", SYSTEM_PROMPTS[event_type]),
        ("user", compact_json(SHOT_INPUTS[event_type])),
        ("assistant", SHOT_OUTPUTS[event_type]),
        ("user", compact_json(payload)),
    )
    prompt = "".join(
        f"<|im_start|>{role}\n{content}<|im_end|>\n" for role, content in messages
    )
    return prompt + "<|im_start|>assistant\n", payload


def validate_output(payload: dict[str, Any], output: str) -> tuple[bool, float, list[str]]:
    """Validate semantic coverage and basic safety without rewriting output."""

    output = _clean_output(output)
    lower = output.lower()
    checks: dict[str, bool] = {
        "one_sentence": bool(output)
        and output[-1:] in ".!?"
        and len(re.findall(r"[.!?](?:\s|$)", output)) == 1,
        "no_raw_keys": not any(
            key in lower
            for key in (
                "path_conflict", "track_id", "bbox_pct", "risk_min", "closing_rate_s",
                "confirmation_frames", "trigger_path", "lane_quality_min",
                "emergency_near_field", "vulnerable_fallback", "vehicle_merge_override",
                "proximity_override", "risk_gate", "kinematic_observations_min",
            )
        ),
        "no_hallucinated_physics": not re.search(
            r"\b(ttc|m/s|mét|meter|khoảng cách)\b", lower
        ),
        "no_action_advice": not re.search(
            r"\b(hãy|nên|cần phải)\s+(phanh|đánh lái|chuyển làn|giảm tốc|tăng tốc)\b",
            lower,
        ),
        "bounded_length": len(output.split()) <= 100,
    }
    event_type = payload["event"]
    checks["event"] = {
        "fcw": "fcw" in lower,
        "lead_vehicle_braking": "giảm tốc" in lower or "phanh" in lower,
        "vulnerable_road_user": any(
            token in lower for token in ("người đi bộ", "người đi xe máy", "xe đạp", "xe máy")
        ),
        "cut_in": "nhập" in lower or "cắt vào" in lower,
        "cross_traffic": "cắt ngang" in lower,
        "ldw": "lệch làn" in lower,
        "speed_sign": "biển" in lower and "tốc độ" in lower and "km/h" in lower,
        "traffic_sign": "biển" in lower,
    }[event_type]
    if "object" in payload:
        checks["object"] = str(payload["object"]).lower() in lower
    if "track" in payload:
        checks["track"] = "track" in lower and _has_number(output, payload["track"])
    if "position" in payload:
        checks["position"] = str(payload["position"]).lower() in lower
    if payload.get("conflict") is True and event_type != "cut_in":
        checks["conflict"] = "xung đột" in lower and "quỹ đạo" in lower
    if event_type == "cut_in":
        checks["origin"] = str(payload.get("origin", "")).lower() in lower
        checks["path_conflict"] = "quỹ đạo" in lower
    if event_type == "cross_traffic":
        checks["path_crossing"] = "quỹ đạo" in lower and "cắt ngang" in lower
    if event_type == "ldw":
        checks["side"] = str(payload.get("side", "")).lower() in lower
    if event_type == "traffic_sign":
        checks["sign"] = str(payload.get("sign", "biển")).lower() in lower or str(payload.get("label", "")).lower() in lower
    if event_type == "lead_vehicle_braking" and "brake_light" not in payload:
        checks["no_unprovided_brake_evidence"] = "đèn phanh" not in lower and "đèn thắng" not in lower
    if event_type == "speed_sign" and "red_ring" not in payload:
        checks["no_unprovided_red_ring_evidence"] = "viền đỏ" not in lower

    numeric_pairs = {
        "bbox_value_threshold": ("bbox_pct", "bbox_min_pct"),
        "bbox_area_value_threshold": ("bbox_area_pct", "bbox_area_min_pct"),
        "closing_value_threshold": ("closing_rate_s", "closing_min_s"),
        "risk_value_threshold": ("risk", "risk_min"),
        "proximity_value_threshold": ("proximity", "proximity_min"),
        "accel_value_threshold": ("closing_accel_s2", "accel_min_s2"),
        "brake_value_threshold": ("brake_light", "brake_min"),
        "trajectory_lateral_value_threshold": ("trajectory_lateral", "trajectory_lateral_min"),
        "approach_value_threshold": ("approach", "approach_min"),
        "lateral_velocity_threshold": ("lateral_velocity", "lateral_min"),
        "lateral_displacement_threshold": ("lateral_displacement", "displacement_min"),
        "observations_threshold": ("motion_observations", "observations_min"),
        "kinematic_observations_threshold": ("kinematic_observations", "kinematic_observations_min"),
        "offset_value_threshold": ("lane_offset", "lane_offset_min"),
        "quality_value_threshold": ("lane_quality", "lane_quality_min"),
        "confidence_threshold": ("confidence", "confidence_min"),
        "red_ring_threshold": ("red_ring", "red_ring_min"),
        "hits_threshold": ("hits", "hits_min"),
        "seconds_threshold": ("seconds", "seconds_min"),
    }
    for check_name, (value_key, threshold_key) in numeric_pairs.items():
        if value_key in payload and threshold_key in payload:
            checks[check_name] = _has_number(output, payload[value_key]) and _has_number(output, payload[threshold_key])
    if "frames" in payload:
        checks["frames"] = _has_number(output, payload["frames"]) and "frame" in lower

    critical = [name for name, value in checks.items() if name != "bounded_length"]
    quality = round(100 * sum(bool(checks[name]) for name in checks) / max(len(checks), 1), 2)
    failed = [name for name in critical if not checks[name]]
    return not failed, quality, failed


def _np_dtype(type_name: str) -> Any:
    import numpy as np

    mapping = {
        "tensor(float16)": np.float16,
        "tensor(float)": np.float32,
        "tensor(int64)": np.int64,
        "tensor(int32)": np.int32,
        "tensor(bool)": np.bool_,
    }
    if type_name not in mapping:
        raise ValueError(f"ONNX input type không hỗ trợ: {type_name}")
    return np.dtype(mapping[type_name])


class OrtCausalLM:
    """Small manual decoder for the Qwen2.5-0.5B ONNX export used in benchmark."""

    def __init__(self, model_dir: Path, device: str = "auto") -> None:
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._np = np
        self._ort = ort
        self.model_dir = model_dir
        self.config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        # Accept both the original P-162 layout (`onnx/model_q4f16.onnx`) and
        # the flat layout produced by the downloaded model bundle
        # (`model_q4f16.onnx`). Never select a GGUF or an arbitrary ONNX file:
        # the decoder contract is specifically the Q4F16 causal-LM artifact.
        model_candidates = (
            model_dir / "onnx" / "model_q4f16.onnx",
            model_dir / "model_q4f16.onnx",
            model_dir / "model.onnx",
        )
        model_path = next((candidate for candidate in model_candidates if candidate.is_file()), None)
        if model_path is None:
            expected = ", ".join(str(candidate) for candidate in model_candidates)
            raise FileNotFoundError(f"Không tìm thấy ONNX SLM; đã kiểm tra: {expected}")
        options = ort.SessionOptions()
        # The exported Q4F16 graph is valid, but ORT 1.24's ALL-level rewrite
        # can attempt an invalid SimplifiedLayerNorm fusion on this artifact.
        # BASIC keeps safe graph rewrites and works on CPU/DirectML/CUDA while
        # allowing an explicit override for a runtime that has been validated.
        optimization = os.getenv("ROADWATCH_SLM_GRAPH_OPT_LEVEL", "basic").strip().lower()
        optimization_levels = {
            "disable": ort.GraphOptimizationLevel.ORT_DISABLE_ALL,
            "basic": ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
            "extended": ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
            "all": ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
        }
        if optimization not in optimization_levels:
            raise ValueError(
                "ROADWATCH_SLM_GRAPH_OPT_LEVEL phải là disable, basic, extended hoặc all"
            )
        options.graph_optimization_level = optimization_levels[optimization]
        options.enable_mem_pattern = False
        intra = int(os.getenv("ROADWATCH_SLM_INTRA_OP_NUM_THREADS", os.getenv("ROADWATCH_ORT_INTRA_OP_NUM_THREADS", "0")))
        inter = int(os.getenv("ROADWATCH_SLM_INTER_OP_NUM_THREADS", os.getenv("ROADWATCH_ORT_INTER_OP_NUM_THREADS", "0")))
        if intra > 0:
            options.intra_op_num_threads = intra
        if inter > 0:
            options.inter_op_num_threads = inter
        providers = self._providers(ort, device)
        started = time.perf_counter()
        self.session = ort.InferenceSession(str(model_path), sess_options=options, providers=providers)
        self.load_ms = round((time.perf_counter() - started) * 1000, 2)
        self.provider = self.session.get_providers()[0] if self.session.get_providers() else "none"
        self.inputs = {node.name: node for node in self.session.get_inputs()}
        self.output_names = [node.name for node in self.session.get_outputs()]
        if "input_ids" not in self.inputs or "attention_mask" not in self.inputs:
            raise RuntimeError("ONNX SLM thiếu input_ids/attention_mask")
        self.logits_name = next(name for name in self.output_names if name == "logits")
        self.past_inputs = sorted(
            (name for name in self.inputs if name.startswith("past_key_values.")),
            key=self._cache_sort_key,
        )
        self.past_outputs = sorted(
            (name for name in self.output_names if name.startswith("present.")),
            key=self._cache_sort_key,
        )
        if len(self.past_inputs) != len(self.past_outputs):
            raise RuntimeError(
                f"KV-cache mismatch: {len(self.past_inputs)} inputs vs {len(self.past_outputs)} outputs"
            )

    @staticmethod
    def _providers(ort: Any, device: str) -> list[Any]:
        available = set(ort.get_available_providers())
        requested = str(device or "auto").lower()
        selected: list[Any] = []
        if requested in {"auto", "cuda", "gpu"} and "CUDAExecutionProvider" in available:
            selected.append(("CUDAExecutionProvider", {
                "device_id": 0,
                "arena_extend_strategy": "kSameAsRequested",
                "cudnn_conv_algo_search": "DEFAULT",
                "do_copy_in_default_stream": True,
            }))
        # Q4F16 onnxruntime graphs can produce semantically invalid greedy
        # decoding through DirectML on some AMD Windows stacks even when the
        # session initializes successfully. Keep auto deterministic: use CUDA
        # when explicitly available, otherwise CPU. DirectML remains an opt-in
        # experiment for a runtime that has passed its own output gate.
        if requested in {"directml", "dml"} and "DmlExecutionProvider" in available:
            selected.append("DmlExecutionProvider")
        if "CPUExecutionProvider" in available and (requested in {"auto", "cpu"} or not selected):
            selected.append("CPUExecutionProvider")
        if not selected:
            raise RuntimeError(f"ONNX Runtime không có provider phù hợp: {sorted(available)}")
        return selected

    @staticmethod
    def _cache_sort_key(name: str) -> tuple[int, int]:
        match = re.search(r"\.(\d+)\.(key|value)$", name)
        if not match:
            return (10_000, 10_000)
        return (int(match.group(1)), 0 if match.group(2) == "key" else 1)

    def _eos_ids(self) -> set[int]:
        raw = self.config.get("eos_token_id", 151645)
        return ({int(value) for value in raw} if isinstance(raw, list) else {int(raw), 151643})

    def _empty_cache(self, input_name: str) -> Any:
        node = self.inputs[input_name]
        kv_heads = int(self.config["num_key_value_heads"])
        head_dim = int(self.config["hidden_size"] // self.config["num_attention_heads"])
        return self._np.empty((1, kv_heads, 0, head_dim), dtype=_np_dtype(node.type))

    def _feed(self, token_ids: list[int], total_length: int, cache: dict[str, Any] | None) -> dict[str, Any]:
        feed: dict[str, Any] = {}
        for name, node in self.inputs.items():
            dtype = _np_dtype(node.type)
            if name == "input_ids":
                feed[name] = self._np.asarray([token_ids], dtype=dtype)
            elif name == "attention_mask":
                feed[name] = self._np.ones((1, total_length), dtype=dtype)
            elif name == "position_ids":
                start = total_length - len(token_ids)
                feed[name] = self._np.arange(start, total_length, dtype=dtype)[None, :]
            elif name.startswith("past_key_values."):
                feed[name] = self._empty_cache(name) if cache is None else cache[name]
            else:
                raise RuntimeError(f"ONNX SLM có input không dự kiến: {name}")
        return feed

    def generate(self, prompt: str, max_new_tokens: int) -> Generation:
        prompt_ids = self.tokenizer.encode(prompt).ids
        generated: list[int] = []
        cache: dict[str, Any] | None = None
        current = prompt_ids
        total_length = len(prompt_ids)
        started = time.perf_counter()
        output_indexes = {name: index for index, name in enumerate(self.output_names)}
        eos_ids = self._eos_ids()
        for _ in range(max_new_tokens):
            values = self.session.run(self.output_names, self._feed(current, total_length, cache))
            token_id = int(self._np.argmax(values[output_indexes[self.logits_name]][0, -1]))
            if token_id in eos_ids:
                break
            generated.append(token_id)
            cache = {
                input_name: values[output_indexes[output_name]]
                for input_name, output_name in zip(self.past_inputs, self.past_outputs)
            }
            current = [token_id]
            total_length += 1
        latency_ms = (time.perf_counter() - started) * 1000
        return Generation(
            output=_clean_output(self.tokenizer.decode(generated, skip_special_tokens=True)),
            prompt_tokens=len(prompt_ids),
            output_tokens=len(generated),
            latency_ms=round(latency_ms, 2),
        )


class SlmExplanationWorker:
    """One bounded, FIFO SLM worker shared by the RoadWatch service."""

    def __init__(
        self,
        config: dict[str, Any],
        on_result: Callable[[str, SlmResult], None],
    ) -> None:
        slm_config = config.get("slm", {})
        self.config = config
        self.enabled = bool(slm_config.get("enabled", False))
        self.model_dir = ConfigManager.model_path(
            str(slm_config.get("model_dir", "qwen2.5-0.5b"))
        )
        self.device = str(slm_config.get("device", "auto"))
        self.max_new_tokens = max(16, min(int(slm_config.get("max_new_tokens", 128)), 192))
        self.max_queue_size = max(1, min(int(slm_config.get("queue_size", 8)), 64))
        self.max_queue_age_seconds = max(0.1, float(slm_config.get("max_queue_age_seconds", 30.0)))
        self._on_result = on_result
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=self.max_queue_size)
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._model: OrtCausalLM | None = None
        self._state = "disabled" if not self.enabled else "standby"
        self._error: str | None = None
        self._last_latency_ms: float | None = None
        self._model_load_ms: float | None = None
        self._last_result_status: str | None = None
        self._last_event_id: str | None = None
        self._last_failure_reason: str | None = None
        self._last_quality_score: float | None = None
        self._last_output_tokens: int | None = None
        self._last_result_at: float | None = None
        self._generated = 0
        self._failed = 0
        self._closed = False

    def start(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._closed:
                return
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._state = "warming"
            self._thread = threading.Thread(target=self._run, name="roadwatch-slm", daemon=True)
            self._thread.start()

    def _load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
        try:
            model = OrtCausalLM(self.model_dir, self.device)
            with self._lock:
                self._model = model
                self._state = "ready"
                self._error = None
                self._model_load_ms = model.load_ms
            LOGGER.info("RoadWatch SLM ready: provider=%s load_ms=%.2f", model.provider, model.load_ms)
        except Exception as exc:  # missing optional asset must not stop RoadWatch
            with self._lock:
                self._state = "error"
                self._error = str(exc)[:500]
            LOGGER.exception("RoadWatch SLM unavailable; accepted alerts will use fallback")

    def _run(self) -> None:
        self._load()
        while not self._stop.is_set():
            try:
                job = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._process(job)
            finally:
                self._queue.task_done()

    def _process(self, job: dict[str, Any]) -> None:
        event_id = str(job["event_id"])
        if time.monotonic() - float(job["enqueued_at"]) > self.max_queue_age_seconds:
            with self._lock:
                self._failed += 1
            self._finish(event_id, SlmResult("fallback", failure_reason="stale_queue"))
            return
        with self._lock:
            model = self._model
            model_error = self._error
        if model is None:
            with self._lock:
                self._failed += 1
            self._finish(event_id, SlmResult("fallback", failure_reason=model_error or "model_unavailable"))
            return
        try:
            prompt, payload = build_chat(job["event"], self.config)
            generation = model.generate(prompt, self.max_new_tokens)
            valid, quality, failed = validate_output(payload, generation.output)
            with self._lock:
                self._last_latency_ms = generation.latency_ms
                if valid:
                    self._generated += 1
                else:
                    self._failed += 1
            if valid:
                self._finish(
                    event_id,
                    SlmResult(
                        "ready", generation.output, generation.latency_ms, None, quality,
                        generation.prompt_tokens, generation.output_tokens,
                    ),
                )
            else:
                self._finish(
                    event_id,
                    SlmResult(
                        "fallback", latency_ms=generation.latency_ms,
                        failure_reason=f"validator:{','.join(failed[:8])}", quality_score=quality,
                        prompt_tokens=generation.prompt_tokens, output_tokens=generation.output_tokens,
                    ),
                )
        except Exception as exc:  # generation must never affect the pipeline
            with self._lock:
                self._failed += 1
                self._error = str(exc)[:500]
            LOGGER.exception("RoadWatch SLM generation failed for event=%s", event_id)
            self._finish(event_id, SlmResult("fallback", failure_reason="generation_error"))

    def _finish(self, event_id: str, result: SlmResult) -> None:
        with self._lock:
            if self._closed:
                return
            self._last_result_status = result.status
            self._last_event_id = event_id
            self._last_failure_reason = result.failure_reason
            self._last_quality_score = result.quality_score
            self._last_output_tokens = result.output_tokens
            self._last_result_at = time.time()
        try:
            self._on_result(event_id, result)
        except Exception:  # callback/database errors must not kill the SLM worker
            LOGGER.exception("RoadWatch SLM result callback failed for event=%s", event_id)

    def submit(self, event: dict[str, Any]) -> str:
        if not self.enabled:
            return "disabled"
        with self._lock:
            if self._closed:
                return "fallback"
        item = {
            "event_id": str(event.get("event_id", "")),
            "event": dict(event),
            "enqueued_at": time.monotonic(),
        }
        if not item["event_id"]:
            return "fallback"
        try:
            self._queue.put_nowait(item)
            return "pending"
        except queue.Full:
            with self._lock:
                self._failed += 1
            # SLM is an optional Engineer explanation path. Keep the newest
            # event useful instead of allowing a burst of alerts to turn every
            # later job into stale_queue. The dropped job remains persisted as
            # fallback and never affects deterministic alerting.
            try:
                previous = self._queue.get_nowait()
            except queue.Empty:
                previous = None
            if previous is not None:
                try:
                    self._finish(str(previous["event_id"]), SlmResult("fallback", failure_reason="queue_replaced"))
                finally:
                    self._queue.task_done()
            try:
                self._queue.put_nowait(item)
                return "pending"
            except queue.Full:
                self._finish(item["event_id"], SlmResult("fallback", failure_reason="queue_full"))
                return "fallback"

    def clear_pending(self, reason: str = "cancelled") -> None:
        while True:
            try:
                job = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                self._finish(str(job["event_id"]), SlmResult("fallback", failure_reason=reason))
            finally:
                self._queue.task_done()

    def status(self) -> dict[str, Any]:
        with self._lock:
            model = self._model
            return {
                "enabled": self.enabled,
                "state": self._state,
                "model": str(self.model_dir.relative_to(MODEL_ROOT)) if self.model_dir.is_relative_to(MODEL_ROOT) else self.model_dir.name,
                "provider": model.provider if model is not None else "-",
                "queue_size": self._queue.qsize(),
                "max_queue_age_seconds": self.max_queue_age_seconds,
                "load_ms": self._model_load_ms,
                "generated": self._generated,
                "failed": self._failed,
                "last_latency_ms": self._last_latency_ms,
                "last_result_status": self._last_result_status,
                "last_event_id": self._last_event_id,
                "last_failure_reason": self._last_failure_reason,
                "last_quality_score": self._last_quality_score,
                "last_output_tokens": self._last_output_tokens,
                "last_result_at": self._last_result_at,
                "error": self._error,
            }

    def close(self) -> None:
        self.clear_pending("service_closed")
        with self._lock:
            self._closed = True
        self._stop.set()
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        with self._lock:
            self._state = "closed" if self.enabled else "disabled"
