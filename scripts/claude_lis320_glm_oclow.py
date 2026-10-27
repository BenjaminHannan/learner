#!/usr/bin/env python3
"""lis-320 GLM wording through Ben's opencode route with reasoning effort "low" (reading thread, 2026-09-26;
ADDENDUM-6). New file; claude_lis320_glm_oc.py, claude_lis320_glm_oc11.py and the Director's helpers stay unchanged.

The Director's helper v1.1 (scripts/claude_glm_opencode_v11.py, sha 7a067cfb...) cannot pass a flag, so call_low() is
its call() with one addition: "--variant low" on the `opencode run` line (opencode's per-model variant; for
opencode-go/glm-5.3-flash, low = reasoningEffort low, per `opencode models --verbose opencode-go` in ocdiag3). Everything
else is v1.1's own code, used through its functions: per-attempt uuid --title tag, private temp dir, stdin /dev/null,
3 tries on nonzero exit (a 300 s timeout exits 124 and is retried), ANSI chrome stripped, and exactly its own session
deleted from the project where opencode filed it. Prompt, parser, batching, time cap, failed-call stop and output rows
are claude_lis320_glm_oc's; rows record model "opencode-go/glm-5.3-flash" and temperature null, as before.
Same flags as claude_lis320_glm_oc.py.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_glm_opencode_v11 as H  # noqa: E402
import claude_lis320_glm_oc as B  # noqa: E402

VARIANT = "low"
_LOCK = threading.Lock()


def call_low(text, model=H.MODEL, timeout=300):
    project_dir = H._project_dir()
    last_err = ""
    for _attempt in range(1, 4):
        tag = "glm11-%s" % uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix="glm-opencode-") as td:
            code, out, err = H._run_opencode(
                ["run", "--model", model, "--variant", VARIANT, "--title", tag, text], cwd=td,
                stdin_devnull=True, timeout=timeout)
            try:
                if code == 0:
                    reply = H._strip_chrome(out)
                    if reply:
                        return reply
                    last_err = "empty reply (stderr: %s)" % H._strip_chrome(err)[:200]
                else:
                    first = (H._strip_chrome(err) or H._strip_chrome(out)).split("\n")
                    last_err = "exit %s: %s" % (code, first[0][:200] if first else "")
            finally:
                H._delete_own_session(project_dir, tag)
    raise RuntimeError("opencode call failed after 3 tries: %s" % last_err)


def call_opencode_low(text):
    try:
        out = call_low(text, model=B.MODEL) or ""
    except Exception as e:                            # a failed call is logged and counted, never guessed
        print(f"[glm320oclow] call failed: {type(e).__name__} {str(e)[:120]}", flush=True)
        out = ""
    if not out:
        with _LOCK:
            B.FAILED["n"] += 1
    return out, {}


def selftest():
    seen = []

    def fake_run(args, cwd, stdin_devnull=True, timeout=300):
        seen.append(list(args))
        return (0, "\x1b[0m{\"turns\": []}\n", "") if args[0] == "run" else (0, "[]", "")
    real = H._run_opencode
    H._run_opencode = fake_run
    try:
        assert call_low("hello") == "{\"turns\": []}"
    finally:
        H._run_opencode = real
    a = seen[0]
    assert a[:5] == ["run", "--model", "opencode-go/glm-5.3-flash", "--variant", "low"] and a[5] == "--title" \
        and a[6].startswith("glm11-") and a[7] == "hello", a
    assert B.MODEL == "opencode-go/glm-5.3-flash"
    B.call_opencode = call_opencode_low
    B.selftest()
    print("lis320 glm_oclow selftest ok (variant low on the run line; no network)")


if __name__ == "__main__":
    B.call_opencode = call_opencode_low
    if "--selftest" in sys.argv:
        selftest()
    else:
        sys.exit(B.main())
