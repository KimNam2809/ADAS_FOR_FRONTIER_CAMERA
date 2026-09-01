from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from roadwatch.api import create_app
from roadwatch.catalog import media_catalog


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"username": "driver", "password": "driver123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _video_bytes(tmp_path: Path) -> bytes:
    path = tmp_path / "sample.mp4"
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (64, 48)
    )
    assert writer.isOpened()
    for index in range(3):
        writer.write(np.full((48, 64, 3), index * 40, dtype=np.uint8))
    writer.release()
    return path.read_bytes()


def test_library_exposes_source_safe_metadata(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "library.db")
    with TestClient(app) as client:
        response = client.get("/api/library", headers=_login(client))
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "roadwatch.library.v1"
    assert payload["items"]
    assert all("source" in item and not Path(item["source"]).is_absolute() for item in payload["items"])


def test_cloud_library_lists_manifest_media_without_startup_download(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("ROADWATCH_GCS_ASSET_BUCKET", "roadwatch-test-assets")
    monkeypatch.setattr("roadwatch.catalog.MEDIA_ROOT", tmp_path / "empty-media")

    items = media_catalog()

    assert {item["name"] for item in items} == {
        "test_video1.mp4",
        "test_video10.mp4",
        "dashcam_vietnam_night.mp4",
        "dashcam_vietnam_rain+night.mp4",
    }
    assert all(item["storage_mode"] == "gcs_lazy" for item in items)
    assert all(item["duration_seconds"] > 0 and item["size_mb"] > 0 for item in items)


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "upload-invalid.db")
    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers=_login(client),
            files={"file": ("not-a-video.txt", io.BytesIO(b"bad"), "text/plain")},
        )
    assert response.status_code == 400
    assert "video" in response.json()["detail"].lower()


def test_upload_returns_isolated_replay_source(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "upload-valid.db")
    with TestClient(app) as client:
        response = client.post(
            "/api/uploads",
            headers=_login(client),
            files={"file": ("My test clip.mp4", io.BytesIO(_video_bytes(tmp_path)), "video/mp4")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_kind"] == "upload"
    assert payload["storage_mode"] == "local_ephemeral"
    assert payload["durable"] is False
    assert payload["source"].startswith("uploads/")
    assert payload["run_id"] in payload["source"]
    assert len(payload["sha256"]) == 64
    assert payload["frame_count"] == 3


def test_start_contract_forwards_run_identity_and_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "roadwatch.api.materialize_media_source",
        lambda _source: {"available": True},
    )
    app = create_app(database_path=tmp_path / "run.db")
    captured: dict[str, object] = {}

    def fake_start(*args: object, **kwargs: object) -> None:
        captured["args"] = args
        captured.update(kwargs)

    app.state.service.start = fake_start
    app.state.service.status = lambda: {
        "run_id": "run-12345678",
        "session_id": "session-12345678",
        "analysis_mode": "fresh",
    }
    with TestClient(app) as client:
        response = client.post(
            "/api/session/start",
            headers=_login(client),
            json={
                "source": "test_video10.mp4",
                "run_id": "run-12345678",
                "source_kind": "library",
                "analysis_mode": "fresh",
            },
        )
    assert response.status_code == 200
    assert captured["args"] == ("test_video10.mp4", 0.0, None, "run-12345678", "library", "fresh")
    assert response.json()["run_id"] == "run-12345678"
