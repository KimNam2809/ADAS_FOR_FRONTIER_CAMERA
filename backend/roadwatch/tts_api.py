from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .asset_bootstrap import bootstrap_assets
from .tts import MAX_TEXT_LENGTH, PiperSynthesizer, default_alert_corpus


LOGGER = logging.getLogger(__name__)
synthesizer = PiperSynthesizer(cache_size=256)


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.asset_bootstrap = bootstrap_assets()
    try:
        messages = (
            default_alert_corpus()
            if os.getenv("ROADWATCH_TTS_PRECACHE", "1") == "1"
            else None
        )
        synthesizer.warmup(messages)
    except Exception as exc:  # pragma: no cover - cloud asset/runtime dependent
        synthesizer.error = str(exc)
        LOGGER.exception("Piper warmup thất bại")
    yield


app = FastAPI(
    title="RoadWatch Vietnamese Piper TTS",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, Any]:
    status = synthesizer.status()
    status["asset_bootstrap"] = getattr(
        app.state, "asset_bootstrap", {"enabled": False, "reason": "not_started"}
    )
    status["status"] = "ready" if status["available"] and not status["error"] else "degraded"
    return status


@app.post("/synthesize")
def synthesize(request: SynthesisRequest) -> Response:
    try:
        result = synthesizer.synthesize(request.text)
        return Response(
            content=result.wav,
            media_type="audio/wav",
            headers={
                "Cache-Control": "private, max-age=86400",
                "X-RoadWatch-TTS-Provider": result.provider,
                "X-RoadWatch-TTS-Voice": "Truc-Ly"
                if (result.voice_name or "Trúc Ly") == "Trúc Ly"
                else (result.voice_name or "Truc-Ly"),
                "X-RoadWatch-TTS-Cache": "hit" if result.cache_hit else "miss",
                "X-RoadWatch-TTS-Ms": f"{result.synthesis_ms:.3f}",
                "X-RoadWatch-TTS-Model": result.voice_model_sha256 or "unknown",
            },
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Piper synthesis thất bại")
        raise HTTPException(status_code=503, detail="Piper tiếng Việt chưa sẵn sàng") from exc
