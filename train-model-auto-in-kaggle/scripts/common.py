from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTROL_ROOT = ROOT / "train-model-auto-in-kaggle"

SECRET_PATTERNS = (
    re.compile(r"(?i)(KAGGLE_API_TOKEN|KAGGLE_KEY|ROBOFLOW_KEY|GEMINI_API_KEY)\s*[=:]\s*\S+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def redact(text: str) -> str:
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(lambda m: m.group(0).split(":", 1)[0].split("=", 1)[0] + "=[REDACTED]", result)
    token = os.getenv("KAGGLE_API_TOKEN", "")
    if token:
        result = result.replace(token, "[REDACTED]")
    return result


def run(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if check and completed.returncode:
        detail = redact((completed.stdout or "") + "\n" + (completed.stderr or ""))
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}\n{detail.strip()}")
    return completed


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_kaggle_env() -> tuple[str, str]:
    username = os.getenv("KAGGLE_USERNAME", "").strip()
    token = os.getenv("KAGGLE_API_TOKEN", "").strip()
    if not username or not token:
        raise RuntimeError("Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN")
    if len(token) < 20:
        raise RuntimeError("KAGGLE_API_TOKEN appears invalid")
    return username, token


def normalize_status(raw: str) -> str:
    upper = raw.upper()
    for status in ("COMPLETE", "RUNNING", "QUEUED", "ERROR"):
        if status in upper:
            return status
    return "UNKNOWN"


def set_github_output(name: str, value: str) -> None:
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")

