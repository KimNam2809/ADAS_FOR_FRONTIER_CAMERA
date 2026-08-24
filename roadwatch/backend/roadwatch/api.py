from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth import TokenManager
from .asset_bootstrap import bootstrap_assets
from .asset_store import materialize_media_source, persist_uploaded_media
from .catalog import media_catalog
from .config import ConfigManager, PROJECT_ROOT, media_inventory
from .pipeline import RoadWatchService
from .schemas import ConfigPatch, LoginRequest, SeekRequest, SessionRequest, TokenResponse, User
from .storage import Storage
from .uploads import save_upload


LOGGER = logging.getLogger(__name__)


def create_app(start_pipeline: bool = False, database_path: Path | None = None) -> FastAPI:
    config_manager = ConfigManager()
    storage = Storage(database_path)
    token_manager = TokenManager(config_manager.snapshot()["security"]["token_ttl_minutes"])
    service = RoadWatchService(config_manager, storage)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        app.state.asset_bootstrap = bootstrap_assets()
        # Perception is constructed before FastAPI lifespan. If cloud assets
        # were materialized during startup, rebuild adapters so existence-based
        # ONNX selection sees the files and never falls back to PT/download.
        if app.state.asset_bootstrap.get("enabled") and not app.state.asset_bootstrap.get("error"):
            service.reload_config()
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
        result = service.health()
        result["asset_bootstrap"] = getattr(
            app.state, "asset_bootstrap", {"enabled": False, "reason": "not_started"}
        )
        return result

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
        return media_catalog()

    @app.get("/api/library")
    def library(_: User = Depends(current_user)) -> dict[str, Any]:
        items = media_catalog()
        return {
            "schema_version": "roadwatch.library.v1",
            "items": items,
            "cached_results": "not_available_local_runtime",
        }

    @app.post("/api/uploads")
    def upload_video(
        file: UploadFile = File(...), _: User = Depends(current_user)
    ) -> dict[str, Any]:
        try:
            result = save_upload(file)
            result.update(persist_uploaded_media(str(result["source"])))
            return result
        except (ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception("Không thể lưu upload vào asset store")
            raise HTTPException(status_code=503, detail="Kho lưu trữ video cloud chưa sẵn sàng") from exc

    @app.post("/api/session/start")
    def start_session(
        request: SessionRequest, _: User = Depends(current_user)
    ) -> dict[str, Any]:
        try:
            if isinstance(request.source, str) and not request.source.isdigit():
                materialized = materialize_media_source(request.source)
                if not materialized.get("available"):
                    raise FileNotFoundError(f"Không tìm thấy video: {request.source}")
            service.start(
                request.source,
                request.start_seconds,
                request.duration_seconds,
                request.run_id,
                request.source_kind,
                request.analysis_mode,
            )
            current = service.status()
            return {
                "ok": True,
                "source": request.source,
                "run_id": current.get("run_id"),
                "session_id": current.get("session_id"),
                "analysis_mode": current.get("analysis_mode", request.analysis_mode),
            }
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/stop")
    def stop_session(_: User = Depends(current_user)) -> dict[str, bool]:
        service.stop()
        return {"ok": True}

    @app.post("/api/session/pause")
    def pause_session(_: User = Depends(current_user)) -> dict[str, Any]:
        try:
            service.pause()
            return {"ok": True, "playback": service.status()["playback"]}
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/resume")
    def resume_session(_: User = Depends(current_user)) -> dict[str, Any]:
        try:
            service.resume()
            return {"ok": True, "playback": service.status()["playback"]}
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/session/seek")
    def seek_session(request: SeekRequest, _: User = Depends(current_user)) -> dict[str, Any]:
        try:
            target = service.seek(request.seconds, relative=request.relative)
            return {"ok": True, "target_seconds": target}
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    def stream(token: str = Query(...), session_id: str | None = Query(default=None)) -> StreamingResponse:
        try:
            token_manager.verify(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return StreamingResponse(
            service.mjpeg(session_id), media_type="multipart/x-mixed-replace; boundary=frame"
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

    frontend_dist = Path(
        os.getenv("ROADWATCH_FRONTEND_DIST", str(PROJECT_ROOT / "frontend" / "dist"))
    ).resolve()
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
