from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.alerts import AlertGovernor  # noqa: E402
from roadwatch.audio import AudioManager  # noqa: E402


CONFIG = {
    "alerts": {
        "global_audio_gap_seconds": 2.5, "warning_cooldown_seconds": 7.0,
        "critical_cooldown_seconds": 2.0, "sign_cooldown_seconds": 20.0,
        "advisory_audio_window_seconds": 60.0, "advisory_audio_max_per_window": 3,
    },
    "audio": {"enabled": True, "tts_enabled": True, "piper_voice": "missing.onnx"},
}


def candidate(index: int, severity: str = "advisory") -> dict:
    message = f"Xe máy bên phải {index}"
    return {
        "event_type": "vulnerable_road_user", "severity": severity,
        "message": message, "confidence": 0.9,
        "risk_score": 0.95 if severity == "critical" else 0.6,
        "object_id": index, "location": "bên phải", "cooldown_key": f"vru:{index}",
        "semantic_audio_key": "vru:motorcycle:right", "evidence": {},
    }


def main() -> int:
    governor = AlertGovernor(CONFIG)
    emitted = []
    for index, clock in enumerate((10.0, 13.0, 16.0, 19.0)):
        events, _ = governor.decide([candidate(index)], now=100.0 + clock, clock=clock)
        emitted.extend(events)
    critical, _ = governor.decide([candidate(9, "critical")], now=120.0, clock=20.0)

    manager = AudioManager(CONFIG)
    manager._speak = lambda _message: "rw12-test-provider"  # type: ignore[method-assign]
    manager.start()
    for index in range(100):
        manager.submit({
            "event_id": f"rw12-{index}", "event_type": "test_advisory",
            "severity": "advisory", "message": f"Thông báo {index}",
            "spoken_message": f"Thông báo {index}", "audio_action": "tts",
            "expires_at": time.time() + 10, "supersede_key": f"rw12:{index}",
        })
    manager._queue.join()
    audio = manager.status()
    manager.stop()

    gates = {
        "canonical_hud_tts_equality": all(
            event["display_message"] == event["spoken_message"] for event in emitted + critical
        ),
        "critical_beep_preempts_advisory": critical[0]["audio_action"] == "beep_tts",
        "audio_completion_at_least_099": audio["completion_rate"] >= 0.99,
        "stale_rate_below_002": audio["stale_rate"] < 0.02,
        "start_latency_p95_at_most_750_ms": audio["start_latency_p95_ms"] <= 750.0,
        "global_advisory_gap_at_least_2_5_seconds": CONFIG["alerts"]["global_audio_gap_seconds"] >= 2.5,
        "semantic_advisory_budget_at_most_3_per_minute": (
            sum(event["audio_action"] == "tts" for event in emitted) == 3
            and emitted[-1]["suppression_reason"] == "semantic_audio_budget"
        ),
    }
    report = {
        "schema_version": 1, "task_id": "RW-12",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "software_pass_human_cabin_gate_pending" if all(gates.values()) else "fail",
        "gates": gates, "audio_simulation": audio,
        "human_gate": "Vietnamese intelligibility and cabin volume remain pending",
        "metric_scope": "deterministic software queue simulation; not physical cabin evidence",
    }
    output = ROOT / "evaluation" / "rw12_quality_gate.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
