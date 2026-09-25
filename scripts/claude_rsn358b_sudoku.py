#!/usr/bin/env python3
"""rsn-358b: the 358 loop reasoner on Sudoku-Extreme under bm-394s rules (sleep research thread, 2026-09-25).

Plan: design/v3/30-modes/358b-sudoku-extreme-plan.md. Test and pass marks belong to the benchmarks thread
(artifacts/claude-bm394-20260925/PLAN-sudoku.md; harness scripts/claude_bm394_grid.py). Rules kept here:
  - practice = the harness's 1,000 practice puzzles only, with the published rule-keeping shuffles (relabel digits,
    rows within a band, bands, columns within a stack, stacks, transpose); nothing else;
  - one try per test puzzle: the net's own rounds and learned stop only; no search, solver, retries or voting.

Net: 358a's loop (2 attention layers, width 512, puzzle re-added every round, a stop head; attention knows only the
row/column offset between two cells) plus one more thing it needs to read Sudoku: a learned bias for "same 3x3 box".
Training follows the TRM recipe's outline (arXiv 2510.04871): batch slots that keep their thinking state across up
to 16 supervision steps, each step = 14 rounds without gradient then 7 with; a slot is replaced by a new shuffled
puzzle when its stop head says done (after >= 2 steps) or after 16 steps; AdamW (0.9, 0.95), lr 1e-4, weight decay
1.0, 2,000 warm-up steps, EMA 0.999 of the weights (the EMA copy is what is saved and tested). Differences from TRM,
stated: one thinking state instead of TRM's two (z and y), plain cross-entropy instead of stable-max, and the
steps budget is set per run (the published run is ~78,000 steps; a shorter run is labelled with its fraction).
The plain twin: 8 layers, width 256, one pass per puzzle, same data, optimiser, steps and EMA.

  python -B scripts/claude_rsn358b_sudoku.py train --arm loop|plain --data DIR --seed 1 --out W/loop-s1 [--steps N]
  RSN358B_CKPT=W/loop-s1/ema.pt python -B scripts/claude_bm394_grid.py run --task sudoku \
      --arm py:claude_rsn358b_sudoku:solve --name loop-s1 --data DIR --out RUNS     (the benchmarks thread runs this)
  python -B scripts/claude_rsn358b_sudoku.py smoke
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

CLIP = 4
V = 11                    # 0 unused, 1 blank, 2..10 digit symbols (relabelled every shuffle)
ARMS = {"plain": dict(d=256, layers=8, heads=8), "loop": dict(d=512, layers=2, heads=8)}
N_FREE, N_GRAD, N_SUP = 14, 7, 16


# ---------------- data ----------------
def load_practice(data):
    rows = [json.loads(l) for l in (Path(data) / "sudoku_practice.jsonl").read_text().splitlines() if l.strip()]
    assert len(rows) <= 1000, "bm-394s: at most 1,000 practice puzzles"
    return [(r["puzzle"], r["answer"]) for r in rows]


def encode(puzzle):
    return [1 if ch in ".0" else 1 + int(ch) for ch in puzzle]


def shuffle(rng, puz, ans):
    """the published rule-keeping shuffles: digits, rows in bands, bands, cols in stacks, stacks, transpose."""
    digits = list(range(1, 10))
    rng.shuffle(digits)
    relabel = {str(i + 1): str(d) for i, d in enumerate(digits)}
    bands = rng.sample(range(3), 3)
    rows = [b * 3 + r for b in bands for r in rng.sample(range(3), 3)]
    stacks = rng.sample(range(3), 3)
    cols = [s * 3 + c for s in stacks for c in rng.sample(range(3), 3)]
    tr = rng.random() < 0.5

    def f(g):
        moved = [[g[rows[r] * 9 + cols[c]] for c in range(9)] for r in range(9)]
        if tr:
            moved = [list(col) for col in zip(*moved)]
        return "".join(relabel.get(ch, ch) for row in moved for ch in row)
    return f(puz), f(ans)


def valid_solution(puz, ans):
    if any(p not in ".0" and p != a for p, a in zip(puz, ans)):
        return False
    units = [[r * 9 + c for c in range(9)] for r in range(9)] + [[r * 9 + c for r in range(9)] for c in range(9)] + \
        [[(br * 3 + r) * 9 + bc * 3 + c for r in range(3) for c in range(3)] for br in range(3) for bc in range(3)]
    return all(sorted(ans[i] for i in u) == list("123456789") for u in units)


# ---------------- model ----------------
def offsets(device):
    r = torch.arange(9, device=device).repeat_interleave(9)
    c = torch.arange(9, device=device).repeat(9)
    dr = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
    dc = (c[:, None] - c[None, :]).clamp(-CLIP, CLIP) + CLIP
    box = ((r // 3)[:, None] == (r // 3)[None, :]) & ((c // 3)[:, None] == (c // 3)[None, :])
    return dr, dc, box.long()


class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.bb = nn.Parameter(torch.zeros(h, 2))           # the one addition over 358a: same 3x3 box or not

    def forward(self, x, geo):
        dr, dc, box = geo
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        bias = (self.br[:, dr] + self.bc[:, dc] + self.bb[:, box]).unsqueeze(0).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))


class Net(nn.Module):
    def __init__(self, arm):
        super().__init__()
        c = ARMS[arm]
        self.arm, d = arm, c["d"]
        self.tok = nn.Embedding(V, d)
        self.blocks = nn.ModuleList(Block(d, c["heads"]) for _ in range(c["layers"]))
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, V)
        if arm == "loop":
            self.ln_state = nn.LayerNorm(d)
            self.halt = nn.Linear(d, 1)

    def step(self, h, e, geo):
        z = h + e
        for b in self.blocks:
            z = b(z, geo)
        return self.ln_state(z)

    def read(self, h):
        z = self.ln_out(h)
        return self.head(z), (self.halt(z.mean(1)).squeeze(-1) if self.arm == "loop" else None)

    def plain(self, x, geo):
        h = self.tok(x)
        for b in self.blocks:
            h = b(h, geo)
        return self.read(h)[0]

    def sup_step(self, h, x, geo, n_free=N_FREE, n_grad=N_GRAD):
        e = self.tok(x)
        with torch.no_grad():
            for _ in range(n_free):
                h = self.step(h, e.detach(), geo)
        h = h.detach()
        for _ in range(n_grad):
            h = self.step(h, e, geo)
        return h


# ---------------- training ----------------
def train(a):
    torch.manual_seed(a.seed)
    rng = random.Random(3580 + a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    practice = load_practice(a.data)
    geo = offsets(device)
    net = Net(a.arm).to(device)
    ema = copy.deepcopy(net).eval()
    for p in ema.parameters():
        p.requires_grad_(False)
    nparams = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=a.wd, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1.0, (i + 1) / a.warmup))
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    B = a.batch

    def draw(n):
        xs, ys = [], []
        for _ in range(n):
            p, s = shuffle(rng, *rng.choice(practice))
            xs.append(encode(p)); ys.append(encode(s))
        return torch.tensor(xs, device=device), torch.tensor(ys, device=device)

    x, y = draw(B)
    d = ARMS[a.arm]["d"]
    h = torch.zeros(B, 81, d, device=device)
    steps = torch.zeros(B, dtype=torch.long, device=device)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    t0, acc = time.time(), {"ce": 0.0, "cell": 0.0, "exact": 0.0, "halt": 0.0, "n": 0, "done_steps": [], "replaced": 0}
    print(f"{a.arm} seed {a.seed}: {nparams} weights on {device}", flush=True)
    for it in range(1, a.steps + 1):
        net.train()
        blank = x == 1
        with amp:
            if a.arm == "plain":
                logits, q = net.plain(x, geo), None
            else:
                h = net.sup_step(h, x, geo)
                logits, q = net.read(h)
            ce = F.cross_entropy(logits.float()[blank], y[blank])
            pred = logits.argmax(-1)
            exact = ((pred == y) | ~blank).all(1)
            loss = ce
            if q is not None:
                hl = F.binary_cross_entropy_with_logits(q.float(), exact.float())
                loss = ce + 0.5 * hl
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        with torch.no_grad():
            for pe, pn in zip(ema.parameters(), net.parameters()):
                pe.mul_(a.ema).add_(pn.detach(), alpha=1 - a.ema)
        acc["ce"] += ce.item(); acc["cell"] += (pred == y)[blank].float().mean().item()
        acc["exact"] += exact.float().mean().item(); acc["n"] += 1
        if q is not None:
            acc["halt"] += hl.item()
            h = h.detach()
            steps += 1
            done = (steps >= N_SUP) | ((q.detach() > 0) & (steps >= 2))
            if done.any():
                idx = done.nonzero().squeeze(1)
                acc["done_steps"] += steps[idx].tolist()
                nx, ny = draw(len(idx))
                x, y = x.clone(), y.clone()
                x[idx], y[idx] = nx, ny
                h[idx] = 0
                steps[idx] = 0
                acc["replaced"] += len(idx)
        else:
            x, y = draw(B)
        if it % a.log_every == 0 or it == a.steps:
            n = acc["n"]
            rec = {"step": it, "ce": round(acc["ce"] / n, 4), "cell": round(acc["cell"] / n, 4),
                   "exact": round(acc["exact"] / n, 4), "min": round((time.time() - t0) / 60, 1)}
            if q is not None:
                ds = acc["done_steps"]
                rec.update(halt_bce=round(acc["halt"] / n, 4), replaced=acc["replaced"],
                           mean_sup_steps=round(sum(ds) / len(ds), 2) if ds else None)
            if it % (a.log_every * 10) == 0 or it == a.steps:
                rec["practice_exact_ema"] = practice_exact(ema, practice[:200], device)
                torch.save({"arm": a.arm, "seed": a.seed, "step": it, "state": ema.state_dict()}, out / "ema.pt")
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            acc = {"ce": 0.0, "cell": 0.0, "exact": 0.0, "halt": 0.0, "n": 0, "done_steps": [], "replaced": 0}
    torch.save({"arm": a.arm, "seed": a.seed, "step": a.steps, "state": ema.state_dict()}, out / "ema.pt")
    json.dump({"arm": a.arm, "seed": a.seed, "weights": nparams, "steps": a.steps, "batch": B, "lr": a.lr, "wd": a.wd,
               "ema": a.ema, "warmup": a.warmup, "published_steps_fraction": round(a.steps / 78000, 3),
               "minutes": round((time.time() - t0) / 60, 1), "device": device},
              open(out / "train_summary.json", "w"), indent=1)


# ---------------- answering (one try) ----------------
@torch.no_grad()
def answer(net, puzzles, device, bs=256):
    geo = offsets(device)
    outs, sup_used = [], []
    for i in range(0, len(puzzles), bs):
        chunk = puzzles[i:i + bs]
        x = torch.tensor([encode(p) for p in chunk], device=device)
        if net.arm == "plain":
            pred = net.plain(x, geo).argmax(-1)
        else:
            h = torch.zeros(len(chunk), 81, ARMS["loop"]["d"], device=device)
            pred = torch.zeros_like(x)
            live = torch.ones(len(chunk), dtype=torch.bool, device=device)
            used = torch.full((len(chunk),), N_SUP, device=device)
            for s in range(N_SUP):
                h = net.sup_step(h, x, geo)
                logits, q = net.read(h)
                p = logits.argmax(-1)
                pred[live] = p[live]
                stop = live & (q > 0)
                used[stop] = s + 1
                live &= ~stop
                if not live.any():
                    break
            sup_used += used.tolist()
        for p, pr in zip(chunk, pred.tolist()):
            outs.append("".join(ch if ch not in ".0" else str(max(1, min(9, t - 1))) for ch, t in zip(p, pr)))
    return outs, sup_used


def practice_exact(net, practice, device):
    net.eval()
    outs, _ = answer(net, [p for p, _ in practice], device)
    return sum(o == s for o, (_, s) in zip(outs, practice))


def solve(puzzles, task):
    """bm-394 harness arm: 81-char strings in, 81-digit strings out, one try each."""
    assert task == "sudoku"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    d = torch.load(os.environ["RSN358B_CKPT"], map_location=device)
    net = Net(d["arm"]).to(device)
    net.load_state_dict(d["state"])
    net.eval()
    outs, used = answer(net, puzzles, device)
    if used:
        print(json.dumps({"mean_sup_steps": round(sum(used) / len(used), 2)}), flush=True)
    return outs


def selftest():
    rng = random.Random(0)
    puz = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
    ans = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    assert valid_solution(puz, ans)
    for _ in range(200):
        p2, a2 = shuffle(rng, puz, ans)
        assert valid_solution(p2, a2) and p2.count(".") == puz.count(".")
    print("selftest ok")


def smoke(_):
    import tempfile
    selftest()
    tmp = Path(tempfile.mkdtemp())
    puz = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
    ans = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    (tmp / "sudoku_practice.jsonl").write_text(json.dumps({"qid": "x", "puzzle": puz, "answer": ans}) + "\n")
    for arm in ARMS:
        train(argparse.Namespace(arm=arm, data=tmp, seed=1, out=tmp / arm, steps=4, batch=8, lr=1e-4, wd=1.0,
                                 warmup=2, ema=0.999, log_every=2))
        os.environ["RSN358B_CKPT"] = str(tmp / arm / "ema.pt")
        o = solve([puz] * 3, "sudoku")
        assert len(o) == 3 and all(len(s) == 81 and s.isdigit() for s in o)
    print("smoke ok", tmp)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("train")
    p.add_argument("--arm", choices=list(ARMS), required=True); p.add_argument("--data", required=True)
    p.add_argument("--seed", type=int, required=True); p.add_argument("--out", required=True)
    p.add_argument("--steps", type=int, default=78000); p.add_argument("--batch", type=int, default=768)
    p.add_argument("--lr", type=float, default=1e-4); p.add_argument("--wd", type=float, default=1.0)
    p.add_argument("--warmup", type=int, default=2000); p.add_argument("--ema", type=float, default=0.999)
    p.add_argument("--log-every", type=int, default=200)
    sub.add_parser("selftest")
    sub.add_parser("smoke")
    a = ap.parse_args()
    {"train": train, "selftest": lambda _: selftest(), "smoke": smoke}[a.cmd](a)


if __name__ == "__main__":
    main()
