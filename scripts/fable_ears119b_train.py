#!/usr/bin/env python3
"""Exp 119b — seed-namespace shim over the 119 trainer (Muse PREP).

fable_ears119_train.py hardcodes SEEDS119 = (11901, 11902, 11903) and asserts
membership, but the 119b wave renames the seeds to 11911-11913 (PASSMARKS §1:
same recipe, same scorer, renamed ids). This shim patches ONLY the seed tuple
and delegates to the 119 trainer's main(), so recipe asserts (2 epochs, batch
32, lr 3e-5, freeze 0, CUDA), pool loading, shuffle-by-seed, CAL temperatures,
and checkpoint layout are 119 verbatim. Called by fable_ears119b_wave.bat.

Reading94 is never touched here (trainer sees only the remapped pool file +
sealed 47 CAL).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears119_train as T119  # noqa: E402  (119 recipe, read-only)

# THE ONLY DIFFERENCE vs calling fable_ears119_train.py directly.
SEEDS119B = (11911, 11912, 11913)
T119.SEEDS119 = SEEDS119B

if __name__ == "__main__":
    T119.main()
