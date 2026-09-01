from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth import TokenManager
from .asset_bootstrap import bootstrap_assets
from .asset_store import materialize_media_source, persist_uploaded_media
from .alert_copy import alert_copy_profile
from .catalog import media_catalog
from .config import ConfigManager, PROJECT_ROOT, media_inventory
from .pipeline import RoadWatchService
from .schemas import ConfigPatch, LoginRequest, SeekRequest, SessionRequest, TokenResponse, User
from .storage import Storage
from .tts import PiperGateway
from .uploads import save_upload


LOGGER = logging.getLogger(__name__)


def _frontend_release() -> dict[str, str]:
    configured = os.getenv("ROADWATCH_FRONTEND_DIST", "").strip()
    if configured:
        path = Path(configured).resolve()
    else:
        candidates = (
            PROJECT_ROOT / "frontend" / "dist-ui-v4",
            PROJECT_ROOT / "frontend" / "dist-ui-v3",
            PROJECT_ROOT / "frontend" / "dist-ui-v2",
            PROJECT_ROOT / "frontend" / "dist",
            PROJECT_ROOT / "frontend" / "dist-local",
        )
        path = next(
            (candidate.resolve() for candidate in candidates if (candidate / "index.html").is_file()),
            (PROJECT_ROOT / "frontend" / "dist").resolve(),
        )
    index = path / "index.html"
    return {
        "bundle": path.name,
        "index_mtime": str(index.stat().st_mtime_ns) if index.is_file() else "missing",
    }


def create_app(start_pipeline: bool = False, database_path: Path | None = None) -> FastAPI:
    config_manager = ConfigManager()
    storage = Storage(database_path)
    token_manager = TokenManager(config_manager.snapshot()["security"]["token_ttl_minutes"])
    service = RoadWatchService(config_manager, storage)
    tts_gateway = PiperGateway()
    cloud_mode = bool(os.getenv("ROADWATCH_CLOUD_MODE"))
    deferred_startup = cloud_mode and os.getenv("ROADWATCH_DEFERRED_STARTUP", "1") == "1"
    startup_started_at = time.time()
    startup_lock = threading.RLock()
    startup_cancelled = threading.Event()
    startup_state: dict[str, Any] = {
        "deployment_profile": "cloud_demo" if cloud_mode else "edge_local",
        "deferred": deferred_startup,
        "ready": False,
        "state": "starting",
        "stage": "container",
        "message": "Đang khởi động dịch vụ RoadWatch.",
        "started_at": startup_started_at,
        "ready_at": None,
        "error": None,
    }

    def update_startup(**changes: Any) -> None:
        with startup_lock:
            startup_state.update(changes)

    def startup_snapshot() -> dict[str, Any]:
        with startup_lock:
            result = dict(startup_state)
        end = float(result.get("ready_at") or time.time())
        result["elapsed_seconds"] = round(max(0.0, end - startup_started_at), 1)
        result["retry_after_seconds"] = 2 if not result.get("ready") else 0
        return result

    def initialize_runtime() -> None:
        try:
            update_startup(
                stage="assets",
                message="Đang tải và kiểm tra model, video mẫu từ Cloud Storage.",
            )
            assets = bootstrap_assets()
            app.state.asset_bootstrap = assets
            if assets.get("error"):
                raise RuntimeError(f"Cloud asset bootstrap thất bại: {assets['error']}")
            if startup_cancelled.is_set():
                return
            if assets.get("enabled"):
                update_startup(
                    stage="perception",
                    message="Đang khởi tạo Object, Traffic Sign và Lane Detection.",
                )
                service.reload_config()
            # Cloud on-demand mode must finish model graph initialization before
            # the gate announces readiness. Local/edge keeps its established
            # session-start warmup semantics to avoid changing offline startup.
            if cloud_mode:
                service.perception.warmup()
            if startup_cancelled.is_set():
                return
            update_startup(
                stage="tts",
                message="Đang đánh thức bộ đọc cảnh báo tiếng Việt và hoàn tất kiểm tra hệ thống.",
            )
            tts_gateway.warmup()
            if start_pipeline or config_manager.snapshot()["app"].get("auto_start", False):
                service.start()
            update_startup(
                ready=True,
                state="ready",
                stage="ready",
                message="RoadWatch đã sẵn sàng phân tích video.",
                ready_at=time.time(),
                error=None,
            )
        except Exception as exc:  # pragma: no cover - cloud metadata/runtime dependent
            LOGGER.exception("RoadWatch deferred startup thất bại")
            update_startup(
                ready=False,
                state="error",
                stage="error",
                message="Không thể hoàn tất khởi động AI. Vui lòng tải lại trang sau ít phút.",
                error=str(exc)[:500],
            )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        app.state.asset_bootstrap = {"enabled": False, "reason": "not_started"}
        app.state.startup_task = None
        if deferred_startup:
            # Yield immediately so the cached/static React shell can explain a
            # Cloud Run cold start while model/media bootstrap continues with
            # instance-based CPU in a background worker.
            app.state.startup_task = asyncio.create_task(asyncio.to_thread(initialize_runtime))
        else:
            await asyncio.to_thread(initialize_runtime)
        yield
        startup_cancelled.set()
        task = getattr(app.state, "startup_task", None)
        if task is not None and not task.done():
            task.cancel()
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
    app.state.tts_gateway = tts_gateway
    app.state.startup_snapshot = startup_snapshot

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
        startup = startup_snapshot()
        if not startup["ready"]:
            result["status"] = "starting" if startup["state"] != "error" else "degraded"
        result["startup"] = startup
        result["alert_copy_profile"] = alert_copy_profile()
        result["tts"] = tts_gateway.status()
        result["frontend_release"] = _frontend_release()
        result["asset_bootstrap"] = getattr(
            app.state, "asset_bootstrap", {"enabled": False, "reason": "not_started"}
        )
        return result

    @app.get("/api/startup")
    def startup() -> JSONResponse:
        """Public, secret-free readiness used by the first-visit startup gate."""

        payload = startup_snapshot()
        if payload.get("error"):
            payload["error"] = "STARTUP_INIT_FAILED"
        return JSONResponse(
            payload,
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Retry-After": str(payload["retry_after_seconds"]),
            },
        )

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
        result = service.status()
        cloud = bool(os.getenv("ROADWATCH_CLOUD_MODE"))
        result["deployment_profile"] = "cloud_demo" if cloud else "edge_local"
        result["status_transport"] = "polling" if cloud else "websocket_or_polling"
        result["cloud_fast_preview"] = os.getenv("ROADWATCH_CLOUD_FAST", "0") == "1"
        result["cloud_full_perception"] = os.getenv("ROADWATCH_CLOUD_FULL", "0") == "1"
        result["alert_copy_profile"] = alert_copy_profile()
        result["tts"] = tts_gateway.status()
        result["frontend_release"] = _frontend_release()
        return result

    @app.get("/api/media/file")
    def media_file(
        source: str = Query(..., min_length=1, max_length=512),
        token: str = Query(..., min_length=16),
    ) -> FileResponse:
        """Serve an authenticated replay source so the UI can preview it immediately.

        This is deliberately limited to the media root and is not a camera or
        vehicle data endpoint. Cloud Run materializes a durable GCS upload on
        the current instance before returning the file.
        """
        try:
            token_manager.verify(token)
            if source.isdigit():
                raise ValueError("Camera live không có file preview")
            materialized = materialize_media_source(source)
            if not materialized.get("available"):
                raise FileNotFoundError(source)
            path = Path(ConfigManager.media_source(source))
            return FileResponse(path, media_type="video/mp4", filename=path.name)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Không tìm thấy video preview") from exc

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
        startup = startup_snapshot()
        if cloud_mode and not startup["ready"]:
            raise HTTPException(
                status_code=503,
                detail=(
                    "RoadWatch AI đang khởi động. Vui lòng đợi màn hình báo sẵn sàng "
                    "rồi bắt đầu phân tích."
                ),
                headers={"Retry-After": str(startup["retry_after_seconds"])},
            )
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

    @app.get("/api/tts/events/{event_id}.wav")
    def tts_event(event_id: str, _: User = Depends(current_user)) -> Response:
        """Return selected Vietnamese TTS audio only for a server-generated alert event."""
        if not 1 <= len(event_id) <= 80 or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:."
            for character in event_id
        ):
            raise HTTPException(status_code=400, detail="Event ID không hợp lệ")
        event = storage.get_event_by_uuid(event_id)
        if event is None:
            event = next(
                (
                    item
                    for item in service.status().get("events", [])
                    if str(item.get("event_id")) == event_id
                ),
                None,
            )
        if event is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo để phát TTS")
        if event.get("audio_action") not in {"tts", "beep_tts"}:
            raise HTTPException(status_code=409, detail="Cảnh báo này không được phép phát TTS")
        message = str(event.get("spoken_message") or event.get("message") or "").strip()
        try:
            audio = tts_gateway.synthesize(message)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            LOGGER.exception("Không thể lấy TTS audio cho event %s", event_id)
            raise HTTPException(status_code=503, detail="TTS tiếng Việt chưa sẵn sàng") from exc
        return Response(
            content=audio.wav,
            media_type="audio/wav",
            headers={
                "Cache-Control": "private, max-age=86400",
                "X-RoadWatch-TTS-Provider": audio.provider,
                # HTTP headers are Latin-1/ASCII in the current test client;
                # keep the accented display name in JSON/status and use an
                # ASCII wire token for the audio response.
                "X-RoadWatch-TTS-Voice": "Truc-Ly"
                if (audio.voice_name or "Trúc Ly") == "Trúc Ly"
                else (audio.voice_name or "Truc-Ly"),
                "X-RoadWatch-TTS-Cache": "hit" if audio.cache_hit else "miss",
                "X-RoadWatch-TTS-Ms": f"{audio.synthesis_ms:.3f}",
                "X-RoadWatch-TTS-Model": audio.voice_model_sha256 or "unknown",
                **(
                    {"X-RoadWatch-TTS-Fallback": audio.fallback_reason[:300]}
                    if audio.fallback_reason
                    else {}
                ),
            },
        )

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

    configured_frontend = os.getenv("ROADWATCH_FRONTEND_DIST", "").strip()
    if configured_frontend:
        frontend_dist = Path(configured_frontend).resolve()
    else:
        # Prefer the newest local bundle when uvicorn is launched directly.
        # Docker/Cloud only ships frontend/dist, so it remains the final
        # candidate. An explicit env path still wins for rollback/canary.
        frontend_candidates = (
            PROJECT_ROOT / "frontend" / "dist-ui-v4",
            PROJECT_ROOT / "frontend" / "dist-ui-v3",
            PROJECT_ROOT / "frontend" / "dist-ui-v2",
            PROJECT_ROOT / "frontend" / "dist",
            PROJECT_ROOT / "frontend" / "dist-local",
        )
        frontend_dist = next(
            (candidate.resolve() for candidate in frontend_candidates if (candidate / "index.html").is_file()),
            (PROJECT_ROOT / "frontend" / "dist").resolve(),
        )
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
