#!/usr/bin/env python3
"""Control for the history-read plug-in: identical extra weights and compute, WINDOW = 1 (sees only the previous state, no history).
See scripts/claude_dir_hist_net.py and artifacts/claude-dir-hist-20260929/DESIGN.md. Not executed where written (no torch)."""
from __future__ import annotations

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_hist_net as V  # noqa: E402

ARMS, TRAIN_ROUNDS, GRAD_ROUNDS = V.ARMS, V.TRAIN_ROUNDS, V.GRAD_ROUNDS
LR, WD, WARMUP = V.LR, V.WD, V.WARMUP
tensors, ce_and_exact, train_loss = V.tensors, V.ce_and_exact, V.train_loss


class Net(V.Net):
    WINDOW = 1


class Practice(V.Practice):
    NET = Net


def load_net(path):
    d = torch.load(path, map_location="cpu")
    net = Net(d["arm"])
    net.load_state_dict(d["state"])
    return net
