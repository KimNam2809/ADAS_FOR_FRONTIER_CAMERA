from __future__ import annotations

from .contracts import Layer3_DecisionOutput


class AudioAdapter:
    def emit(self, output: Layer3_DecisionOutput) -> None:
        signals = (
            output.decision_matrix.actuation_signals
        )

        selected = output.decision_matrix.selected_alert

        if selected is None:
            return

        if signals.beep_immediate:
            self.play_urgent_beep()
            return

        if signals.tts_allowed:
            text = self.message_to_text(
                selected.message_key
            )
            self.enqueue_tts(text)

    @staticmethod
    def play_urgent_beep() -> None:
        print("[AUDIO] URGENT_BEEP")

    @staticmethod
    def enqueue_tts(text: str) -> None:
        print(f"[AUDIO] TTS_QUEUE: {text}")

    @staticmethod
    def message_to_text(message_key: str) -> str:
        messages = {
            "slow_down": "Phía trước có nguy cơ, giảm tốc.",
            "slow_down_immediately": "Cảnh báo, giảm tốc ngay.",
            "motorcycle_cut_in_slow_down": (
                "Xe máy cắt vào phía trước, giảm tốc."
            ),
            "car_cut_in_slow_down": (
                "Xe phía trước cắt làn, giảm tốc."
            ),
            "person_cut_in_slow_down": (
                "Có người phía trước, giảm tốc."
            ),
            "lane_departure": (
                "Bạn đang lệch làn."
            ),
            "perception_unavailable": (
                "Hệ thống nhận diện đang tạm thời suy giảm."
            ),
        }

        return messages.get(
            message_key,
            "Có cảnh báo phía trước.",
        )