#!/usr/bin/env python3
"""GPT-6 Luna via the Mac's bundled Codex CLI (Ben's Codex plan; no key handled).

New helper (Director, 2026-09-27). Ben 03:25:33 UTC "you can use unlimited luna",
03:47:24 card "Allow Luna", 03:47:41 "just have luna rewrite all the training
data". Model id gpt-6-luna answered "ok" in probe 000-probe-codex2 (03:37 UTC).

Same interface as scripts/claude_glm_opencode_v11.py: call(text, model=MODEL,
timeout=300) -> str, plus --selftest. Each attempt runs
  codex exec -m gpt-6-luna -C <empty temp dir> --sandbox read-only
             --skip-git-repo-check [-o <file>] -
with the prompt on stdin, in a fresh empty temp dir, so the agent can read
nothing of the project and write nothing anywhere. This script never reads
or prints anything under ~/.codex.

Differences from the GLM helper, on purpose:
- An empty reply, or a short reply that looks like an error / limit / login
  message, is a FAILURE (retried, then RuntimeError), never returned as a row.
  (The GLM v1.1 helper returns stdout whenever exit is 0; see the 09-27
  route-loss finding.)
- The reply is the agent's last message: read from the -o file when this
  codex supports --output-last-message, else stdout stripped of ANSI chrome.

Usage:
    from claude_luna_codex import call
    text = call("Reply with the word ok")

    python3 scripts/claude_luna_codex.py --selftest
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

CODEX = os.environ.get(
    "LUNA_CODEX_BIN",
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex")
MODEL = "gpt-6-luna"

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\r")
# A reply this short that matches is treated as a route failure, not text.
_ERRLIKE = re.compile(
    r"usage limit|rate limit|quota|insufficient|unauthori[sz]ed|not logged in|"
    r"please log ?in|authentication|error:|exceeded|temporarily unavailable|"
    r"model .{0,40}not (found|supported|available)|stream disconnected",
    re.I)
_ERR_MAXLEN = 400

_HAS_O = None


def _strip_chrome(text: str) -> str:
    return _ANSI.sub("", text or "").strip()


def _supports_output_file() -> bool:
    global _HAS_O
    if _HAS_O is None:
        try:
            p = subprocess.run([CODEX, "exec", "--help"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               timeout=60)
            _HAS_O = b"--output-last-message" in p.stdout
        except Exception:
            _HAS_O = False
    return _HAS_O


def looks_like_error(reply: str) -> bool:
    r = (reply or "").strip()
    return (not r) or (len(r) <= _ERR_MAXLEN and bool(_ERRLIKE.search(r)))


def _once(text, model, timeout):
    with tempfile.TemporaryDirectory(prefix="luna-codex-") as td:
        out_file = os.path.join(td, ".last.txt")
        args = [CODEX, "exec", "-m", model, "-C", td, "--sandbox", "read-only",
                "--skip-git-repo-check"]
        if _supports_output_file():
            args += ["--output-last-message", out_file]
        args.append("-")
        try:
            p = subprocess.run(args, input=text.encode("utf-8"),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=td, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, "timeout after %ss" % timeout
        out = p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace")
        if p.returncode != 0:
            first = (_strip_chrome(err) or _strip_chrome(out)).split("\n")
            return None, "exit %s: %s" % (p.returncode, first[-1][:200] if first else "")
        reply = ""
        if os.path.exists(out_file):
            with open(out_file, encoding="utf-8", errors="replace") as f:
                reply = f.read().strip()
        if not reply:
            reply = _strip_chrome(out)
        if looks_like_error(reply):
            return None, "error-like or empty reply: %r" % reply[:200]
        return reply, ""


def call(text, model=MODEL, timeout=300):
    """Send one prompt to Luna; return the reply text.

    Up to 3 tries. Empty or error-like replies count as failures.
    Raises RuntimeError if all tries fail.
    """
    last = ""
    for _ in range(3):
        reply, last = _once(text, model, timeout)
        if reply is not None:
            return reply
    raise RuntimeError("luna call failed after 3 tries: %s" % last)


def selftest():
    assert looks_like_error("") and looks_like_error("Error: usage limit exceeded")
    assert not looks_like_error("ok")
    assert not looks_like_error("x" * 500 + " rate limit")
    reply = call("Reply with exactly the word ok and nothing else.", timeout=180)
    assert "ok" in reply.lower(), "unexpected reply: %r" % reply[:200]
    print("selftest ok: model %s, output-file %s" % (MODEL, _supports_output_file()))


def main(argv):
    if "--selftest" in argv:
        return selftest()
    print(__doc__.strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
