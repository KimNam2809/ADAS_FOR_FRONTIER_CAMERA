from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "kaggle/export_object_v2_artifacts/roadwatch_export_object_v2_artifacts.py"


def load_exporter():
    spec = importlib.util.spec_from_file_location("roadwatch_export_object_v2_artifacts", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_select_artifacts_prefers_source_kernel(tmp_path: Path) -> None:
    exporter = load_exporter()
    generic = tmp_path / "generic/best.pt"
    preferred = tmp_path / f"{exporter.SOURCE_SLUG}/best.pt"
    generic.parent.mkdir(parents=True)
    preferred.parent.mkdir(parents=True)
    generic.write_bytes(b"generic")
    preferred.write_bytes(b"preferred")
    selected = exporter.select_artifacts(tmp_path)
    assert selected["best.pt"] == preferred


def test_sha256_file_is_reproducible(tmp_path: Path) -> None:
    exporter = load_exporter()
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"RoadWatch")
    assert exporter.sha256_file(artifact) == exporter.sha256_file(artifact)
    assert len(exporter.sha256_file(artifact)) == 64
