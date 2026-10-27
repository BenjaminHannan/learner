#!/usr/bin/env python3
"""Writes-off arm for the equal-practice ruler (ADDENDUM-2 fix P2): the PRACTISED patch net, never written.

Same class setting as claude_patch_eq_fresh (Net.WRITES = False: patch zeroed, writer, rank slots and
gate frozen, only the harness loop's ordinary updates), but run with --init pre so it starts from the
practised patch net's source.pt. Comparing the patch with this arm separates "the writes helped" from
"the practised patch net is a better start".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_patch_eq_fresh as Fr  # noqa: E402

Net, Learner, train_loss = Fr.Net, Fr.Learner, Fr.train_loss
tensors, ce_and_exact = Fr.tensors, Fr.ce_and_exact
TRAIN_ROUNDS, GRAD_ROUNDS = Fr.TRAIN_ROUNDS, Fr.GRAD_ROUNDS
