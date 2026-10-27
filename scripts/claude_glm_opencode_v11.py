#!/usr/bin/env python3
"""GLM 5.3 Flash via the Mac's opencode CLI (no API key needed).

v1.1 (2026-09-26): deletes exactly its own session; v1 sha 3b597086 leaked sessions.

Same interface as scripts/claude_glm_opencode.py: call(text, model=MODEL,
timeout=300) -> str, plus --selftest. Auth comes from the Mac's existing
opencode setup, which this script never reads or modifies.

Why v1 leaked: it listed and deleted sessions with cwd set to its private
temp dir, but opencode files new sessions under the enclosing git worktree
project, so its before/after diff was always empty.

Fix: every attempt passes --title with a unique per-attempt uuid tag, runs
in a private temp dir exactly like v1 (default output format, so the reply
text is identical to v1's: stdout stripped of ANSI chrome only), and
afterwards lists sessions with cwd set to the enclosing project directory,
finds exactly the session id(s) whose title equals the tag, and deletes
only those. Under parallel load from other processes no other caller's
session can match the uuid tag, so exactly the session this call created
is removed -- never a plain before/after diff.

Usage:
    from claude_glm_opencode_v11 import call
    text = call("Reply with the word ok")

    python3 scripts/claude_glm_opencode_v11.py --selftest
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

OPENCODE = "/usr/local/bin/opencode"
MODEL = "opencode-go/glm-5.3-flash"

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\r")


def _project_dir():
    """Directory under which opencode files this helper's sessions.

    Resolved from this file's location (scripts/ -> worktree root) so
    session list/delete run in the project where the sessions live,
    not in the call's private temp dir.
    """
    return str(Path(__file__).resolve().parent.parent)


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


def _ids_with_title(project_dir, title, limit=1000):
    """Return ids of sessions in project_dir whose title equals title."""
    code, out, _ = _run_opencode(
        ["session", "list", "-n", str(limit), "--format", "json"],
        cwd=project_dir, timeout=60)
    if code != 0:
        return set()
    try:
        items = json.loads(out or "[]")
    except (ValueError, TypeError):
        return set()
    if isinstance(items, dict):
        items = items.get("sessions", [])
    return {s.get("id") for s in items
            if isinstance(s, dict) and s.get("id")
            and s.get("title") == title}


def _delete_sessions(project_dir, ids):
    for sid in sorted(ids):
        try:
            _run_opencode(["session", "delete", sid], cwd=project_dir,
                          timeout=60)
        except Exception:
            pass


def _delete_own_session(project_dir, tag):
    """Delete exactly the session(s) carrying this call's unique tag."""
    try:
        _delete_sessions(project_dir, _ids_with_title(project_dir, tag))
    except Exception:
        pass


def call(text, model=MODEL, timeout=300):
    """Send one prompt to the model via opencode; return reply text.

    Retries up to 3 times on nonzero exit. Each attempt tags its session
    with a unique uuid title and afterwards deletes exactly that session
    id from the project where opencode filed it. Raises RuntimeError if
    all tries fail.
    """
    project_dir = _project_dir()
    last_err = ""
    for attempt in range(1, 4):
        tag = "glm11-%s" % uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix="glm-opencode-") as td:
            code, out, err = _run_opencode(
                ["run", "--model", model, "--title", tag, text], cwd=td,
                stdin_devnull=True, timeout=timeout)
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
                _delete_own_session(project_dir, tag)
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
