#!/usr/bin/env python3
"""dl-5s (FINDING ONLY): could a small learned switch have kept dl-5's grid adapters off the general panel?
(Fix-sleep thread, 2026-09-26; expectations: artifacts/claude-dl5s-20260926/PASSMARKS.md). Step (1) of the Thread
manager's 19:25 plan after Ben's 19:20 "just put the old skills somewhere where they don't get overridden".

Every dl run already keeps the base 1B frozen (claude_blurt2.add_lora); only the add-on learns. What is missing is a
switch that turns the add-on off for questions that are not its kind. This script fits that switch and applies it to
the answers dl-5 already saved, so nothing is trained into the 1B and no adapter is needed:
- dl-5's carry row (artifacts/claude-dl5-20260926/carry/dl5_carry.json) holds the base's and each saved S adapter's
  greedy answers to the 300 panel items; X (switch-served) = the adapter's answer where the switch is on, the base's
  where it is off.
- Switch = claude_dl9_experts.fit_switch (logistic regression on the frozen base's last-layer state at the last prompt
  token). Labels are code-made from where an item came from: 1 = states along the true solution of dl-5's own practice
  grids (seed 8, days 1-5; 600 sampled); 0 = short quiz questions the base wrote itself (dl-7's recipe, panel topics
  dropped, pool seed 3391), 80% to fit and 20% held out, half with GLM 5.3 Flash's "Answer only, no explanation."
The grid wording is Claude's (rv-385's prompt), so this is a finding, not a registered result.

  python -B scripts/claude_dl5s_switch.py --selftest
  python -B scripts/claude_dl5s_switch.py --model M --out DIR [--dev]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import claude_dl9_experts as E  # noqa: E402

ROOT = HERE.parent
CARRY = ROOT / "artifacts/claude-dl5-20260926/carry/dl5_carry.json"
RESULTS = ROOT / "artifacts/claude-dl5-20260926/gpu/dl5_results.json"
POOL_SEED = 3391
DL5_DAY_SEED, DL5_TEST_SEED, DL5_SEED, DL5_NIGHTS = 39100, 38990, 8, 5


def grid_states(seed, n) -> list[str]:
    """The user message of every state along the true solution of n grids (dl-5's own grid code)."""
    import claude_gridday as GD
    import claude_rv385 as R
    out = []
    for p in R.make_puzzles(seed, n, GD.SIZE):
        for i in range(len(R.empties(p["puz"]))):
            out.append(GD.state_at(p, i).prompt_parts()[0])
    return out


def run(a) -> None:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    torch = __import__("torch")
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    _, _, suffix = E.glm_texts()
    carry = json.loads(CARRY.read_text(encoding="utf-8"))
    dl5 = json.loads(RESULTS.read_text(encoding="utf-8"))
    panel = D1.harm_panel()[:300]
    pos_all = [m for d in range(1, DL5_NIGHTS + 1) for m in grid_states(DL5_DAY_SEED + 100 * DL5_SEED + d, a.n_day)]
    pos = random.Random(POOL_SEED).sample(pos_all, min(a.n_pos, len(pos_all)))
    test = grid_states(DL5_TEST_SEED + a.shift, a.n_test)          # dev: shifted, never the test grids
    qs = E.question_pool(s, a.n_ask, POOL_SEED + a.shift)
    rng = random.Random(POOL_SEED)
    rng.shuffle(qs)
    cut = int(0.8 * len(qs))
    tag = [rng.random() < 0.5 for _ in qs]
    neg = [q + " " + suffix if t else q for q, t in zip(qs, tag)]
    res = {"what": "dl-5s finding (Claude grid wording in dl-5)", "pool_seed": POOL_SEED,
           "positives": {"from": f"dl-5 seed {DL5_SEED} days 1-{DL5_NIGHTS}", "all_states": len(pos_all),
                         "sampled": len(pos)},
           "pool": {"asked": a.n_ask, "questions": len(qs), "fit": cut, "held": len(qs) - cut, "with_suffix": sum(tag),
                    "sample": qs[:5]},
           "test_states": len(test)}
    print(f"[dl5s] {json.dumps(res)}", flush=True)
    f = {k: E.feats(s, [E.chat_text(s, t) for t in v]) for k, v in
         {"pos": pos, "neg_fit": neg[:cut], "neg_held": neg[cut:], "test": test,
          "panel": [it["q"] for it in panel]}.items()}
    X = torch.cat([f["pos"], f["neg_fit"]])
    y = torch.cat([torch.ones(len(f["pos"])), torch.zeros(len(f["neg_fit"]))])
    sw = E.fit_switch(torch, X, y, POOL_SEED)
    on = {k: E.switch_on(sw, f[k]) for k in ("test", "panel", "neg_held")}
    kinds = sorted({it["kind"] for it in panel})
    res["switch"] = {"fit_loss": sw["train_loss"], "test_on": sum(on["test"]), "test_states": len(on["test"]),
                     "panel_on": sum(on["panel"]), "held_neg_on": sum(on["neg_held"]),
                     "held_neg": len(on["neg_held"]),
                     "panel_on_by_kind": {k: [sum(o for o, it in zip(on["panel"], panel) if it["kind"] == k),
                                              sum(it["kind"] == k for it in panel)] for k in kinds}}
    base = carry["base"]["harm_items"]
    fin = {r["seed"]: r["nights"][-1] for r in dl5["arms"] if r["arm"] == "S"}
    res["seeds"] = {}
    for name, sd in (("dl5-S-s8", 8), ("dl5-S-s9", 9)):
        ad = carry[name]["harm_items"]
        xs = E.serve(on["panel"], ad, base)
        S = D1.flips(base, ad)
        Xf = D1.flips(base, xs)
        k_off = len(test) - sum(on["test"])
        g = fin[sd]["test"]
        res["seeds"][name] = {"S_panel": S, "X_panel": Xf,
                              "S_lost_items_switched_on": sum(on["panel"][i] for i, (b0, x) in
                                                              enumerate(zip(base, ad)) if b0 and not x),
                              "S_grid_right": g["right"], "grid_states": g["states"], "test_states_off": k_off,
                              "X_grid_right_bounds": [max(0, g["right"] - k_off), min(g["states"], g["right"] + k_off)]}
    lx = [res["seeds"][n]["X_panel"]["lost"] for n in res["seeds"]]
    ls = [res["seeds"][n]["S_panel"]["lost"] for n in res["seeds"]]
    res["expected"] = {
        "X lost <= 5 on each seed": max(lx) <= 5,
        "switch on for >= 95% of grid test states": sum(on["test"]) >= 0.95 * len(test),
        "switch off for >= 95% of panel items": sum(on["panel"]) <= 0.05 * len(panel),
        "shown wrong: X lost > 0.5 x S lost on either seed": any(x > 0.5 * y for x, y in zip(lx, ls))}
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl5s_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "pool"}, indent=1))


def selftest() -> None:
    carry = json.loads(CARRY.read_text(encoding="utf-8"))
    assert len(carry["base"]["harm_items"]) == 300 and len(carry["dl5-S-s8"]["harm_items"]) == 300
    dl5 = json.loads(RESULTS.read_text(encoding="utf-8"))
    fin = {r["seed"]: r["nights"][-1] for r in dl5["arms"] if r["arm"] == "S"}
    assert set(fin) == {8, 9} and fin[8]["night"] == DL5_NIGHTS and fin[8]["test"]["seed"] == DL5_TEST_SEED
    t = grid_states(DL5_TEST_SEED, 60)
    assert len(t) == fin[8]["test"]["states"], (len(t), fin[8]["test"]["states"])
    assert fin[8]["day_seed"] == DL5_DAY_SEED + 100 * 8 + DL5_NIGHTS, fin[8]["day_seed"]
    print("dl5s selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-pos", type=int, default=600)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--n-ask", type=int, default=1000)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    ap.set_defaults(shift=0)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.n_day, a.n_pos, a.n_test, a.n_ask, a.shift = 2, 20, 2, 20, 60000
    run(a)


if __name__ == "__main__":
    main()
