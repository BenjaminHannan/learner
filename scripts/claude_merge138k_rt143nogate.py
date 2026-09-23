#!/usr/bin/env python3
"""Merge 138k K3 driver: the verifier's rt143 no-gate run, pointed at 138k.

Runs artifacts/claude-verify-20260922/138j/rt143_nogate.py UNCHANGED (via
runpy) with arm "138j" and guard 1, after substituting, in this process
only, a shim module for fable_loop138j_agent whose Loop138jDaemon /
DEFAULT_CONFIG138J are loop138k's. The verifier file is never edited.

usage: claude_merge138k_rt143nogate.py <prefix none|rt136> <out.json>
"""
from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_loop138k_agent as K  # noqa: E402 (imports the real 138j first)

shim = types.ModuleType("fable_loop138j_agent")
shim.Loop138jDaemon = K.Loop138kDaemon
shim.DEFAULT_CONFIG138J = K.DEFAULT_CONFIG138K
sys.modules["fable_loop138j_agent"] = shim

prefix, out = sys.argv[1], sys.argv[2]
target = ROOT / "artifacts/claude-verify-20260922/138j/rt143_nogate.py"
sys.argv = [str(target), "138j", "1", prefix, out]
runpy.run_path(str(target), run_name="__main__")
