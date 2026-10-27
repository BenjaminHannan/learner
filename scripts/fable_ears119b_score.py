#!/usr/bin/env python3
"""Exp 119b — seed-namespace shim over the 119 scorer (Muse PREP).

fable_ears119_score.py hardcodes SEEDS119 = (11901, 11902, 11903) for run-dir
lookup (w-<seed>), tau dict keys, and the W3 bars. The 119b wave trains seeds
11911-11913 with the positional W3 bars renamed per PASSMARKS §2 (11911>=27,
11912>=33, 11913>=30, i.e. 3x exp-107's 9/11/10). This shim patches ONLY the
seed tuple (+ the renamed W3 bars) and delegates to the 119 scorer's main(),
so gate definitions, tau rule, verdicts, and the 106 normaliser are 119
verbatim. Called by fable_ears119b_wave.bat.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119_score as S119  # noqa: E402  (119 scorer, read-only)

# THE ONLY DIFFERENCE vs calling fable_ears119_score.py directly.
S119.SEEDS119 = (11911, 11912, 11913)
S119.W3_BAR = {11911: 27, 11912: 33, 11913: 30}  # PASSMARKS §2, positional

if __name__ == "__main__":
    S119.main()
