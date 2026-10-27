#!/usr/bin/env python3
"""feas-24: can a cheap head on the frozen 1B tell a still-solvable partial state from a dead end?
(creative research thread, 2026-09-25; experiment 3 of the GPT-6 Pro review Ben relayed at 19:13 UTC)

Why: Tree of Thoughts took GPT-4 from 4% to 74% on the 24 game by judging whether a partial state can still reach 24
(reviews/creative-research-2026-09-25/B-feedback-kinds.md). Ben rejected "22 is close to 24" as warmth and liked
"still solvable?" judges instead. Before putting any judge into search, this asks whether a cheap one works at all.

One change, offline only: a logistic head on the frozen 1B's hidden state. The generator, the search and the LoRA are
untouched.
  State: a 4-card hand (cards 1-13, target 24) after one step (3 values left) or two steps (2 values left); a step
         combines two values with + - * / (fractions and negatives kept exact). Label: can the values left still
         make 24 (exhaustive exact search). Shown to the 1B as "Numbers left: 8/3, 3. Target: 24. ..." and the
         hidden state of the last prompt token is the feature.
  Only 195 distinct 2-value states (and 1,507 distinct 3-value states) can make 24, so states are split by state:
  each distinct sorted value list lives in exactly one of train / dev / test (reachable: 65% / 10% / 25% per stage;
  unreachable states are drawn to match, seed 791). Test: 200 matched pairs from held-out test hands (a quarter of
  the 1,820 hands), each one reachable and one dead-end test-split state from the same hand at the same stage (100
  with 3 values, 100 with 2), one pair per hand and stage, no dead-end state reused, fresh reachable states
  preferred. Train pool: 2,210 states, balanced per stage; each seed 0/1/2 trains on 85% of each (stage, label)
  cell (1,878 states). Dev: 342 states, balanced.
  Frozen before the test: layer from {8, 12, 16, 20, 24} and l2 from {1, 30, 300}, chosen by dev AUC of the seed-0
  real-label head. Placebo: the same head trained on labels shuffled within each stage.
  Pair score: the head ranks the reachable state higher (ties count half).

  python -B scripts/claude_feas24.py --model M --out DIR [--feats F.npz]
  python -B scripts/claude_feas24.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_cre333e_train import fit_lr, predict  # noqa: E402

LAYERS = [8, 12, 16, 20, 24]
L2S = [1.0, 30.0, 300.0]
T = Fraction(24)


def steps(vals):
    """All states after one step: combine two values with + - * / (both orders for - and /)."""
    out = set()
    for i, j in itertools.combinations(range(len(vals)), 2):
        a, b = vals[i], vals[j]
        rest = [vals[k] for k in range(len(vals)) if k not in (i, j)]
        for v in {a + b, a - b, b - a, a * b} | ({a / b} if b else set()) | ({b / a} if a else set()):
            out.add(tuple(sorted(rest + [v])))
    return out


@lru_cache(maxsize=None)
def reach(state) -> bool:
    if len(state) == 1:
        return state[0] == T
    return any(reach(s) for s in steps(list(state)))


def fmt(v: Fraction) -> str:
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def text(state) -> str:
    return (f"Numbers left: {', '.join(fmt(v) for v in state)}. Target: 24. Using each number left exactly once with "
            f"+ - * / and brackets, can they still make the target?")


def build(seed=791, npairs=100):
    """States are split by state (each distinct sorted value list lives in one split) because only 195 distinct
    2-value states can make 24. Reachable states per stage: 25% test, 10% dev, 65% train; unreachable states are
    drawn from the other splits' shares in the same proportions. Test pairs come only from held-out test hands and
    use only test-split states."""
    hands = [tuple(Fraction(c) for c in h) for h in itertools.combinations_with_replacement(range(1, 14), 4)]
    rng = random.Random(seed)
    rng.shuffle(hands)
    test_hands = set(hands[int(0.75 * len(hands)):])
    by_hand, allst = {}, {2: set(), 3: set()}
    for h in hands:
        s3 = steps(list(h))
        s2 = {x for y in s3 for x in steps(list(y))}
        by_hand[h] = {3: s3, 2: s2}
        allst[3] |= s3
        allst[2] |= s2
    split = {}
    for k in (3, 2):
        for lab in (True, False):
            c = sorted(st for st in allst[k] if reach(st) == lab)
            rng.shuffle(c)
            n = len(c)
            for i, st in enumerate(c):
                split[st] = "test" if i < 0.25 * n else "dev" if i < 0.35 * n else "train"
    pairs = {3: [], 2: []}
    for h in sorted(test_hands):
        for k in (3, 2):
            pos = sorted(st for st in by_hand[h][k] if split[st] == "test" and reach(st))
            used = {q for _, _, q in pairs[k]}
            neg = sorted(st for st in by_hand[h][k] if split[st] == "test" and not reach(st) and st not in used)
            if pos and neg and len(pairs[k]) < npairs:
                fresh = [x for x in pos if x not in {pp for _, pp, _ in pairs[k]}]   # prefer unused reachable states
                pairs[k].append((h, rng.choice(fresh or pos), rng.choice(neg)))
    for k in pairs:
        assert len(pairs[k]) == npairs, (k, len(pairs[k]))

    def cells(name):
        out = []
        for k in (3, 2):
            pos = sorted(st for st in allst[k] if split[st] == name and reach(st))
            neg = sorted(st for st in allst[k] if split[st] == name and not reach(st))
            out += [(st, True) for st in pos] + [(st, False) for st in rng.sample(neg, len(pos))]
        return out
    return cells("train"), cells("dev"), pairs


def pair_score(fs, pairs_flat):
    return sum((fs[p] > fs[q]) + 0.5 * (fs[p] == fs[q]) for p, q in pairs_flat)


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum())
                 / (len(pos) * len(neg)))


def features(a, states):
    fp = Path(a.feats) if a.feats else Path(a.out) / "feats.npz"
    if fp.exists():
        d = np.load(fp, allow_pickle=True)
        keys = [tuple(Fraction(x) for x in k.split(",")) for k in d["keys"]]
        assert keys == states, "feature cache does not match the states"
        return d["X"]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model, trust_remote_code=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, dtype=torch.bfloat16).to(dev).eval()
    X = np.zeros((len(states), len(LAYERS), m.config.hidden_size), dtype=np.float32)
    for i, st in enumerate(states):
        s = tok.apply_chat_template([{"role": "user", "content": text(st)}], tokenize=False,
                                    add_generation_prompt=True, enable_thinking=False)
        with torch.no_grad():
            hs = m(**tok(s, return_tensors="pt").to(dev), output_hidden_states=True).hidden_states
        X[i] = np.stack([hs[k][0, -1].float().cpu().numpy() for k in LAYERS])
        if i % 250 == 0:
            print(f"[feats] {i}/{len(states)}", flush=True)
    fp.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(fp, X=X.astype(np.float16), keys=np.array([",".join(str(v) for v in st) for st in states]))
    return X.astype(np.float16)


def run(a):
    t0 = time.time()
    train, dev, pairs = build(a.seed)
    tstates = sorted({s for k in pairs for _, p, q in pairs[k] for s in (p, q)})
    states = [s for s, _ in train] + [s for s, _ in dev] + tstates
    X = features(a, states).astype(np.float32)
    idx = {s: i for i, s in enumerate(states)}
    ntr, ndv = len(train), len(dev)
    ytr = np.array([float(r) for _, r in train])
    ydv = np.array([float(r) for _, r in dev])
    stage_tr = np.array([len(s) for s, _ in train])
    res = {"n_train_pool": ntr, "n_dev": ndv, "n_test_pairs_3": len(pairs[3]), "n_test_pairs_2": len(pairs[2]),
           "train_reachable": int(ytr.sum()), "dev_reachable": int(ydv.sum()),
           "test_distinct_reachable": {k: len({p for _, p, _ in pairs[k]}) for k in pairs}}

    def sub(seed):
        r = np.random.default_rng(seed)
        take = []
        for k in (2, 3):
            for lab in (0.0, 1.0):
                cell = np.where((stage_tr == k) & (ytr == lab))[0]
                take += r.choice(cell, int(0.85 * len(cell)), replace=False).tolist()
        return np.array(sorted(take))

    def shuffled(seed, rows):
        r = np.random.default_rng(1000 + seed)
        y = ytr[rows].copy()
        for k in (2, 3):
            m = stage_tr[rows] == k
            y[m] = r.permutation(y[m])
        return y
    rows0 = sub(0)
    cv = {}
    for li, L in enumerate(LAYERS):
        for l2 in L2S:
            h = fit_lr(X[rows0, li], ytr[rows0], l2=l2)
            p = predict(h, X[ntr:ntr + ndv, li])
            cv[f"{L}/{l2}"] = round(auc(p[ydv == 1], p[ydv == 0]), 4)
            print(f"[dev] layer {L} l2 {l2}: dev AUC {cv[f'{L}/{l2}']}", flush=True)
    best = max(cv, key=cv.get)
    L, l2 = int(best.split("/")[0]), float(best.split("/")[1])
    li = LAYERS.index(L)
    res.update({"dev_auc": cv, "layer": L, "l2": l2})
    pf = {k: [(idx[p], idx[q]) for _, p, q in pairs[k]] for k in pairs}
    for sd in (0, 1, 2):
        rows = sub(sd)
        for arm, y in (("real", ytr[rows]), ("shuffled", shuffled(sd, rows))):
            h = fit_lr(X[rows, li], y, l2=l2)
            fs = predict(h, X[:, li])
            s3, s2 = pair_score(fs, pf[3]), pair_score(fs, pf[2])
            res[f"{arm}_seed{sd}"] = {"pairs_right": s3 + s2, "pairs_right_3": s3, "pairs_right_2": s2}
            print(f"[feas] {arm} seed {sd}: {res[f'{arm}_seed{sd}']}", flush=True)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "feas24_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    F = Fraction
    assert reach((F(3), F(8))) and not reach((F(1), F(1))) and reach((F(3), F(3), F(8, 3)))
    assert reach(tuple(sorted((F(3), F(3), F(8), F(8))))) and not reach((F(1), F(1), F(1), F(1)))
    assert reach((F(8), F(3))) and not reach((F(5), F(7)))
    hands = list(itertools.combinations_with_replacement(range(1, 14), 4))
    assert sum(not reach(tuple(F(c) for c in h)) for h in hands) == 458
    train, dev, pairs = build()
    tr = {s for s, _ in train}
    dv = {s for s, _ in dev}
    ts = {s for k in pairs for _, p, q in pairs[k] for s in (p, q)}
    assert not (tr & ts) and not (tr & dv) and not (dv & ts)
    assert sum(r for _, r in train) * 2 == len(train) and sum(r for _, r in dev) * 2 == len(dev)
    for k in pairs:
        hs = [h for h, _, _ in pairs[k]]
        assert len(hs) == len(set(hs)) == 100 and len({(p, q) for _, p, q in pairs[k]}) == 100
        for h, p, q in pairs[k]:
            assert reach(p) and not reach(q) and len(p) == len(q) == k and p in steps_closure(h, k)
    print("selftest ok", len(train), len(dev), {k: len({p for _, p, _ in pairs[k]}) for k in pairs}, "|",
          text(dev[0][0]), dev[0][1])


def steps_closure(h, k):
    s3 = steps(list(h))
    return s3 if k == 3 else {s for x in s3 for s in steps(list(x))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--feats", default="")
    ap.add_argument("--seed", type=int, default=791)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a)


if __name__ == "__main__":
    main()
