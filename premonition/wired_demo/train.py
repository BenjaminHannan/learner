"""Tiny training loop for the plumbing tests: teacher-forced steps, AdamW, checks that the LM never gets a gradient.

claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

import random
import torch

from .model import WiredModel, StepSpec, gold_steps, run_episode
from .notebook import Notebook
from . import tools


def fit(model: WiredModel, steps: list, updates: int, batch: int = 8, lr: float = 1e-3, seed: int = 0,
        wd: float = 0.01, optimizer=None, decay: bool = False):
    """Returns per-update losses. `steps` = list[StepSpec] with gold actions."""
    rng = random.Random(seed)
    torch.manual_seed(seed)
    model.train(); model.lm.eval()
    opt = optimizer or torch.optim.AdamW(model.trainable_parameters(), lr=lr, weight_decay=wd)
    by_len = sorted(steps, key=lambda s: len(s.question) + sum(map(len, s.notebook)))
    chunks = [by_len[i:i + batch] for i in range(0, len(by_len), batch)]
    losses, order = [], []
    base = [g['lr'] for g in opt.param_groups]
    for u in range(updates):
        if decay:   # linear decay to 10% of the base rate
            for g, b0 in zip(opt.param_groups, base): g['lr'] = b0 * (1 - 0.9 * u / max(1, updates - 1))
        if not order:
            order = list(range(len(chunks))); rng.shuffle(order)
        b = model.collate(chunks[order.pop()])
        loss = model.step_loss(b)
        opt.zero_grad(); loss.backward()
        if any(p.grad is not None for p in model.lm.parameters()):
            raise RuntimeError("frozen LM received a gradient")
        torch.nn.utils.clip_grad_norm_(model.trainable_parameters(), 1.0)
        opt.step(); losses.append(float(loss.detach()))
    return losses


def step_exact_match(model: WiredModel, steps: list) -> float:
    """Fraction of steps whose argmax action equals the gold action (teacher-forced inputs)."""
    model.eval()
    ok = 0
    for i in range(0, len(steps), 16):
        chunk = steps[i:i + 16]
        acts, _ = model.decode(model.collate(chunk))
        ok += sum(a == s.gold for a, s in zip(acts, chunk))
    return ok / len(steps)


def episode_correct(model: WiredModel, episode) -> bool:
    r = run_episode(model, episode.question, Notebook.from_facts(list(episode.notebook)), say=False)
    return r.status == "ANSWER" and r.value == episode.key
