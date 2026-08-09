from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Policy:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    @classmethod
    def from_json(cls, path: str | Path) -> "Policy":
        path = Path(path)

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return cls(data)

    def get(self, *keys: str, default=None):
        value = self.data

        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default

            value = value[key]

        return value

    @property
    def max_frame_age_ms(self) -> int:
        return self.get(
            "global",
            "max_frame_age_ms",
            default=250,
        )

    @property
    def min_stable_frames(self) -> int:
        return self.get(
            "global",
            "min_stable_frames",
            default=4,
        )

    @property
    def min_object_confidence(self) -> float:
        return self.get(
            "global",
            "min_object_confidence",
            default=0.5,
        )

    @property
    def critical_cooldown_ms(self) -> int:
        return self.get(
            "global",
            "critical_cooldown_ms",
            default=1200,
        )

    @property
    def warning_cooldown_ms(self) -> int:
        return self.get(
            "global",
            "warning_cooldown_ms",
            default=5000,
        )