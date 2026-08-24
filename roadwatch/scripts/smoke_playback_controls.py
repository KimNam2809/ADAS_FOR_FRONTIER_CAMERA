from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.pipeline import RoadWatchService  # noqa: E402
from roadwatch.storage import Storage  # noqa: E402


def wait_until(predicate, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return False


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="roadwatch-playback-") as temp:
        storage = Storage(Path(temp) / "smoke.db")
        service = RoadWatchService(ConfigManager(), storage)
        checks: dict[str, bool] = {}
        try:
            service.start("test_video10.mp4")
            checks["started_and_has_duration"] = wait_until(
                lambda: service.status().get("duration_seconds", 0) > 0
                and service.status().get("source_time", 0) > 0,
            )
            service.pause()
            paused_at = float(service.status()["source_time"])
            time.sleep(0.5)
            checks["pause_preserves_position"] = abs(
                float(service.status()["source_time"]) - paused_at
            ) <= 0.25
            target = service.seek(paused_at + 5.0)
            checks["seek_applied_while_paused"] = wait_until(
                lambda: abs(float(service.status()["source_time"]) - target) <= 0.25,
                timeout=5.0,
            )
            service.resume()
            checks["resume_advances"] = wait_until(
                lambda: float(service.status()["source_time"]) > target + 0.2,
                timeout=10.0,
            )
            first_status = service.status()
            first_resumed_at = first_status.get("source_time")
            first_session = first_status.get("session_id")
            with service._frame_lock:
                first_frame_hash = hashlib.sha256(service._latest_jpeg or b"").hexdigest()
            service.stop()
            service.start("test_video1.mp4")
            second_loading = service.status()
            with service._frame_lock:
                checks["new_session_clears_old_frame_immediately"] = service._latest_jpeg is None
            checks["new_session_updates_source_immediately"] = (
                second_loading.get("source") == "test_video1.mp4"
            )
            checks["new_session_has_unique_identity"] = (
                bool(second_loading.get("session_id"))
                and second_loading.get("session_id") != first_session
            )
            checks["second_video_produces_frame"] = wait_until(
                lambda: service.status().get("source_time", 0) > 0.2,
                timeout=20.0,
            )
            with service._frame_lock:
                second_frame_hash = hashlib.sha256(service._latest_jpeg or b"").hexdigest()
            checks["second_video_frame_is_not_first_video_frame"] = (
                bool(second_frame_hash) and second_frame_hash != first_frame_hash
            )
            status = service.status()
            report = {
                "status": "pass" if all(checks.values()) else "fail",
                "checks": checks,
                "source": status.get("source"),
                "duration_seconds": status.get("duration_seconds"),
                "paused_at_seconds": round(paused_at, 3),
                "seek_target_seconds": target,
                "resumed_at_seconds": first_resumed_at,
                "second_video_current_seconds": status.get("source_time"),
                "first_session_id": first_session,
                "second_session_id": status.get("session_id"),
            }
        finally:
            service.close()
            storage.close()
    output = ROOT / "evaluation" / "playback_controls_smoke.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
