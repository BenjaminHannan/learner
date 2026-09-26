#!/usr/bin/env python3
"""dl-7b: dl-7 with its Claude-written answer suffix replaced by GLM's (Fix-sleep thread, 2026-09-26; marks:
artifacts/claude-dl7-20260926/PASSMARKS.md with Addendum 2). Replaces dl-7, which never ran.

Why. Ben chose "Use GLM" (16:39 UTC 09-26) and "Count it" (16:50) for the fixed one-line puzzle instruction, so dl-7
keeps dl-6's puzzle frame but may not keep its Claude-written " Reply with the answer only." suffix on the anchor
questions. Dropping the suffix outright does not work: a CPU check (pool seed 3291 + 60000, 60 asks) kept 32 questions
but only 1 base answer finished within 16 tokens, so the shaky pool would be empty. dl-7b appends GLM 5.3 Flash's
suffix instead (artifacts/claude-glmframes-20260926/frames.json, "suffix" -> "chosen", after one space), pinned by
sha256 below. Everything else is dl-7 (scripts/claude_dl7_fragile.py, imported unchanged): arms S and F, seeds 12 and
13, 7 nights, TEST seed 3290, pool seed 3291, 3000 asks, marks F1-F5.

  python -B scripts/claude_dl7b_glmsuffix.py --selftest
  python -B scripts/claude_dl7b_glmsuffix.py --model M --out DIR        (registered run; dl-7's arguments)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_dl7_fragile as F7  # noqa: E402

FRAMES = HERE.parent / "artifacts/claude-glmframes-20260926/frames.json"
FRAMES_SHA256 = ""        # filled when frames.json lands, in the sealing commit, before any run


def glm_suffix() -> str:
    raw = FRAMES.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FRAMES_SHA256:
        raise SystemExit(f"frames.json sha256 {hashlib.sha256(raw).hexdigest()} != pinned {FRAMES_SHA256!r}")
    t = json.loads(raw.decode("utf-8"))["suffix"]["chosen"]
    if not t:
        raise SystemExit("frames.json has no chosen suffix")
    return " " + t


def selftest() -> None:
    old = F7.SUFFIX
    F7.SUFFIX = " Just the answer."
    assert F7.SUFFIX == " Just the answer."
    F7.SUFFIX = old
    F7.selftest()
    print("dl7b selftest ok")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    F7.SUFFIX = glm_suffix()                         # make_pool reads the module global at call time
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "suffix.json").write_text(json.dumps({"suffix": F7.SUFFIX, "sha256": FRAMES_SHA256}), encoding="utf-8")
    sys.argv[0] = "claude_dl7_fragile.py"
    F7.main()


if __name__ == "__main__":
    main()
