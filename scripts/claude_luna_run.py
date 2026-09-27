#!/usr/bin/env python3
"""Run a sealed script with GPT-6 Luna in place of GLM (Trustworthy notes thread, 2026-09-27).

Same idea as scripts/claude_glm_v11_run.py: bind the module name claude_glm_opencode, then run the named script
unchanged, so sealed wrappers (claude_rd378k_teacher3oc.py, claude_rd378g_writemore_oc.py) need no edit. Here the name
is bound to scripts/claude_luna_codex.py (the Director's Luna helper: call(text, model="gpt-6-luna", timeout=300)).
That helper RAISES after 3 failed tries (empty or error-like replies count as failures). Both wrappers already catch
any exception from OC.call, print their "call failed" line and use "" as the raw answer, so a Luna route failure is
counted as a route loss exactly as before; --check shows this.

python -B scripts/claude_luna_run.py SCRIPT.py ARGS...
python -B scripts/claude_luna_run.py --check   (no network: fakes the codex call; prints "luna bound ok")
"""
from __future__ import annotations

import contextlib
import io
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_luna_codex as L  # noqa: E402

sys.modules["claude_glm_opencode"] = L


def check():
    import claude_glm_opencode as bound
    import claude_rd378g_writemore_oc as W
    import claude_rd378k_teacher3oc as K
    seen = []

    def fake_once(text, model, timeout):
        seen.append((model, timeout))
        return (None, "error-like or empty reply") if "FAIL" in text else ("reply", "")
    real = L._once
    L._once = fake_once
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            good = (K.call_opencode("k", "m", "grade this", 0)[0], W.oc_call("write this"))
            bad = (K.call_opencode("k", "m", "FAIL", 0)[0], W.oc_call("FAIL"))
    finally:
        L._once = real
    log = buf.getvalue()
    return (bound is L and K.OC is L and good == ("reply", "reply") and bad == ("", "")
            and "[rd378k-teacher3oc] call failed: RuntimeError" in log
            and "[rd378g-writemore] call failed: RuntimeError" in log
            and len(seen) == 2 + 3 + 3 and all(m == "gpt-6-luna" and t == 300 for m, t in seen))


def main():
    if sys.argv[1:] == ["--check"]:
        ok = check()
        print("luna bound ok" if ok else "luna bound FAIL")
        sys.exit(0 if ok else 1)
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
