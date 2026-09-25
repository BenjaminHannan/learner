#!/usr/bin/env python3
"""ask-24ab: is the "none on everything" collapse an answer-format problem? (creative research thread, 2026-09-25;
experiment 2 of the GPT-6 Pro review Ben relayed at 19:13 UTC)

Why: offered "an expression, or the word none", the base 1B said none on 20/20 impossible AND 20/20 solvable DEV
puzzles (ask-24 DEV). The reviewer's hypothesis: the model may partly tell solvable from impossible hands, and the
expression-or-none answer format hides it.

One change, model frozen (no training, no examples, no reasoning asked for): replace "give an expression or none"
with a yes/no question answered by ONE letter, A or B. The decision is read from the model's next-token scores:
whichever of the two letters it scores higher.
  original : ask-24's prompt and decoder (rule keeper + the word none), greedy; "impossible" iff it answers none.
  AB1      : A = "yes, it can be done", B = "no, it cannot be done".
  AB2      : the same question with the letters' meanings swapped (catches a plain liking for one letter).
Panel: 120 impossible and 120 solvable four-card hands (cards 1-13, target 24), built as 120 matched pairs: each
impossible hand with a solvable twin that differs in one card. Every label is proved by exhaustive search. Seed 790.
Scored on meaning (impossible / solvable), not on the letter.

  python -B scripts/claude_ask24ab.py --model M --out DIR
  python -B scripts/claude_ask24ab.py --selftest
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ask24 as A24  # noqa: E402
import claude_blurt1 as B1  # noqa: E402

YES, NO = "yes, it can be done", "no, it cannot be done"


def all_hands():
    return [list(h) for h in itertools.combinations_with_replacement(range(1, 14), 4)]


def panel(seed=790, n_pairs=120):
    """n_pairs (impossible hand, solvable twin differing in one card). Hands are unique across the panel."""
    hands = all_hands()
    ok = {tuple(h): B1.solve(h, 24) is not None for h in hands}
    imp = [h for h in hands if not ok[tuple(h)]]
    rng = random.Random(seed)
    rng.shuffle(imp)
    pairs, used = [], set()
    for h in imp:
        twins = set()
        for i in range(4):
            for c in range(1, 14):
                t = tuple(sorted(h[:i] + [c] + h[i + 1:]))
                if ok[t] and t not in used:
                    twins.add(t)
        if not twins:
            continue
        t = rng.choice(sorted(twins))
        used |= {tuple(h), t}
        pairs.append((h, list(t)))
        if len(pairs) == n_pairs:
            break
    ps = []
    for k, (h, t) in enumerate(pairs):
        ps.append({"id": f"ab-{k:03d}-imp", "nums": h, "target": 24, "solvable": False, "pair": k})
        ps.append({"id": f"ab-{k:03d}-sol", "nums": t, "target": 24, "solvable": True, "pair": k})
    return ps


def ab_prompt(tok, p, a_means_yes: bool) -> str:
    ns = ", ".join(str(n) for n in p["nums"])
    a, b = (YES, NO) if a_means_yes else (NO, YES)
    q = (f"Can the numbers {ns} be combined, using each number exactly once with + - * / and brackets, to make "
         f"{p['target']}? Reply with only one letter: A if {a}, B if {b}.")
    return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
                                   enable_thinking=False)


def letter_ids(tok, letter):
    out = set()
    for v in (letter, " " + letter):
        ids = tok.encode(v, add_special_tokens=False)
        if len(ids) == 1:
            out.add(ids[0])
    return sorted(out)


def ab_decide(s, p, a_means_yes):
    """Returns (says_impossible, p_A, p_B, top_is_letter) from the next-token distribution."""
    torch = s.torch
    ids = s.tok(ab_prompt(s.tok, p, a_means_yes), return_tensors="pt").to(s.dev)
    with torch.no_grad():
        logits = s.model(**ids).logits[0, -1].float()
    pr = torch.softmax(logits, -1)
    pa = float(sum(pr[i] for i in s.a_ids))
    pb = float(sum(pr[i] for i in s.b_ids))
    top = int(pr.argmax())
    says_yes = (pa > pb) if a_means_yes else (pb > pa)
    return (not says_yes), pa, pb, top in s.a_ids + s.b_ids


def score(dec, ps):
    imp_right = sum(1 for d, p in zip(dec, ps) if not p["solvable"] and d)
    sol_false_imp = sum(1 for d, p in zip(dec, ps) if p["solvable"] and d)
    n_imp = sum(not p["solvable"] for p in ps)
    n_sol = len(ps) - n_imp
    ba = 50 * (imp_right / n_imp + (n_sol - sol_false_imp) / n_sol)
    return {"imp_said_impossible": imp_right, "sol_said_impossible": sol_false_imp, "n_imp": n_imp, "n_sol": n_sol,
            "balanced_acc_pct": round(ba, 1),
            "pairs_both_right": sum(1 for k in range(len(ps) // 2) if dec[2 * k] and not dec[2 * k + 1])}


def run(a):
    t0 = time.time()
    s = A24.AskSolver(a.model)
    s.a_ids, s.b_ids = letter_ids(s.tok, "A"), letter_ids(s.tok, "B")
    ps = panel(a.seed, a.n_pairs)
    res = {"n": len(ps), "seed": a.seed, "a_ids": s.a_ids, "b_ids": s.b_ids}
    dec_o, answers_expr_right = [], 0
    for p in ps:
        ans = s.answer(p)
        dec_o.append(A24.is_none(ans))
        answers_expr_right += (not A24.is_none(ans)) and B1.check(ans, p["nums"], p["target"])
    res["original"] = score(dec_o, ps)
    res["original"]["expr_right_on_solvable"] = answers_expr_right
    print(f"[ab] original {res['original']}", flush=True)
    decs = {}
    for name, amy in (("AB1", True), ("AB2", False)):
        rows = [ab_decide(s, p, amy) for p in ps]
        decs[name] = [r[0] for r in rows]
        res[name] = score(decs[name], ps)
        res[name]["mean_mass_on_letters"] = round(sum(r[1] + r[2] for r in rows) / len(rows), 3)
        res[name]["top_token_is_letter"] = sum(r[3] for r in rows)
        res[name]["letter_A_chosen"] = sum(r[1] > r[2] for r in rows)
        print(f"[ab] {name} {res[name]}", flush=True)
    res["flips_AB1_vs_AB2"] = sum(x != y for x, y in zip(decs["AB1"], decs["AB2"]))
    res["minutes"] = round((time.time() - t0) / 60, 1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ask24ab_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


def selftest():
    hands = all_hands()
    assert len(hands) == 1820 and sum(B1.solve(h, 24) is None for h in hands) == 458
    ps = panel()
    assert len(ps) == 240 and len({tuple(p["nums"]) for p in ps}) == 240
    for k in range(120):
        i, t = ps[2 * k], ps[2 * k + 1]
        assert not i["solvable"] and t["solvable"] and B1.solve(i["nums"], 24) is None and B1.solve(t["nums"], 24)
        diff = sum((__import__("collections").Counter(i["nums"]) - __import__("collections").Counter(t["nums"]))
                   .values())
        assert diff == 1, (i, t)
    d = [True, False] * 120
    assert score(d, ps)["balanced_acc_pct"] == 100.0 and score([True] * 240, ps)["balanced_acc_pct"] == 50.0
    print("selftest ok", ps[0]["nums"], ps[1]["nums"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--seed", type=int, default=790)
    ap.add_argument("--n-pairs", type=int, default=120)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    selftest() if a.selftest else run(a)


if __name__ == "__main__":
    main()
