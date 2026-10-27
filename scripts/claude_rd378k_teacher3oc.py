#!/usr/bin/env python3
"""rd-378k labeller v3 through Ben's opencode route (Trustworthy notes thread, 2026-09-26). New file; teacher3 stays.

gate3 (labeller v3 via OpenRouter) ran while the OpenRouter account had no funds, so it does not count (Thread manager,
19:00 UTC). Ben (18:47 UTC) offered GLM 5.3 Flash through his opencode subscription instead. The one change here: every
teacher call goes through scripts/claude_glm_opencode.py call() (the Director's shared helper) instead of OpenRouter.
Prompt words, verdict words, windows of at most 7 graded turns, the tolerant parser and the two passes are
claude_rd378k_teacher3's, run unchanged. The route sets no temperature (opencode's default) and may add its own system
text; this labeller measures that route as it is, and it is the route that would grade training data.
No key is read: opencode holds its own login, and this script never touches opencode config or auth files.

label  python -B scripts/claude_rd378k_teacher3oc.py label --judge-in J.jsonl --out DIR [--only-hash K] [--hash-rem R]
       (same outputs as claude_rd378k_teacher3.py label; cost_usd is 0 because the route reports none)
selftest (no network)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_glm_opencode as OC  # noqa: E402
import claude_rd378k_teacher3 as T3  # noqa: E402


def call_opencode(_key, _model, text, _temperature):
    try:
        return OC.call(text) or "", {}
    except Exception as e:                            # a failed call is logged and counted, never guessed
        print(f"[rd378k-teacher3oc] call failed: {type(e).__name__} {str(e)[:120]}", flush=True)
        return "", {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["label", "selftest"])
    ap.add_argument("--judge-in", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--only-hash", type=int, default=1)
    ap.add_argument("--hash-rem", type=int, default=0)
    a = ap.parse_args()
    T3.call = call_opencode
    if a.mode == "selftest":
        T3.selftest()
        assert T3.call is call_opencode
        print("rd378k teacher3oc selftest 1/1 ok")
        return
    a.model = "opencode-go/glm-5.3-flash"
    T3.label(a, None)


if __name__ == "__main__":
    main()
