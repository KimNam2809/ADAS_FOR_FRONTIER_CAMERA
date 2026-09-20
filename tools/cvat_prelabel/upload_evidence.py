from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .cvat_api import CvatApiError, CvatClient
from .evidence import write_json


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_hash(run_dir: Path, filename: str) -> str:
    for line in (run_dir / "hashes.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if relative == filename:
            return digest
    raise CvatApiError(f"Missing {filename} in hashes.sha256")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upload an immutable RoadWatch pre-label evidence payload to an empty CVAT task."
    )
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()

    run_dir = args.evidence_dir.resolve()
    payload_path = run_dir / "cvat_annotation_payload.json"
    actual_hash = _sha256(payload_path)
    expected_hash = _expected_hash(run_dir, payload_path.name)
    if actual_hash != expected_hash:
        raise CvatApiError("Evidence payload hash mismatch; refusing upload")

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    client = CvatClient(args.env_file.resolve())
    before = client.get_annotations(args.task_id)
    if before.get("tags") or before.get("shapes") or before.get("tracks"):
        raise CvatApiError("CVAT task is not empty; refusing to overwrite annotations")

    client.replace_annotations(args.task_id, payload)
    after = client.get_annotations(args.task_id)
    expected_shapes = len(payload.get("shapes", []))
    actual_shapes = len(after.get("shapes", []))
    if actual_shapes != expected_shapes:
        raise CvatApiError(
            f"Upload verification failed: expected {expected_shapes} shapes, server has {actual_shapes}"
        )

    receipt = {
        "status": "uploaded_and_verified",
        "task_id": args.task_id,
        "payload_sha256": actual_hash,
        "server_annotation_version": after.get("version"),
        "server_shapes": actual_shapes,
    }
    write_json(run_dir / "upload_receipt.json", receipt)
    write_json(run_dir / "post_upload_annotations.json", after)
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
