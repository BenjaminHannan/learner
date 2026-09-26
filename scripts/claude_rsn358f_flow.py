#!/usr/bin/env python3
"""rsn-358f: the 358a loop trained as a LOOPED FLOW (sleep research thread, 2026-09-26; idea from "Thinking with
Looped Flows", arXiv 2609.11801, handed over by the papers thread; plan and marks in artifacts/claude-rsn358f-20260926/).

Why: in 358a (registered FAIL) the loop beat its plain twin on bigger grids on both seeds (+67/+76 of 300) but lost
bigger sums on one seed; its sums answers peak around round 4-8 and then slip, and "right at any round" was well above
what it kept. In 358a every graded round has the same target, so early rounds have no reason to build state that
later rounds use. A looped flow gives each round a different job: round i sees a noisy copy of the answer whose noise
falls as i rises, and learns to denoise it, carrying its state forward.

ONE change vs the 358a loop arm (as one package, as the paper defines it; nothing else changes):
  input   each round also reads I_t = (1-t) x0 + t x1 on the answer cells (x1 = one-hot answer, x0 ~ N(0, sigma^2),
          sigma = 1/sqrt(|V|), shared across the rounds of a rollout) through a bias-free |V| -> d projection, plus a
          time embedding (1 -> d -> d MLP, SiLU), added to the puzzle embedding that is re-added every round
  train   K = 8 rounds per step at sorted times t_0 < ... < t_7 ~ U[0, 1]; cross-entropy to x1 at EVERY round,
          gradient stopped between rounds (each round gets its own gradient); stop head trained as in 358a (weight
          0.5, report only; the flow always runs to t = 1)
  test    deterministic Euler integration (gamma = 0) over n = 32 equal steps from t = 0 (pure noise) to 1, the state
          carried across steps: x_{i+1} = x_i + (t_{i+1} - t_i)(xhat_i - x_i)/(1 - t_i); the answer is the last xhat.
          n = 32 is fixed in advance; 16 and 64 are reported only. Test noise comes from a fixed seed.
Width: the loop's width is trimmed from 512 to 496 so the flow net (with its extra ~0.3M input weights) matches the
plain twin's 6.385M weights within 2% (6.356M). Data stream, steps, batch, lr, schedule, seeds (1, 2), tests: as 358a.
The plain arm is 358a's (same code, seeds and data stream; its registered test counts are reused, not re-run).
Not copied from the paper (to keep the 358a body and cost): its TRM two-state cycles, SDE sampler, pseudotargets,
ACT early exit in training, EMA, StableMax, weight decay 1.0, K = 16.

  python -B scripts/claude_rsn358f_flow.py train --seed 1 --out W/flow-s1 [--steps 60000]
  python -B scripts/claude_rsn358f_flow.py eval  --ckpt W/flow-s1/final.pt --tests DIR --out W/flow-s1/tests.json
  python -B scripts/claude_rsn358f_flow.py smoke
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
import claude_rsn358a_run as R  # noqa: E402

WIDTH, HEADS, K, N_TEST, REPORT_N = 496, 8, 8, 32, (16, 32, 64)
SIGMA = 1 / math.sqrt(E.VOCAB)
R.ARMS["flow"] = dict(d=WIDTH, layers=2, heads=HEADS)


class FlowNet(R.Net):
    def __init__(self):
        super().__init__("flow")
        d = WIDTH
        self.arm = "flow"
        self.ln_state = nn.LayerNorm(d)
        self.halt = nn.Linear(d, 1)
        self.xin = nn.Linear(E.VOCAB, d, bias=False)
        self.tmlp = nn.Sequential(nn.Linear(1, d), nn.SiLU(), nn.Linear(d, d))

    def read(self, h):
        logits = self.head(self.ln_out(h))
        return logits, self.halt(self.ln_out(h).mean(1)).squeeze(-1)

    def flow_in(self, e, x, t, slot):
        """puzzle embedding + noisy-answer input (answer cells only) + time embedding."""
        B = e.shape[0]
        m = slot.view(B, -1, 1).to(x.dtype)
        return e + self.xin(x * m) + self.tmlp(t.view(B, 1).to(e.dtype))[:, None, :]

    def flow_train(self, tokens, slot, env, y, gen):
        """K rounds at sorted times; returns [(logits, q)] with the gradient stopped between rounds."""
        e, (dr, dc) = self.embed(tokens, slot, env)
        B, T, _ = e.shape
        x1 = F.one_hot(y.view(B, -1), E.VOCAB).float()
        x0 = torch.randn(B, T, E.VOCAB, generator=gen, device=e.device) * SIGMA
        ts = torch.sort(torch.rand(B, K + 1, generator=gen, device=e.device), dim=1).values[:, :K]
        h = torch.zeros_like(e)
        outs = []
        for i in range(K):
            t = ts[:, i]
            x = (1 - t)[:, None, None] * x0 + t[:, None, None] * x1
            h = self.step(h.detach(), self.flow_in(e, x, t, slot), dr, dc)
            outs.append(self.read(h))
        return outs

    @torch.no_grad()
    def flow_solve(self, tokens, slot, env, n, gen):
        """Euler (gamma = 0) from t = 0 to 1 over n equal steps; returns the argmax of xhat after every step [B, n, T]."""
        e, (dr, dc) = self.embed(tokens, slot, env)
        B, T, _ = e.shape
        x = torch.randn(B, T, E.VOCAB, generator=gen, device=e.device) * SIGMA
        h = torch.zeros_like(e)
        preds = []
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            t = torch.full((B,), t0, device=e.device)
            h = self.step(h, self.flow_in(e, x, t, slot), dr, dc)
            lg, _ = self.read(h)
            xhat = lg.float().softmax(-1)
            x = x + (t1 - t0) * (xhat - x) / (1 - t0)
            preds.append(lg.argmax(-1))
        return torch.stack(preds, 1)


def train(a):
    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    src = R.Source(a.seed, latin_pool=a.latin_pool)           # the same practice stream as 358a at this seed
    dev_rng = random.Random(7000 + a.seed)
    dev = {f"{env}{size}": [E.make_sum(dev_rng, size) if env == "sums" else
                            E.latin_item(dev_rng, *E.make_latin_base(dev_rng, size)) for _ in range(200)]
           for env, size in (("sums", 4), ("grids", 5))}
    net = FlowNet().to(device)
    nparams = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup) * 0.5 *
                                              (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    gen = torch.Generator(device=device)
    gen.manual_seed(9100 + a.seed)
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0}
    print(f"flow seed {a.seed}: {nparams} weights, data ready in {time.time() - t0:.0f}s on {device}", flush=True)
    for step in range(1, a.steps + 1):
        net.train()
        items = src.batch(a.batch)
        t, s, y, env = R.tensors(items, device)
        with amp:
            outs = net.flow_train(t, s, env, y, gen)
            ces, hls = [], []
            for lg, q in outs:
                c_, ex = R.ce_and_exact(lg, s, y)
                ces.append(c_)
                hls.append(F.binary_cross_entropy_with_logits(q.float(), ex))
            ce, hl = torch.stack(ces).mean(), torch.stack(hls).mean()
            exact = ex                                       # last round (highest t) of the rollout
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
            rec = {"step": step, "ce": round(run["ce"] / n, 4), "exact_last_round": round(run["exact"] / n, 4),
                   "halt_bce": round(run["halt"] / n, 4), "lr": sched.get_last_lr()[0], "min": round((time.time() - t0) / 60, 1),
                   "exact_by_kind": {k: round(v[0] / v[1], 3) for k, v in sorted(run.get("by_kind", {}).items())}}
            if step % (a.log_every * 5) == 0 or step == a.steps:
                rec["dev"] = {k: evaluate(net, v, device, ns=(N_TEST,))["right"] for k, v in dev.items()}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0}
    torch.save({"arm": "flow", "seed": a.seed, "state": net.state_dict()}, out / "final.pt")
    json.dump({"arm": "flow", "seed": a.seed, "weights": nparams, "steps": a.steps, "batch": a.batch, "lr": a.lr,
               "warmup": a.warmup, "latin_pool": a.latin_pool, "K": K, "width": WIDTH,
               "minutes": round((time.time() - t0) / 60, 1), "device": device},
              open(out / "train_summary.json", "w"), indent=1)


@torch.no_grad()
def evaluate(net, items, device, bs=100, ns=REPORT_N):
    """right after n Euler steps for each n in ns; "right" = at N_TEST (graded). Fixed test noise (seed 4242)."""
    net.eval()
    gen = torch.Generator(device=device)
    counts = {n: 0 for n in ns}
    for n in ns:
        gen.manual_seed(4242)
        for i in range(0, len(items), bs):
            chunk = items[i:i + bs]
            t, s, _, env = R.tensors(chunk, device)
            preds = net.flow_solve(t, s, env, n, gen)[:, -1].tolist()
            counts[n] += sum(E.check(it, R.grid_of(p, it)) for it, p in zip(chunk, preds))
    return {"n": len(items), "right": counts.get(N_TEST, counts[ns[-1]]),
            "right_by_steps": {str(k): v for k, v in counts.items()}}


def load(ckpt, device):
    d = torch.load(ckpt, map_location=device)
    net = FlowNet().to(device)
    net.load_state_dict(d["state"])
    return net


def run_eval(a):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    net = load(a.ckpt, device)
    tests = R.load_tests(a.tests, a.limit)
    res = {"arm": "flow", "ckpt": str(a.ckpt), "graded_steps": N_TEST, "tests": {}}
    for name, env, size, seed, role in R.TESTS:
        r = evaluate(net, tests[name], device)
        r["role"] = role
        res["tests"][name] = r
        print(name, json.dumps(r), flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


def smoke(_):
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    R.make_tests(argparse.Namespace(out=tmp / "tests"))
    train(argparse.Namespace(seed=1, out=tmp / "flow", steps=6, batch=16, lr=3e-4, warmup=2, latin_pool=50, log_every=2))
    run_eval(argparse.Namespace(ckpt=tmp / "flow" / "final.pt", tests=tmp / "tests", limit=10, out=tmp / "t.json"))
    w = sum(p.numel() for p in FlowNet().parameters())
    plain = sum(p.numel() for p in R.Net("plain").parameters())
    assert abs(w - plain) / plain <= 0.02, (w, plain)
    print("smoke ok", tmp, "flow weights", w, "plain", plain)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("train")
    p.add_argument("--seed", type=int, required=True); p.add_argument("--out", required=True)
    p.add_argument("--steps", type=int, default=60000); p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=3e-4); p.add_argument("--warmup", type=int, default=1000)
    p.add_argument("--latin-pool", type=int, default=20000); p.add_argument("--log-every", type=int, default=500)
    p = sub.add_parser("eval")
    p.add_argument("--ckpt", required=True); p.add_argument("--tests", required=True); p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=None)
    sub.add_parser("smoke")
    a = ap.parse_args()
    {"train": train, "eval": run_eval, "smoke": smoke}[a.cmd](a)


if __name__ == "__main__":
    main()
