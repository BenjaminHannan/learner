#!/usr/bin/env python3
"""slp-358sf: does a night that practises the day's MISTAKES first beat a night that practises the day at random?
(sleep research thread, 2026-09-26; the "surprises first" step of the sleep map: prioritise what the model got wrong.)

Base: slp-358n2's sleep night (scripts/claude_slp358n2_nights.py, registered PASS). ONE change, in which day puzzles
the night's day batches are drawn from:
  S  random: a kind (half each), a shape, 64 day puzzles drawn from all of that kind's day puzzles (= slp-358n2 sleep)
  P  mistakes first: the same, but drawn only from the day puzzles of that kind the model got WRONG on that day's try
     (all checked answers still come from code; if a kind has fewer than 16 misses, draw from all of that kind)
  N  no night
Rehearsal batches (half the steps), step count, learning rate, tests and scoring are identical. Scores after night 3;
marks in artifacts/claude-slp358sf-20260926/PASSMARKS.md. Caution noted before running: "most surprising" can chase
noise; here every answer is code-checked, so a miss is a real miss, not a noisy label.

  python -B scripts/claude_slp358sf_nights.py run --seed 9 --out DIR
  python -B scripts/claude_slp358sf_nights.py smoke
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rsn358a_run as R  # noqa: E402
import claude_slp358n2_nights as N2  # noqa: E402  (patches N.night_batches / N.shuffled_answers)

N = N2.N
E = N.E
ARMS = "SPN"
MIN_MISSES = 16


@torch.no_grad()
def wrong_items(net, items, bs=100):
    """the items the net gets wrong after N.ROUNDS rounds (same scoring as N.score)."""
    net.eval()
    groups = {}
    for it in items:
        groups.setdefault((len(it.tokens), len(it.tokens[0])), []).append(it)
    out = []
    for g in groups.values():
        for i in range(0, len(g), bs):
            chunk = g[i:i + bs]
            t, s, _, env = R.tensors(chunk, "cpu")
            preds, _ = net.loop_rounds(t, s, env, N.ROUNDS)
            out += [it for it, p in zip(chunk, preds[:, -1].tolist()) if not E.check(it, R.grid_of(p, it))]
    return out


def mistakes_first(day, wrong):
    """per kind: the missed puzzles if there are at least MIN_MISSES, else all of that kind."""
    keep = []
    for kind in sorted({it.env for it in day}):
        miss = [it for it in wrong if it.env == kind]
        keep += miss if len(miss) >= MIN_MISSES else [it for it in day if it.env == kind]
    return keep


def run(a, cfg=N.CFG):
    torch.manual_seed(a.seed)
    torch.set_num_threads(a.threads)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    trng = random.Random(58600)                            # same fixed tests as slp-358n / n2 / t / lp
    tests = {"day_sums": [E.make_sum(trng, trng.choice([5, 6])) for _ in range(cfg["n_test"])],
             "day_grids": [E.latin_item(trng, *E.make_latin_base(trng, 5)) for _ in range(cfg["n_test"])],
             "harm_sums4": [E.make_sum(trng, 4) for _ in range(cfg["n_harm"])],
             "harm_grids4": [E.latin_item(trng, *E.make_latin_base(trng, 4)) for _ in range(cfg["n_harm"])],
             "transfer_sums8": [E.make_sum(trng, 8) for _ in range(cfg["n_transfer"])],
             "transfer_grids6": [E.latin_item(trng, *E.make_latin_base(trng, 6)) for _ in range(cfg["n_transfer"])]}
    test_keys = {N.key(it) for v in tests.values() for it in v}
    rng = random.Random(58610 + a.seed)
    rr = random.Random(58620 + a.seed)
    net = R.Net("loop")
    opt = torch.optim.AdamW(net.parameters(), lr=cfg["pre_lr"], weight_decay=0.1)
    N.train_steps(net, opt, [N.practice_batch(rng, cfg["batch"]) for _ in range(cfg["pre_steps"])], rr)
    log = {"seed": a.seed, "cfg": cfg, "min_misses": MIN_MISSES, "morning": {}, "day": {}, "excluded_day_items_in_tests": 0}

    def morning(n):
        return {k: N.score(n, v) for k, v in tests.items()}
    log["morning"]["base"] = morning(net)
    print("base", json.dumps(log["morning"]["base"]), f"{(time.time() - t0) / 60:.1f} min", flush=True)
    nets = {arm: copy.deepcopy(net) for arm in ARMS}
    opts = {arm: torch.optim.AdamW(nets[arm].parameters(), lr=cfg["night_lr"], weight_decay=0.1) for arm in "SP"}
    for day in range(1, cfg["days"] + 1):
        drng = random.Random(58700 + 10 * a.seed + day)
        sums, grids = N.day_items(drng, cfg["n_day"])
        items = [it for it in sums + grids if N.key(it) not in test_keys]
        log["excluded_day_items_in_tests"] += len(sums) + len(grids) - len(items)
        log["day"][str(day)] = {}
        for arm in ARMS:
            wrong = wrong_items(nets[arm], items)
            rec = {"sums_right": sum(it.env == "sums" for it in items) - sum(it.env == "sums" for it in wrong),
                   "grids_right": sum(it.env == "grids" for it in items) - sum(it.env == "grids" for it in wrong),
                   "n": len(items)}
            log["day"][str(day)][arm] = rec
            if arm == "N":
                continue
            data = items if arm == "S" else mistakes_first(items, wrong)
            rec["night_pool"] = {k: sum(it.env == k for it in data) for k in ("sums", "grids")}
            nrng = random.Random(58900 + 10 * a.seed + day)  # same batch-plan seed for S and P
            N.train_steps(nets[arm], opts[arm], N2.night_batches("S", data, nrng, cfg), rr)
        log["morning"][str(day)] = {arm: morning(nets[arm]) for arm in ARMS}
        print("morning", day, json.dumps(log["morning"][str(day)]), json.dumps(log["day"][str(day)]),
              f"{(time.time() - t0) / 60:.1f} min", flush=True)
    log["minutes"] = round((time.time() - t0) / 60, 1)
    (out / f"slp358sf-seed{a.seed}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


def smoke(_):
    import tempfile
    cfg = dict(N.CFG, pre_steps=4, night_steps=6, batch=8, days=1, n_day=6, n_test=6, n_harm=4, n_transfer=3)
    tmp = Path(tempfile.mkdtemp())
    run(argparse.Namespace(seed=1, out=tmp, threads=2), cfg)
    d = json.loads((tmp / "slp358sf-seed1.json").read_text())
    assert set(d["morning"]["1"]) == set(ARMS) and "night_pool" in d["day"]["1"]["P"]
    day = [E.make_sum(random.Random(i), 5) for i in range(20)] + [E.latin_item(random.Random(i), *E.make_latin_base(random.Random(i), 5)) for i in range(20)]
    kept = mistakes_first(day, day[:17] + day[20:25])
    assert sum(it.env == "sums" for it in kept) == 17 and sum(it.env == "grids" for it in kept) == 20
    print("smoke ok", tmp, json.dumps(d["day"]["1"]))


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
