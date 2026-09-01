"""Download allowlisted members from a very large Kaggle output ZIP via HTTP Range."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Iterable

import requests
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


KERNEL = "lekimnam/roadwatch-object-detector-v2-target-domain"
ARCHIVE_NAME = "_output_.zip"
CACHE_BYTES = 4 * 1024 * 1024
MAX_MEMBER_BYTES = 250 * 1024 * 1024
MAX_TOTAL_BYTES = 400 * 1024 * 1024
ALLOWLIST = {
    "best.pt": "roadwatch_objects_v2.pt",
    "best.onnx": "roadwatch_objects_v2.onnx",
    "job_status.json": "job_status.json",
    "pseudo_label_quality_gate.json": "pseudo_label_quality_gate.json",
    "results.csv": "training_results.csv",
    "args.yaml": "training_args.yaml",
    "confusion_matrix.png": "confusion_matrix.png",
    "confusion_matrix_normalized.png": "confusion_matrix_normalized.png",
    "results.png": "training_curves.png",
}
REQUIRED = {"best.pt", "best.onnx", "job_status.json"}


def build_session() -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def signed_output_url(kernel: str, archive_name: str) -> str:
    owner, slug = kernel.split("/", 1)
    api = KaggleApi()
    api.authenticate()
    request = ApiListKernelSessionOutputRequest()
    request.user_name = owner
    request.kernel_slug = slug
    api._set_paging(request, 200, None)
    with api.build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.list_kernel_session_output(request)
    for item in response.files or []:
        if item.file_name == archive_name:
            return str(item.url)
    raise FileNotFoundError(f"Kaggle output does not contain {archive_name!r}")


class HttpRangeReader(io.RawIOBase):
    def __init__(self, session: requests.Session, url: str, size: int, cache_bytes: int = CACHE_BYTES):
        self.session = session
        self.url = url
        self.size = size
        self.position = 0
        self.cache_bytes = cache_bytes
        self.cache_start = 0
        self.cache = b""

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self.position + offset
        elif whence == io.SEEK_END:
            position = self.size + offset
        else:
            raise ValueError(f"Unsupported whence: {whence}")
        if position < 0:
            raise ValueError("Negative seek position")
        self.position = min(position, self.size)
        return self.position

    def _fetch(self, start: int, requested: int) -> None:
        length = max(requested, self.cache_bytes)
        end = min(self.size - 1, start + length - 1)
        response = self.session.get(
            self.url,
            headers={"Range": f"bytes={start}-{end}"},
            timeout=(15, 180),
        )
        if response.status_code != 206:
            response.close()
            raise RuntimeError(f"Range request must return HTTP 206, got {response.status_code}")
        expected = end - start + 1
        content = response.content
        response.close()
        if len(content) != expected:
            raise RuntimeError(f"Range length mismatch: expected {expected}, got {len(content)}")
        self.cache_start = start
        self.cache = content

    def read(self, size: int = -1) -> bytes:
        if self.position >= self.size or size == 0:
            return b""
        if size < 0:
            size = self.size - self.position
        size = min(size, self.size - self.position)
        if size > MAX_MEMBER_BYTES:
            raise RuntimeError(f"Single remote read exceeds safety limit: {size}")
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            cache_end = self.cache_start + len(self.cache)
            if not (self.cache_start <= self.position < cache_end):
                self._fetch(self.position, remaining)
                cache_end = self.cache_start + len(self.cache)
            offset = self.position - self.cache_start
            take = min(remaining, cache_end - self.position)
            chunks.append(self.cache[offset : offset + take])
            self.position += take
            remaining -= take
        return b"".join(chunks)


def archive_size(session: requests.Session, url: str) -> int:
    response = session.get(url, headers={"Range": "bytes=0-0"}, timeout=(15, 60))
    if response.status_code != 206:
        response.close()
        raise RuntimeError(f"Kaggle artifact server does not honor Range: HTTP {response.status_code}")
    content_range = response.headers.get("Content-Range", "")
    response.close()
    match = re.fullmatch(r"bytes 0-0/(\d+)", content_range)
    if not match:
        raise RuntimeError(f"Invalid Content-Range header: {content_range!r}")
    return int(match.group(1))


def member_score(info: zipfile.ZipInfo) -> tuple[int, int]:
    name = info.filename.replace("\\", "/").lower()
    score = 0
    if "roadwatch_object_v2/roadwatch_objects_v2" in name:
        score += 10
    if "/weights/" in name:
        score += 5
    if "roadwatch_object_v2" in name:
        score += 2
    return score, info.date_time[0]


def select_members(infos: Iterable[zipfile.ZipInfo]) -> dict[str, zipfile.ZipInfo]:
    candidates: dict[str, list[zipfile.ZipInfo]] = {}
    for info in infos:
        basename = Path(info.filename).name
        if not info.is_dir() and basename in ALLOWLIST:
            candidates.setdefault(basename, []).append(info)
    return {name: max(items, key=member_score) for name, items in candidates.items()}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_selected(output: Path, list_only: bool = False) -> dict:
    url = signed_output_url(KERNEL, ARCHIVE_NAME)
    session = build_session()
    size = archive_size(session, url)
    reader = HttpRangeReader(session, url, size)
    with zipfile.ZipFile(reader) as archive:
        selected = select_members(archive.infolist())
        missing = sorted(REQUIRED - set(selected))
        if missing:
            raise FileNotFoundError(f"Archive is missing required artifacts: {missing}")
        summary = {
            "kernel": KERNEL,
            "source_version": 4,
            "archive_size_bytes": size,
            "selected": {
                name: {"archive_path": info.filename, "size_bytes": info.file_size}
                for name, info in selected.items()
            },
        }
        if list_only:
            return summary
        if output.exists() and any(output.iterdir()):
            raise FileExistsError(f"Output directory is not empty: {output}")
        output.mkdir(parents=True, exist_ok=True)
        total = sum(info.file_size for info in selected.values())
        if total > MAX_TOTAL_BYTES:
            raise RuntimeError(f"Selected artifacts exceed safety limit: {total}")
        manifest_artifacts = []
        for source_name, info in selected.items():
            if info.file_size > MAX_MEMBER_BYTES:
                raise RuntimeError(f"Artifact exceeds member limit: {info.filename} ({info.file_size})")
            destination = output / ALLOWLIST[source_name]
            with archive.open(info) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            manifest_artifacts.append(
                {
                    "name": destination.name,
                    "archive_path": info.filename,
                    "size_bytes": destination.stat().st_size,
                    "sha256": sha256_file(destination),
                }
            )
    session.close()
    manifest = {
        "kernel": KERNEL,
        "source_version": 4,
        "archive_size_bytes": size,
        "promotion_status": "blocked_pending_human_pseudo_label_review_and_event_regression",
        "artifacts": manifest_artifacts,
    }
    (output / "download_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/kaggle/object_v2_v4_selected"))
    parser.add_argument("--list-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        result = download_selected(args.output, list_only=args.list_only)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "type": type(exc).__name__, "message": str(exc)}))
        raise
