#!/usr/bin/env python3
"""Run a sealed script with GPT-6 Luna at a chosen reasoning effort and time limit (Trustworthy notes thread,
2026-09-27). Same idea as scripts/claude_luna_run.py (bind the module name claude_glm_opencode, run the named script
unchanged), bound instead to scripts/claude_luna_effort.py with its TIMEOUT and EFFORT set from the flags. A failed call
raises after 3 tries; the sealed wrappers print their "call failed" line and use "" as the raw answer, as before.

python -B scripts/claude_luna_run2.py --effort low|medium|high|default --timeout SECONDS SCRIPT.py ARGS...
python -B scripts/claude_luna_run2.py --check   (no network: fakes the codex run; prints "luna2 bound ok")
"""
from __future__ import annotations

import contextlib
import io
import runpy
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_luna_effort as E  # noqa: E402

sys.modules["claude_glm_opencode"] = E


def check():
    import claude_glm_opencode as bound
    import claude_rd378g_writemore_oc as W
    import claude_rd378k_teacher3oc as K
    seen = []

    class P:
        def __init__(self, rc, out):
            self.returncode, self.stdout, self.stderr = rc, out, b""

    def fake_run(args, input=None, stdout=None, stderr=None, cwd=None, timeout=None, **kw):
        if args[1:3] == ["exec", "--help"]:
            return P(0, b"--output-last-message")
        seen.append((list(args), timeout))
        if b"SLOW" in input:
            raise subprocess.TimeoutExpired(args, timeout)
        return P(0, b"reply\n")
    real = subprocess.run
    subprocess.run = fake_run
    E.L._HAS_O = None
    buf = io.StringIO()
    try:
        E.EFFORT, E.TIMEOUT = "low", 600
        with contextlib.redirect_stdout(buf):
            good = W.oc_call("write this")
            slow = W.oc_call("SLOW")
            graded = K.call_opencode("k", "m", "grade this", 0)[0]
        low_args = seen[0][0]
        E.EFFORT, E.TIMEOUT = None, 1200
        with contextlib.redirect_stdout(buf):
            W.oc_call("write this")
        def_args = seen[-1][0]
    finally:
        subprocess.run = real
        E.L._HAS_O = None
    i = low_args.index("-c")
    return (bound is E and W.__dict__.get("G") is not None and good == "reply" and slow == "" and graded == "reply"
            and "[rd378g-writemore] call failed: RuntimeError luna call failed after 3 tries: timeout after 600s"
            in buf.getvalue()
            and low_args[1:4] == ["exec", "-m", "gpt-6-luna"] and low_args[i + 1] == 'model_reasoning_effort="low"'
            and "--output-last-message" in low_args and low_args[-1] == "-"
            and "-c" not in def_args and seen[-1][1] == 1200
            and [t for _a, t in seen[:4]] == [600, 600, 600, 600])


def main():
    if sys.argv[1:] == ["--check"]:
        ok = check()
        print("luna2 bound ok" if ok else "luna2 bound FAIL")
        sys.exit(0 if ok else 1)
    a = sys.argv[1:]
    assert a[0] == "--effort" and a[2] == "--timeout", "usage: --effort E --timeout S SCRIPT ARGS"
    E.EFFORT = None if a[1] == "default" else a[1]
    E.TIMEOUT = int(a[3])
    script = a[4]
    sys.argv = a[4:]
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
