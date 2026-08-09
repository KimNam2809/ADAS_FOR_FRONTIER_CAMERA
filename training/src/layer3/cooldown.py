from __future__ import annotations

from typing import Optional


class CooldownManager:
    """
    Quản lý cooldown theo từng loại event và track_id.

    Ví dụ:
        ("FCW", 17) và ("FCW", 22) là hai cooldown độc lập.
    """

    def __init__(self):
        self._last_emitted: dict[
            tuple[str, Optional[int]],
            int,
        ] = {}

    def can_emit(
        self,
        event_type: str,
        track_id: Optional[int],
        now_ms: int,
        cooldown_ms: int,
    ) -> bool:
        key = (event_type, track_id)
        last_time = self._last_emitted.get(key)

        if last_time is None:
            return True

        return now_ms - last_time >= cooldown_ms

    def mark_emitted(
        self,
        event_type: str,
        track_id: Optional[int],
        now_ms: int,
    ) -> None:
        key = (event_type, track_id)
        self._last_emitted[key] = now_ms

    def remaining_ms(
        self,
        event_type: str,
        track_id: Optional[int],
        now_ms: int,
        cooldown_ms: int,
    ) -> int:
        key = (event_type, track_id)
        last_time = self._last_emitted.get(key)

        if last_time is None:
            return 0

        elapsed = now_ms - last_time
        return max(0, cooldown_ms - elapsed)

    def reset(self) -> None:
        self._last_emitted.clear()