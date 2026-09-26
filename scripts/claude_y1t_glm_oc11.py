#!/usr/bin/env python3
"""y1t top-up runner on helper v1.1 (Answering-from-memory thread, 2026-09-26). New file; nothing else changes.

Runs scripts/claude_lis320_glm_oc.py (Reading facts' opencode wrapper: prompt, parser, batches and rows unchanged)
with the Director's helper v1.1 (scripts/claude_glm_opencode_v11.py, sha 7a067cfb...; same call() interface and reply
text as v1, but each call deletes its own opencode session) in place of v1 (claude_glm_opencode.py leaves one session
behind per call). The only change: the module the wrapper imports as claude_glm_opencode is v1.1.

  python -B scripts/claude_y1t_glm_oc11.py --seeds S.jsonl --out raw.jsonl --workers 3 --batch 40 --max-minutes 150
  python -B scripts/claude_y1t_glm_oc11.py --selftest       (no network: the wrapper's own selftest + the swap check)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_glm_opencode_v11 as V11  # noqa: E402

sys.modules["claude_glm_opencode"] = V11
import claude_lis320_glm_oc as W  # noqa: E402


def selftest() -> None:
    import claude_glm_opencode as OC
    assert OC is V11 and callable(OC.call) and W.MODEL == V11.MODEL, "helper swap failed"
    seen = []
    real = V11.call
    try:
        V11.call = lambda text, model=None, timeout=300: seen.append(model) or "stub"
        assert W.call_opencode("hi") == ("stub", {}) and seen == [W.MODEL]     # the wrapper's calls reach v1.1
    finally:
        V11.call = real
    W.selftest()
    print("y1t glm_oc11 selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(W.main())
