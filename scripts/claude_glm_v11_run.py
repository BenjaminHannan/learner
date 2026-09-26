#!/usr/bin/env python3
"""Run a sealed script with the Director's opencode helper v1.1 in place of v1 (Trustworthy notes thread, 2026-09-26).

v1 (scripts/claude_glm_opencode.py, sha256 3b597086...) leaks one opencode session per call: its cleanup diff is always
empty because opencode files sessions under the enclosing worktree (builder-outbox cd1bf6977). v1.1
(scripts/claude_glm_opencode_v11.py) tags each call's session and deletes exactly that one; same call() interface, same
reply text. This launcher binds the module name claude_glm_opencode to v1.1, then runs the named script unchanged, so
sealed wrappers (claude_rd378k_teacher3oc.py, claude_rd378g_writemore_oc.py) need no edit.

python -B scripts/claude_glm_v11_run.py SCRIPT.py ARGS...
python -B scripts/claude_glm_v11_run.py --check      (no network: prints "glm v11 bound ok" when the swap holds)
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_glm_opencode_v11 as V11  # noqa: E402

sys.modules["claude_glm_opencode"] = V11


def main():
    if sys.argv[1:] == ["--check"]:
        import claude_glm_opencode as bound
        ok = bound is V11 and Path(bound.__file__).name == "claude_glm_opencode_v11.py"
        print("glm v11 bound ok" if ok else "glm v11 bound FAIL")
        sys.exit(0 if ok else 1)
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
