#!/usr/bin/env python3
"""lis-320 GLM wording through Ben's opencode route with the Director's helper v1.1 (reading thread, 2026-09-26;
ADDENDUM-5). New file; claude_lis320_glm_oc.py (helper v1, pilot 3) stays as sealed.

The one difference from claude_lis320_glm_oc: each call goes through scripts/claude_glm_opencode_v11.py call()
(sha256 7a067cfb...), which adds a per-call --title tag to `opencode run` and deletes exactly that session afterwards
(v1 leaked one session per call). Prompt, model id, reply text handling, batching, time cap, failed-call stop and
output rows are claude_lis320_glm_oc's, run unchanged. Same flags as claude_lis320_glm_oc.py.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_lis320_glm_oc as B  # noqa: E402

_LOCK = threading.Lock()


def call_opencode_v11(text):
    import claude_glm_opencode_v11 as OC
    try:
        out = OC.call(text, model=B.MODEL) or ""
    except Exception as e:                            # a failed call is logged and counted, never guessed
        print(f"[glm320oc11] call failed: {type(e).__name__} {str(e)[:120]}", flush=True)
        out = ""
    if not out:
        with _LOCK:
            B.FAILED["n"] += 1
    return out, {}


if __name__ == "__main__":
    B.call_opencode = call_opencode_v11
    if "--selftest" in sys.argv:
        assert B.call_opencode is call_opencode_v11
        B.selftest()
        print("lis320 glm_oc11 selftest ok (v1.1 caller wired)")
    else:
        sys.exit(B.main())
