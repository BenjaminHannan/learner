#!/usr/bin/env python3
"""rsn-358a: a loop reasoner vs its plain same-size twin on general puzzles (sleep research thread, 2026-09-25).

Plan and pass marks: design/v3/30-modes/358a-loop-vs-plain-general-puzzles.md,
artifacts/claude-rsn358a-20260925/PASSMARKS.md. Puzzles: scripts/claude_rsn358a_envs.py (sums with carries,
Latin-square grids, the creative thread's number puzzles). No relation facts.

Both nets read a puzzle as a grid of tokens (no absolute positions: attention gets a learned bias for the row and
column offset between two cells, clipped at 4, so the same weights read any grid size) and fill the blank cells.
  plain  8 different layers, width 256, one pass.                                  (~6.3M weights)
  loop   2 layers, width 512, applied again and again ("rounds"); the puzzle is re-added every round and a
         stop head guesses after every round whether the current answer is fully right.   (~6.3M weights)
The loop is trained with a random number of rounds (1-16), learning from the last 1-6 of them; at test time it
thinks for up to 48 rounds and stops at the first round whose stop head says "right" (p > 0.5), else at the round
it was most confident in. Same data stream, steps, batch, learning rate and schedule for both arms.

  python -B scripts/claude_rsn358a_run.py make-tests --out artifacts/claude-rsn358a-20260925/tests
  python -B scripts/claude_rsn358a_run.py train --arm plain|loop --seed 1 --out W/plain-s1 [--steps 60000]
  python -B scripts/claude_rsn358a_run.py eval  --ckpt W/plain-s1/final.pt --tests DIR --out W/plain-s1/tests.json
  python -B scripts/claude_rsn358a_run.py smoke     (CPU, a few steps of each arm + eval on 20 items per test)
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_envs as E  # noqa: E402

CLIP = 4
ARMS = {"plain": dict(d=256, layers=8, heads=8), "loop": dict(d=512, layers=2, heads=8)}
TRAIN_ROUNDS, GRAD_ROUNDS, TEST_ROUNDS = 16, 6, 48
FIXED_REPORT = [1, 2, 4, 8, 12, 16, 24, 32, 48]
TESTS = [  # (name, env, size, seed, graded role)
    ("sums4", "sums", 4, 35811, "practised"), ("sums6", "sums", 6, 35812, "bigger"), ("sums8", "sums", 8, 35813, "report"),
    ("grids5", "grids", 5, 35821, "practised"), ("grids6", "grids", 6, 35822, "bigger"), ("grids7", "grids", 7, 35823, "report"),
    ("numbers4", "numbers", 4, None, "practised"), ("numbers5", "numbers", 5, 35832, "bigger"),
]
N_TEST = 300


# ---------------- model ----------------
class Block(nn.Module):
    def __init__(self, d, h):
        super().__init__()
        self.h = h
        self.ln1, self.ln2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.out = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))
        self.br = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))
        self.bc = nn.Parameter(torch.zeros(h, 2 * CLIP + 1))

    def forward(self, x, dr, dc):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        bias = (self.br[:, dr] + self.bc[:, dc]).unsqueeze(0).to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))


class Net(nn.Module):
    def __init__(self, arm):
        super().__init__()
        c = ARMS[arm]
        self.arm, d = arm, c["d"]
        self.tok = nn.Embedding(E.VOCAB, d)
        self.slot = nn.Embedding(2, d)
        self.env = nn.Embedding(len(E.ENVS), d)
        self.blocks = nn.ModuleList(Block(d, c["heads"]) for _ in range(c["layers"]))
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, E.VOCAB)
        if arm == "loop":
            self.ln_state = nn.LayerNorm(d)
            self.halt = nn.Linear(d, 1)

    @staticmethod
    def offsets(H, W, device):
        r = torch.arange(H, device=device).repeat_interleave(W)
        c = torch.arange(W, device=device).repeat(H)
        dr = (r[:, None] - r[None, :]).clamp(-CLIP, CLIP) + CLIP
        dc = (c[:, None] - c[None, :]).clamp(-CLIP, CLIP) + CLIP
        return dr, dc

    def embed(self, tokens, slot, env):
        B, H, W = tokens.shape
        e = self.tok(tokens.view(B, -1)) + self.slot(slot.view(B, -1)) + self.env(env)[:, None, :]
        return e, self.offsets(H, W, tokens.device)

    def step(self, h, e, dr, dc):
        z = h + e
        for b in self.blocks:
            z = b(z, dr, dc)
        return self.ln_state(z)

    def read(self, h):
        logits = self.head(self.ln_out(h))
        q = self.halt(self.ln_out(h).mean(1)).squeeze(-1) if self.arm == "loop" else None
        return logits, q

    def plain_forward(self, tokens, slot, env):
        h, (dr, dc) = self.embed(tokens, slot, env)
        for b in self.blocks:
            h = b(h, dr, dc)
        return self.read(h)[0]

    def loop_train(self, tokens, slot, env, n_free, n_grad):
        e, (dr, dc) = self.embed(tokens, slot, env)
        h = torch.zeros_like(e)
        with torch.no_grad():
            for _ in range(n_free):
                h = self.step(h, e.detach(), dr, dc)
        h = h.detach()
        outs = []
        for _ in range(n_grad):
            h = self.step(h, e, dr, dc)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def loop_rounds(self, tokens, slot, env, n):
        e, (dr, dc) = self.embed(tokens, slot, env)
        h = torch.zeros_like(e)
        preds, qs = [], []
        for _ in range(n):
            h = self.step(h, e, dr, dc)
            lg, q = self.read(h)
            preds.append(lg.argmax(-1))
            qs.append(torch.sigmoid(q.float()))
        return torch.stack(preds, 1), torch.stack(qs, 1)       # [B, n, T], [B, n]


# ---------------- data ----------------
class Source:
    """The practice stream. Identical for both arms at the same seed (own RNG, never touched by the model)."""
    def __init__(self, seed, latin_pool=20000):
        self.rng = random.Random(1000 + seed)
        four, three = E.number_hands()
        self.four, _ = E.split_four(four)
        self.three = three
        self.latin = {s: [E.make_latin_base(self.rng, s) for _ in range(latin_pool)] for s in E.TRAIN_SIZES["grids"]}

    def item(self, env, size):
        rng = self.rng
        if env == "sums":
            return E.make_sum(rng, size)
        if env == "grids":
            sol, puz = E.augment_latin(rng, *rng.choice(self.latin[size]))
            return E.latin_item(rng, sol, puz)
        h, t, s = rng.choice(self.four if size == 4 else self.three)
        return E.number_item(rng, h, t, s)

    def batch(self, B):
        env = self.rng.choice(E.ENVS)
        size = self.rng.choice(E.TRAIN_SIZES[env])
        return [self.item(env, size) for _ in range(B)]


def tensors(items, device):
    t = torch.tensor([it.tokens for it in items], device=device)
    s = torch.tensor([it.slot for it in items], device=device)
    y = torch.tensor([it.target for it in items], device=device)
    env = torch.full((len(items),), E.ENVS.index(items[0].env), device=device)
    return t, s, y, env


def ce_and_exact(logits, s, y):
    B = s.shape[0]
    s, y = s.view(B, -1).bool(), y.view(B, -1)
    ce = F.cross_entropy(logits.float()[s], y[s])
    exact = ((logits.argmax(-1) == y) | ~s).all(1).float()
    return ce, exact


# ---------------- tests ----------------
def item_to_json(it):
    return {"env": it.env, "size": it.size, "tokens": it.tokens, "slot": it.slot, "target": it.target, "meta": it.meta}


def item_from_json(d):
    return E.Item(d["env"], d["size"], d["tokens"], d["slot"], d["target"], d["meta"])


def make_test(name, env, size, seed, n=N_TEST):
    if env == "numbers":
        rng = random.Random(35830 + size)
        if size == 4:
            _, held = E.split_four(E.number_hands()[0])
            hands = held
        else:
            hands = E.five_hands(seed, n)
        return [E.number_item(rng, h, t, s) for h, t, s in hands[:n]]
    rng = random.Random(seed)
    if env == "sums":
        return [E.make_sum(rng, size) for _ in range(n)]
    return [E.latin_item(rng, *E.make_latin_base(rng, size)) for _ in range(n)]


def make_tests(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, env, size, seed, role in TESTS:
        items = make_test(name, env, size, seed)
        (out / f"{name}.jsonl").write_text("".join(json.dumps(item_to_json(i)) + "\n" for i in items), encoding="utf-8")
        print(f"{name}: {len(items)} items ({role})")


def load_tests(d, limit=None):
    return {name: [item_from_json(json.loads(l)) for l in (Path(d) / f"{name}.jsonl").read_text().splitlines()[:limit]]
            for name, *_ in TESTS}


def grid_of(pred_row, item):
    H, W = len(item.tokens), len(item.tokens[0])
    return [pred_row[r * W:(r + 1) * W] for r in range(H)]


@torch.no_grad()
def evaluate(net, items, device, bs=100):
    net.eval()
    res = {"n": len(items)}
    if net.arm == "plain":
        right = 0
        for i in range(0, len(items), bs):
            chunk = items[i:i + bs]
            t, s, _, env = tensors(chunk, device)
            pred = net.plain_forward(t, s, env).argmax(-1).tolist()
            right += sum(E.check(it, grid_of(p, it)) for it, p in zip(chunk, pred))
        res["right"] = right
        return res
    fixed = {r: 0 for r in FIXED_REPORT}
    right, rounds, oracle = 0, [], 0
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _, env = tensors(chunk, device)
        preds, qs = net.loop_rounds(t, s, env, TEST_ROUNDS)
        preds, qs = preds.tolist(), qs.tolist()
        for it, p, q in zip(chunk, preds, qs):
            stop = next((r for r in range(TEST_ROUNDS) if q[r] > 0.5), max(range(TEST_ROUNDS), key=lambda r: q[r]))
            rounds.append(stop + 1)
            right += E.check(it, grid_of(p[stop], it))
            for r in FIXED_REPORT:
                fixed[r] += E.check(it, grid_of(p[r - 1], it))
            oracle += any(E.check(it, grid_of(p[r], it)) for r in range(TEST_ROUNDS))
    res.update(right=right, mean_rounds=round(sum(rounds) / len(rounds), 2),
               rounds_hist={str(k): rounds.count(k) for k in sorted(set(rounds))},
               fixed_rounds={str(k): v for k, v in fixed.items()}, right_at_any_round=oracle)
    return res


# ---------------- training ----------------
def train(a):
    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    src = Source(a.seed, latin_pool=a.latin_pool)
    dev_rng = random.Random(7000 + a.seed)
    dev = {f"{env}{size}": [E.make_sum(dev_rng, size) if env == "sums" else
                            E.latin_item(dev_rng, *E.make_latin_base(dev_rng, size)) for _ in range(200)]
           for env, size in (("sums", 4), ("grids", 5))}
    net = Net(a.arm).to(device)
    nparams = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup) * 0.5 *
                                              (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    round_rng = random.Random(9000 + a.seed)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0}
    print(f"{a.arm} seed {a.seed}: {nparams} weights, data ready in {time.time() - t0:.0f}s on {device}", flush=True)
    for step in range(1, a.steps + 1):
        net.train()
        items = src.batch(a.batch)
        t, s, y, env = tensors(items, device)
        with amp:
            if a.arm == "plain":
                ce, exact = ce_and_exact(net.plain_forward(t, s, env), s, y)
                loss, hl = ce, torch.zeros(())
            else:
                total = round_rng.randint(1, TRAIN_ROUNDS)
                k = round_rng.randint(1, min(total, GRAD_ROUNDS))
                outs = net.loop_train(t, s, env, total - k, k)
                ces, hls = [], []
                for lg, q in outs:
                    c_, ex = ce_and_exact(lg, s, y)
                    ces.append(c_)
                    hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
                ce, hl = torch.stack(ces).mean(), torch.stack(hls).mean()
                exact = ex                                   # last graded round
                loss = ce + 0.5 * hl
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        run["ce"] += ce.item(); run["exact"] += exact.mean().item(); run["halt"] += float(hl.detach()); run["n"] += 1
        kind = run.setdefault("by_kind", {}).setdefault(f"{items[0].env}{items[0].size}", [0.0, 0])
        kind[0] += exact.mean().item(); kind[1] += 1
        if step % a.log_every == 0 or step == a.steps:
            n = run["n"]
            rec = {"step": step, "ce": round(run["ce"] / n, 4), "exact": round(run["exact"] / n, 4),
                   "halt_bce": round(run["halt"] / n, 4), "lr": sched.get_last_lr()[0], "min": round((time.time() - t0) / 60, 1),
                   "exact_by_kind": {k: round(v[0] / v[1], 3) for k, v in sorted(run.get("by_kind", {}).items())}}
            if step % (a.log_every * 5) == 0 or step == a.steps:
                rec["dev"] = {k: evaluate(net, v, device)["right"] for k, v in dev.items()}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0}
    torch.save({"arm": a.arm, "seed": a.seed, "state": net.state_dict()}, out / "final.pt")
    json.dump({"arm": a.arm, "seed": a.seed, "weights": nparams, "steps": a.steps, "batch": a.batch, "lr": a.lr,
               "warmup": a.warmup, "latin_pool": a.latin_pool, "minutes": round((time.time() - t0) / 60, 1), "device": device},
              open(out / "train_summary.json", "w"), indent=1)


def load(ckpt, device):
    d = torch.load(ckpt, map_location=device)
    net = Net(d["arm"]).to(device)
    net.load_state_dict(d["state"])
    return net


def run_eval(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = load(a.ckpt, device)
    tests = load_tests(a.tests, a.limit)
    res = {"arm": net.arm, "ckpt": str(a.ckpt), "tests": {}}
    for name, env, size, seed, role in TESTS:
        r = evaluate(net, tests[name], device)
        r["role"] = role
        res["tests"][name] = r
        print(name, json.dumps(r), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


def smoke(_):
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    make_tests(argparse.Namespace(out=tmp / "tests"))
    for arm in ARMS:
        train(argparse.Namespace(arm=arm, seed=1, out=tmp / arm, steps=6, batch=16, lr=3e-4, warmup=2,
                                 latin_pool=50, log_every=2))
        run_eval(argparse.Namespace(ckpt=tmp / arm / "final.pt", tests=tmp / "tests", limit=20, out=tmp / arm / "t.json"))
    print("smoke ok", tmp)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("make-tests"); p.add_argument("--out", required=True)
    p = sub.add_parser("train")
    p.add_argument("--arm", choices=list(ARMS), required=True); p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True); p.add_argument("--steps", type=int, default=60000)
    p.add_argument("--batch", type=int, default=256); p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--warmup", type=int, default=1000); p.add_argument("--latin-pool", type=int, default=20000)
    p.add_argument("--log-every", type=int, default=500)
    p = sub.add_parser("eval")
    p.add_argument("--ckpt", required=True); p.add_argument("--tests", required=True); p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=None)
    sub.add_parser("smoke")
    a = ap.parse_args()
    {"make-tests": make_tests, "train": train, "eval": run_eval, "smoke": smoke}[a.cmd](a)


if __name__ == "__main__":
    main()
