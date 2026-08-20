from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class VehicleTelemetry:
    """Read-only ego telemetry. No actuator command is represented by design."""

    timestamp: float
    speed_kph: float | None = None
    turn_signal: str | None = None
    brake_pressed: bool | None = None
    source: str = "unavailable"

    def public(self) -> dict[str, object]:
        return asdict(self)


class ReadOnlyVehicleAdapter(Protocol):
    def read(self) -> VehicleTelemetry: ...

    def status(self) -> dict[str, object]: ...


class DisabledVehicleAdapter:
    def read(self) -> VehicleTelemetry:
        return VehicleTelemetry(timestamp=0.0)

    def status(self) -> dict[str, object]:
        return {
            "mode": "disabled",
            "read_only": True,
            "actuator_api": False,
            "reason": "CAN/OBD chưa được cấu hình hoặc kiểm chứng trên phần cứng.",
        }
