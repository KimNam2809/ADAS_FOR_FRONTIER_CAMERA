from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class SessionRequest(BaseModel):
    source: str | int
    start_seconds: float = Field(default=0.0, ge=0.0)
    duration_seconds: float | None = Field(default=None, gt=0.0, le=3600.0)


class SeekRequest(BaseModel):
    seconds: float = Field(ge=-86400.0, le=86400.0)
    relative: bool = False


class ConfigPatch(BaseModel):
    patch: dict[str, Any]


class User(BaseModel):
    username: str
    role: Literal["driver", "engineer"]


class TokenResponse(BaseModel):
    token: str
    user: User
