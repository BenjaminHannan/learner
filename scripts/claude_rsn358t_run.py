#!/usr/bin/env python3
"""rsn-358t (sleep research thread, 2026-09-26): rsn-358i (scripts/claude_rsn358i_run.py: 358a v2 + grid legend +
half-narrow attention) with ONE change, the loop's TRAINING SCHEDULE, copied in outline from the Tiny Recursive
Model (TRM, arXiv 2510.04871). Why: artifacts/claude-rsn358i-20260926/NOTE-vs-TRM.md rows 1, 2, 4.

358i's loop schedule (scripts/claude_rsn358a_run.py:291-299): each batch draws 1-16 rounds from a blank state and
grades the answer after each of the last 1-6 rounds, so one batch in 16 grades a bare round-1 answer. Training never
goes past 16 rounds, but tests run up to 48.
358t's schedule ("carried state", TRM-style deep supervision):
  - a batch of one puzzle kind lives for up to N_SUP = 16 optimizer steps ("segments");
  - each segment continues from the state the previous segment left (carried forward, detached): F_ROUNDS = 4
    rounds without gradient, then G_ROUNDS = 4 rounds with gradient, then ONE grade (answer loss + stop-head loss)
    on the final round only; the answer is never graded on a fresh first pass alone;
  - a puzzle whose answer has been exactly right at the end of 2 segments in a row leaves the batch and is replaced
    by a fresh puzzle of the same kind with a blank state (easy puzzles leave, so practice goes to hard ones);
  - EMA of the weights (decay 0.999); the EMA weights are the ones saved as final.pt and tested.
One segment costs about what one 358i loop step costs (8 rounds forward and 4 back, vs about 8.5 forward and 3.5 back
on average), and the number of optimizer steps (60,000), batch, lr, schedule, data stream, nets, tests and the v2
stop rule are 358i's. A puzzle can be practised up to 16 x 8 = 128 rounds deep, so 48 test rounds are practised.
TRM's other settings (weight decay 1.0, lr 1e-4, batch 768, two states, stable-max loss) are NOT copied.

The plain arm here is report-only: 358i's plain recipe unchanged plus an EMA copy (final.pt = EMA, final-raw.pt =
raw weights, which re-run 358i's plain recipe). The graded comparison uses 358i's own plain results.

  python -B scripts/claude_rsn358t_run.py train --arm loop|plain --seed S --out DIR      (other flags as 358a)
  python -B scripts/claude_rsn358t_run.py eval --ckpt DIR/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out F
  python -B scripts/claude_rsn358t_run.py smoke | check-mask | audit | selftest
"""
from __future__ import annotations

import copy
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358i_run as I  # noqa: E402  (legend grids + v2 stop rule + half-narrow heads)

R, E = I.R, I.E
F_ROUNDS, G_ROUNDS, N_SUP, KEEP_RIGHT, EMA_DECAY = 4, 4, 16, 2, 0.999


def segment(net, h, t, s, env):
    """F_ROUNDS rounds without gradient from the carried state, then G_ROUNDS with gradient; read the last round"""
    e, (dr, dc) = net.embed(t, s, env)
    with torch.no_grad():
        for _ in range(F_ROUNDS):
            h = net.step(h, e, dr, dc)
    h = h.detach()
    for _ in range(G_ROUNDS):
        h = net.step(h, e, dr, dc)
    return h, net.read(h)


@torch.no_grad()
def ema_update(ema, net):
    for pe, p in zip(ema.parameters(), net.parameters()):
        pe.lerp_(p.detach(), 1 - EMA_DECAY)


def train(a):
    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    src = R.Source(a.seed, latin_pool=a.latin_pool)
    dev_rng = random.Random(7000 + a.seed)
    dev = {f"{env}{size}": [E.make_sum(dev_rng, size) if env == "sums" else
                            E.latin_item(dev_rng, *E.make_latin_base(dev_rng, size)) for _ in range(200)]
           for env, size in (("sums", 4), ("grids", 5))}
    net = R.Net(a.arm).to(device)
    ema = copy.deepcopy(net)
    for p in ema.parameters():
        p.requires_grad_(False)
    nparams = sum(p.numel() for p in net.parameters())
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=0.1, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda i: min(1, (i + 1) / a.warmup) * 0.5 *
                                              (1 + math.cos(math.pi * min(i, a.steps) / a.steps)))
    amp = torch.autocast("cuda", dtype=torch.bfloat16) if device == "cuda" else torch.autocast("cpu", enabled=False)
    log = open(out / "train_log.jsonl", "w", encoding="utf-8")
    run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0, "replaced": 0, "batches": 0}
    print(f"{a.arm} seed {a.seed}: {nparams} weights, data ready in {time.time() - t0:.0f}s on {device}", flush=True)
    step = 0

    def after_step(ce, hl, exact, kind):
        nonlocal run
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        ema_update(ema, net)
        run["ce"] += ce.item(); run["exact"] += exact.mean().item(); run["halt"] += float(hl.detach()); run["n"] += 1
        k = run.setdefault("by_kind", {}).setdefault(kind, [0.0, 0])
        k[0] += exact.mean().item(); k[1] += 1
        if step % a.log_every == 0 or step == a.steps:
            n = run["n"]
            rec = {"step": step, "ce": round(run["ce"] / n, 4), "exact": round(run["exact"] / n, 4),
                   "halt_bce": round(run["halt"] / n, 4), "lr": sched.get_last_lr()[0],
                   "replaced": run["replaced"], "batches": run["batches"], "min": round((time.time() - t0) / 60, 1),
                   "exact_by_kind": {kk: round(v[0] / v[1], 3) for kk, v in sorted(run.get("by_kind", {}).items())}}
            if step % (a.log_every * 5) == 0 or step == a.steps:
                rec["dev_ema"] = {kk: R.evaluate(ema, v, device)["right"] for kk, v in dev.items()}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            run = {"ce": 0.0, "exact": 0.0, "halt": 0.0, "n": 0, "replaced": 0, "batches": 0}

    while step < a.steps:
        net.train()
        items = src.batch(a.batch)
        env_name, size = items[0].env, items[0].size
        kind = f"{env_name}{size}"
        t, s, y, env = R.tensors(items, device)
        run["batches"] += 1
        if a.arm == "plain":
            with amp:
                ce, exact = R.ce_and_exact(net.plain_forward(t, s, env), s, y)
            opt.zero_grad(set_to_none=True)
            ce.backward()
            step += 1
            after_step(ce, torch.zeros(()), exact, kind)
            continue
        B, T = t.shape[0], t.shape[1] * t.shape[2]
        h = torch.zeros(B, T, R.ARMS["loop"]["d"], device=device)
        streak = torch.zeros(B, device=device)
        for seg in range(N_SUP):
            if step >= a.steps:
                break
            net.train()
            with amp:
                h, (lg, q) = segment(net, h, t, s, env)
                ce, exact = R.ce_and_exact(lg, s, y)
                hl = F.binary_cross_entropy_with_logits(q.float(), exact)
                loss = ce + 0.5 * hl
            opt.zero_grad(set_to_none=True)
            loss.backward()
            step += 1
            after_step(ce, hl, exact, kind)
            h = h.detach().float()
            streak = (streak + 1) * exact
            done = (streak >= KEEP_RIGHT).nonzero().flatten().tolist()
            if done and seg < N_SUP - 1:
                ft, fs, fy, _ = R.tensors([src.item(env_name, size) for _ in done], device)
                t[done], s[done], y[done] = ft, fs, fy
                h[done] = 0.0
                streak[done] = 0.0
                run["replaced"] += len(done)
    torch.save({"arm": a.arm, "seed": a.seed, "state": ema.state_dict(), "weights": "ema"}, out / "final.pt")
    torch.save({"arm": a.arm, "seed": a.seed, "state": net.state_dict(), "weights": "raw"}, out / "final-raw.pt")
    json.dump({"arm": a.arm, "seed": a.seed, "weights": nparams, "steps": a.steps, "batch": a.batch, "lr": a.lr,
               "warmup": a.warmup, "latin_pool": a.latin_pool, "schedule": "carried-state" if a.arm == "loop" else "358i",
               "F_ROUNDS": F_ROUNDS, "G_ROUNDS": G_ROUNDS, "N_SUP": N_SUP, "KEEP_RIGHT": KEEP_RIGHT,
               "EMA_DECAY": EMA_DECAY, "minutes": round((time.time() - t0) / 60, 1), "device": device},
              open(out / "train_summary.json", "w"), indent=1)


R.train = train                  # R.main and R.smoke look the name up at call time


def selftest():
    """CPU: a carried segment backprops only through the last G_ROUNDS; replacement resets state; EMA moves"""
    torch.manual_seed(0)
    net = R.Net("loop")
    it = [E.make_sum(random.Random(i), 4) for i in range(4)]
    t, s, y, env = R.tensors(it, "cpu")
    h0 = torch.zeros(4, t.shape[1] * t.shape[2], R.ARMS["loop"]["d"], requires_grad=True)
    h, (lg, q) = segment(net, h0, t, s, env)
    lg.sum().backward()
    assert h0.grad is None or float(h0.grad.abs().sum()) == 0.0, "gradient leaked into the carried state"
    ema = copy.deepcopy(net)
    before = [p.clone() for p in ema.parameters()]
    with torch.no_grad():
        for p in net.parameters():
            p.add_(1.0)
    ema_update(ema, net)
    moved = sum(float((p.detach() - b.detach()).abs().sum()) for p, b in zip(ema.parameters(), before))
    assert moved > 0, "EMA did not move"
    print("selftest ok: carried state gets no gradient; EMA updates")


if __name__ == "__main__":
    cmd = sys.argv[1:]
    if cmd == ["check-mask"]:
        I.check_mask()
    elif cmd == ["audit"]:
        I.G.audit()
    elif cmd == ["selftest"]:
        selftest()
    else:
        R.main()
