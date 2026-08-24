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
        self.warmup_started_at: float | None = None
        self.warmup_ms: float = 0.0
        self.captured_frames = 0
        self.processed_frames = 0
        self.dropped_frames = 0
        self.scheduled_skipped_frames = 0
        self.overload_dropped_frames = 0
        self.alerts_emitted = 0
        self.alerts_suppressed = 0
        self.audio_completed = 0
        self.audio_dropped_stale = 0
        self.events_by_type: dict[str, int] = defaultdict(int)
        self.suppression_reasons: dict[str, int] = defaultdict(int)
        self.lane_frames = 0
        self.lane_eligible_frames = 0

    def begin_warmup(self) -> None:
        with self._lock:
            self.warmup_started_at = time.perf_counter()

    def finish_warmup(self) -> None:
        with self._lock:
            if self.warmup_started_at is not None:
                self.warmup_ms = round(
                    (time.perf_counter() - self.warmup_started_at) * 1000, 2
                )
                self.warmup_started_at = None

    def record_lane_quality(self, quality: float, threshold: float) -> None:
        with self._lock:
            self.lane_frames += 1
            if quality >= threshold:
                self.lane_eligible_frames += 1

    def record_event(self, event_type: str) -> None:
        with self._lock:
            self.events_by_type[event_type] += 1

    def record_suppression(self, reason: str) -> None:
        with self._lock:
            self.suppression_reasons[reason] += 1

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
                "warmup_ms": self.warmup_ms,
                "captured_frames": self.captured_frames,
                "processed_frames": self.processed_frames,
                "dropped_frames": self.dropped_frames,
                "scheduled_skipped_frames": self.scheduled_skipped_frames,
                "overload_dropped_frames": self.overload_dropped_frames,
                "processed_fps": round(self.processed_frames / elapsed, 2),
                "frame_drop_ratio": round(
                    self.dropped_frames / max(self.captured_frames, 1), 4
                ),
                "sampling_skip_ratio": round(
                    self.scheduled_skipped_frames / max(self.captured_frames, 1), 4
                ),
                "overload_drop_ratio": round(
                    self.overload_dropped_frames / max(self.captured_frames, 1), 4
                ),
                "alerts_emitted": self.alerts_emitted,
                "alerts_suppressed": self.alerts_suppressed,
                "audio_completed": self.audio_completed,
                "audio_dropped_stale": self.audio_dropped_stale,
                "audio_stale_event_rate": round(
                    self.audio_dropped_stale
                    / max(self.audio_completed + self.audio_dropped_stale, 1),
                    4,
                ),
                "events_by_type": dict(self.events_by_type),
                "suppression_reasons": dict(self.suppression_reasons),
                "lane_quality_coverage": round(
                    self.lane_eligible_frames / max(self.lane_frames, 1), 4
                ),
                "latencies": latencies,
            }
