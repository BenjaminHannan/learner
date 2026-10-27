#!/usr/bin/env python3
"""Fresh-patch arm for the equal-practice ruler: the patch net, never written.

Same parameters and random init as claude_patch_eq_plugin.Net under the harness's seed, but
WRITES is False: the Learner zeroes the patch, freezes writer, rank slots and gate, and makes
only the harness loop's ordinary updates. Run with --init fresh.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_patch_eq_plugin as P  # noqa: E402


class Net(P.Net):
    WRITES = False


Learner, train_loss = P.Learner, P.train_loss
tensors, ce_and_exact = P.tensors, P.ce_and_exact
TRAIN_ROUNDS, GRAD_ROUNDS = P.TRAIN_ROUNDS, P.GRAD_ROUNDS
