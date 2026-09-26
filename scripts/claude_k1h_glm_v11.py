#!/usr/bin/env python3
"""k1h teacher jobs through GLM helper v1.1 (Creative answers in chat thread, 2026-09-26; k1h ADDENDUM-2).

scripts/claude_k1h_glm.py (sealed in SEAL-k1h.sha256.txt, not edited) with one change: its GLM calls go through
scripts/claude_glm_opencode_v11.py, which deletes exactly the opencode session each call creates (v1,
claude_glm_opencode.py sha 3b597086, left one session behind per call: the Director's 000-glm-throughput finding).
Same model, prompts, parsing, resume, time cap and outputs; at most 2 calls at once (k1h's share of the Director's
opencode budget of 16, the Thread manager 20:00 UTC).
  python3 -B scripts/claude_k1h_glm_v11.py chats|answer|selftest ...   (the same arguments as claude_k1h_glm.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_k1h_glm as K      # noqa: E402

MAX_WORKERS = 2


def _call_v11(text: str) -> str:
    import claude_glm_opencode_v11 as G11
    return G11.call(text, model=K.MODEL, timeout=300)


def main() -> None:
    if "--workers" in sys.argv:
        w = int(sys.argv[sys.argv.index("--workers") + 1])
        if w > MAX_WORKERS:
            raise SystemExit(f"k1h-glm v1.1: at most {MAX_WORKERS} calls at once (k1h's share of the opencode budget)")
    elif sys.argv[1:2] != ["selftest"]:
        sys.argv += ["--workers", str(MAX_WORKERS)]
    K._call = _call_v11
    K.main()


if __name__ == "__main__":
    main()
