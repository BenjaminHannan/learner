#!/usr/bin/env python3
"""tgt-5: does sleep make the model match an answer to the RIGHT target? (creative research thread, 2026-09-26;
experiment A of the GPT-6 Pro review of the 09-25 results, reviews/gpt6pro-creative-problems-2026-09-26.md)

Why: blurt-5s showed sleeping on correct answers to newly won puzzles widens coverage whoever wrote the answers, and
that repeating known answers collapses it. The reviewer's point: none of our tables separates "sleep taught the
model which expressions fit which target" from "sleep just broadened which expressions it likes". This measures
target matching directly, with no sampling.

Measure: for a 3-number hand, two targets g and h the hand can make, and correct answers a (makes g) and b (makes h)
with the SAME tokenizer length, all four under one model:
    D = log P(a | g) + log P(b | h) - log P(a | h) - log P(b | g)
A preference for an answer that ignores the target cancels out. D > 0 means the model matches answers to their own
targets. log P is the answer's tokens plus end-of-answer, each renormalised over the tokens the rule keeper allows at
that point (the same constraint the guesser samples under); the raw, unmasked version is reported too.
Models: the frozen base, and W trained by the blurt-5s recipe (claude_blurt5s.py, practice seed 9, the DEV
temperature rule, LoRA seeds 0/1/2). E and C (blurt-5s arms) are secondary and reported only.
Pairs: 120 = 2 per hand x 60 fresh 3-number hands (seed 795); no (hand, target) is a practice or DEV puzzle.

  python -B scripts/claude_tgt5.py --model M --out DIR --temps 1.0,1.5 --dev-puzzles F
  python -B scripts/claude_tgt5.py --selftest --model M
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402
import claude_blurt5s as S5  # noqa: E402


def build_pairs(tok, banned, seed=795, n_hands=60, per_hand=2):
    rng = random.Random(seed)
    hands, pairs, tried = set(), [], 0
    while len(hands) < n_hands:
        tried += 1
        assert tried < 20000, "cannot build pairs"
        h = tuple(sorted(rng.randint(1, 9) for _ in range(3)))
        if h in hands:
            continue
        sols = {t: S5.all_solutions(list(h), t) for t in range(5, 41) if (h, t) not in banned}
        sols = {t: v for t, v in sols.items() if v}
        rk = B2.RuleKeeper(tok, list(h), 0)
        ok_tok = {}

        def toks(e):
            if e not in ok_tok:
                ids = tok(e, add_special_tokens=False)["input_ids"]
                good = all(i in rk.allowed(tok.decode(ids[:j], skip_special_tokens=True)) for j, i in enumerate(ids))
                ok_tok[e] = len(ids) if good else None
            return ok_tok[e]
        cands = []
        ts = sorted(sols)
        for g_i in range(len(ts)):
            for h_i in range(g_i + 1, len(ts)):
                g, t2 = ts[g_i], ts[h_i]
                la = {}
                for a in sols[g]:
                    n = toks(a)
                    if n:
                        la.setdefault(n, []).append(a)
                for b in sols[t2]:
                    n = toks(b)
                    if n and n in la:
                        cands.append((g, t2, la[n][0], b))
                        break
        used_t, chosen = set(), []
        rng.shuffle(cands)
        for g, t2, a, b in cands:
            if g in used_t or t2 in used_t:
                continue
            chosen.append({"nums": list(h), "g": g, "h": t2, "a": a, "b": b})
            used_t |= {g, t2}
            if len(chosen) == per_hand:
                break
        if len(chosen) < per_hand:
            continue
        hands.add(h)
        pairs += chosen
    return pairs


def logp(s, model, nums, target, expr):
    """(masked, raw) log-probability of expr + end-of-answer after the puzzle prompt."""
    torch = s.torch
    p = {"nums": nums, "target": target}
    pr = s.tok(s.prompt(p), return_tensors="pt")["input_ids"][0]          # exactly as train_lora and generate
    an = s.tok(expr, add_special_tokens=False)["input_ids"] + [s.tok.eos_token_id]
    ids = torch.cat([pr, torch.tensor(an)]).unsqueeze(0).to(s.dev)
    with torch.no_grad():
        lg = model(input_ids=ids).logits[0].float()
    rk = B2.RuleKeeper(s.tok, nums, 0)
    masked = raw = 0.0
    for j, t in enumerate(an):
        row = lg[len(pr) + j - 1]
        raw += float(torch.log_softmax(row, -1)[t])
        allowed = rk.allowed(s.tok.decode(an[:j], skip_special_tokens=True))
        masked += float(row[t] - torch.logsumexp(row[allowed], -1)) if t in allowed else float("-inf")
    return masked, raw


def contrast(s, model, pairs):
    out = []
    for q in pairs:
        n = q["nums"]
        ag, ah = logp(s, model, n, q["g"], q["a"]), logp(s, model, n, q["h"], q["a"])
        bh, bg = logp(s, model, n, q["h"], q["b"]), logp(s, model, n, q["g"], q["b"])
        out.append(tuple(ag[k] + bh[k] - ah[k] - bg[k] for k in (0, 1)))
    return out


def summ(d):
    m = [x[0] for x in d]
    r = [x[1] for x in d]
    return {"pairs_D_pos": int(sum(x > 0 for x in m)), "mean_D": round(float(np.mean(m)), 4),
            "raw_pairs_D_pos": int(sum(x > 0 for x in r)), "raw_mean_D": round(float(np.mean(r)), 4)}


def boot_lower(pairs, diffs, reps=4000, q=0.0167, seed=0):
    """Hand-grouped bootstrap: one-sided lower bound (q quantile) of the mean of diffs; also the upper (1-q)."""
    groups = {}
    for i, p in enumerate(pairs):
        groups.setdefault(tuple(p["nums"]), []).append(i)
    keys = sorted(groups)
    rng = random.Random(seed)
    ms = []
    for _ in range(reps):
        idx = [i for k in (rng.choice(keys) for _ in keys) for i in groups[k]]
        ms.append(float(np.mean([diffs[i] for i in idx])))
    ms.sort()
    return round(ms[int(q * reps)], 4), round(ms[int((1 - q) * reps) - 1], 4)


def run(a):
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    temp, res = B2.pick_temp(s, a)
    train = B2.puzzles(a.train_seed, a.n_train)
    banned = {(tuple(p["nums"]), p["target"]) for p in train}
    if a.dev_puzzles:
        banned |= {(tuple(p["nums"]), p["target"]) for p in
                   (json.loads(x) for x in Path(a.dev_puzzles).read_text().splitlines() if x)}
    pairs = build_pairs(s.tok, banned, a.pair_seed)
    (out / "pairs.jsonl").write_text("".join(json.dumps(q) + "\n" for q in pairs), encoding="utf-8")
    res.update({"temp": temp, "n_pairs": len(pairs), "n_hands": len({tuple(q["nums"]) for q in pairs})})
    d = {"base": contrast(s, s.model, pairs)}
    res["base"] = summ(d["base"])
    print(f"[tgt] base {res['base']}", flush=True)
    own, wins = [], []
    for p in train:
        g = s.answer(p)
        if B1.check(g, p["nums"], p["target"]):
            own.append((p, g))
            continue
        hits = [t for t in s.generate(p, a.n, temp) if B1.check(t, p["nums"], p["target"])]
        if hits:
            wins.append((p, hits[0]))
    ewins = [(p, S5.solver_target(p, h)) for p, h in wins]
    ex_w, ex_e = own + wins, own + ewins
    ex_c = (own * (len(ex_w) // max(1, len(own)) + 1))[:len(ex_w)] if own else []
    res.update({"own": len(own), "wins": len(wins), "examples": len(ex_w)})
    print(f"[tgt] practice own {len(own)} wins {len(wins)}", flush=True)
    for arm, ex in (("W", ex_w), ("E", ex_e), ("C", ex_c)):
        for sd in (0, 1, 2):
            if not ex:
                continue
            m = B2.train_lora(s, list(ex), a.epochs, sd)
            m.eval()
            d[f"{arm}{sd}"] = contrast(s, m, pairs)
            res[f"{arm}_seed{sd}"] = summ(d[f"{arm}{sd}"])
            print(f"[tgt] {arm} seed {sd}: {res[f'{arm}_seed{sd}']}", flush=True)
            del m
            if s.dev == "cuda":
                s.torch.cuda.empty_cache()
    # W minus base, per pair, averaged over the three W seeds (masked D)
    if all(f"W{sd}" in d for sd in (0, 1, 2)):
        diffs = [np.mean([d[f"W{sd}"][i][0] for sd in (0, 1, 2)]) - d["base"][i][0] for i in range(len(pairs))]
        res["W_minus_base_mean_D"] = round(float(np.mean(diffs)), 4)
        res["W_minus_base_bounds_98_33"] = boot_lower(pairs, diffs)
    (out / "contrasts.json").write_text(json.dumps({k: v for k, v in d.items()}), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "tgt5_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest(model_dir):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    pairs = build_pairs(tok, set(), seed=1, n_hands=4)
    assert len(pairs) == 8
    for q in pairs:
        assert B1.check(q["a"], q["nums"], q["g"]) and B1.check(q["b"], q["nums"], q["h"]) and q["g"] != q["h"]
        assert not B1.check(q["a"], q["nums"], q["h"]) and not B1.check(q["b"], q["nums"], q["g"])
        la = len(tok(q["a"], add_special_tokens=False)["input_ids"])
        assert la == len(tok(q["b"], add_special_tokens=False)["input_ids"])
    print("selftest ok", pairs[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--train-seed", type=int, default=9)
    ap.add_argument("--n-train", type=int, default=400)
    ap.add_argument("--pair-seed", type=int, default=795)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--temps", default="1.0,1.5")
    ap.add_argument("--dev-puzzles", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest(a.model) if a.selftest else run(a)


if __name__ == "__main__":
    main()
