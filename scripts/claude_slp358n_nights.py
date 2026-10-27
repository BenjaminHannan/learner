#!/usr/bin/env python3
"""slp-358n: does a night of sleep make the small reasoner better at the day's kind of puzzle, without harm?
(sleep research thread, 2026-09-26; plan design/v3/30-modes/slp-358n-reasoner-nights.md, marks
artifacts/claude-slp358n-20260926/PASSMARKS.md). CPU, small nets, $0. No relation facts.

The reasoner is 358a's loop net made small (width 256, 2 layers; scripts/claude_rsn358a_run.py). It first practises
the small sizes (sums up to 4 digits, 4x4 Latin grids). Then 3 days, each followed by a night:
  day    it tries 300 fresh sums (5-6 digits) and 300 fresh 5x5 grids, sizes it never practised. Every try is graded
         and every puzzle gets its checked answer from code (the creative thread found solver answers teach as well
         as the model's own lucky hits, blurt-5s).
  night  300 small steps (lr 1e-4, a tenth of the day-0 rate), each batch half the day's puzzles with answers, half
         old practice (rehearsal). Arms:
           S  sleep: the day's puzzles with their right answers
           R  rehearsal-only night: same steps, all old practice (controls for "just more training")
           Z  placebo night: the day's puzzles with answers shuffled between puzzles of the same kind and size
           N  no night at all
  morning  fixed fresh tests (never a day item): 400 sums (5-6 digits), 400 5x5 grids; harm check: 300 4-digit sums,
           300 4x4 grids (practised sizes); transfer (report): 200 8-digit sums, 200 6x6 grids.
Scoring: exact code check of the answer after 8 rounds of thinking (fixed, so no stop rule is involved).

  python -B scripts/claude_slp358n_nights.py run --seed 1 --out DIR        (one seed, all arms; ~1-2 h on 2 CPU threads)
  python -B scripts/claude_slp358n_nights.py smoke
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
import claude_rsn358a_envs as E  # noqa: E402
import claude_rsn358a_run as R  # noqa: E402

R.ARMS = {"loop": dict(d=256, layers=2, heads=4)}
ROUNDS = 8
CFG = dict(pre_steps=3000, pre_lr=1e-3, night_steps=300, night_lr=1e-4, batch=64, days=3, n_day=300,
           n_test=400, n_harm=300, n_transfer=200)


def practice_item(rng):
    if rng.random() < 0.5:
        return E.make_sum(rng, rng.choice([1, 2, 3, 4]))
    return E.latin_item(rng, *E.make_latin_base(rng, 4))


def practice_batch(rng, B):
    first = practice_item(rng)
    same = (lambda: E.make_sum(rng, first.size)) if first.env == "sums" else \
        (lambda: E.latin_item(rng, *E.make_latin_base(rng, 4)))
    return [first] + [same() for _ in range(B - 1)]


def day_items(rng, n):
    sums = [E.make_sum(rng, rng.choice([5, 6])) for _ in range(n)]
    grids = [E.latin_item(rng, *E.make_latin_base(rng, 5)) for _ in range(n)]
    return sums, grids


def key(it):
    return json.dumps(it.tokens)


def train_steps(net, opt, batches, rr):
    net.train()
    for items in batches:
        t, s, y, env = R.tensors(items, "cpu")
        total = rr.randint(1, 12)
        k = rr.randint(1, min(total, 4))
        outs = net.loop_train(t, s, env, total - k, k)
        loss = 0
        for lg, q in outs:
            ce, ex = R.ce_and_exact(lg, s, y)
            loss = loss + ce + 0.5 * F.binary_cross_entropy_with_logits(q.float(), ex)
        loss = loss / k
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()


@torch.no_grad()
def score(net, items, bs=100):
    """right after ROUNDS rounds; groups by grid shape so each batch has one shape."""
    net.eval()
    groups = {}
    for it in items:
        groups.setdefault((len(it.tokens), len(it.tokens[0])), []).append(it)
    right = 0
    for g in groups.values():
        for i in range(0, len(g), bs):
            chunk = g[i:i + bs]
            t, s, _, env = R.tensors(chunk, "cpu")
            preds, _ = net.loop_rounds(t, s, env, ROUNDS)
            right += sum(E.check(it, R.grid_of(p, it)) for it, p in zip(chunk, preds[:, -1].tolist()))
    return right


def answered(items, answers_from):
    """copy of items whose targets come from answers_from (same shapes)."""
    return [E.Item(it.env, it.size, it.tokens, it.slot, src.target, it.meta) for it, src in zip(items, answers_from)]


def shuffled_answers(items, rng):
    """placebo: each puzzle gets another same-shape puzzle's answer."""
    by = {}
    for i, it in enumerate(items):
        by.setdefault((it.env, len(it.tokens), len(it.tokens[0])), []).append(i)
    src = list(range(len(items)))
    for idx in by.values():
        perm = idx[:]
        rng.shuffle(perm)
        for a, b in zip(idx, perm):
            src[a] = b
    return answered(items, [items[j] for j in src])


def night_batches(arm, day, rng, cfg):
    """half day batches, half rehearsal (S, Z); all rehearsal (R). Day batches keep one grid shape each."""
    groups = {}
    for it in day:
        groups.setdefault((it.env, len(it.tokens), len(it.tokens[0])), []).append(it)
    groups = list(groups.values())
    out = []
    for _ in range(cfg["night_steps"]):
        if arm == "R" or rng.random() < 0.5:
            out.append(practice_batch(rng, cfg["batch"]))
        else:
            g = rng.choice(groups)
            out.append([rng.choice(g) for _ in range(cfg["batch"])])
    return out


def run(a, cfg=CFG):
    torch.manual_seed(a.seed)
    torch.set_num_threads(a.threads)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    trng = random.Random(58600)                            # fixed tests, same for every seed and arm
    tests = {"day_sums": [E.make_sum(trng, trng.choice([5, 6])) for _ in range(cfg["n_test"])],
             "day_grids": [E.latin_item(trng, *E.make_latin_base(trng, 5)) for _ in range(cfg["n_test"])],
             "harm_sums4": [E.make_sum(trng, 4) for _ in range(cfg["n_harm"])],
             "harm_grids4": [E.latin_item(trng, *E.make_latin_base(trng, 4)) for _ in range(cfg["n_harm"])],
             "transfer_sums8": [E.make_sum(trng, 8) for _ in range(cfg["n_transfer"])],
             "transfer_grids6": [E.latin_item(trng, *E.make_latin_base(trng, 6)) for _ in range(cfg["n_transfer"])]}
    test_keys = {key(it) for v in tests.values() for it in v}
    rng = random.Random(58610 + a.seed)
    rr = random.Random(58620 + a.seed)
    net = R.Net("loop")
    opt = torch.optim.AdamW(net.parameters(), lr=cfg["pre_lr"], weight_decay=0.1)
    train_steps(net, opt, [practice_batch(rng, cfg["batch"]) for _ in range(cfg["pre_steps"])], rr)
    base = copy.deepcopy(net.state_dict())
    log = {"seed": a.seed, "cfg": cfg, "morning": {}, "day": {}, "excluded_day_items_in_tests": 0}

    def morning(n):
        return {k: score(n, v) for k, v in tests.items()}
    log["morning"]["base"] = morning(net)
    print("base", json.dumps(log["morning"]["base"]), f"{(time.time() - t0) / 60:.1f} min", flush=True)
    nets = {arm: copy.deepcopy(net) for arm in "SRZN"}
    opts = {arm: torch.optim.AdamW(nets[arm].parameters(), lr=cfg["night_lr"], weight_decay=0.1) for arm in "SRZ"}
    for day in range(1, cfg["days"] + 1):
        drng = random.Random(58700 + 10 * a.seed + day)     # the day's puzzles: same for every arm
        sums, grids = day_items(drng, cfg["n_day"])
        items = [it for it in sums + grids if key(it) not in test_keys]
        log["excluded_day_items_in_tests"] += len(sums) + len(grids) - len(items)
        log["day"][str(day)] = {}
        for arm in "SRZN":
            log["day"][str(day)][arm] = {"sums_right": score(nets[arm], [i for i in items if i.env == "sums"]),
                                         "grids_right": score(nets[arm], [i for i in items if i.env == "grids"]),
                                         "n": len(items)}
            if arm == "N":
                continue
            day_data = items if arm == "S" else shuffled_answers(items, random.Random(58800 + 10 * a.seed + day))
            nrng = random.Random(58900 + 10 * a.seed + day)  # same batch plan draw for S and Z
            train_steps(nets[arm], opts[arm], night_batches(arm, day_data, nrng, cfg), rr)
        log["morning"][str(day)] = {arm: morning(nets[arm]) for arm in "SRZN"}
        print("morning", day, json.dumps(log["morning"][str(day)]), f"{(time.time() - t0) / 60:.1f} min", flush=True)
    log["minutes"] = round((time.time() - t0) / 60, 1)
    (out / f"slp358n-seed{a.seed}.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    torch.save(base, out / f"base-seed{a.seed}.pt")


def smoke(_):
    import tempfile
    cfg = dict(CFG, pre_steps=4, night_steps=3, batch=8, days=1, n_day=6, n_test=6, n_harm=4, n_transfer=3)
    tmp = Path(tempfile.mkdtemp())
    run(argparse.Namespace(seed=1, out=tmp, threads=2), cfg)
    d = json.loads((tmp / "slp358n-seed1.json").read_text())
    assert set(d["morning"]["1"]) == set("SRZN")
    it = E.make_sum(random.Random(0), 3)
    sh = shuffled_answers([it, E.make_sum(random.Random(1), 3)], random.Random(2))
    assert len(sh) == 2
    print("smoke ok", tmp)


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
