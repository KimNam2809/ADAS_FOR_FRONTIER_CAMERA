from __future__ import annotations

import statistics
import threading
import time
from collections import defaultdict, deque
from typing import Any


class MetricsCollector:
    def __init__(self, window: int = 240) -> None:
        self.window = window
        self._latencies: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=window))
        self._lock = threading.RLock()
        self.started_at = time.time()
        self.captured_frames = 0
        self.processed_frames = 0
        self.dropped_frames = 0
        self.alerts_emitted = 0
        self.alerts_suppressed = 0

    def observe(self, name: str, milliseconds: float) -> None:
        with self._lock:
            self._latencies[name].append(float(milliseconds))

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = (len(ordered) - 1) * percentile
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = index - lower
        return ordered[lower] * (1 - fraction) + ordered[upper] * fraction

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            elapsed = max(time.time() - self.started_at, 0.001)
            latencies = {}
            for name, samples in self._latencies.items():
                values = list(samples)
                latencies[name] = {
                    "mean_ms": round(statistics.fmean(values), 2) if values else 0,
                    "p50_ms": round(self._percentile(values, 0.50), 2),
                    "p95_ms": round(self._percentile(values, 0.95), 2),
                    "samples": len(values),
                }
            return {
                "uptime_seconds": round(elapsed, 1),
                "captured_frames": self.captured_frames,
                "processed_frames": self.processed_frames,
                "dropped_frames": self.dropped_frames,
                "processed_fps": round(self.processed_frames / elapsed, 2),
                "frame_drop_ratio": round(
                    self.dropped_frames / max(self.captured_frames, 1), 4
                ),
                "alerts_emitted": self.alerts_emitted,
                "alerts_suppressed": self.alerts_suppressed,
                "latencies": latencies,
            }

