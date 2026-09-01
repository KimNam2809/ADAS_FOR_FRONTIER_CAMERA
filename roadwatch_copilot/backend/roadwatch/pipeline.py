from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
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
from .optional_perception import OptionalPerceptionWorker
from .perception import PerceptionEngine
from .risk import RiskEngine
from .release import verify_release
from .slm import SlmExplanationWorker, SlmResult
from .storage import Storage
from .tracking import IoUTracker
from .traffic_context import TrafficContextEngine
from .vehicle_io import DisabledVehicleAdapter


LOGGER = logging.getLogger(__name__)


class RoadWatchService:
    def __init__(self, config_manager: ConfigManager, storage: Storage) -> None:
        self.config_manager = config_manager
        self.storage = storage
        self._state_lock = threading.RLock()
        self._frame_lock = threading.RLock()
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._control_lock = threading.RLock()
        self._pending_seek_seconds: float | None = None
        self._thread: threading.Thread | None = None
        self._latest_jpeg: bytes | None = None
        self._latest_jpeg_sequence = 0
        self._display_queue: queue.Queue[tuple[Any, ...] | None] | None = None
        self._display_stop = threading.Event()
        self._display_thread: threading.Thread | None = None
        self._display_session_id: str | None = None
        self._recent_events: deque[dict[str, Any]] = deque(maxlen=20)
        self._active_events: dict[str, dict[str, Any]] = {}
        self._status: dict[str, Any] = {
            "running": False,
            "mode": "idle",
            "source": None,
            "frame_id": 0,
            "source_time": 0.0,
            "source_fps": 0,
            "duration_seconds": 0.0,
            "seekable": False,
            "playback": "stopped",
            "stage": "idle",
            "session_id": None,
            "tracks": [],
            "signs": [],
            "lane": {"quality": 0, "offset": 0},
            "traffic_context": {
                "mode": "normal",
                "risk_state": "calm",
                "density_score": 0.0,
                "confirmed_road_users": 0,
                "two_wheeler_count": 0,
                "road_occupancy": 0.0,
                "low_motion_ratio": 0.0,
                "audio_policy": "normal",
                "policy_mode": "off",
                "attention_due": False,
                "transition": None,
                "fallback": False,
                "error": None,
            },
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
        self.traffic_context = TrafficContextEngine(config)
        self.audio = AudioManager(config, self._audio_lifecycle)
        self.metrics = MetricsCollector()
        self.slm = SlmExplanationWorker(config, self._slm_lifecycle)
        self.vehicle_io = DisabledVehicleAdapter()
        # Keep the idle/API snapshot aligned with the configured policy. A
        # literal `policy_mode=off` made the feature appear disabled until the
        # first inference frame, even when demo mode was enforced.
        with self._state_lock:
            self._status["traffic_context"] = self.traffic_context.snapshot()

    def reload_config(self) -> None:
        if self.is_running:
            raise RuntimeError("Hãy dừng phiên phân tích trước khi nạp cấu hình mới")
        self.audio.stop()
        self.slm.close()
        self._build_components()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(
        self,
        source: str | int | None = None,
        start_seconds: float = 0.0,
        duration_seconds: float | None = None,
        run_id: str | None = None,
        source_kind: str = "library",
        analysis_mode: str = "fresh",
    ) -> None:
        if self.is_running:
            raise RuntimeError("Một phiên phân tích đang chạy")
        config = self.config_manager.snapshot()
        source = source if source is not None else config["app"]["default_source"]
        resolved = ConfigManager.media_source(source)
        if analysis_mode == "cached":
            raise RuntimeError("Cached result chưa được cấu hình cho runtime local; dùng fresh run")
        run_id = run_id or str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        self._stop.clear()
        self._pause.clear()
        with self._control_lock:
            self._pending_seek_seconds = None
        self.tracker.reset()
        self.kinematics.reset()
        self.risk.reset()
        self.governor.reset()
        if not hasattr(self, "traffic_context"):
            self.traffic_context = TrafficContextEngine(config)
        else:
            self.traffic_context.reset()
        self._recent_events.clear()
        self._active_events.clear()
        slm = getattr(self, "slm", None)
        if slm is not None:
            slm.clear_pending("new_session")
        with self._frame_lock:
            self._latest_jpeg = None
            self._latest_jpeg_sequence = 0
        with self._state_lock:
            self._status.update({
                "running": True,
                "mode": "loading" if isinstance(resolved, str) else "camera",
                "playback": "loading",
                "session_id": session_id,
                "run_id": run_id,
                "source_key": str(source) if isinstance(source, str) else None,
                "source_kind": source_kind,
                "analysis_mode": analysis_mode,
                "source": Path(resolved).name if isinstance(resolved, str) else f"camera:{resolved}",
                "frame_id": 0,
                "source_fps": 0,
                "source_time": round(float(start_seconds), 3),
                "duration_seconds": 0.0,
                "seekable": isinstance(resolved, str),
                "events": [],
                "tracks": [],
                "signs": [],
                "lane": {"quality": 0, "offset": 0},
                "traffic_context": self.traffic_context.snapshot(),
                "degraded_reasons": [],
                "models": self.perception.status(),
                "error": None,
            })
        self.metrics = MetricsCollector()
        self._start_display_worker(
            session_id,
            config.get("app", {}),
        )
        if slm is not None:
            slm.start()
        self.audio.start()
        self._thread = threading.Thread(
            target=self._run,
            args=(resolved, float(start_seconds), duration_seconds, session_id, run_id),
            name="roadwatch-pipeline",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._pause.clear()
        if self._thread:
            self._thread.join(timeout=5.0)
        with self._state_lock:
            self._status["running"] = False
            self._status["mode"] = "idle"
            self._status["playback"] = "stopped"
        with self._frame_lock:
            self._latest_jpeg = None
            self._latest_jpeg_sequence = 0
        self._stop_display_worker()
        slm = getattr(self, "slm", None)
        if slm is not None:
            slm.clear_pending("session_stopped")
        self.traffic_context.reset()
        with self._state_lock:
            self._status["traffic_context"] = self.traffic_context.snapshot()

    def pause(self) -> None:
        with self._state_lock:
            if not self.is_running or not self._status.get("seekable"):
                raise RuntimeError("Chỉ có thể tạm dừng một video replay đang chạy")
            self._pause.set()
            self._status["mode"] = "paused"
            self._status["playback"] = "paused"
        self.audio.clear_pending("playback_paused")

    def resume(self) -> None:
        with self._state_lock:
            if not self.is_running or not self._status.get("seekable"):
                raise RuntimeError("Không có video replay để tiếp tục")
            self._pause.clear()
            self._status["mode"] = "replay"
            self._status["playback"] = "playing"

    def seek(self, seconds: float, relative: bool = False) -> float:
        with self._state_lock:
            if not self.is_running or not self._status.get("seekable"):
                raise RuntimeError("Nguồn hiện tại không hỗ trợ tua video")
            current = float(self._status.get("source_time", 0.0))
            duration = float(self._status.get("duration_seconds", 0.0))
        target = current + float(seconds) if relative else float(seconds)
        target = max(0.0, min(target, duration if duration > 0 else target))
        with self._control_lock:
            self._pending_seek_seconds = target
        self.audio.clear_pending("playback_seek")
        slm = getattr(self, "slm", None)
        if slm is not None:
            slm.clear_pending("playback_seek")
        return round(target, 3)

    def close(self) -> None:
        self.stop()
        self.audio.stop()
        slm = getattr(self, "slm", None)
        if slm is not None:
            slm.close()

    def _start_display_worker(
        self, session_id: str, app_config: dict[str, Any]
    ) -> None:
        """Start a bounded latest-frame renderer for the browser/AAOS stream.

        Rendering and JPEG compression are deliberately outside the inference
        thread.  The queue has capacity one: when the encoder is busy, an old
        display frame is discarded instead of creating unbounded latency.
        """
        self._stop_display_worker()
        self._display_queue = queue.Queue(maxsize=1)
        self._display_stop = threading.Event()
        self._display_session_id = session_id
        quality = int(app_config.get("stream_jpeg_quality", app_config.get("jpeg_quality", 80)))
        self._display_jpeg_quality = max(35, min(95, quality))
        self._display_max_width = max(320, int(app_config.get("stream_max_width", 1280)))
        self._display_thread = threading.Thread(
            target=self._display_loop,
            args=(session_id,),
            name="roadwatch-display-renderer",
            daemon=True,
        )
        self._display_thread.start()

    def _stop_display_worker(self) -> None:
        stop = getattr(self, "_display_stop", None)
        if stop is not None:
            stop.set()
        display_queue = getattr(self, "_display_queue", None)
        if display_queue is not None:
            try:
                display_queue.put_nowait(None)
            except queue.Full:
                try:
                    display_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    display_queue.put_nowait(None)
                except queue.Full:
                    pass
        display_thread = getattr(self, "_display_thread", None)
        if (
            display_thread is not None
            and display_thread is not threading.current_thread()
        ):
            display_thread.join(timeout=2.0)
        self._display_thread = None
        self._display_queue = None
        self._display_session_id = None

    def _submit_display_frame(
        self,
        frame: np.ndarray,
        session_id: str | None,
        tracks: list[dict[str, Any]],
        signs: list[dict[str, Any]],
        lane_output: dict[str, Any] | None,
        lane_state: dict[str, Any],
        events: list[dict[str, Any]],
        full_overlay: bool = True,
    ) -> None:
        """Publish a display-only frame without blocking inference."""
        display_queue = getattr(self, "_display_queue", None)
        if display_queue is None or session_id is None:
            return
        # The capture frame is not mutated after this call.  Keep copies of
        # small metadata containers so the renderer cannot observe the next
        # inference iteration mutating a track/event dictionary.
        payload = (
            session_id,
            frame,
            [dict(item) for item in tracks[:30]],
            [dict(item) for item in signs[:12]],
            lane_output,
            dict(lane_state),
            [dict(item) for item in events[:6]],
            bool(full_overlay),
        )
        try:
            display_queue.put_nowait(payload)
            return
        except queue.Full:
            pass
        # Latest-frame semantics: discard stale visual work and never wait for
        # the encoder.  This is intentionally not an inference/drop metric.
        try:
            display_queue.get_nowait()
            self.metrics.record_display_drop()
        except queue.Empty:
            pass
        try:
            display_queue.put_nowait(payload)
        except queue.Full:
            self.metrics.record_display_drop()

    def _display_loop(self, session_id: str) -> None:
        display_queue = self._display_queue
        if display_queue is None:
            return
        while not self._display_stop.is_set():
            try:
                payload = display_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if payload is None:
                return
            (
                payload_session,
                frame,
                tracks,
                signs,
                lane_output,
                lane_state,
                events,
                full_overlay,
            ) = payload
            if payload_session != session_id or self._display_stop.is_set():
                continue
            try:
                if full_overlay:
                    annotated = self._annotate(
                        frame,
                        tracks,
                        signs,
                        lane_output,
                        lane_state,
                        events,
                    )
                else:
                    # Skip-frame rendering is deliberately lightweight. Lane
                    # masks are expensive to blend at source resolution and
                    # are already present on the most recent inference frame;
                    # the intermediate frame only needs motion + compact
                    # object/event context to keep the video fluid.
                    annotated = self._annotate_light(
                        frame, tracks, signs, events
                    )
                if annotated.shape[1] > self._display_max_width:
                    scale = self._display_max_width / float(annotated.shape[1])
                    resized = cv2.resize(
                        annotated,
                        (
                            self._display_max_width,
                            max(1, int(round(annotated.shape[0] * scale))),
                        ),
                        interpolation=cv2.INTER_AREA,
                    )
                else:
                    resized = annotated
                encode_ok, jpeg = cv2.imencode(
                    ".jpg",
                    resized,
                    [cv2.IMWRITE_JPEG_QUALITY, self._display_jpeg_quality],
                )
                if not encode_ok:
                    continue
                encoded = jpeg.tobytes()
                with self._state_lock:
                    current_session = self._status.get("session_id")
                if current_session != session_id:
                    continue
                with self._frame_lock:
                    self._latest_jpeg = encoded
                    self._latest_jpeg_sequence = getattr(
                        self, "_latest_jpeg_sequence", 0
                    ) + 1
                self.metrics.record_display_frame()
            except Exception:  # pragma: no cover - display must not stop AI
                LOGGER.exception("Không thể render frame RoadWatch")

    def _run(
        self,
        source: str | int,
        start_seconds: float = 0.0,
        duration_seconds: float | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        config = self.config_manager.snapshot()
        app_config = config["app"]
        inf_config = config["inference"]
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            self._set_error(f"Không thể mở nguồn video: {Path(str(source)).name}")
            self._stop_display_worker()
            return
        if isinstance(source, str) and start_seconds > 0:
            cap.set(cv2.CAP_PROP_POS_MSEC, start_seconds * 1000.0)
        source_fps = float(cap.get(cv2.CAP_PROP_FPS))
        if source_fps <= 0 or source_fps > 240:
            source_fps = float(app_config["max_processed_fps"])
        target_fps = min(float(app_config["max_processed_fps"]), source_fps)
        frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = frame_count / source_fps if isinstance(source, str) and frame_count > 0 else 0.0
        stride = max(1, round(source_fps / max(target_fps, 1)))
        processed_id = 0
        captured_id = 0
        objects: list[dict[str, Any]] = []
        signs: list[dict[str, Any]] = []
        lane_output: dict[str, Any] | None = None
        tracks: list[dict[str, Any]] = []
        lane_state: dict[str, Any] = {}
        active_events: list[dict[str, Any]] = []
        optional_worker: OptionalPerceptionWorker | None = None
        optional_status: dict[str, Any] = {}
        consumed_sign_sequence = 0
        started = time.perf_counter()
        next_frame_due = time.perf_counter()

        with self._state_lock:
            self._status.update(
                {
                    "running": True,
                    "mode": "replay" if isinstance(source, str) else "camera",
                    "source": Path(source).name if isinstance(source, str) else f"camera:{source}",
                    "source_fps": round(source_fps, 2),
                    "duration_seconds": round(total_duration, 3),
                    "seekable": isinstance(source, str),
                    "playback": "playing",
                    "session_id": session_id,
                    "run_id": run_id,
                    "error": None,
                    "stage": "loading_models",
                }
            )
        try:
            LOGGER.info("RoadWatch warmup started: run_id=%s", run_id)
            self.metrics.begin_warmup()
            self.perception.warmup()
            self.metrics.finish_warmup()
            async_optional_requested = bool(
                inf_config.get("async_optional_perception", False)
            )
            providers = self.perception.status()
            directml_active = any(
                "DmlExecutionProvider" in str(item.get("provider", ""))
                for item in providers.values()
                if isinstance(item, dict)
            )
            # DirectML sessions are not reliably re-entrant on this Windows
            # laptop/driver combination. Running lane/sign heads concurrently
            # can return DmlFusedNode errors and poison the GPU session. Keep
            # the safe sequential path automatically; CPU/CUDA cloud/edge
            # profiles retain the bounded async worker.
            async_optional_enabled = async_optional_requested and not directml_active
            if async_optional_requested and directml_active:
                optional_status = {
                    "enabled": False,
                    "disabled_reason": "directml_serial_fallback",
                }
                LOGGER.warning(
                    "Async optional perception disabled for DirectML; using serial fallback"
                )
            if async_optional_enabled:
                optional_worker = OptionalPerceptionWorker(
                    self.perception.signs,
                    self.perception.lane,
                    self.metrics,
                    int(inf_config.get("sign_interval", 5)),
                    int(inf_config.get("sign_candidate_interval", 1)),
                    int(inf_config.get("lane_interval", 2)),
                    float(inf_config.get("optional_max_staleness_seconds", 1.5)),
                )
                optional_worker.reset()
                optional_worker.start()
            LOGGER.info("RoadWatch warmup completed: run_id=%s", run_id)
            self.metrics.mark_processing_started()
            with self._state_lock:
                self._status["stage"] = "inference"
            while not self._stop.is_set():
                seek_target: float | None = None
                with self._control_lock:
                    if self._pending_seek_seconds is not None:
                        seek_target = self._pending_seek_seconds
                        self._pending_seek_seconds = None
                if seek_target is not None:
                    with self._frame_lock:
                        self._latest_jpeg = None
                        self._latest_jpeg_sequence = 0
                    self._clear_display_queue()
                    cap.set(cv2.CAP_PROP_POS_MSEC, seek_target * 1000.0)
                    captured_id = 0
                    objects, signs, lane_output = [], [], None
                    tracks, lane_state, active_events = [], {}, []
                    consumed_sign_sequence = 0
                    if optional_worker is not None:
                        optional_worker.reset()
                    self.tracker.reset()
                    self.kinematics.reset()
                    self.risk.reset()
                    self.governor.reset()
                    self.traffic_context.reset()
                    self._active_events.clear()
                    next_frame_due = time.perf_counter()
                    with self._state_lock:
                        self._status.update({
                            "source_time": round(seek_target, 3),
                            # Keep the session audit history when seeking. The
                            # active risk/tracker state is reset above, but a
                            # seek is an evidence navigation action, not a new
                            # session and must not erase Event History.
                            "events": list(self._recent_events),
                            "traffic_context": self.traffic_context.snapshot(),
                        })
                if self._pause.is_set():
                    next_frame_due = time.perf_counter()
                    time.sleep(0.05)
                    continue
                ok, frame = cap.read()
                if not ok:
                    if isinstance(source, str) and app_config.get("loop_video", True):
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.tracker.reset()
                        self.risk.reset()
                        self.governor.reset()
                        self.traffic_context.reset()
                        self.slm.clear_pending("video_loop")
                        self._active_events.clear()
                        objects, signs, lane_output = [], [], None
                        tracks, lane_state, active_events = [], {}, []
                        consumed_sign_sequence = 0
                        if optional_worker is not None:
                            optional_worker.reset()
                        next_frame_due = time.perf_counter()
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
                    # This frame is never sent to perception/risk. It is only
                    # rendered with the latest known state so the browser can
                    # retain source motion instead of freezing between two
                    # inference results.
                    if bool(app_config.get("publish_skipped_frames", True)):
                        self._submit_display_frame(
                            frame,
                            session_id,
                            tracks,
                            signs,
                            lane_output,
                            lane_state,
                            active_events,
                            full_overlay=False,
                        )
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
                if optional_worker is not None:
                    optional_worker.submit(frame, processed_id, source_time)
                    optional_status = optional_worker.snapshot(source_time)
                    signs = optional_status["signs"]
                    sign_sequence = int(optional_status["sign_sequence"])
                    sign_fresh = sign_sequence > consumed_sign_sequence
                    consumed_sign_sequence = max(consumed_sign_sequence, sign_sequence)
                    lane_output = optional_status["lane"]
                else:
                    sign_interval = int(
                        inf_config.get("sign_candidate_interval", 1)
                        if signs
                        else inf_config["sign_interval"]
                    )
                    if inf_config.get("enable_signs", True) and processed_id % sign_interval == 0:
                        signs, latency = self.perception.signs.infer(frame)
                        self.metrics.observe("traffic_sign", latency)
                        sign_fresh = True

                    if lane_output is None and inf_config.get("enable_lane", True):
                        lane_output, latency = self.perception.lane.infer(frame)
                        self.metrics.observe("lane_detection", latency)
                    elif (
                        lane_output is not None
                        and inf_config.get("enable_lane", True)
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
                traffic_context = self.traffic_context.update(
                    tracks,
                    candidates,
                    frame.shape[:2],
                    source_time,
                )
                emitted, suppressed = self.governor.decide(
                    candidates,
                    now=time.time(),
                    clock=source_time,
                    frame_id=processed_id,
                    source_time=source_time,
                    context=traffic_context,
                )
                self.metrics.alerts_suppressed += suppressed
                for item in self.governor.last_suppressed:
                    self.metrics.record_suppression(item.get("suppression_reason", "unknown"))
                for event in emitted:
                    event["run_id"] = run_id
                    event["slm_status"] = "pending" if self.slm.enabled else "disabled"
                    event["slm_explanation"] = None
                    event["slm_latency_ms"] = None
                    event["slm_failure_reason"] = None
                    event_id = self.storage.add_event(event)
                    event["id"] = event_id
                    self._recent_events.appendleft(event)
                    self.metrics.alerts_emitted += 1
                    self.metrics.record_event(event["event_type"])
                    self._active_events[event["event_id"]] = event
                    slm_status = self.slm.submit(event)
                    if slm_status != event["slm_status"]:
                        event["slm_status"] = slm_status
                        if slm_status == "fallback":
                            self.storage.update_event_slm(
                                str(event["event_id"]),
                                "fallback",
                                None,
                                None,
                                "submit_failed",
                            )
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
                self._submit_display_frame(
                    frame,
                    session_id,
                    tracks,
                    signs,
                    lane_output,
                    lane_state,
                    active_events,
                )

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
                            "traffic_context": traffic_context,
                            "events": list(self._recent_events)[: int(app_config["retain_events"])],
                            "degraded_reasons": degraded,
                            "stage": "inference",
                            "models": self.perception.status(),
                            "optional_perception": {
                                key: value
                                for key, value in optional_status.items()
                                if key not in {"signs", "lane"}
                            },
                        }
                    )

                if not isinstance(source, str) or app_config.get("pace_replay", True):
                    next_frame_due += 1.0 / max(target_fps, 1)
                    remaining = next_frame_due - time.perf_counter()
                    if remaining > 0:
                        time.sleep(min(remaining, 0.1))
        except Exception as exc:  # pragma: no cover - integration guard
            LOGGER.exception("Pipeline stopped unexpectedly")
            self._set_error(str(exc))
        finally:
            if optional_worker is not None:
                optional_worker.close()
            self.slm.clear_pending("session_finished")
            cap.release()
            self.traffic_context.reset()
            self._stop_display_worker()
            with self._state_lock:
                if session_id is None or self._status.get("session_id") == session_id:
                    self._status["running"] = False
                    self._status["mode"] = "idle"
                    self._status["playback"] = "stopped"
                    self._status["traffic_context"] = self.traffic_context.snapshot()

    def _set_error(self, message: str) -> None:
        with self._state_lock:
            self._status.update({"running": False, "mode": "error", "error": message})

    def _clear_display_queue(self) -> None:
        display_queue = getattr(self, "_display_queue", None)
        if display_queue is None:
            return
        while True:
            try:
                display_queue.get_nowait()
            except queue.Empty:
                return

    @staticmethod
    def _annotate_light(
        frame: np.ndarray,
        tracks: list[dict[str, Any]],
        signs: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> np.ndarray:
        """Cheap overlay for non-inference frames between full renders."""
        canvas = frame.copy()
        for item in tracks:
            x1, y1, x2, y2 = (int(v) for v in item["bbox"])
            state = item.get("alert_state", "observed")
            color = (25, 35, 230) if state == "active" else (235, 145, 40)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        for sign in signs:
            x1, y1, x2, y2 = (int(v) for v in sign["bbox"])
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (255, 120, 30), 2)
        if events:
            color = (0, 0, 220) if events[0]["severity"] == "critical" else (0, 150, 255)
            cv2.rectangle(
                canvas,
                (0, canvas.shape[0] - 56),
                (canvas.shape[1], canvas.shape[0]),
                color,
                -1,
            )
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
        result["slm"] = self.slm.status()
        return result

    def _audio_lifecycle(
        self, event: dict[str, Any], status: str, reason: str | None = None
    ) -> None:
        event_uuid = str(event.get("event_id", ""))
        if event_uuid:
            self.storage.update_event_audio(
                event_uuid,
                status,
                reason,
                str(event.get("audio_claim_id")) if event.get("audio_claim_id") else None,
                int(event.get("audio_play_count", 0) or 0),
            )
        if status == "completed":
            self.metrics.audio_completed += 1
        elif status == "dropped_stale":
            self.metrics.audio_dropped_stale += 1
            self.metrics.record_suppression(reason or "stale_audio")

    def _slm_lifecycle(self, event_id: str, result: SlmResult) -> None:
        self.storage.update_event_slm(
            event_id,
            result.status,
            result.explanation,
            result.latency_ms,
            result.failure_reason,
        )
        if result.latency_ms is not None:
            self.metrics.observe("slm_generation", result.latency_ms)
        with self._state_lock:
            for event in self._recent_events:
                if event.get("event_id") == event_id:
                    event.update(
                        {
                            "slm_status": result.status,
                            "slm_explanation": result.explanation,
                            "slm_latency_ms": result.latency_ms,
                            "slm_failure_reason": result.failure_reason,
                        }
                    )
            event = self._active_events.get(event_id)
            if event is not None:
                event.update(
                    {
                        "slm_status": result.status,
                        "slm_explanation": result.explanation,
                        "slm_latency_ms": result.latency_ms,
                        "slm_failure_reason": result.failure_reason,
                    }
                )

    def health(self) -> dict[str, Any]:
        inventory = model_inventory()
        release = verify_release(self.config_manager.snapshot(), verify_hashes=False)
        required_ready = all(
            item["available"] for item in inventory if item.get("required", True)
        )
        return {
            "status": "ready"
            if required_ready and release["status"] == "pass"
            else "degraded",
            "release": release,
            "models": inventory,
            "pipeline_running": self.is_running,
            "providers": self.perception.status(),
            "audio": self.audio.status(),
            "vehicle_io": self.vehicle_io.status(),
            "kinematics": self.kinematics.status(),
            "slm": self.slm.status(),
        }

    def mjpeg(self, session_id: str | None = None) -> Iterator[bytes]:
        last_sequence = -1
        config_manager = getattr(self, "config_manager", None)
        if config_manager is not None:
            stream_fps = float(
                config_manager.snapshot().get("app", {}).get("stream_fps", 30.0)
            )
        else:
            stream_fps = 30.0
        frame_interval = 1.0 / max(1.0, min(stream_fps, 60.0))
        next_emit = 0.0
        while True:
            if session_id is not None:
                with self._state_lock:
                    if self._status.get("session_id") != session_id:
                        return
            with self._frame_lock:
                frame = self._latest_jpeg
                sequence = getattr(self, "_latest_jpeg_sequence", 0)
            now = time.perf_counter()
            if frame and sequence != last_sequence and now >= next_emit:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                last_sequence = sequence
                next_emit = time.perf_counter() + frame_interval
            else:
                # Wait for a new encoded frame rather than repeatedly sending
                # the same JPEG. This reduces browser decode/repaint pressure.
                time.sleep(min(0.02, frame_interval / 2))

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
        if lane_output is not None:
            lane_mask = lane_output["lane_mask"].astype(bool)
            drive_mask = lane_output["drivable_mask"].astype(bool)
            if lane_mask.shape[:2] == canvas.shape[:2] and drive_mask.shape[:2] == canvas.shape[:2]:
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
