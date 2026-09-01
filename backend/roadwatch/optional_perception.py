from __future__ import annotations

import threading
from typing import Any

import numpy as np


class OptionalPerceptionWorker:
    """Run sign/lane heads on the latest frame without blocking object/risk replay.

    Cloud Run has no GPU quota in the RoadWatch demo project. This worker drops
    superseded requests and publishes only results from the active generation,
    so optional CPU heads cannot leak across seek, loop, or video switches.
    """

    def __init__(
        self,
        signs: Any,
        lane: Any,
        metrics: Any,
        sign_interval: int,
        sign_candidate_interval: int,
        lane_interval: int,
        max_staleness_seconds: float,
    ) -> None:
        self.signs = signs
        self.lane = lane
        self.metrics = metrics
        self.sign_interval = max(1, int(sign_interval))
        self.sign_candidate_interval = max(1, int(sign_candidate_interval))
        self.lane_interval = max(1, int(lane_interval))
        self.max_staleness_seconds = max(0.1, float(max_staleness_seconds))
        self._lock = threading.RLock()
        self._sign_wake = threading.Event()
        self._lane_wake = threading.Event()
        self._stop = threading.Event()
        self._sign_thread: threading.Thread | None = None
        self._lane_thread: threading.Thread | None = None
        self._generation = 0
        self._sign_pending: tuple[int, int, float, np.ndarray] | None = None
        self._lane_pending: tuple[int, int, float, np.ndarray] | None = None
        self._last_sign_frame = -1_000_000
        self._last_lane_frame = -1_000_000
        self._signs: list[dict[str, Any]] = []
        self._sign_source_time = -1.0
        self._sign_sequence = 0
        self._lane: dict[str, Any] | None = None
        self._lane_source_time = -1.0
        self._lane_sequence = 0
        self._submitted = 0
        self._sign_replaced = 0
        self._lane_replaced = 0

    def start(self) -> None:
        if self._sign_thread and self._sign_thread.is_alive():
            return
        self._stop.clear()
        self._sign_thread = threading.Thread(
            target=self._run_sign, name="roadwatch-sign-perception", daemon=True
        )
        self._lane_thread = threading.Thread(
            target=self._run_lane, name="roadwatch-lane-perception", daemon=True
        )
        self._sign_thread.start()
        self._lane_thread.start()

    def close(self) -> None:
        self._stop.set()
        self._sign_wake.set()
        self._lane_wake.set()
        if self._sign_thread:
            self._sign_thread.join(timeout=2.0)
        if self._lane_thread:
            self._lane_thread.join(timeout=2.0)

    def reset(self) -> None:
        with self._lock:
            self._generation += 1
            self._sign_pending = None
            self._lane_pending = None
            self._last_sign_frame = -1_000_000
            self._last_lane_frame = -1_000_000
            self._signs = []
            self._sign_source_time = -1.0
            self._sign_sequence = 0
            self._lane = None
            self._lane_source_time = -1.0
            self._lane_sequence = 0
        self._sign_wake.clear()
        self._lane_wake.clear()

    def submit(self, frame: np.ndarray, frame_id: int, source_time: float) -> None:
        with self._lock:
            if self._sign_pending is not None:
                self._sign_replaced += 1
            if self._lane_pending is not None:
                self._lane_replaced += 1
            request = (
                self._generation,
                int(frame_id),
                float(source_time),
                frame.copy(),
            )
            self._sign_pending = request
            self._lane_pending = request
            self._submitted += 1
        self._sign_wake.set()
        self._lane_wake.set()

    def snapshot(self, source_time: float) -> dict[str, Any]:
        with self._lock:
            sign_age = (
                max(0.0, float(source_time) - self._sign_source_time)
                if self._sign_source_time >= 0
                else float("inf")
            )
            lane_age = (
                max(0.0, float(source_time) - self._lane_source_time)
                if self._lane_source_time >= 0
                else float("inf")
            )
            return {
                "signs": list(self._signs) if sign_age <= self.max_staleness_seconds else [],
                "sign_sequence": self._sign_sequence,
                "sign_age_seconds": round(sign_age, 3) if sign_age != float("inf") else None,
                "lane": self._lane if lane_age <= self.max_staleness_seconds else None,
                "lane_sequence": self._lane_sequence,
                "lane_age_seconds": round(lane_age, 3) if lane_age != float("inf") else None,
                "submitted": self._submitted,
                "replaced": self._sign_replaced + self._lane_replaced,
                "sign_replaced": self._sign_replaced,
                "lane_replaced": self._lane_replaced,
            }

    def _run_sign(self) -> None:
        while not self._stop.is_set():
            self._sign_wake.wait(timeout=0.2)
            if self._stop.is_set():
                return
            with self._lock:
                request = self._sign_pending
                self._sign_pending = None
                self._sign_wake.clear()
                current_generation = self._generation
            if request is None:
                continue
            generation, frame_id, source_time, frame = request
            if generation != current_generation:
                continue

            with self._lock:
                sign_interval = (
                    self.sign_candidate_interval if self._signs else self.sign_interval
                )
                run_sign = frame_id - self._last_sign_frame >= sign_interval
            if not run_sign:
                continue
            sign_result, latency = self.signs.infer(frame)
            self.metrics.observe("traffic_sign", latency)

            with self._lock:
                if generation != self._generation:
                    continue
                self._signs = sign_result
                self._sign_source_time = source_time
                self._sign_sequence += 1
                self._last_sign_frame = frame_id

    def _run_lane(self) -> None:
        while not self._stop.is_set():
            self._lane_wake.wait(timeout=0.2)
            if self._stop.is_set():
                return
            with self._lock:
                request = self._lane_pending
                self._lane_pending = None
                self._lane_wake.clear()
                current_generation = self._generation
            if request is None:
                continue
            generation, frame_id, source_time, frame = request
            if generation != current_generation:
                continue
            with self._lock:
                run_lane = frame_id - self._last_lane_frame >= self.lane_interval
            if not run_lane:
                continue
            lane_result, latency = self.lane.infer(frame)
            self.metrics.observe("lane_detection", latency)
            with self._lock:
                if generation != self._generation:
                    continue
                self._lane = lane_result
                self._lane_source_time = source_time
                self._lane_sequence += 1
                self._last_lane_frame = frame_id
