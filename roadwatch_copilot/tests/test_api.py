import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from roadwatch.api import create_app


def test_health_and_local_roles(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "test.db")
    with TestClient(app) as client:
        index = client.get("/")
        assert index.status_code == 200
        assert "RoadWatch" in index.text

        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] in {"ready", "degraded"}

        driver_login = client.post(
            "/api/auth/login", json={"username": "driver", "password": "driver123"}
        )
        assert driver_login.status_code == 200
        driver_token = driver_login.json()["token"]
        forbidden = client.get(
            "/api/config", headers={"Authorization": f"Bearer {driver_token}"}
        )
        assert forbidden.status_code == 403

        engineer_login = client.post(
            "/api/auth/login", json={"username": "engineer", "password": "engineer123"}
        )
        engineer_token = engineer_login.json()["token"]
        config = client.get(
            "/api/config", headers={"Authorization": f"Bearer {engineer_token}"}
        )
        assert config.status_code == 200
        assert config.json()["vehicle"]["profile"] == "VF6"


def test_playback_control_routes_require_auth_and_forward_commands(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "playback.db")
    service = app.state.service
    service.pause = lambda: None
    service.resume = lambda: None
    service.seek = lambda seconds, relative=False: 42.0 if relative else seconds
    original_status = service.status
    service.status = lambda: {"playback": "paused"}
    with TestClient(app) as client:
        assert client.post("/api/session/pause").status_code == 401
        login = client.post(
            "/api/auth/login", json={"username": "driver", "password": "driver123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        assert client.post("/api/session/pause", headers=headers).json()["playback"] == "paused"
        assert client.post("/api/session/resume", headers=headers).status_code == 200
        seek = client.post(
            "/api/session/seek",
            headers=headers,
            json={"seconds": -10, "relative": True},
        )
        assert seek.json()["target_seconds"] == 42.0
    service.status = original_status


def test_cloud_deferred_startup_is_public_and_blocks_analysis_until_ready(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("ROADWATCH_CLOUD_MODE", "web_demo")
    monkeypatch.setenv("ROADWATCH_DEFERRED_STARTUP", "1")
    monkeypatch.setattr(
        "roadwatch.api.bootstrap_assets",
        lambda: {"enabled": False, "downloaded": [], "reason": "test"},
    )
    app = create_app(database_path=tmp_path / "deferred.db")
    warmup_started = threading.Event()
    allow_ready = threading.Event()

    def delayed_warmup() -> None:
        warmup_started.set()
        assert allow_ready.wait(timeout=3)

    app.state.service.perception.warmup = delayed_warmup
    app.state.tts_gateway.warmup = lambda: None

    with TestClient(app) as client:
        assert warmup_started.wait(timeout=2)
        startup = client.get("/api/startup")
        assert startup.status_code == 200
        assert startup.headers["cache-control"].startswith("no-store")
        assert startup.json()["ready"] is False
        assert startup.json()["state"] == "starting"

        login = client.post(
            "/api/auth/login", json={"username": "driver", "password": "driver123"}
        )
        blocked = client.post(
            "/api/session/start",
            headers={"Authorization": f"Bearer {login.json()['token']}"},
            json={"source": "test_video10.mp4"},
        )
        assert blocked.status_code == 503
        assert blocked.headers["retry-after"] == "2"

        allow_ready.set()
        deadline = time.time() + 3
        while time.time() < deadline:
            payload = client.get("/api/startup").json()
            if payload["ready"]:
                break
            time.sleep(0.02)
        assert payload["state"] == "ready"
        assert payload["stage"] == "ready"
