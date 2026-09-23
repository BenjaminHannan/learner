#!/usr/bin/env python3
"""Dev-only: render a sweep-frames file through sealed 241b render_line.

Writes --out-frames (one row per frame: id, act, route, ms, frame,
legacy_text) and --out-sweep (id, act, text). For m2a/m5 dev pilot.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop241b_agent as A  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--out-frames", required=True)
    ap.add_argument("--out-sweep", required=True)
    a = ap.parse_args(argv)
    n = 0
    with open(a.frames, encoding="utf-8") as fh, \
            open(a.out_frames, "w", encoding="utf-8") as fo, \
            open(a.out_sweep, "w", encoding="utf-8") as so:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            f = json.loads(line)
            r = A.render_line(f["legacy_text"], f.get("records"), [])
            fo.write(json.dumps({"id": f["id"], "act": f["act"],
                                 "route": r["route"], "ms": r["ms"],
                                 "frame": r.get("frame") or f["frame"],
                                 "legacy_text": f["legacy_text"]},
                                ensure_ascii=False) + "\n")
            so.write(json.dumps({"id": f["id"], "act": f["act"],
                                 "text": r["text"]},
                                ensure_ascii=False) + "\n")
            n += 1
    print(f"rendered {n} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
