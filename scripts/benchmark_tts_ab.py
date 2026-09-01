from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.tts import PiperSynthesizer, TTSProvider, default_alert_corpus  # noqa: E402
from roadwatch.tts_vieneu import VieNeuSynthesizer  # noqa: E402


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def rss_mb() -> float | None:
    try:
        import psutil  # type: ignore[import-not-found]

        return round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
    except Exception:
        return None


def run_provider(name: str, factory: Callable[[], TTSProvider], corpus: tuple[str, ...]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        provider = factory()
        initial_status = provider.status()
        if not initial_status.get("available"):
            return {
                "provider": name,
                "status": "dependency_missing_or_asset_unavailable",
                "initial_status": initial_status,
                "corpus_count": len(corpus),
                "errors": ["Provider is not available; no synthesis attempted."],
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            }

        # Use a non-corpus prime phrase so all active canonical messages are
        # measured as uncached calls, while model/session cold loading is still
        # separated from the alert corpus timings.
        provider.synthesize("RoadWatch khởi động.")
        warm_status = provider.status()
        uncached_ms: list[float] = []
        cached_ms: list[float] = []
        errors: list[dict[str, str]] = []
        valid_wav = 0

        for message in corpus:
            call_started = time.perf_counter()
            try:
                result = provider.synthesize(message)
                elapsed = (time.perf_counter() - call_started) * 1000.0
                uncached_ms.append(elapsed)
                if result.wav[:4] == b"RIFF" and result.wav[8:12] == b"WAVE":
                    valid_wav += 1
            except Exception as exc:
                errors.append({"message": message, "error": str(exc)[:300]})

        for message in corpus:
            call_started = time.perf_counter()
            try:
                result = provider.synthesize(message)
                cached_ms.append((time.perf_counter() - call_started) * 1000.0)
                if not result.cache_hit:
                    errors.append({"message": message, "error": "Expected cache hit on second pass."})
            except Exception as exc:
                errors.append({"message": message, "error": str(exc)[:300]})

        final_status = provider.status()
        uncached_p95 = percentile(uncached_ms, 0.95)
        cached_p95 = percentile(cached_ms, 0.95)
        static_pass = (
            len(uncached_ms) == len(corpus)
            and valid_wav == len(corpus)
            and not errors
            and uncached_p95 <= 2_000.0
            and cached_p95 <= 750.0
        )
        return {
            "provider": name,
            "status": "pass_static_performance_pending_human_listening" if static_pass else "failed_static_performance",
            "initial_status": initial_status,
            "warm_status": warm_status,
            "final_status": final_status,
            "corpus_count": len(corpus),
            "uncached_success": len(uncached_ms),
            "cached_success": len(cached_ms),
            "valid_wav": valid_wav,
            "errors": errors[:20],
            "error_count": len(errors),
            "uncached_ms": {
                "p50": round(percentile(uncached_ms, 0.50), 3),
                "p95": round(uncached_p95, 3),
                "max": round(max(uncached_ms), 3) if uncached_ms else 0.0,
            },
            "cached_start_ms": {
                "p50": round(percentile(cached_ms, 0.50), 3),
                "p95": round(cached_p95, 3),
                "max": round(max(cached_ms), 3) if cached_ms else 0.0,
            },
            "memory_rss_mb": rss_mb(),
            "human_listening_gate": "pending",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "provider": name,
            "status": "runtime_error",
            "corpus_count": len(corpus),
            "errors": [str(exc)[:500]],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B benchmark Piper và VieNeu trên corpus cảnh báo RoadWatch")
    parser.add_argument("--provider", choices=("all", "piper", "vieneu"), default="all")
    parser.add_argument("--output", default="reports/tts-ab-latest.json")
    args = parser.parse_args()

    corpus = default_alert_corpus()
    providers: dict[str, Callable[[], TTSProvider]] = {
        # Use one common cache budget for the active profile corpus so
        # the second pass measures real cache-start latency for every phrase.
        "piper": lambda: PiperSynthesizer(cache_size=256),
        "vieneu": lambda: VieNeuSynthesizer(cache_size=256),
    }
    selected = ("piper", "vieneu") if args.provider == "all" else (args.provider,)
    results = {name: run_provider(name, providers[name], corpus) for name in selected}
    report = {
        "schema_version": "roadwatch.tts_ab.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
        },
        "corpus_count": len(corpus),
        "gates": {
            "canonical_messages": len(corpus),
            "uncached_p95_ms_max": 2_000,
            "cached_start_p95_ms_max": 750,
            "audio_completion_min": 0.99,
            "human_listeners_min": 3,
            "human_average_score_min": 4.0,
        },
        "results": results,
        "promotion_decision": "blocked_pending_human_listening",
        "release_provider": "piper",
        "measurement_note": (
            "Uncached timings include provider inference but exclude the separate model prime. "
            "memory_rss_mb is null when psutil is unavailable. Human listening is never automated."
        ),
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nĐã lưu bằng chứng A/B TTS: {output}")
    candidate = results.get("vieneu")
    return 0 if candidate and candidate.get("status") == "pass_static_performance_pending_human_listening" else 2


if __name__ == "__main__":
    raise SystemExit(main())
