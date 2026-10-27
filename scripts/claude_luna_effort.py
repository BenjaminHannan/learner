#!/usr/bin/env python3
"""GPT-6 Luna through the Director's Codex helper, with a chosen reasoning effort and time limit (Trustworthy notes
thread, 2026-09-27). New file; scripts/claude_luna_codex.py stays unchanged and supplies everything but the run line.

rd-378g's writer pilot (007-rd378g-writeluna) failed on time only: 9 of 9 Luna attempts at the helper's fixed 300 s
limit timed out while writing one practice batch (6 dialogs of about 12 turns, with notes). This module is the helper's
_once() and call() with two knobs set by the caller: TIMEOUT (seconds per attempt) and EFFORT (None keeps the Codex
default; otherwise "-c model_reasoning_effort=<EFFORT>" is added, Codex's documented config override). Same empty-temp-
dir, read-only sandbox, --skip-git-repo-check, --output-last-message, error-like-reply rule, 3 tries and raise as the
helper. Same interface as claude_glm_opencode.call(text) -> str.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_luna_codex as L  # noqa: E402

MODEL = L.MODEL
TIMEOUT = 300
EFFORT = None


def args_for(td, out_file, model, effort, extra=()):
    a = [L.CODEX, "exec", "-m", model, "-C", td, "--sandbox", "read-only", "--skip-git-repo-check"]
    if effort:
        a += ["-c", 'model_reasoning_effort="%s"' % effort]
    if L._supports_output_file():
        a += ["--output-last-message", out_file]
    return a + list(extra) + ["-"]


def _once(text, model, timeout, effort):
    with tempfile.TemporaryDirectory(prefix="luna-codex-") as td:
        out_file = os.path.join(td, ".last.txt")
        try:
            p = subprocess.run(args_for(td, out_file, model, effort), input=text.encode("utf-8"),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=td, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, "timeout after %ss" % timeout
        out = p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace")
        if p.returncode != 0:
            first = (L._strip_chrome(err) or L._strip_chrome(out)).split("\n")
            return None, "exit %s: %s" % (p.returncode, first[-1][:200] if first else "")
        reply = ""
        if os.path.exists(out_file):
            with open(out_file, encoding="utf-8", errors="replace") as f:
                reply = f.read().strip()
        if not reply:
            reply = L._strip_chrome(out)
        if L.looks_like_error(reply):
            return None, "error-like or empty reply: %r" % reply[:200]
        return reply, ""


def call(text, model=MODEL, timeout=None):
    last = ""
    for _ in range(3):
        reply, last = _once(text, model, timeout or TIMEOUT, EFFORT)
        if reply is not None:
            return reply
    raise RuntimeError("luna call failed after 3 tries: %s" % last)
