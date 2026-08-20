from __future__ import annotations

import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Iterator

import cv2
import numpy as np

from .alerts import AlertGovernor
from .audio import AudioManager
from .config import ConfigManager, PROJECT_ROOT, model_inventory
from .metrics import MetricsCollector
from .kinematics import MonocularKinematics
from .perception import PerceptionEngine
from .risk import RiskEngine
from .storage import Storage
from .tracking import IoUTracker
from .vehicle_io import DisabledVehicleAdapter


LOGGER = logging.getLogger(__name__)


class RoadWatchService:
    def __init__(self, config_manager: ConfigManager, storage: Storage) -> None:
        self.config_manager = config_manager
        self.storage = storage
        self._state_lock = threading.RLock()
        self._frame_lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest_jpeg: bytes | None = None
        self._recent_events: deque[dict[str, Any]] = deque(maxlen=20)
        self._active_events: dict[str, dict[str, Any]] = {}
        self._status: dict[str, Any] = {
            "running": False,
            "mode": "idle",
            "source": None,
            "frame_id": 0,
            "source_time": 0.0,
            "source_fps": 0,
            "tracks": [],
            "signs": [],
            "lane": {"quality": 0, "offset": 0},
            "events": [],
            "degraded_reasons": [],
            "error": None,
        }
        self._build_components()

    def _build_components(self) -> None:
        config = self.config_manager.snapshot()
        self.perception = PerceptionEngine(config)
        self.tracker = IoUTracker(config["tracking"])
        self.kinematics = MonocularKinematics(
            PROJECT_ROOT / "configs" / "camera_calibration.json",
            enabled=bool(config["vehicle"].get("camera_calibrated", False)),
        )
        self.risk = RiskEngine(config)
        self.governor = AlertGovernor(config)
        self.audio = AudioManager(config, self._audio_lifecycle)
        self.metrics = MetricsCollector()
        self.vehicle_io = DisabledVehicleAdapter()

    def reload_config(self) -> None:
        if self.is_running:
            raise RuntimeError("Hãy dừng phiên phân tích trước khi nạp cấu hình mới")
        self.audio.stop()
        self._build_components()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(
        self,
        source: str | int | None = None,
        start_seconds: float = 0.0,
        duration_seconds: float | None = None,
    ) -> None:
        if self.is_running:
            raise RuntimeError("Một phiên phân tích đang chạy")
        config = self.config_manager.snapshot()
        source = source if source is not None else config["app"]["default_source"]
        resolved = ConfigManager.media_source(source)
        self._stop.clear()
        self.tracker.reset()
        self.kinematics.reset()
        self.risk.reset()
        self.governor.reset()
        self._recent_events.clear()
        self._active_events.clear()
        self.metrics = MetricsCollector()
        self.audio.start()
        self._thread = threading.Thread(
            target=self._run,
            args=(resolved, float(start_seconds), duration_seconds),
            name="roadwatch-pipeline",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        with self._state_lock:
            self._status["running"] = False
            self._status["mode"] = "idle"

    def close(self) -> None:
        self.stop()
        self.audio.stop()

    def _run(
        self, source: str | int, start_seconds: float = 0.0, duration_seconds: float | None = None
    ) -> None:
        config = self.config_manager.snapshot()
        app_config = config["app"]
        inf_config = config["inference"]
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            self._set_error(f"Không thể mở nguồn video: {Path(str(source)).name}")
            return
        if isinstance(source, str) and start_seconds > 0:
            cap.set(cv2.CAP_PROP_POS_MSEC, start_seconds * 1000.0)
        source_fps = float(cap.get(cv2.CAP_PROP_FPS))
        if source_fps <= 0 or source_fps > 240:
            source_fps = float(app_config["max_processed_fps"])
        target_fps = min(float(app_config["max_processed_fps"]), source_fps)
        stride = max(1, round(source_fps / max(target_fps, 1)))
        processed_id = 0
        captured_id = 0
        objects: list[dict[str, Any]] = []
        signs: list[dict[str, Any]] = []
        lane_output: dict[str, Any] | None = None
        started = time.perf_counter()

        with self._state_lock:
            self._status.update(
                {
                    "running": True,
                    "mode": "replay" if isinstance(source, str) else "camera",
                    "source": Path(source).name if isinstance(source, str) else f"camera:{source}",
                    "source_fps": round(source_fps, 2),
                    "error": None,
                }
            )
        try:
            self.perception.warmup()
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    if isinstance(source, str) and app_config.get("loop_video", True):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.tracker.reset()
                        self.risk.reset()
                        self.governor.reset()
                        self._active_events.clear()
                        continue
                    break
                captured_id += 1
                self.metrics.captured_frames += 1
                source_time = (
                    float(cap.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
                    if isinstance(source, str)
                    else time.monotonic()
                )
                if duration_seconds is not None and source_time >= start_seconds + duration_seconds:
                    break
                if (captured_id - 1) % stride:
                    self.metrics.dropped_frames += 1
                    self.metrics.scheduled_skipped_frames += 1
                    continue
                frame_started = time.perf_counter()
                processed_id += 1
                timestamp = source_time

                if inf_config.get("enable_objects", True) and processed_id % int(
                    inf_config["object_interval"]
                ) == 0:
                    objects, latency = self.perception.objects.infer(frame)
                    self.metrics.observe("object_detection", latency)

                sign_fresh = False
                sign_interval = int(
                    inf_config.get("sign_candidate_interval", 1)
                    if signs
                    else inf_config["sign_interval"]
                )
                if inf_config.get("enable_signs", True) and processed_id % sign_interval == 0:
                    signs, latency = self.perception.signs.infer(frame)
                    self.metrics.observe("traffic_sign", latency)
                    sign_fresh = True

                if lane_output is None or (
                    inf_config.get("enable_lane", True)
                    and processed_id % int(inf_config["lane_interval"]) == 0
                ):
                    lane_output, latency = self.perception.lane.infer(frame)
                    self.metrics.observe("lane_detection", latency)
                if lane_output is None:
                    lane_output = self.perception.lane.empty(frame.shape[:2])

                tracks = self.tracker.update(objects, timestamp, frame.shape[1])
                tracks = self.kinematics.enrich(tracks, timestamp)
                candidates, tracks, lane_state = self.risk.analyze(
                    tracks,
                    signs,
                    lane_output,
                    frame.shape[:2],
                    sign_fresh,
                    frame=frame,
                    timestamp=source_time,
                )
                self.metrics.record_lane_quality(
                    float(lane_state.get("quality", 0.0)),
                    float(config["risk"]["lane_quality_min"]),
                )
                emitted, suppressed = self.governor.decide(
                    candidates,
                    now=time.time(),
                    clock=source_time,
                    frame_id=processed_id,
                    source_time=source_time,
                )
                self.metrics.alerts_suppressed += suppressed
                for item in self.governor.last_suppressed:
                    self.metrics.record_suppression(item.get("suppression_reason", "unknown"))
                for event in emitted:
                    event_id = self.storage.add_event(event)
                    event["id"] = event_id
                    self._recent_events.appendleft(event)
                    self.metrics.alerts_emitted += 1
                    self.metrics.record_event(event["event_type"])
                    self._active_events[event["event_id"]] = event
                    self.audio.submit(event)

                candidate_by_object = {
                    item.get("object_id"): item for item in candidates if item.get("object_id") is not None
                }
                suppressed_by_object = {
                    item.get("object_id"): item
                    for item in self.governor.last_suppressed
                    if item.get("object_id") is not None
                }
                accepted_by_object = {
                    item.get("object_id"): item for item in emitted if item.get("object_id") is not None
                }
                now_epoch = time.time()
                visual_ttl = float(config["alerts"].get("visual_ttl_seconds", 2.5))
                self._active_events = {
                    key: item
                    for key, item in self._active_events.items()
                    if now_epoch - float(item["created_at"]) <= visual_ttl
                }
                active_by_object = {
                    item.get("object_id"): item
                    for item in self._active_events.values()
                    if item.get("object_id") is not None
                }
                for track in tracks:
                    object_id = track["track_id"]
                    track["alert_state"] = "observed"
                    if object_id in candidate_by_object:
                        track["alert_state"] = "candidate"
                    if object_id in suppressed_by_object:
                        track["alert_state"] = "suppressed"
                        track["suppression_reason"] = suppressed_by_object[object_id].get(
                            "suppression_reason"
                        )
                    if object_id in active_by_object or object_id in accepted_by_object:
                        active = accepted_by_object.get(object_id) or active_by_object[object_id]
                        track["alert_state"] = "active"
                        track["alert_severity"] = active["severity"]

                active_events = sorted(
                    self._active_events.values(),
                    key=lambda item: (item["severity"] == "critical", item["risk_score"]),
                    reverse=True,
                )
                annotated = self._annotate(
                    frame, tracks, signs, lane_output, lane_state, active_events
                )
                encode_ok, jpeg = cv2.imencode(
                    ".jpg",
                    annotated,
                    [cv2.IMWRITE_JPEG_QUALITY, int(app_config["jpeg_quality"])],
                )
                if encode_ok:
                    with self._frame_lock:
                        self._latest_jpeg = jpeg.tobytes()

                elapsed_ms = (time.perf_counter() - frame_started) * 1000
                self.metrics.observe("end_to_end", elapsed_ms)
                self.metrics.processed_frames += 1
                degraded = [
                    f"{name}: {item['error']}"
                    for name, item in self.perception.status().items()
                    if item.get("error")
                ]
                with self._state_lock:
                    self._status.update(
                        {
                            "frame_id": processed_id,
                            "source_time": round(source_time, 3),
                            "tracks": tracks[:30],
                            "signs": signs[:12],
                            "sign_trace": self.risk.last_sign_trace,
                            "lane": {
                                key: value
                                for key, value in lane_state.items()
                                if key not in {"left_poly", "right_poly"}
                            },
                            "events": list(self._recent_events)[: int(app_config["retain_events"])],
                            "degraded_reasons": degraded,
                            "models": self.perception.status(),
                        }
                    )

                if not isinstance(source, str) or app_config.get("pace_replay", True):
                    target_elapsed = processed_id / max(target_fps, 1)
                    actual_elapsed = time.perf_counter() - started
                    if target_elapsed > actual_elapsed:
                        time.sleep(min(target_elapsed - actual_elapsed, 0.1))
        except Exception as exc:  # pragma: no cover - integration guard
            LOGGER.exception("Pipeline stopped unexpectedly")
            self._set_error(str(exc))
        finally:
            cap.release()
            with self._state_lock:
                self._status["running"] = False
                self._status["mode"] = "idle"

    def _set_error(self, message: str) -> None:
        with self._state_lock:
            self._status.update({"running": False, "mode": "error", "error": message})

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            result = dict(self._status)
            result["events"] = list(self._recent_events)
            result["active_events"] = list(self._active_events.values())
        result["metrics"] = self.metrics.snapshot()
        result["audio"] = self.audio.status()
        result["guardrail"] = "Chỉ hỗ trợ cảnh báo — không tự lái, phanh hoặc đánh lái."
        result["vehicle_io"] = self.vehicle_io.status()
        result["kinematics"] = self.kinematics.status()
        return result

    def _audio_lifecycle(
        self, event: dict[str, Any], status: str, reason: str | None = None
    ) -> None:
        event_uuid = str(event.get("event_id", ""))
        if event_uuid:
            self.storage.update_event_audio(event_uuid, status, reason)
        if status == "completed":
            self.metrics.audio_completed += 1
        elif status == "dropped_stale":
            self.metrics.audio_dropped_stale += 1
            self.metrics.record_suppression(reason or "stale_audio")

    def health(self) -> dict[str, Any]:
        inventory = model_inventory()
        required_ready = all(
            item["available"] for item in inventory if item.get("required", True)
        )
        return {
            "status": "ready" if required_ready else "degraded",
            "models": inventory,
            "pipeline_running": self.is_running,
            "providers": self.perception.status(),
            "audio": self.audio.status(),
            "vehicle_io": self.vehicle_io.status(),
            "kinematics": self.kinematics.status(),
        }

    def mjpeg(self) -> Iterator[bytes]:
        while True:
            with self._frame_lock:
                frame = self._latest_jpeg
            if frame:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            else:
                time.sleep(0.1)
                continue
            time.sleep(0.04)

    @staticmethod
    def _annotate(
        frame: np.ndarray,
        tracks: list[dict[str, Any]],
        signs: list[dict[str, Any]],
        lane_output: dict[str, Any],
        lane_state: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> np.ndarray:
        canvas = frame.copy()
        lane_mask = lane_output["lane_mask"].astype(bool)
        drive_mask = lane_output["drivable_mask"].astype(bool)
        overlay = canvas.copy()
        overlay[drive_mask] = (65, 125, 45)
        overlay[lane_mask] = (245, 210, 35)
        canvas = cv2.addWeighted(overlay, 0.20, canvas, 0.80, 0)

        for item in tracks:
            x1, y1, x2, y2 = (int(v) for v in item["bbox"])
            risk = float(item.get("risk_score", 0))
            state = item.get("alert_state", "observed")
            color = {
                "observed": (235, 145, 40),
                "candidate": (25, 175, 245),
                "suppressed": (145, 145, 145),
                "active": (25, 35, 230),
            }.get(state, (235, 145, 40))
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
            text = f"#{item['track_id']} {item['label']} {risk:.2f} {state}"
            cv2.putText(canvas, text, (x1, max(20, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2)

        for sign in signs:
            x1, y1, x2, y2 = (int(v) for v in sign["bbox"])
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (255, 120, 30), 2)
            cv2.putText(
                canvas,
                sign["label"][:34],
                (x1, max(20, y1 - 7)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.46,
                (255, 180, 70),
                1,
            )

        lane_text = f"Lane quality {lane_state.get('quality', 0):.2f} | offset {lane_state.get('offset', 0):+.2f}"
        cv2.putText(canvas, lane_text, (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
        if events:
            color = (0, 0, 220) if events[0]["severity"] == "critical" else (0, 150, 255)
            cv2.rectangle(canvas, (0, canvas.shape[0] - 56), (canvas.shape[1], canvas.shape[0]), color, -1)
            cv2.putText(
                canvas,
                f"{events[0]['severity'].upper()}: {events[0]['event_type']}",
                (20, canvas.shape[0] - 19),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
            )
        return canvas
