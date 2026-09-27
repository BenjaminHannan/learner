#!/usr/bin/env python3
"""lis-320 Luna full run: claude_lis320_luna2 plus a log line for every failed helper try (reading thread, 2026-09-27;
ADDENDUM-12). New file; luna2, luna and claude_luna_codex stay as sealed.

The Director allowed 6 parallel Luna calls from chunk 2 on (09:56 UTC 09-27) on one condition: rate-limit or usage errors,
or climbing helper retries, send the next chunk back to 3. claude_luna_codex.call retries up to 3 times without printing,
so this wrapper counts each failed try and prints one line per failed try:
    [luna-try] failed: <reason, first 120 chars>
The prompt, writer, rows and checks are unchanged: the wrapper only observes _once's result and returns it as it was.
    python -B scripts/claude_lis320_luna3.py --seeds S --out R --workers 6 --batch 12 --max-minutes 55
    python -B scripts/claude_lis320_luna3.py --selftest
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_luna_codex as L  # noqa: E402
import claude_lis320_luna2 as LU2  # noqa: E402

_REAL_ONCE = L._once
_LOCK = threading.Lock()
TRIES = {"failed": 0}


def _once_logged(text, model, timeout):
    reply, why = _REAL_ONCE(text, model, timeout)
    if reply is None:
        with _LOCK:
            TRIES["failed"] += 1
        print(f"[luna-try] failed: {str(why)[:120]}", flush=True)
    return reply, why


def install():
    L._once = _once_logged


def selftest():
    seq = [(None, "exit 1: Rate limit exceeded"), ("ok reply", "")]
    L._once = lambda t, m, to: seq.pop(0)
    global _REAL_ONCE
    real, _REAL_ONCE = _REAL_ONCE, L._once
    try:
        L._once = _once_logged
        assert L.call("x") == "ok reply" and TRIES["failed"] == 1, TRIES
    finally:
        _REAL_ONCE = real
        L._once = real
        TRIES["failed"] = 0
    LU2.selftest()                                         # style sentence, writer, rows, failure path (no network)
    print("lis320 luna3 selftest ok (failed helper tries logged and counted; reply passed through; no network)")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    install()
    return LU2.main()


if __name__ == "__main__":
    sys.exit(main())
