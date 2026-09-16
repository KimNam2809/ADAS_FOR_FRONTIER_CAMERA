from __future__ import annotations

import argparse
from pathlib import Path

from common import load_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True)
    parser.add_argument("--output", default="build/mobile-summary.md")
    args = parser.parse_args()
    status = load_json(Path(args.status))
    body = "\n".join(
        [
            "# RoadWatch Kaggle status",
            "",
            f"- Kernel: `{status.get('kernel_ref', 'unknown')}`",
            f"- Status: **{status.get('status', 'UNKNOWN')}**",
            f"- Checked: `{status.get('checked_at', '')}`",
            "- Promotion: **không tự động**",
            "",
            "Nếu ERROR, tải artifact diagnostics và gửi log đã che secret trong cuộc trò chuyện.",
        ]
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(body + "\n", encoding="utf-8")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

