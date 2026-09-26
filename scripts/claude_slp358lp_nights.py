#!/usr/bin/env python3
"""slp-358lp: does picking the night's practice by LEARNING PROGRESS beat picking it at random?
(sleep research thread, 2026-09-26; Ben's yes 02:06 UTC; idea from "Self-Play Pretraining with Zero Data": a practice
item is worth more when its lesson pushes the weights the way they have recently been moving.)

Base: slp-358n2 (scripts/claude_slp358n2_nights.py, registered PASS): the small loop reasoner practises small sizes,
then 3 days of fresh 5-6 digit sums and 5x5 grids, each followed by a night of 300 small steps, half the day's
puzzles with checked answers and half old practice. ONE change, in how a night's DAY batches are picked:
  S  random (exactly slp-358n2's sleep arm): each day batch = a kind (half each), a shape, 64 random day puzzles
  L  learning progress: draw K=4 candidate day batches the same way; score each by the cosine between its descent
     direction (minus its loss gradient) and the recent weight movement (an average of the last steps' weight
     changes, decay 0.9); train on the best. The first day step of each night has no movement yet: take candidate 1.
  F  flipped control: same candidates and scores, train on the WORST (the paper's flipped-reward control)
  N  no night
Rehearsal batches, step count, learning rate, tests and scoring are identical. A "shuffled scores" arm would pick a
uniformly random candidate, the same distribution as S, so S is that control.
Scores after night 3; marks in artifacts/claude-slp358lp-20260926/PASSMARKS.md.

  python -B scripts/claude_slp358lp_nights.py run --seed 7 --out DIR
  python -B scripts/claude_slp358lp_nights.py smoke
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_run as R  # noqa: E402
import claude_slp358n2_nights as N2  # noqa: E402  (patches N.night_batches / N.shuffled_answers)

N = N2.N
K, DECAY = 4, 0.9
ARMS = "SLFN"


def loss_of(net, items, rr):
    t, s, y, env = R.tensors(items, "cpu")
    total = rr.randint(1, 12)
    k = rr.randint(1, min(total, 4))
    outs = net.loop_train(t, s, env, total - k, k)
    loss = 0
    for lg, q in outs:
        ce, ex = R.ce_and_exact(lg, s, y)
        loss = loss + ce + 0.5 * F.binary_cross_entropy_with_logits(q.float(), ex)
    return loss / k


def flat_grad(net, items, rr):
    net.zero_grad(set_to_none=True)
    loss_of(net, items, rr).backward()
    return torch.cat([(p.grad if p.grad is not None else torch.zeros_like(p)).reshape(-1) for p in net.parameters()])


def night(arm, net, opt, day, rng, rr, cfg, log):
    """S: slp-358n2's night unchanged. L/F: day batches chosen among K candidates by learning progress."""
    if arm == "S":
        N.train_steps(net, opt, N2.night_batches("S", day, rng, cfg), rr)
        return
    groups = {}
    for it in day:
        groups.setdefault(it.env, {}).setdefault((len(it.tokens), len(it.tokens[0])), []).append(it)
    groups = {k: list(v.values()) for k, v in sorted(groups.items())}
    names = sorted(groups)
    move, prev = None, None
    picks = []
    for _ in range(cfg["night_steps"]):
        if rng.random() < 0.5:
            batch = N.practice_batch(rng, cfg["batch"])
        else:
            cands = []
            for _ in range(K):
                g = rng.choice(groups[rng.choice(names)])
                cands.append([rng.choice(g) for _ in range(cfg["batch"])])
            if move is None:
                batch, pick = cands[0], 0
            else:
                srr = random.Random(rr.random())
                net.train()
                scores = [F.cosine_similarity(-flat_grad(net, c, srr), move, dim=0).item() for c in cands]
                pick = max(range(K), key=lambda i: scores[i]) if arm == "L" else min(range(K), key=lambda i: scores[i])
            batch = cands[pick]
            picks.append(pick)
        before = torch.cat([p.detach().reshape(-1) for p in net.parameters()])
        N.train_steps(net, opt, [batch], rr)
        after = torch.cat([p.detach().reshape(-1) for p in net.parameters()])
        d = after - before
        move = d if move is None else DECAY * move + (1 - DECAY) * d
    log.setdefault("picks", []).append({str(i): picks.count(i) for i in range(K)})


def run(a, cfg=N.CFG):
    torch.manual_seed(a.seed)
    torch.set_num_threads(a.threads)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    trng = random.Random(58600)                            # same fixed tests as slp-358n / n2 / t
    tests = {"day_sums": [N.E.make_sum(trng, trng.choice([5, 6])) for _ in range(cfg["n_test"])],
             "day_grids": [N.E.latin_item(trng, *N.E.make_latin_base(trng, 5)) for _ in range(cfg["n_test"])],
             "harm_sums4": [N.E.make_sum(trng, 4) for _ in range(cfg["n_harm"])],
             "harm_grids4": [N.E.latin_item(trng, *N.E.make_latin_base(trng, 4)) for _ in range(cfg["n_harm"])],
             "transfer_sums8": [N.E.make_sum(trng, 8) for _ in range(cfg["n_transfer"])],
             "transfer_grids6": [N.E.latin_item(trng, *N.E.make_latin_base(trng, 6)) for _ in range(cfg["n_transfer"])]}
    test_keys = {N.key(it) for v in tests.values() for it in v}
    rng = random.Random(58610 + a.seed)
    rr = random.Random(58620 + a.seed)
    net = R.Net("loop")
    opt = torch.optim.AdamW(net.parameters(), lr=cfg["pre_lr"], weight_decay=0.1)
    N.train_steps(net, opt, [N.practice_batch(rng, cfg["batch"]) for _ in range(cfg["pre_steps"])], rr)
    log = {"seed": a.seed, "cfg": cfg, "K": K, "decay": DECAY, "morning": {}, "day": {}, "arm_log": {},
           "excluded_day_items_in_tests": 0}

    def morning(n):
        return {k: N.score(n, v) for k, v in tests.items()}
    log["morning"]["base"] = morning(net)
    print("base", json.dumps(log["morning"]["base"]), f"{(time.time() - t0) / 60:.1f} min", flush=True)
    nets = {arm: copy.deepcopy(net) for arm in ARMS}
    opts = {arm: torch.optim.AdamW(nets[arm].parameters(), lr=cfg["night_lr"], weight_decay=0.1) for arm in "SLF"}
    for day in range(1, cfg["days"] + 1):
        drng = random.Random(58700 + 10 * a.seed + day)
        sums, grids = N.day_items(drng, cfg["n_day"])
        items = [it for it in sums + grids if N.key(it) not in test_keys]
        log["excluded_day_items_in_tests"] += len(sums) + len(grids) - len(items)
        log["day"][str(day)] = {}
        for arm in ARMS:
            log["day"][str(day)][arm] = {"sums_right": N.score(nets[arm], [i for i in items if i.env == "sums"]),
                                         "grids_right": N.score(nets[arm], [i for i in items if i.env == "grids"]),
                                         "n": len(items)}
            if arm == "N":
                continue
            nrng = random.Random(58900 + 10 * a.seed + day)  # same seed for S, L, F (L/F draw more, so streams part)
            night(arm, nets[arm], opts[arm], items, nrng, rr, cfg, log["arm_log"].setdefault(arm, {}))
        log["morning"][str(day)] = {arm: morning(nets[arm]) for arm in ARMS}
        print("morning", day, json.dumps(log["morning"][str(day)]), f"{(time.time() - t0) / 60:.1f} min", flush=True)
    log["minutes"] = round((time.time() - t0) / 60, 1)
    (out / f"slp358lp-seed{a.seed}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


def smoke(_):
    import tempfile
    cfg = dict(N.CFG, pre_steps=4, night_steps=6, batch=8, days=1, n_day=6, n_test=6, n_harm=4, n_transfer=3)
    tmp = Path(tempfile.mkdtemp())
    run(argparse.Namespace(seed=1, out=tmp, threads=2), cfg)
    d = json.loads((tmp / "slp358lp-seed1.json").read_text())
    assert set(d["morning"]["1"]) == set(ARMS)
    assert all("picks" in d["arm_log"][arm] for arm in "LF")
    print("smoke ok", tmp, json.dumps(d["arm_log"]))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--seed", type=int, required=True); p.add_argument("--out", required=True)
    p.add_argument("--threads", type=int, default=2)
    sub.add_parser("smoke")
    a = ap.parse_args()
    {"run": run, "smoke": smoke}[a.cmd](a)


if __name__ == "__main__":
    main()
