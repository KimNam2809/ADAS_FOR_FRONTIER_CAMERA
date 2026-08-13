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
