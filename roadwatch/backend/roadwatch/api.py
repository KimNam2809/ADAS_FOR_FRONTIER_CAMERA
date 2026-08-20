from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth import TokenManager
from .config import ConfigManager, PROJECT_ROOT, media_inventory
from .pipeline import RoadWatchService
from .schemas import ConfigPatch, LoginRequest, SessionRequest, TokenResponse, User
from .storage import Storage


LOGGER = logging.getLogger(__name__)


def create_app(start_pipeline: bool = False, database_path: Path | None = None) -> FastAPI:
    config_manager = ConfigManager()
    storage = Storage(database_path)
    token_manager = TokenManager(config_manager.snapshot()["security"]["token_ttl_minutes"])
    service = RoadWatchService(config_manager, storage)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if start_pipeline or config_manager.snapshot()["app"].get("auto_start", False):
            try:
                service.start()
            except Exception:
                LOGGER.exception("Auto-start thất bại")
        yield
        service.close()
        storage.close()

    app = FastAPI(
        title="RoadWatch Edge API",
        version="0.2.1",
        description="Local-only API for an evidence-aware driver warning assistant.",
        lifespan=lifespan,
    )
    app.state.config_manager = config_manager
    app.state.storage = storage
    app.state.service = service
    app.state.token_manager = token_manager

    def current_user(authorization: str | None = Header(default=None)) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Thiếu token đăng nhập")
        try:
            payload = token_manager.verify(authorization.removeprefix("Bearer ").strip())
            return User(username=payload["sub"], role=payload["role"])
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    def engineer_only(user: User = Depends(current_user)) -> User:
        if user.role != "engineer":
            raise HTTPException(status_code=403, detail="Chỉ kỹ sư ADAS được phép thực hiện")
        return user

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return service.health()

    @app.post("/api/auth/login", response_model=TokenResponse)
    def login(request: LoginRequest) -> TokenResponse:
        user = storage.authenticate(request.username, request.password)
        if not user:
            raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")
        return TokenResponse(token=token_manager.issue(user["username"], user["role"]), user=user)

    @app.get("/api/auth/me", response_model=User)
    def me(user: User = Depends(current_user)) -> User:
        return user

    @app.get("/api/status")
    def status(_: User = Depends(current_user)) -> dict[str, Any]:
        return service.status()

    @app.get("/api/media")
    def media(_: User = Depends(current_user)) -> list[dict[str, Any]]:
        return media_inventory()

    @app.post("/api/session/start")
    def start_session(
        request: SessionRequest, _: User = Depends(current_user)
    ) -> dict[str, Any]:
        try:
            service.start(request.source, request.start_seconds, request.duration_seconds)
            return {"ok": True, "source": request.source}
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/stop")
    def stop_session(_: User = Depends(current_user)) -> dict[str, bool]:
        service.stop()
        return {"ok": True}

    @app.get("/api/events")
    def events(
        _: User = Depends(current_user), limit: int = Query(100, ge=1, le=500)
    ) -> list[dict[str, Any]]:
        return storage.list_events(limit)

    @app.get("/api/config")
    def get_config(_: User = Depends(engineer_only)) -> dict[str, Any]:
        return config_manager.snapshot()

    @app.patch("/api/config")
    def patch_config(
        request: ConfigPatch, user: User = Depends(engineer_only)
    ) -> dict[str, Any]:
        before = config_manager.snapshot()
        try:
            after = config_manager.update(request.patch)
            service.reload_config()
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        storage.add_audit(user.username, "config.update", before, after)
        return after

    @app.get("/api/audit")
    def audits(
        _: User = Depends(engineer_only), limit: int = Query(50, ge=1, le=200)
    ) -> list[dict[str, Any]]:
        return storage.list_audits(limit)

    @app.get("/api/stream.mjpg")
    def stream(token: str = Query(...)) -> StreamingResponse:
        try:
            token_manager.verify(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return StreamingResponse(
            service.mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    @app.websocket("/ws")
    async def websocket_status(websocket: WebSocket, token: str = Query(...)) -> None:
        try:
            token_manager.verify(token)
        except ValueError:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(service.status())
                await asyncio.sleep(0.35)
        except WebSocketDisconnect:
            return

    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    if frontend_dist.exists():
        assets = frontend_dist / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> Response:
            requested = (frontend_dist / path).resolve()
            if requested.is_file() and frontend_dist.resolve() in requested.parents:
                return FileResponse(requested)
            return FileResponse(frontend_dist / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        def root() -> JSONResponse:
            return JSONResponse(
                {
                    "name": "RoadWatch",
                    "message": "Frontend chưa build. API docs tại /docs.",
                    "health": "/api/health",
                }
            )
    return app


app = create_app()
