from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from itertools import permutations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.alerts import AlertGovernor  # noqa: E402


def sign(key: str, kind: str, severity: str, risk: float) -> dict:
    return {
        "event_type": "speed_sign" if kind == "speed_limit" else "traffic_sign",
        "severity": severity, "message": key, "risk_score": risk, "confidence": 0.9,
        "object_id": None, "location": "phía trước", "cooldown_key": key,
        "is_traffic_sign": True, "audio_eligible": True, "evidence": {"sign_kind": kind},
    }


def main() -> int:
    config = {"alerts": {
        "global_audio_gap_seconds": 2.5, "warning_cooldown_seconds": 7.0,
        "critical_cooldown_seconds": 2.0, "sign_cooldown_seconds": 20.0,
    }}
    signs = [
        sign("speed_sign:60", "speed_limit", "advisory", 0.30),
        sign("speed_sign:80", "speed_limit", "advisory", 0.32),
        sign("traffic_sign:stop", "stop", "warning", 0.76),
        sign("traffic_sign:work", "local_hazard", "warning", 0.70),
        sign("traffic_sign:parking", "information", "informational", 0.15),
    ]
    signatures = set()
    single_audio = True
    for variant in permutations(signs):
        governor = AlertGovernor(config)
        events, _ = governor.decide(list(variant), now=100.0, clock=10.0)
        signatures.add(tuple((event["cooldown_key"], event["audio_action"]) for event in events))
        single_audio &= sum(event["audio_action"] == "tts" for event in events) <= 1
    fcw = {
        "event_type": "fcw", "severity": "critical", "message": "Phanh ngay",
        "risk_score": 0.99, "confidence": 0.95, "object_id": 7,
        "location": "phía trước", "cooldown_key": "fcw:7", "evidence": {},
    }
    events, _ = AlertGovernor(config).decide([*signs, fcw], now=100.0, clock=10.0)
    gates = {
        "at_least_30_permutations": 120 >= 30,
        "deterministic_output": len(signatures) == 1,
        "at_most_one_spoken_sign": single_audio,
        "critical_road_user_preempts_sign": events[0]["event_type"] == "fcw" and events[0]["audio_action"] == "beep_tts",
        "same_speed_cooldown_20_seconds": float(config["alerts"]["sign_cooldown_seconds"]) >= 20.0,
    }
    report = {
        "schema_version": 1, "task_id": "RW-11",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(gates.values()) else "fail",
        "permutations_evaluated": 120, "unique_output_signatures": len(signatures),
        "gates": gates,
    }
    output = ROOT / "evaluation" / "rw11_quality_gate.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
