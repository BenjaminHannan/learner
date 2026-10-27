#!/usr/bin/env python3
"""Clip-on patch plug-in for the equal-practice ruler (scripts/claude_fewex_eq_bench.py).

Design: artifacts/claude-patch-eq-20260928/DESIGN.md. The net is the sealed patch core
(scripts/claude_patch_net.py, arm 'patch': rank 8, writer, gate, bounds) with its persistent
A/B patch held in two buffers, so every harness checkpoint carries the patch. The harness
only knows arms 'loop' and 'plain'; this net answers to 'loop'.

Learner (the practised patch): every maze batch is first written into the patch (one write
per batch), then gets the harness loop's own four ordinary updates. A rung is 512 writes and
2,048 updates. Sleep is the harness's 512-update sleep with the patch held fixed; the patch
is zeroed after update 512. The fresh-patch arm uses scripts/claude_patch_eq_fresh.py, which
sets Net.WRITES = False: no write ever, patch stays zero, writer/rank slots/gate frozen.

Learner objects are identified by nothing but their creation order; nothing here knows a
puzzle kind. fp32, no autocast.
"""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import torch
from torch.nn import functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fewex_net as FN  # noqa: E402  (the ruler's tensors / ce_and_exact / round counts)
import claude_patch_net as C  # noqa: E402  (the sealed patch core)

TRAIN_ROUNDS, GRAD_ROUNDS, MAX_ROUNDS = FN.TRAIN_ROUNDS, FN.GRAD_ROUNDS, 48
UPDATES, SLEEP_STEPS = 4, 512
WRITER_PARTS = ("writer.", "rank_slot.", "gate.")
tensors = FN.tensors
ce_and_exact = FN.ce_and_exact


class Net(C.Net):
    WRITES = True  # a class setting, never stored: the fresh arm's module subclasses it

    def __init__(self, arm="loop"):
        if arm != "loop":
            raise ValueError("the patch plug-in has only the recurrent arm ('loop')")
        super().__init__("patch")
        self.arm = "loop"
        self.register_buffer("patch_a", torch.zeros(1, C.RANK, C.WIDTH))
        self.register_buffer("patch_b", torch.zeros(1, C.WIDTH, C.RANK))

    # ----- the patch -----
    def stored_patch(self):
        return C.PatchState(self.patch_a, self.patch_b)

    @torch.no_grad()
    def store_patch(self, patch):
        a, b = patch.A.detach(), patch.B.detach()
        if a.shape != self.patch_a.shape or b.shape != self.patch_b.shape:
            raise ValueError("the persistent patch has batch size one")
        if bool((a.abs() > C.SLOT_LIMIT + 1e-6).any()) or bool((b.abs() > C.SLOT_LIMIT + 1e-6).any()):
            raise ValueError("patch outside the sealed factor bound")
        self.patch_a.copy_(a)
        self.patch_b.copy_(b)

    @torch.no_grad()
    def remove_patch(self):
        self.patch_a.zero_()
        self.patch_b.zero_()

    def weight_count(self):
        """Every stored number: parameters plus the 4,096 A/B coefficients."""
        return sum(p.numel() for p in self.parameters()) + self.patch_a.numel() + self.patch_b.numel()

    # ----- the recurrent core (claude_patch_net.Net.step, patch taken from the buffers) -----
    def step(self, h, e, dr, dc, patch=None):
        if patch is None:
            patch = self.stored_patch()
        z = h + e
        for block in self.blocks:
            z = block(z, dr, dc)
        z = self.ln_state(z)
        low = torch.einsum("btd,brd->btr", h, patch.A.expand(h.shape[0], -1, -1))
        delta = torch.einsum("btr,bdr->btd", low, patch.B.expand(h.shape[0], -1, -1))
        applicability = torch.sigmoid(self.gate(torch.cat((e, h), dim=-1)))
        return z + C.PATCH_EFFECT * applicability * delta

    def loop_train(self, tokens, slot, n_free, n_grad, patch=None):
        return self._run_train(tokens, slot, n_free, n_grad, patch)[0]

    def forward(self, tokens, positions):
        """Harness API: 48 cell-logit and 48 stop-logit tensors, stored patch."""
        e, (dr, dc) = self.embed(tokens, positions)
        h = torch.zeros_like(e)
        cells, stops = [], []
        for _ in range(MAX_ROUNDS):
            h = self.step(h, e, dr, dc)
            cell, stop = self.read(h)
            cells.append(cell)
            stops.append(stop)
        return cells, stops

    @torch.no_grad()
    def infer_rounds(self, tokens, positions, n=MAX_ROUNDS):
        return C.Net.loop_rounds(self, tokens, positions, n, None)

    # ----- writing (claude_patch_net.Net.write_support's formula, arm check removed) -----
    def proposals(self, h, logits, slot, target):
        """Per-puzzle (A rows, B columns) proposals from correct-minus-predicted feedback."""
        batch, length, vocab = logits.shape
        mask = slot.reshape(batch, length).bool()
        safe = torch.where(mask, target.reshape(batch, length), 0).long()
        correction = (F.one_hot(safe, vocab).to(logits.dtype) - logits.float().softmax(-1)) * mask.unsqueeze(-1)
        denominator = mask.sum(1, keepdim=True).clamp_min(1)
        activity = (self.ln_out(h) * mask.unsqueeze(-1)).sum(1) / denominator
        feedback = (correction @ self.head.weight).sum(1) / denominator
        context = activity[:, None, :] + self.rank_slot.weight[None, :, :]
        features = torch.cat((context, feedback[:, None, :].expand(-1, C.RANK, -1)), -1)
        proposal = torch.tanh(self.writer(features)) * C.SLOT_LIMIT
        a, b_rows = proposal.split(C.WIDTH, -1)
        return a, b_rows.transpose(1, 2)

    @staticmethod
    def blend(patch, a, b):
        return C.PatchState((C.RHO * patch.A + (1 - C.RHO) * a).clamp(-C.SLOT_LIMIT, C.SLOT_LIMIT),
                            (C.RHO * patch.B + (1 - C.RHO) * b).clamp(-C.SLOT_LIMIT, C.SLOT_LIMIT))

    def write_support(self, tokens, slot, target, patch, n_free, n_grad):
        """Sealed practice write (claude_patch_net.Net.write_support), differentiable."""
        outputs, h = self._run_train(tokens, slot, n_free, n_grad, patch)
        a, b = self.proposals(h, outputs[-1][0], slot, target)
        return self.blend(patch, a, b)

    @torch.no_grad()
    def own_halt_states(self, tokens, slot, patch=None):
        """Each puzzle's own learned-stop round (from round 3, cap 48): state, logits, round."""
        e, (dr, dc) = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        n = tokens.shape[0]
        done = torch.zeros(n, dtype=torch.bool)
        rounds = torch.full((n,), MAX_ROUNDS, dtype=torch.long)
        keep_h, keep_lg, history = None, None, []
        for r in range(1, MAX_ROUNDS + 1):
            h = self.step(h, e, dr, dc, patch)
            lg, q = self.read(h)
            pred = lg.argmax(-1)
            history = (history + [pred])[-3:]
            if keep_h is None:
                keep_h, keep_lg = h.clone(), lg.clone()
            stop = torch.zeros(n, dtype=torch.bool)
            if r >= 3:
                same = (history[0] == history[1]).all(1) & (history[1] == history[2]).all(1)
                stop = (torch.sigmoid(q.float()) > .5) & same
            take = (~done) & (stop | (r == MAX_ROUNDS))
            keep_h[take], keep_lg[take] = h[take], lg[take]
            rounds[take] = r
            done |= take
            if bool(done.all()):
                break
        return keep_h, keep_lg, rounds

    @torch.no_grad()
    def write_batch(self, items):
        """One write per batch: the mean of the batch's per-puzzle proposals, blended once."""
        t, s, y = tensors(items)
        h, lg, rounds = self.own_halt_states(t, s)
        a, b = self.proposals(h, lg, s, y)
        self.store_patch(self.blend(self.stored_patch(), a.mean(0, keepdim=True), b.mean(0, keepdim=True)))
        return int(rounds.sum())


def train_loss(net, items, round_rng):
    """V2 loss. Practised patch: two supports written differentiably (own-halt depth, last
    1..6 rounds with gradient), then the loop loss on the remaining, different queries with
    the written patch. Fresh patch (Net.WRITES False): the ordinary loop loss."""
    patch = C.PatchState(net.patch_a.detach().clone(), net.patch_b.detach().clone())
    if net.WRITES:
        for item in items[:2]:
            t, s, y = tensors([item])
            _, _, rounds = net.own_halt_states(t, s, patch)
            depth = int(rounds[0])
            grad = min(depth, GRAD_ROUNDS)
            patch = net.write_support(t, s, y, patch, depth - grad, grad)
        items = items[2:]
    t, s, y = tensors(items)
    total = round_rng.randint(1, TRAIN_ROUNDS)
    k = round_rng.randint(1, min(total, GRAD_ROUNDS))
    ces, hls = [], []
    for lg, q in net.loop_train(t, s, total - k, k, patch):
        c_, ex = ce_and_exact(lg, s, y)
        ces.append(c_)
        hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
    return torch.stack(ces).mean() + 0.5 * torch.stack(hls).mean()


class Learner:
    """The harness learner (claude_fewex_bench.Learner) plus one write before each batch."""

    def __init__(self, net, lr):
        self.net = net
        self.writes = 0
        self.write_rounds = 0
        self.write_seconds = 0.0
        if not net.WRITES:
            net.remove_patch()
            for name, p in net.named_parameters():
                if name.startswith(WRITER_PARTS):
                    p.requires_grad_(False)
        self.opt = torch.optim.AdamW([p for p in net.parameters() if p.requires_grad],
                                     lr=lr, weight_decay=.1, betas=(.9, .95))
        self.sched = torch.optim.lr_scheduler.LambdaLR(self.opt, lambda i: min(1., (i + 1) / 50))
        self.steps = 0

    def update(self, loss):
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.)
        self.opt.step()
        self.sched.step()
        self.steps += 1

    def maze_batch(self, items):
        self.net.train()
        if self.net.WRITES:
            t0 = time.monotonic()
            self.write_rounds += self.net.write_batch(items)
            self.writes += 1
            self.write_seconds += time.monotonic() - t0
        t, s, y = tensors(items)
        h = None
        for _ in range(UPDATES):
            e, (dr, dc) = self.net.embed(t, s)
            if h is None:
                h = torch.zeros_like(e)
            with torch.no_grad():
                for _ in range(3):
                    h = self.net.step(h, e.detach(), dr, dc)
            h = h.detach()
            ces = []
            for _ in range(2):
                h = self.net.step(h, e, dr, dc)
                ces.append(ce_and_exact(self.net.read(h)[0], s, y)[0])
            self.update(torch.stack(ces).mean())  # no maze stop-head loss
            h = h.detach()

    def sleep(self, mazes, seed, old):
        """The harness sleep, unchanged, with the patch fixed; the patch is removed after it."""
        rng = random.Random(9262700 + seed)
        round_rng = random.Random(9282700 + seed)
        t0 = time.monotonic()
        for _ in range(SLEEP_STEPS):
            old_a = rng.sample(old["sums4"], 4)
            old_b = rng.sample(old["grids5"], 4)
            new = rng.choices(mazes, k=8)
            losses = []
            for items in (old_a, old_b, new):
                t, s, y = tensors(items)
                rr = round_rng.randint(1, TRAIN_ROUNDS)
                grad = round_rng.randint(1, min(rr, GRAD_ROUNDS))
                losses.append(torch.stack([ce_and_exact(lg, s, y)[0]
                                           for lg, _ in self.net.loop_train(t, s, rr - grad, grad)]).mean())
            self.update(.25 * losses[0] + .25 * losses[1] + .5 * losses[2])
        self.net.remove_patch()
        return time.monotonic() - t0
