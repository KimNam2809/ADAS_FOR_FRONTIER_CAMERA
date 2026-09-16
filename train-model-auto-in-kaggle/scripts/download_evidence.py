from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import require_kaggle_env, run, sha256, utc_now, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--output-dir", default="evidence")
    args = parser.parse_args()
    require_kaggle_env()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    run(["kaggle", "kernels", "output", args.kernel, "-p", str(output), "--force"])
    files = [{"path": str(path.relative_to(output)), "sha256": sha256(path), "bytes": path.stat().st_size} for path in sorted(output.rglob("*")) if path.is_file()]
    manifest = {"kernel_ref": args.kernel, "downloaded_at": utc_now(), "files": files}
    write_json(output / "evidence_manifest.json", manifest)
    print(json.dumps({"files": len(files), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
