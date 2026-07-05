"""
Build a JSON body for the /verify/face k6 test, and print the matching
enrollment body.

Usage:
    python stress/build_verify_payload.py path/to/face.jpg --user-id loadtest_user

Writes stress/verify_payload.json:
    {"current_face": "<base64>", "user_id": "<user-id>"}

which is what /verify/face expects in user_id mode (see
src/api/schemas.py::VerifyFaceRequest). The referenced user must already be
enrolled; enroll once with:

    curl -X POST http://localhost:5000/enroll/face \
      -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
      -d @stress/enroll_payload.json

This script also writes stress/enroll_payload.json for that one-time call.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build verify + enroll payloads.")
    parser.add_argument("image", help="Path to a JPEG/PNG containing a face.")
    parser.add_argument("--user-id", default="loadtest_user", help="Enrollment user id.")
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parent),
        help="Directory to write the payload files into (default: stress/).",
    )
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.is_file():
        print(f"error: image not found: {img_path}", file=sys.stderr)
        return 1

    b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
    out_dir = Path(args.out_dir)

    verify_path = out_dir / "verify_payload.json"
    verify_path.write_text(
        json.dumps({"current_face": b64, "user_id": args.user_id}), encoding="utf-8"
    )

    enroll_path = out_dir / "enroll_payload.json"
    enroll_path.write_text(
        json.dumps({"user_id": args.user_id, "images": [b64]}), encoding="utf-8"
    )

    print(f"Wrote {verify_path}")
    print(f"Wrote {enroll_path}  (enroll user '{args.user_id}' once before testing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
