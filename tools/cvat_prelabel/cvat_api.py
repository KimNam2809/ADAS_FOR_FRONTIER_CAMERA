from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values


class CvatApiError(RuntimeError):
    pass


class CvatClient:
    def __init__(self, env_path: Path) -> None:
        values = {**dotenv_values(env_path), **os.environ}
        token = str(values.get("CVAT_ACCESS_TOKEN") or "").strip()
        if not token:
            raise CvatApiError(f"Missing CVAT_ACCESS_TOKEN in {env_path}")
        self.base_url = str(values.get("CVAT_BASE_URL") or "https://app.cvat.ai").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.cvat+json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = self.session.request(method, self.base_url + path, timeout=120, **kwargs)
        if not response.ok:
            detail = response.text[:500].replace("\n", " ")
            raise CvatApiError(f"CVAT {method} {path} failed: {response.status_code} {detail}")
        return response

    def get_json(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("GET", path, **kwargs).json()

    def get_task(self, task_id: int) -> dict[str, Any]:
        return self.get_json(f"/api/tasks/{task_id}")

    def get_project(self, project_id: int) -> dict[str, Any]:
        return self.get_json(f"/api/projects/{project_id}")

    def get_labels(self, *, project_id: int) -> list[dict[str, Any]]:
        payload = self.get_json(
            "/api/labels", params={"project_id": project_id, "page_size": 100}
        )
        return list(payload.get("results", []))

    def get_annotations(self, task_id: int) -> dict[str, Any]:
        return self.get_json(f"/api/tasks/{task_id}/annotations")

    def replace_annotations(self, task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "PUT",
            f"/api/tasks/{task_id}/annotations",
            headers={"Content-Type": "application/json", "Accept": "application/vnd.cvat+json"},
            json=payload,
        )
        return response.json() if response.content else {}

    def get_frame(self, task_id: int, frame: int, quality: str = "original") -> bytes:
        # Frame endpoints return PNG/JPEG, so do not send the JSON-only Accept header.
        headers = {"Authorization": self.session.headers["Authorization"]}
        response = requests.get(
            self.base_url + f"/api/tasks/{task_id}/data",
            headers=headers,
            params={"type": "frame", "number": frame, "quality": quality},
            timeout=120,
        )
        if not response.ok:
            raise CvatApiError(
                f"Frame {frame} download failed: {response.status_code} {response.text[:200]}"
            )
        return response.content

