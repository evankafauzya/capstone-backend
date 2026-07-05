"""
Build a JSON body for the k6 capacity test from a real image.

Usage:
    python stress/build_payload.py path/to/face.jpg
    python stress/build_payload.py path/to/face.jpg --out stress/payload.json

Writes ``stress/payload.json`` (or --out) containing:
    {"image": "<base64 of the image>"}

which is the exact body /detect/faces and /embeddings expect (field name
"image", see src/api/schemas.py::DetectFacesRequest). Cross-platform: uses
Python's base64 so it behaves the same on Windows PowerShell, Git Bash, and
Linux.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build payload.json for the k6 stress test.")
    parser.add_argument("image", help="C:\capstone-backend\foto_test\stress_test.jpg" \
    "")
    parser.add_argument(
        "--out" \
        "",
        default=str(Path(__file__).resolve().parent / "payload.json"),
        help="Output JSON path (default: stress/payload.json).",
    )
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.is_file():
        print(f"error: image not found: {img_path}", file=sys.stderr)
        return 1

    raw = img_path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    Path(args.out).write_text(json.dumps({"image": b64}), encoding="utf-8")

    print(f"Wrote {args.out}  ({len(raw) / 1024:.1f} KB image -> {len(b64) / 1024:.1f} KB base64)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
