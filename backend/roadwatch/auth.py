from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


PBKDF2_ITERATIONS = 240_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class TokenManager:
    """Small HMAC token implementation for an offline, localhost-only demo."""

    def __init__(self, ttl_minutes: int = 480) -> None:
        self.ttl_seconds = ttl_minutes * 60
        configured = os.getenv("ROADWATCH_SECRET")
        self.secret = (configured or "roadwatch-local-demo-change-me").encode()

    def issue(self, username: str, role: str) -> str:
        payload = {
            "sub": username,
            "role": role,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.ttl_seconds,
        }
        body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
        signature = _b64encode(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{signature}"

    def verify(self, token: str) -> dict[str, Any]:
        try:
            body, signature = token.split(".", 1)
            expected = _b64encode(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Chữ ký token không hợp lệ")
            payload = json.loads(_b64decode(body))
            if int(payload["exp"]) < int(time.time()):
                raise ValueError("Token đã hết hạn")
            return payload
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError("Token không hợp lệ") from exc

