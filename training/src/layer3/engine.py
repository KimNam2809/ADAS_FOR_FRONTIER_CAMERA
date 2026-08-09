from __future__ import annotations

from typing import Optional

from .config import Policy
from .cooldown import CooldownManager
from .contracts import (
    ActuationSignals,
    AlertCandidate,
    DecisionMatrix,
    Layer2_KinematicsOutput,
    Layer3_DecisionOutput,
    PassthroughContext,
)
from .rules import (
    evaluate_cut_in,
    evaluate_fcw,
    evaluate_ldw,
)


class DecisionEngine:
    def __init__(self, policy: Policy):
        self.policy = policy
        self.cooldown = CooldownManager()
        self.lane_departure_started_ms: Optional[int] = None

    def evaluate(
        self,
        input_data: Layer2_KinematicsOutput,
    ) -> Layer3_DecisionOutput:
        metadata = input_data.frame_metadata

        if metadata.frame_age_ms > self.policy.max_frame_age_ms:
            return self._build_degraded_output(input_data)

        candidates: list[AlertCandidate] = []

        for obj in input_data.tracked_objects:
            fcw = evaluate_fcw(
                obj=obj,
                frame_id=metadata.frame_id,
                policy=self.policy,
            )

            if fcw is not None:
                candidates.append(fcw)

            cut_in = evaluate_cut_in(
                obj=obj,
                frame_id=metadata.frame_id,
                policy=self.policy,
            )

            if cut_in is not None:
                candidates.append(cut_in)

        ldw, self.lane_departure_started_ms = evaluate_ldw(
            lanes=input_data.lanes,
            frame_id=metadata.frame_id,
            timestamp_ms=metadata.timestamp_ms,
            lane_departure_started_ms=(
                self.lane_departure_started_ms
            ),
            policy=self.policy,
        )

        if ldw is not None:
            candidates.append(ldw)

        candidates = self._apply_cooldown(
            candidates=candidates,
            timestamp_ms=metadata.timestamp_ms,
        )

        selected = self._select_highest_priority(candidates)

        if selected is None:
            decision = self._build_no_alert_decision(
                candidates=candidates,
            )
        else:
            decision = self._build_alert_decision(
                selected=selected,
                candidates=candidates,
            )

            self.cooldown.mark_emitted(
                event_type=selected.event_type,
                track_id=selected.track_id,
                now_ms=metadata.timestamp_ms,
            )

        ttc_values = [
            obj.kinematics.ttc_sec
            for obj in input_data.tracked_objects
            if obj.kinematics.ttc_sec is not None
        ]

        closest_ttc = min(ttc_values) if ttc_values else None

        return Layer3_DecisionOutput(
            frame_metadata=metadata,
            decision_matrix=decision,
            passthrough_context=PassthroughContext(
                scene_understanding=(
                    input_data.scene_understanding
                ),
                ttc_closest_sec=closest_ttc,
                source_frame_age_ms=metadata.frame_age_ms,
            ),
        )

    def _apply_cooldown(
        self,
        candidates: list[AlertCandidate],
        timestamp_ms: int,
    ) -> list[AlertCandidate]:
        result = []

        for candidate in candidates:
            if candidate.severity == "critical":
                cooldown_ms = self.policy.critical_cooldown_ms
            else:
                cooldown_ms = self.policy.warning_cooldown_ms

            can_emit = self.cooldown.can_emit(
                event_type=candidate.event_type,
                track_id=candidate.track_id,
                now_ms=timestamp_ms,
                cooldown_ms=cooldown_ms,
            )

            if not can_emit:
                candidate.suppressed = True
                candidate.suppression_reason = (
                    "same_event_in_cooldown"
                )

            result.append(candidate)

        return result

    @staticmethod
    def _select_highest_priority(
        candidates: list[AlertCandidate],
    ) -> Optional[AlertCandidate]:
        emit_candidates = [
            item
            for item in candidates
            if not item.suppressed
        ]

        if not emit_candidates:
            return None

        severity_order = {
            "critical": 0,
            "warning": 1,
            "info": 2,
        }

        emit_candidates.sort(
            key=lambda item: (
                item.priority_level,
                severity_order[item.severity],
            )
        )

        selected = emit_candidates[0]

        for candidate in candidates:
            if candidate.event_id != selected.event_id:
                if not candidate.suppressed:
                    candidate.suppressed = True
                    candidate.suppression_reason = (
                        "higher_priority_alert_selected"
                    )

        return selected

    @staticmethod
    def _build_alert_decision(
        selected: AlertCandidate,
        candidates: list[AlertCandidate],
    ) -> DecisionMatrix:
        if selected.severity == "critical":
            signals = ActuationSignals(
                audio="urgent_beep",
                visual="red_overlay",
                beep_immediate=True,
                tts_allowed=False,
                suppress_lower_priority=True,
            )
        else:
            signals = ActuationSignals(
                audio="chime",
                visual="yellow_overlay",
                beep_immediate=False,
                tts_allowed=True,
                suppress_lower_priority=False,
            )

        return DecisionMatrix(
            active_event=selected.event_type,
            active_severity=selected.severity,
            priority_level=selected.priority_level,
            actuation_signals=signals,
            selected_alert=selected,
            candidates=candidates,
        )

    @staticmethod
    def _build_no_alert_decision(
        candidates: list[AlertCandidate],
    ) -> DecisionMatrix:
        return DecisionMatrix(
            active_event="none",
            active_severity="info",
            priority_level=3,
            actuation_signals=ActuationSignals(
                audio="none",
                visual="none",
                beep_immediate=False,
                tts_allowed=False,
                suppress_lower_priority=False,
            ),
            selected_alert=None,
            candidates=candidates,
        )

    @staticmethod
    def _build_degraded_output(
        input_data: Layer2_KinematicsOutput,
    ) -> Layer3_DecisionOutput:
        alert = AlertCandidate(
            event_id=(
                f"system_degraded_"
                f"{input_data.frame_metadata.frame_id}"
            ),
            event_type="System-Degraded",
            severity="warning",
            priority_level=1,
            message_key="perception_unavailable",
            reason={
                "frame_age_ms": (
                    input_data.frame_metadata.frame_age_ms
                ),
                "reason": "stale_frame",
            },
        )

        decision = DecisionMatrix(
            active_event="System-Degraded",
            active_severity="warning",
            priority_level=1,
            actuation_signals=ActuationSignals(
                audio="none",
                visual="yellow_overlay",
                beep_immediate=False,
                tts_allowed=False,
                suppress_lower_priority=True,
            ),
            selected_alert=alert,
            candidates=[alert],
        )

        return Layer3_DecisionOutput(
            frame_metadata=input_data.frame_metadata,
            decision_matrix=decision,
            passthrough_context=PassthroughContext(
                scene_understanding=(
                    input_data.scene_understanding
                ),
                ttc_closest_sec=None,
                source_frame_age_ms=(
                    input_data.frame_metadata.frame_age_ms
                ),
            ),
        )