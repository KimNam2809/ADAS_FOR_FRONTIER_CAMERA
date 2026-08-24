from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .auth import hash_password, verify_password
from .config import DATA_ROOT


class Storage:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DATA_ROOT / "roadwatch.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('driver', 'engineer')),
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    display_message TEXT,
                    spoken_message TEXT,
                    confidence REAL NOT NULL,
                    risk_score REAL NOT NULL,
                    object_id INTEGER,
                    location TEXT,
                    evidence_json TEXT NOT NULL,
                    audio_action TEXT NOT NULL,
                    event_uuid TEXT,
                    frame_id INTEGER,
                    source_time REAL,
                    expires_at REAL,
                    lifecycle_status TEXT NOT NULL DEFAULT 'accepted',
                    audio_status TEXT NOT NULL DEFAULT 'not_requested',
                    suppression_reason TEXT
                    ,run_id TEXT
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    before_json TEXT,
                    after_json TEXT
                );
                """
            )
            self._migrate_events()
        self.seed_demo_users()

    def _migrate_events(self) -> None:
        existing = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(events)").fetchall()
        }
        additions = {
            "event_uuid": "TEXT",
            "frame_id": "INTEGER",
            "source_time": "REAL",
            "expires_at": "REAL",
            "lifecycle_status": "TEXT NOT NULL DEFAULT 'accepted'",
            "audio_status": "TEXT NOT NULL DEFAULT 'not_requested'",
            "suppression_reason": "TEXT",
            "display_message": "TEXT",
            "spoken_message": "TEXT",
            "run_id": "TEXT",
        }
        for name, sql_type in additions.items():
            if name not in existing:
                self._connection.execute(f"ALTER TABLE events ADD COLUMN {name} {sql_type}")

    def seed_demo_users(self) -> None:
        for username, password, role in (
            ("driver", "driver123", "driver"),
            ("engineer", "engineer123", "engineer"),
        ):
            with self._lock, self._connection:
                exists = self._connection.execute(
                    "SELECT 1 FROM users WHERE username = ?", (username,)
                ).fetchone()
                if not exists:
                    self._connection.execute(
                        "INSERT INTO users(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                        (username, hash_password(password), role, time.time()),
                    )

    def authenticate(self, username: str, password: str) -> dict[str, str] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT username, password_hash, role FROM users WHERE username = ?", (username,)
            ).fetchone()
        if row and verify_password(password, row["password_hash"]):
            return {"username": row["username"], "role": row["role"]}
        return None

    def add_event(self, event: dict[str, Any]) -> int:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO events(
                    created_at, event_type, severity, message, display_message, spoken_message,
                    confidence, risk_score,
                    object_id, location, evidence_json, audio_action, event_uuid, frame_id,
                    source_time, expires_at, lifecycle_status, audio_status, suppression_reason
                    ,run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["created_at"],
                    event["event_type"],
                    event["severity"],
                    event["message"],
                    event.get("display_message", event["message"]),
                    event.get("spoken_message", event["message"]),
                    event["confidence"],
                    event["risk_score"],
                    event.get("object_id"),
                    event.get("location"),
                    json.dumps(event.get("evidence", {}), ensure_ascii=False),
                    event.get("audio_action", "none"),
                    event.get("event_id"),
                    event.get("frame_id"),
                    event.get("source_time"),
                    event.get("expires_at"),
                    event.get("lifecycle_status", "accepted"),
                    event.get("audio_status", "not_requested"),
                    event.get("suppression_reason"),
                    event.get("run_id"),
                ),
            )
            return int(cursor.lastrowid)

    def update_event_audio(
        self, event_uuid: str, audio_status: str, reason: str | None = None
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE events SET audio_status = ?, suppression_reason = COALESCE(?, suppression_reason) WHERE event_uuid = ?",
                (audio_status, reason, event_uuid),
            )

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (safe_limit,)
            ).fetchall()
        events = []
        for row in rows:
            item = dict(row)
            item["evidence"] = json.loads(item.pop("evidence_json"))
            events.append(item)
        return events

    def add_audit(
        self, username: str, action: str, before: dict[str, Any], after: dict[str, Any]
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO audit_log(created_at, username, action, before_json, after_json) VALUES (?, ?, ?, ?, ?)",
                (
                    time.time(),
                    username,
                    action,
                    json.dumps(before, ensure_ascii=False),
                    json.dumps(after, ensure_ascii=False),
                ),
            )

    def list_audits(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["before"] = json.loads(item.pop("before_json") or "{}")
            item["after"] = json.loads(item.pop("after_json") or "{}")
            result.append(item)
        return result

    def close(self) -> None:
        with self._lock:
            self._connection.close()
