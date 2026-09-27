#!/usr/bin/env python3
"""Run a sealed script with GLM called at opencode reasoning effort "low" (Trustworthy notes thread, 2026-09-27).

Same idea as scripts/claude_glm_v11_run.py: bind the module name claude_glm_opencode, then run the named script
unchanged, so sealed wrappers (claude_rd378k_teacher3oc.py, claude_rd378g_writemore_oc.py) need no edit. Here the name
is bound to scripts/claude_glm_opencode_low.py (helper v1.1 plus "--variant low"; see its docstring).

python -B scripts/claude_glm_low_run.py SCRIPT.py ARGS...
python -B scripts/claude_glm_low_run.py --check   (no network: a fake opencode shows the bound call puts
                                                   "--variant low" on the run line; prints "glm low bound ok")
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_glm_opencode_low as LOW  # noqa: E402

sys.modules["claude_glm_opencode"] = LOW


def check():
    import claude_glm_opencode as bound
    seen = []

    def fake_run(args, cwd, stdin_devnull=True, timeout=300):
        seen.append(list(args))
        return (0, "\x1b[0mok\n", "") if args[0] == "run" else (0, "[]", "")
    real = LOW.H._run_opencode
    LOW.H._run_opencode = fake_run
    try:
        reply = bound.call("hello")
    finally:
        LOW.H._run_opencode = real
    a = seen[0] if seen else []
    return (bound is LOW and Path(bound.__file__).name == "claude_glm_opencode_low.py" and reply == "ok"
            and a[:5] == ["run", "--model", "opencode-go/glm-5.3-flash", "--variant", "low"]
            and a[5] == "--title" and a[6].startswith("glm11-") and a[7] == "hello"
            and any(x[:2] == ["session", "list"] for x in seen[1:]))


def main():
    if sys.argv[1:] == ["--check"]:
        ok = check()
        print("glm low bound ok" if ok else "glm low bound FAIL")
        sys.exit(0 if ok else 1)
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
