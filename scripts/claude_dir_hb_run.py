#!/usr/bin/env python3
"""Trainer and scorer for the fact-combining test (Director helper HB, 2026-09-28). Needs torch; NOT RUN where it was written (no torch there).

Items and checker: scripts/claude_dir_hb_kinds.py. Marks: artifacts/claude-dir-hb-dates-20260928/PASSMARKS.md. Two arms, the race's shapes:
  plain  8 different layers, width 256, one pass.                              (about 6.3M weights)
  loop   2 layers, width 512, applied again and again; the input is re-added every round; a stop head guesses after every round whether the
         whole answer is right (train: random 1-16 rounds, learn from the last 1-6; test: up to 48 rounds, stop at the first p > 0.5).
Both read the item as a grid of tokens with no absolute positions (learned bias on the row/column offset of two cells, clipped at 4) and no
puzzle-kind input.  Blocks are the race's Block (claude_rsn358a_run.Block) with an added key mask so padding rows are ignored.
Practice: an endless fresh stream (Stream), nothing repeated, panel items dropped.  Same stream seed, steps, batch, lr and schedule for both arms.

  python3 -B scripts/claude_dir_hb_run.py selftest
  python3 -B scripts/claude_dir_hb_run.py train --arm loop --seed 0 --out RUNS/loop-s0 [--steps 30000 --batch 128]
  python3 -B scripts/claude_dir_hb_run.py eval  --ckpt RUNS/loop-s0/final.pt --panel dev|hold --out RUNS/loop-s0/dev.json
The hold panel can be scored once per checkpoint (a .started marker refuses a second run).
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
import claude_dir_hb_kinds as K  # noqa: E402
import claude_rsn358a_run as R  # noqa: E402  (Block, CLIP: the race's attention block, unchanged)

PAD = K.VOCAB
NVOC = K.VOCAB + 1
ARMS = {"plain": dict(d=256, layers=8, heads=8), "loop": dict(d=512, layers=2, heads=8)}
TRAIN_ROUNDS, GRAD_ROUNDS, TEST_ROUNDS = 16, 6, 48


class Block(R.Block):
    def forward(self, x, dr, dc, kmask):
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        bias = (self.br[:, dr] + self.bc[:, dc]).unsqueeze(0).to(q.dtype) + kmask.to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
        x = x + self.out(a.transpose(1, 2).reshape(B, T, D))
        return x + self.mlp(self.ln2(x))


class Net(nn.Module):
    def __init__(self, arm):
        super().__init__()
        c = ARMS[arm]
        self.arm, d = arm, c["d"]
        self.tok = nn.Embedding(NVOC, d)
        self.slot = nn.Embedding(2, d)
        self.blocks = nn.ModuleList(Block(d, c["heads"]) for _ in range(c["layers"]))
        self.ln_out = nn.LayerNorm(d)
        self.head = nn.Linear(d, NVOC)
        if arm == "loop":
            self.ln_state = nn.LayerNorm(d)
            self.halt = nn.Linear(d, 1)

    def embed(self, tokens, slot):
        B, H, Wd = tokens.shape
        e = self.tok(tokens.view(B, -1)) + self.slot(slot.view(B, -1))
        dr, dc = R.Net.offsets(H, Wd, tokens.device)
        kmask = torch.zeros(B, 1, 1, H * Wd, device=tokens.device)
        kmask.masked_fill_((tokens.view(B, -1) == PAD)[:, None, None, :], float("-inf"))
        return e, dr, dc, kmask

    def step(self, h, e, dr, dc, km):
        z = h + e
        for b in self.blocks:
            z = b(z, dr, dc, km)
        return self.ln_state(z)

    def read(self, h):
        logits = self.head(self.ln_out(h))
        q = self.halt(self.ln_out(h).mean(1)).squeeze(-1) if self.arm == "loop" else None
        return logits, q

    def plain_forward(self, tokens, slot):
        h, dr, dc, km = self.embed(tokens, slot)
        for b in self.blocks:
            h = b(h, dr, dc, km)
        return self.read(h)[0]

    def loop_train(self, tokens, slot, n_free, n_grad):
        e, dr, dc, km = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        with torch.no_grad():
            for _ in range(n_free):
                h = self.step(h, e.detach(), dr, dc, km)
        h = h.detach()
        outs = []
        for _ in range(n_grad):
            h = self.step(h, e, dr, dc, km)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def loop_rounds(self, tokens, slot, n):
        e, dr, dc, km = self.embed(tokens, slot)
        h = torch.zeros_like(e)
        preds, qs = [], []
        for _ in range(n):
            h = self.step(h, e, dr, dc, km)
            lg, q = self.read(h)
            preds.append(lg.argmax(-1))
            qs.append(torch.sigmoid(q.float()))
        return torch.stack(preds, 1), torch.stack(qs, 1)


# ---------------- data ----------------
def tensors(items, device):
    H = max(len(it.tokens) for it in items)
    def pad(rows, fill):
        return rows + [[fill] * K.W] * (H - len(rows))
    t = torch.tensor([pad(it.tokens, PAD) for it in items], device=device)
    s = torch.tensor([pad(it.slot, 0) for it in items], device=device)
    y = torch.tensor([pad(it.target, 0) for it in items], device=device)
    return t, s, y


def ce_and_exact(logits, s, y):
    B = s.shape[0]
    s, y = s.view(B, -1).bool(), y.view(B, -1)
    ce = F.cross_entropy(logits.float()[s], y[s])
    exact = ((logits.argmax(-1) == y) | ~s).all(1).float()
    return ce, exact


def grid_of(pred_row, item):
    return [pred_row[r * K.W:(r + 1) * K.W] for r in range(len(item.tokens))]


def load_panel(tag):
    base = K.DEV_BASE if tag == "dev" else K.HOLD_BASE
    return {s: K.make_panel(s, base) for s in K.SPLITS}


@torch.no_grad()
def evaluate(net, items, device, bs=50):
    net.eval()
    res = {"n": len(items), "right": 0}
    ops = {}
    rounds, oracle = [], 0
    fixed = {r: 0 for r in (1, 2, 4, 8, 16, 32, 48)}
    for i in range(0, len(items), bs):
        chunk = items[i:i + bs]
        t, s, _ = tensors(chunk, device)
        if net.arm == "plain":
            preds = net.plain_forward(t, s).argmax(-1).tolist()
            chosen = preds
        else:
            allp, qs = net.loop_rounds(t, s, TEST_ROUNDS)
            allp, qs = allp.tolist(), qs.tolist()
            chosen = []
            for p, q in zip(allp, qs):
                stop = next((r for r in range(TEST_ROUNDS) if q[r] > 0.5), max(range(TEST_ROUNDS), key=lambda r: q[r]))
                rounds.append(stop + 1)
                chosen.append(p[stop])
        for j, (it, p) in enumerate(zip(chunk, chosen)):
            g = grid_of(p, it)
            res["right"] += K.check(it, g)
            for op, ok in K.part_results(it, g):
                o = ops.setdefault(op, [0, 0])
                o[0] += ok
                o[1] += 1
            if net.arm == "loop":
                for r in fixed:
                    fixed[r] += K.check(it, grid_of(allp[j][r - 1], it))
                oracle += any(K.check(it, grid_of(allp[j][r], it)) for r in range(TEST_ROUNDS))
    res["parts_by_op"] = {k: v for k, v in sorted(ops.items())}
    if net.arm == "loop":
        res.update(mean_rounds=round(sum(rounds) / len(rounds), 2), rounds_at_cap=sum(r == TEST_ROUNDS for r in rounds),
                   fixed_rounds={str(k): v for k, v in fixed.items()}, right_at_any_round=oracle)
    return res


def eval_panels(net, panels, device):
    return {s: evaluate(net, items, device) for s, items in panels.items()}


# ---------------- training ----------------
def build(arm, seed):
    torch.manual_seed(seed)
    return Net(arm)


def train(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    stream = K.Stream(a.seed)
    dev = load_panel("dev")
    dev_small = {s: v[:100] for s, v in dev.items()}
    net = build(a.arm, a.seed).to(device)
    nparams = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup) * 0.5 * (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    round_rng = random.Random(9000 + a.seed)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0}
    print(f"{a.arm} seed {a.seed}: {nparams} weights on {device}", flush=True)
    for step in range(1, a.steps + 1):
        net.train()
        items = stream.batch(a.batch)
        t, s, y = tensors(items, device)
        with amp:
            if a.arm == "plain":
                ce, exact = ce_and_exact(net.plain_forward(t, s), s, y)
                loss, hl = ce, torch.zeros(())
            else:
                total = round_rng.randint(1, TRAIN_ROUNDS)
                k = round_rng.randint(1, min(total, GRAD_ROUNDS))
                outs = net.loop_train(t, s, total - k, k)
                ces, hls = [], []
                for lg, q in outs:
                    c_, ex = ce_and_exact(lg, s, y)
                    ces.append(c_)
                    hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
                ce, hl, exact = torch.stack(ces).mean(), torch.stack(hls).mean(), ex
                loss = ce + 0.5 * hl
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        run["ce"] += ce.item(); run["exact"] += exact.mean().item(); run["halt"] += float(hl.detach()); run["n"] += 1
        if step % a.log_every == 0 or step == a.steps:
            n = run["n"]
            rec = {"step": step, "ce": round(run["ce"] / n, 4), "exact": round(run["exact"] / n, 4), "halt_bce": round(run["halt"] / n, 4),
                   "lr": sched.get_last_lr()[0], "min": round((time.time() - t0) / 60, 1), "dropped_panel_keys": stream.dropped}
            if step % (a.log_every * 5) == 0 or step == a.steps:
                rec["dev100"] = {s: v["right"] for s, v in eval_panels(net, dev_small, device).items()}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0}
    torch.save({"arm": a.arm, "seed": a.seed, "state": net.state_dict()}, out / "final.pt")
    json.dump({"arm": a.arm, "seed": a.seed, "weights": nparams, "steps": a.steps, "batch": a.batch, "lr": a.lr, "warmup": a.warmup,
               "minutes": round((time.time() - t0) / 60, 1), "device": device}, open(out / "train_summary.json", "w"), indent=1)


def run_eval(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ck = Path(a.ckpt)
    if a.panel == "hold":
        marker = ck.parent / "hold.started"
        if marker.exists():
            sys.exit("REFUSED: this checkpoint's holdout was already started; it is scored once.")
        marker.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    d = torch.load(ck, map_location=device)
    net = Net(d["arm"]).to(device)
    net.load_state_dict(d["state"])
    res = {"arm": d["arm"], "seed": d["seed"], "panel": a.panel, "weights": sum(p.numel() for p in net.parameters()),
           "splits": eval_panels(net, load_panel(a.panel), device)}
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print({s: v["right"] for s, v in res["splits"].items()})


def selftest(_):
    """CPU: weights of both arms, one step gives every 2-D matrix a nonzero gradient (halt exempt in plain), pad rows are ignored."""
    st = K.Stream(0)
    items = st.batch(16)
    for arm in ARMS:
        net = build(arm, 0)
        n = sum(p.numel() for p in net.parameters())
        t, s, y = tensors(items, "cpu")
        if arm == "plain":
            ce, _ = ce_and_exact(net.plain_forward(t, s), s, y)
        else:
            ce = torch.stack([ce_and_exact(lg, s, y)[0] for lg, _ in net.loop_train(t, s, 1, 2)]).mean()
        ce.backward()
        dead = [k for k, p in net.named_parameters() if p.dim() == 2 and (p.grad is None or float(p.grad.abs().sum()) == 0.0)]
        assert not dead, dead
        # padding rows must not change an item's logits: the same item alone vs padded next to a taller one
        net.eval()
        it = min(items, key=lambda x: len(x.tokens))
        tall = max(items, key=lambda x: len(x.tokens))
        a1 = tensors([it], "cpu")
        a2 = tensors([it, tall], "cpu")

        def logits_of(tt, ss):
            with torch.no_grad():
                if arm == "plain":
                    return net.plain_forward(tt, ss)[0]
                e, dr, dc, km = net.embed(tt, ss)
                h = torch.zeros_like(e)
                for _ in range(3):
                    h = net.step(h, e, dr, dc, km)
                return net.read(h)[0][0]

        l1, l2 = logits_of(a1[0], a1[1]), logits_of(a2[0], a2[1])
        assert torch.allclose(l1, l2[:l1.shape[0]], atol=1e-4), "padding leaks into the answer"
        print(f"selftest ok {arm}: {n} weights")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    p = sub.add_parser("train")
    p.add_argument("--arm", choices=list(ARMS), required=True); p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True); p.add_argument("--steps", type=int, default=30000)
    p.add_argument("--batch", type=int, default=128); p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--warmup", type=int, default=1000); p.add_argument("--log-every", type=int, default=500)
    p = sub.add_parser("eval")
    p.add_argument("--ckpt", required=True); p.add_argument("--panel", choices=["dev", "hold"], required=True); p.add_argument("--out", required=True)
    a = ap.parse_args()
    {"selftest": selftest, "train": train, "eval": run_eval}[a.cmd](a)


if __name__ == "__main__":
    main()
