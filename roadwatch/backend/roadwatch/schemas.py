from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class SessionRequest(BaseModel):
    source: str | int


class ConfigPatch(BaseModel):
    patch: dict[str, Any]


class User(BaseModel):
    username: str
    role: Literal["driver", "engineer"]


class TokenResponse(BaseModel):
    token: str
    user: User

