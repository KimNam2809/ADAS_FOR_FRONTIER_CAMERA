from __future__ import annotations

import time
from typing import Any


SEVERITY_RANK = {"informational": 0, "advisory": 1, "warning": 2, "critical": 3}


class AlertGovernor:
    """The only component authorized to emit alerts to the HMI/audio layer."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config["alerts"]
        self._last_by_key: dict[str, tuple[float, str]] = {}
        self._last_audio = 0.0

    def reset(self) -> None:
        self._last_by_key.clear()
        self._last_audio = 0.0

    def decide(
        self, candidates: list[dict[str, Any]], now: float | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        now = now or time.time()
        accepted: list[dict[str, Any]] = []
        suppressed = 0
        ordered = sorted(
            candidates,
            key=lambda item: (SEVERITY_RANK.get(item["severity"], 0), item["risk_score"]),
            reverse=True,
        )
        for candidate in ordered:
            key = candidate["cooldown_key"]
            last_time, last_severity = self._last_by_key.get(key, (0.0, "informational"))
            if candidate["event_type"] == "speed_sign":
                cooldown = float(self.config["sign_cooldown_seconds"])
            elif candidate["severity"] == "critical":
                cooldown = float(self.config["critical_cooldown_seconds"])
            else:
                cooldown = float(self.config["warning_cooldown_seconds"])
            escalated = SEVERITY_RANK[candidate["severity"]] > SEVERITY_RANK[last_severity]
            if not escalated and now - last_time < cooldown:
                suppressed += 1
                continue
            event = {**candidate, "created_at": now, "audio_action": "hud"}
            accepted.append(event)
            self._last_by_key[key] = (now, candidate["severity"])

        if accepted:
            winner = accepted[0]
            audio_gap = float(self.config["global_audio_gap_seconds"])
            if winner["severity"] == "critical":
                winner["audio_action"] = "beep_tts"
                self._last_audio = now
            elif now - self._last_audio >= audio_gap:
                winner["audio_action"] = "tts"
                self._last_audio = now
            else:
                suppressed += 1
        return accepted, suppressed

