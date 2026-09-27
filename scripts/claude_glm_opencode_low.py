#!/usr/bin/env python3
"""GLM 5.3 Flash through Ben's opencode route at reasoning effort "low" (Trustworthy notes thread, 2026-09-27).
New file; the Director's helpers and the reading thread's files stay unchanged.

call() here is the reading thread's call_low (scripts/claude_lis320_glm_oclow.py, used by lis-320 pilot 4): the
Director's helper v1.1 call() (scripts/claude_glm_opencode_v11.py) with one addition, "--variant low" on the
`opencode run` line (opencode's variant for opencode-go/glm-5.3-flash, low = reasoningEffort low). ocdiag3 (a5a07655c):
4 of 4 replies parsed in 5-15 s with 0-9 reasoning tokens, against 88 s up to a 300 s timeout at the default effort on
the same prompts. Everything else is v1.1's: per-attempt uuid --title tag, private temp dir, stdin /dev/null, 3 tries,
own-session cleanup. Same interface as claude_glm_opencode.call(text, model=MODEL, timeout=300) -> str.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_glm_opencode_v11 as H  # noqa: E402
from claude_lis320_glm_oclow import VARIANT, call_low  # noqa: E402

MODEL = H.MODEL


def call(text, model=MODEL, timeout=300):
    return call_low(text, model=model, timeout=timeout)
