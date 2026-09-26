#!/usr/bin/env python3
"""dl-2: does a week of copy-practice nights keep making the 1B better, night after night, without harm?
(Fix-sleep thread, 2026-09-26; marks: artifacts/claude-dl2-20260926/PASSMARKS.md)

Why. dl-1 (registered FAIL, artifacts/claude-dl1-20260925/) tested REINFORCE as the night rule and it lost. Its
reference arm S (copy practice: the day's greedy right answers + the first lucky hit on each miss, 3 epochs,
lr 2e-4, one growing adapter) improved on every one of its 6 nights: right guesses on fresh puzzles 69 ->
160/169, puzzles reached 35 -> 44/58, and a 300-item general panel went up, not down (200 -> 225/210). That was 3
nights and not the registered claim. Ben's bar is that nights almost never make the model worse and that it keeps
improving at the day's work. Creative's blurt-5s adds that right answers to NEW puzzles are the good material.

ONE change from dl-1's S arm: 7 nights instead of 3 (fresh seeds 2 and 3). Same day (150 new puzzles, 1 greedy +
30 guesses each, exact checker), same night (claude_dl1_nights.train_copy), same TEST / HARM / KL measures.
Arms:
  S  copy practice on checked right answers (dl-1's S).
  P  placebo: the same number of examples, but each is a legal, complete, WRONG guess from that day's puzzles, so S
     and P differ only in whether the practised answers are right.

  python -B scripts/claude_dl2_nights.py --model M --out DIR        (registered run: arms S,P seeds 2,3 nights 7)
  python -B scripts/claude_dl2_nights.py --selftest
  python -B scripts/claude_dl2_nights.py --model M --out DIR --dev  (plumbing rehearsal, tiny counts, other seeds)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt1 as B1  # noqa: E402
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402


def wrong_examples(groups, n, seed) -> list:
    """P: up to n (puzzle, legal complete wrong guess) pairs, at most one per puzzle, from the day's guesses."""
    rng = random.Random(seed)
    out = []
    for g in groups:
        p = g["puzzle"]
        bad = [t for t, r in zip(g["guesses"], g["rewards"]) if not r and B2.complete(t, p["nums"])]
        if bad:
            out.append((p, rng.choice(bad)))
    rng.shuffle(out)
    return out[:n]


def run_arm(s, arm, seed, a, test, panel, replies, base_harm) -> dict:
    s.torch.manual_seed(seed)
    m = D1.fresh_model(s)
    nights = []
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = D1.gather(s, m, day, a.n_guess)
        right = D1.copy_examples(groups)
        ex = right if arm == "S" else wrong_examples(groups, len(right), seed * 1000 + d)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups), "right_examples": len(right)}
        rec["train"] = D1.train_copy(s, m, ex, seed * 1000 + d) if ex else {"examples": 0}
        meas = D1.measure(s, m, test, a.n_guess_test, panel, replies)
        rec["test"] = {k: meas[k] for k in ("lucky", "reached", "greedy")}
        rec["harm"] = D1.flips(base_harm, meas["harm"])
        rec["kl"] = meas["kl"]
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl2] {arm} s{seed} night {d}: {json.dumps(rec)}", flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md)."""
    L0, R0 = res["base"]["lucky"], res["base"]["reached"]
    by = {(r["arm"], r["seed"]): r["nights"] for r in res["arms"]}
    seeds = sorted({r["seed"] for r in res["arms"]})
    fin = {k: v[-1] for k, v in by.items()}
    worse, harm_nights = 0, 0
    for sd in seeds:
        seq = [L0] + [n["test"]["lucky"] for n in by[("S", sd)]]
        worse += sum(1 for x, y in zip(seq, seq[1:]) if y < 0.85 * x)
        harm_nights += sum(1 for n in by[("S", sd)] if n["harm"]["net_harm"] > 5)
    sl = [fin[("S", sd)]["test"]["lucky"] for sd in seeds]
    pl = [fin[("P", sd)]["test"]["lucky"] for sd in seeds]
    m = {"L0": L0, "reached0": R0, "S_final_lucky": sl, "P_final_lucky": pl, "S_worse_nights": worse,
         "S_nights_net_harm_over_5": harm_nights,
         "S_final_net_harm": [fin[("S", sd)]["harm"]["net_harm"] for sd in seeds],
         "S_final_reached": [fin[("S", sd)]["test"]["reached"] for sd in seeds]}
    m["W1 better after a week: S final lucky >= 2 x L0 on each seed"] = all(x >= 2 * L0 for x in sl)
    m["W2 nights rarely hurt the day's work: S nights with TEST lucky > 15% below the night before <= 1 of 14"] = \
        worse <= 1
    m["W3 nights rarely hurt anything else: S nights with net harm > 5 on the panel <= 1 of 14, and final net "
      "harm <= 0 on each seed"] = harm_nights <= 1 and all(x <= 0 for x in m["S_final_net_harm"])
    m["W4 variety kept: S final reached >= base on each seed"] = all(x >= R0 for x in m["S_final_reached"])
    m["W5 right answers caused it: S >= 1.3 x P (means) and each S seed > each P seed"] = \
        sum(sl) >= 1.3 * sum(pl) and min(sl) > max(pl)
    keys = [k for k in m if k[:1] == "W" and k[1].isdigit()]
    m["verdict"] = "INCONCLUSIVE" if L0 < 10 else ("PASS" if all(m[k] for k in keys) else "FAIL")
    m["proved_wrong"] = any(x <= 1.1 * L0 for x in sl) or worse >= 3 or sum(sl) <= sum(pl)
    return m


def run(a) -> None:
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    keys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
            for p in B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    test = [p for p in B2.puzzles(TEST_SEED + a.seed_shift, a.n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in keys][:a.n_test]
    panel = D1.harm_panel()[:a.n_harm]
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "n_test": len(test), "n_harm": len(panel),
           "temp": D1.TEMP, "test_seed": TEST_SEED}
    base = s.model
    replies = [(q, D1.free_answer(s, q, base, 40)) for q in
               (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    bm = D1.measure(s, base, test, a.n_guess_test, panel)
    res["base"] = {k: bm[k] for k in ("lucky", "reached", "greedy")}
    res["base"]["harm_right"] = sum(bm["harm"])
    print(f"[dl2] base: {res['base']}", flush=True)
    res["arms"] = []
    for arm in a.arms.split(","):
        for sd in seeds:
            res["arms"].append(run_arm(s, arm, sd, a, test, panel, replies, bm["harm"]))
            (out / "dl2_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if set(a.arms.split(",")) >= {"S", "P"}:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl2_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


TEST_SEED = 3890     # new fresh test set (dl-1 used 3990)


def selftest() -> None:
    g = [{"puzzle": {"nums": [1, 2, 3], "target": 6}, "guesses": ["1 + 2 + 3", "1 * 2 * 3", "3 - 2 - 1", "1 + 2"],
          "rewards": [1, 1, 0, 0]}]
    w = wrong_examples(g, 5, 0)
    assert w == [(g[0]["puzzle"], "3 - 2 - 1")], w

    def arm(name, sd, lucky, net, reached=40):
        return {"arm": name, "seed": sd, "nights": [{"test": {"lucky": v, "reached": reached},
                                                      "harm": {"net_harm": net}} for v in lucky]}
    res = {"base": {"lucky": 60, "reached": 35},
           "arms": [arm("S", 2, [90, 100, 110, 120, 125, 130, 140], -5), arm("S", 3, [80, 95, 90, 110, 120, 128, 135], -3),
                    arm("P", 2, [60, 62, 58, 61, 60, 63, 64], 2), arm("P", 3, [59, 60, 61, 62, 60, 58, 61], 1)]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    res["arms"][0]["nights"][3]["harm"]["net_harm"] = 9
    res["arms"][1]["nights"][3]["harm"]["net_harm"] = 9
    assert score(res)["verdict"] == "FAIL"
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--arms", default="S,P")
    ap.add_argument("--seeds", default="2,3")
    ap.add_argument("--nights", type=int, default=7)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-guess", type=int, default=30)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-guess-test", type=int, default=20)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--n-kl", type=int, default=60)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_guess, a.n_test, a.n_guess_test, a.n_harm, a.n_kl = 2, 4, 4, 3, 3, 12, 4
        a.seed_shift, a.seeds = a.seed_shift or 60000, "2"
    run(a)


if __name__ == "__main__":
    main()
