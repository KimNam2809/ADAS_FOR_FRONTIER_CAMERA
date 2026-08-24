from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from typing import Any

from .sign_arbitration import arbitrate_sign_candidates


SEVERITY_RANK = {"informational": 0, "advisory": 1, "warning": 2, "critical": 3}
EVENT_SPECIFICITY = {
    "fcw": 0,
    "vulnerable_road_user": 1,
    "cut_in": 2,
    "lead_vehicle_braking": 3,
    "cross_traffic": 4,
}


class AlertGovernor:
    """The only component authorized to emit alerts to the HMI/audio layer."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config["alerts"]
        self._last_by_key: dict[str, tuple[float, str]] = {}
        self._last_audio = float("-inf")
        self._pending_speed_sign: tuple[dict[str, Any], float] | None = None
        self._audio_history_by_key: dict[str, deque[float]] = defaultdict(deque)
        self.last_suppressed: list[dict[str, Any]] = []

    def reset(self) -> None:
        self._last_by_key.clear()
        self._last_audio = float("-inf")
        self._pending_speed_sign = None
        self._audio_history_by_key.clear()
        self.last_suppressed = []

    def decide(
        self,
        candidates: list[dict[str, Any]],
        now: float | None = None,
        clock: float | None = None,
        frame_id: int | None = None,
        source_time: float | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        now = now or time.time()
        clock = now if clock is None else clock
        candidates = list(candidates)
        if self._pending_speed_sign is not None:
            pending, deadline = self._pending_speed_sign
            if clock > deadline:
                self._pending_speed_sign = None
            elif not any(
                item.get("event_type") == "speed_sign"
                and item.get("cooldown_key") == pending.get("cooldown_key")
                for item in candidates
            ):
                # A confirmed speed limit remains relevant after the physical
                # sign leaves the frame. Retain it briefly so a preceding FCW
                # or sign announcement cannot silence it permanently.
                candidates.append(pending)
        candidates, sign_suppressed = arbitrate_sign_candidates(candidates)
        accepted: list[dict[str, Any]] = []
        suppressed = len(sign_suppressed)
        self.last_suppressed = [
            {**candidate, "lifecycle_status": "suppressed", "suppression_reason": "sign_family_arbitration"}
            for candidate in sign_suppressed
        ]
        # One object can satisfy several rules in the same frame. Keep the
        # most actionable sentence instead of creating competing banners.
        deduplicated: dict[tuple[str, Any], dict[str, Any]] = {}
        for index, candidate in enumerate(candidates):
            object_id = candidate.get("object_id")
            group = (
                ("object", object_id)
                if object_id is not None
                else ("standalone", candidate.get("cooldown_key", index))
            )
            current = deduplicated.get(group)
            score = (
                SEVERITY_RANK.get(candidate["severity"], 0),
                candidate.get(
                    "event_priority", EVENT_SPECIFICITY.get(candidate["event_type"], 0)
                ),
                candidate["risk_score"],
            )
            if current is None or score > (
                SEVERITY_RANK.get(current["severity"], 0),
                current.get(
                    "event_priority", EVENT_SPECIFICITY.get(current["event_type"], 0)
                ),
                current["risk_score"],
            ):
                deduplicated[group] = candidate
        correlated_suppressed = len(candidates) - len(deduplicated)
        suppressed += correlated_suppressed
        if correlated_suppressed:
            kept = {id(item) for item in deduplicated.values()}
            self.last_suppressed.extend(
                {
                    **candidate,
                    "lifecycle_status": "suppressed",
                    "suppression_reason": "correlated_event",
                }
                for candidate in candidates
                if id(candidate) not in kept
            )
        ordered = sorted(
            deduplicated.values(),
            key=lambda item: (
                SEVERITY_RANK.get(item["severity"], 0),
                item.get("event_priority", EVENT_SPECIFICITY.get(item["event_type"], 0)),
                item["risk_score"],
                str(item.get("cooldown_key", "")),
            ),
            reverse=True,
        )
        for candidate in ordered:
            key = candidate["cooldown_key"]
            # Source/video clocks start at zero. Using 0.0 as an unseen event's
            # timestamp accidentally suppresses its first occurrence during
            # the opening cooldown window, especially informational signs.
            last_time, last_severity = self._last_by_key.get(
                key, (float("-inf"), "informational")
            )
            if candidate.get("is_traffic_sign") or candidate["event_type"] == "speed_sign":
                cooldown = float(self.config["sign_cooldown_seconds"])
            elif candidate["severity"] == "critical":
                cooldown = float(self.config["critical_cooldown_seconds"])
            else:
                cooldown = float(self.config["warning_cooldown_seconds"])
            escalated = SEVERITY_RANK[candidate["severity"]] > SEVERITY_RANK[last_severity]
            if not escalated and clock - last_time < cooldown:
                suppressed += 1
                self.last_suppressed.append(
                    {**candidate, "lifecycle_status": "suppressed", "suppression_reason": "cooldown"}
                )
                continue
            ttl_key = (
                "critical_ttl_seconds"
                if candidate["severity"] == "critical"
                else "advisory_ttl_seconds"
                if candidate["severity"] == "advisory"
                else "warning_ttl_seconds"
            )
            ttl = float(self.config.get(ttl_key, 1.5))
            event = {
                **candidate,
                # HMI and audio are derived from the same canonical payload.
                # Separate names make consistency auditable without allowing
                # either layer to rewrite the sentence independently.
                "display_message": candidate["message"],
                "spoken_message": candidate["message"],
                "event_id": str(uuid.uuid4()),
                "frame_id": frame_id,
                "source_time": source_time,
                "created_at": now,
                "expires_at": now + ttl,
                "lifecycle_status": "accepted",
                "suppression_reason": None,
                "audio_status": "not_requested",
                "audio_action": "hud",
                # Different signs must not silently replace one another in the
                # asynchronous audio queue. Repeated detections of the same
                # physical/sign class still supersede stale copies.
                "supersede_key": candidate["cooldown_key"],
            }
            accepted.append(event)
            self._last_by_key[key] = (clock, candidate["severity"])

        audio_candidates = [item for item in accepted if item.get("audio_eligible", True)]
        if audio_candidates:
            winner = audio_candidates[0]
            audio_gap = float(self.config["global_audio_gap_seconds"])
            budget_key = str(
                winner.get("semantic_audio_key")
                or winner.get("cooldown_key")
                or winner["event_type"]
            )
            budget_window = float(self.config.get("advisory_audio_window_seconds", 60.0))
            budget_max = int(self.config.get("advisory_audio_max_per_window", 3))
            history = self._audio_history_by_key[budget_key]
            while history and clock - history[0] >= budget_window:
                history.popleft()
            budget_available = len(history) < budget_max
            if winner["severity"] == "critical":
                winner["audio_action"] = "beep_tts"
                winner["audio_status"] = "queued"
                self._last_audio = clock
            elif not budget_available:
                suppressed += 1
                winner["audio_status"] = "suppressed"
                winner["suppression_reason"] = "semantic_audio_budget"
                self.last_suppressed.append({
                    **winner,
                    "lifecycle_status": "accepted",
                    "suppression_reason": "semantic_audio_budget",
                })
            elif clock - self._last_audio >= audio_gap:
                winner["audio_action"] = "tts"
                winner["audio_status"] = "queued"
                self._last_audio = clock
                history.append(clock)
                if winner["event_type"] == "speed_sign":
                    self._pending_speed_sign = None
            else:
                suppressed += 1
                winner["audio_status"] = "suppressed"
                winner["suppression_reason"] = "global_audio_gap"
                self.last_suppressed.append(
                    {
                        **winner,
                        "lifecycle_status": "accepted",
                        "suppression_reason": "global_audio_gap",
                    }
                )
                if winner.get("is_traffic_sign"):
                    # The sign remains visible in subsequent frames. Re-arm
                    # only its audio attempt so FCW/LDW can pre-empt it now
                    # without silencing it for the entire sign cooldown.
                    retry = float(self.config.get("sign_audio_retry_seconds", 1.0))
                    cooldown = float(self.config["sign_cooldown_seconds"])
                    self._last_by_key[winner["cooldown_key"]] = (
                        clock - cooldown + retry,
                        winner["severity"],
                    )
                    if winner["event_type"] == "speed_sign":
                        pending_seconds = float(
                            self.config.get("speed_sign_audio_pending_seconds", 4.0)
                        )
                        self._pending_speed_sign = (
                            {key: value for key, value in winner.items() if key not in {
                                "event_id", "created_at", "expires_at", "lifecycle_status",
                                "audio_status", "audio_action", "display_message",
                                "spoken_message", "supersede_key", "suppression_reason",
                            }},
                            clock + pending_seconds,
                        )

        # A higher-priority event can win this frame. Re-arm confirmed signs
        # that were accepted for HUD but did not receive an audio slot.
        for event in accepted:
            if (
                event.get("is_traffic_sign")
                and event.get("audio_eligible", True)
                and event["audio_action"] == "hud"
            ):
                retry = float(self.config.get("sign_audio_retry_seconds", 1.0))
                cooldown = float(self.config["sign_cooldown_seconds"])
                self._last_by_key[event["cooldown_key"]] = (
                    clock - cooldown + retry,
                    event["severity"],
                )
                if event["event_type"] == "speed_sign":
                    pending_seconds = float(
                        self.config.get("speed_sign_audio_pending_seconds", 4.0)
                    )
                    self._pending_speed_sign = (
                        {key: value for key, value in event.items() if key not in {
                            "event_id", "created_at", "expires_at", "lifecycle_status",
                            "audio_status", "audio_action", "display_message",
                            "spoken_message", "supersede_key", "suppression_reason",
                        }},
                        clock + pending_seconds,
                    )
        return accepted, suppressed
