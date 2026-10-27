#!/usr/bin/env python3
"""Constant-g damping control for the H3 settle gate (ADDENDUM-1 (e), helper H10, 2026-09-28).

The same plug-in as scripts/claude_dir_h3_net_v2.py with ONE flag set: Net.CONST_G = 0.9. So a round is
h_new = h + 0.9 * (prop - h) with prop = LN(blocks(h + e)), for every cell and every round; there are no gate tensors (stored weights
equal the loop's 1,645,726), nothing is learned about the gate, and everything else (practice recipe, learner, sleep, ladder) is
the loop's. It answers one question: is a gain from H3 just plain under-relaxation of the loop's update? Use it like any plug-in:

  --plugin claude_dir_h3_net_v2_const            (practice: scripts/claude_dir_h3_practice_v2.py --plugin claude_dir_h3_net_v2_const;  ladder: harness adapt / holdout)

NOT EXECUTED where it was written (no torch); scripts/claude_dir_h3_selftest_v2.py checks it first.
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h3_net_v2 as V  # noqa: E402

CONST_G = 0.9

ARMS, TRAIN_ROUNDS, GRAD_ROUNDS = V.ARMS, V.TRAIN_ROUNDS, V.GRAD_ROUNDS
LR, WD, WARMUP = V.LR, V.WD, V.WARMUP
tensors, ce_and_exact, train_loss = V.tensors, V.ce_and_exact, V.train_loss
Learner = V.Learner


class Net(V.Net):
    CONST_G = 0.9


class Practice(V.Practice):
    NET = Net


def load_net(path):
    d = torch.load(path, map_location="cpu")
    net = Net(d["arm"])
    net.load_state_dict(d["state"])
    return net


def describe():
    return V.describe(Net)
