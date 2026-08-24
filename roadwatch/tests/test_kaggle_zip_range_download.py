from __future__ import annotations

import importlib.util
import io
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/download_kaggle_zip_members.py"


def load_downloader():
    spec = importlib.util.spec_from_file_location("download_kaggle_zip_members", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def zip_info(name: str, content: bytes = b"x") -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.file_size = len(content)
    return info


def test_select_members_prefers_training_weight_path() -> None:
    downloader = load_downloader()
    generic = zip_info("dataset/cache/best.pt")
    trained = zip_info("roadwatch_object_v2/roadwatch_objects_v2/weights/best.pt")
    selected = downloader.select_members([generic, trained])
    assert selected["best.pt"] is trained


def test_select_members_ignores_non_allowlisted_files() -> None:
    downloader = load_downloader()
    selected = downloader.select_members(
        [zip_info("roadwatch_object_v2/roadwatch_objects_v2/weights/best.pt"), zip_info("secret.env")]
    )
    assert set(selected) == {"best.pt"}


def test_http_range_reader_seek_and_cache() -> None:
    downloader = load_downloader()
    payload = b"0123456789abcdefghijklmnopqrstuvwxyz"

    class Response:
        status_code = 206

        def __init__(self, content: bytes):
            self.content = content

        def close(self) -> None:
            return None

    class Session:
        calls = 0

        def get(self, _url, headers, timeout):
            del timeout
            self.calls += 1
            start, end = headers["Range"].removeprefix("bytes=").split("-")
            return Response(payload[int(start) : int(end) + 1])

    session = Session()
    reader = downloader.HttpRangeReader(session, "https://invalid.test", len(payload), cache_bytes=8)
    assert reader.read(4) == b"0123"
    reader.seek(-4, io.SEEK_END)
    assert reader.read(4) == b"wxyz"
    assert session.calls == 2
