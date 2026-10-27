#!/usr/bin/env python3
"""GLM 5.3 Flash via the Mac's opencode CLI (no API key needed).

Prompt-in, text-out helper with the same shape as call() in
scripts/claude_lis320_glm.py, but with no key argument: auth comes from the
Mac's existing opencode setup, which this script never reads or modifies.

Each call runs one `opencode run` in a private temp dir with stdin /dev/null,
returns stdout stripped of opencode chrome, retries up to 3 times on nonzero
exit, and always deletes the session(s) it created afterwards.

Usage:
    from claude_glm_opencode import call
    text = call("Reply with the word ok")

    python3 scripts/claude_glm_opencode.py --selftest
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

OPENCODE = "/usr/local/bin/opencode"
MODEL = "opencode-go/glm-5.3-flash"

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\r")


def _strip_chrome(text: str) -> str:
    """Remove ANSI escapes / carriage returns and surrounding blank space."""
    return _ANSI.sub("", text or "").strip()


def _run_opencode(args, cwd, stdin_devnull=True, timeout=300):
    kw = {"cwd": cwd, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE,
          "timeout": timeout}
    if stdin_devnull:
        kw["stdin"] = subprocess.DEVNULL
    try:
        p = subprocess.run([OPENCODE] + args, **kw)
        return p.returncode, p.stdout.decode("utf-8", "replace"), \
            p.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode("utf-8", "replace") \
            if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = (e.stderr or b"").decode("utf-8", "replace") \
            if isinstance(e.stderr, bytes) else (e.stderr or "")
        return 124, out, "TIMEOUT after %ss: %s" % (timeout, err[:200])


def _session_ids(workdir):
    code, out, _ = _run_opencode(
        ["session", "list", "--format", "json"], cwd=workdir, timeout=60)
    if code != 0:
        return set()
    try:
        items = json.loads(out or "[]")
    except (ValueError, TypeError):
        return set()
    if isinstance(items, dict):
        items = items.get("sessions", [])
    return {s.get("id") for s in items
            if isinstance(s, dict) and s.get("id")}


def _delete_sessions(workdir, ids):
    for sid in sorted(ids):
        try:
            _run_opencode(["session", "delete", sid], cwd=workdir, timeout=60)
        except Exception:
            pass


def call(text, model=MODEL, timeout=300):
    """Send one prompt to the model via opencode; return reply text.

    Retries up to 3 times on nonzero exit. Always deletes sessions created
    along the way. Raises RuntimeError if all tries fail.
    """
    last_err = ""
    with tempfile.TemporaryDirectory(prefix="glm-opencode-") as td:
        for attempt in range(1, 4):
            before = _session_ids(td)
            code, out, err = _run_opencode(
                ["run", "--model", model, text], cwd=td, stdin_devnull=True,
                timeout=timeout)
            made = _session_ids(td) - before
            try:
                if code == 0:
                    reply = _strip_chrome(out)
                    if reply:
                        return reply
                    last_err = "empty reply (stderr: %s)" % _strip_chrome(err)[:200]
                else:
                    first = (_strip_chrome(err) or _strip_chrome(out)).split("\n")
                    last_err = "exit %s: %s" % (code, first[0][:200] if first else "")
            finally:
                _delete_sessions(td, made)
    raise RuntimeError("opencode call failed after 3 tries: %s" % last_err)


def selftest():
    reply = call("Reply with the word ok", timeout=300)
    assert "ok" in reply.lower(), "unexpected reply: %r" % reply[:200]
    print("selftest ok")


def main(argv):
    if "--selftest" in argv:
        return selftest()
    print(__doc__.strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
