#!/usr/bin/env python3
"""dl-6: do lighter nights (1 epoch instead of 3) stop the slow forgetting of copy-practice nights?
(Fix-sleep thread, 2026-09-26; marks: artifacts/claude-dl6-20260926/PASSMARKS.md)

Why. dl-2 (registered PASS) learned the day's work well (lucky guesses 64 -> 237/249) but lost 26 of the base's 200
right general-panel items by night 7. Its placebo arm, trained on WRONG answers, lost about as many (17/19), so the
losses track how much the model is trained, not what it is trained on (suggested, not shown). dl-3 (replay) failed;
dl-4 (KL anchor) is being rerun. dl-6 tests the plainest lever: train less each night. RL's Razor (REPORT.md Q1):
forgetting tracks how far the model moves from the base, and dl-2's gains leave room to trade learning for retention.

ONE change from dl-2's S arm: each night trains 1 epoch instead of 3 (same examples, lr 2e-4, batch 8, one growing
adapter). Arms:
  S  dl-2's night unchanged (3 epochs).
  L  the same night, 1 epoch.
Same day, TEST, HARM (lost = right at base and wrong now) and KL measure as dl-2/dl-3/dl-4. New seeds 10 and 11, TEST
seed 3590. Marks: dl-3's F1-F5 with L in place of A (claude_dl3_replay.score), unchanged.

  python -B scripts/claude_dl6_light.py --model M --out DIR        (registered run)
  python -B scripts/claude_dl6_light.py --selftest
  python -B scripts/claude_dl6_light.py --model M --out DIR --dev  (plumbing rehearsal)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_blurt2 as B2  # noqa: E402
import claude_dl1_nights as D1  # noqa: E402
import claude_dl3_replay as R  # noqa: E402

TEST_SEED = 3590
EPOCHS = {"S": D1.S_RECIPE["epochs"], "L": 1}


def run_arm(s, arm, seed, a, test, panel, replies, base_harm) -> dict:
    s.torch.manual_seed(seed)
    m = D1.fresh_model(s)
    nights, prev = [], base_harm
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = D1.gather(s, m, day, a.n_guess)
        right = D1.copy_examples(groups)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups), "right_examples": len(right),
               "epochs": EPOCHS[arm]}
        rec["train"] = D1.train_copy(s, m, right, seed * 1000 + d, epochs=EPOCHS[arm]) if right else {"examples": 0}
        meas = D1.measure(s, m, test, a.n_guess_test, panel, replies)
        rec["test"] = {k: meas[k] for k in ("lucky", "reached", "greedy")}
        rec["harm"] = D1.flips(base_harm, meas["harm"])
        rec["harm_vs_prev"] = D1.flips(prev, meas["harm"])
        rec["harm_items"] = meas["harm"]
        prev = meas["harm"]
        rec["kl"] = meas["kl"]
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl6] {arm} s{seed} night {d}: " + json.dumps({k: v for k, v in rec.items() if k != "harm_items"}),
              flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md): dl-3's F1-F5 with L in place of A (no pool, so pool size is not a gate)."""
    sub = {"base": res["base"], "pool_size": 100,
           "arms": [dict(r, arm="A" if r["arm"] == "L" else r["arm"]) for r in res["arms"]]}
    m3 = R.score(sub)
    return {k.replace("A_", "L_").replace(": A ", ": L ").replace(" A ", " L "): v for k, v in m3.items()}


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
           "temp": D1.TEMP, "test_seed": TEST_SEED, "epochs": EPOCHS}
    base = s.model
    replies = [(q, D1.free_answer(s, q, base, 40)) for q in
               (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    bm = D1.measure(s, base, test, a.n_guess_test, panel)
    res["base"] = {k: bm[k] for k in ("lucky", "reached", "greedy")}
    res["base"]["harm_right"] = sum(bm["harm"])
    res["base_harm_items"] = bm["harm"]
    print(f"[dl6] base: {res['base']}", flush=True)
    res["arms"] = []
    for arm in a.arms.split(","):
        for sd in seeds:
            res["arms"].append(run_arm(s, arm, sd, a, test, panel, replies, bm["harm"]))
            (out / "dl6_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if set(a.arms.split(",")) >= {"S", "L"}:
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl6_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


def selftest() -> None:
    def arm(name, sd, lucky, lost, reached=40):
        return {"arm": name, "seed": sd, "nights": [{"test": {"lucky": v, "reached": reached},
                                                      "harm": {"lost": l}} for v, l in zip(lucky, lost)]}
    res = {"base": {"lucky": 60, "reached": 35},
           "arms": [arm("S", 10, [90, 100, 110, 120, 125, 130, 140], [5, 8, 12, 16, 18, 24, 26]),
                    arm("S", 11, [80, 95, 90, 110, 120, 128, 135], [6, 9, 11, 15, 20, 28, 25]),
                    arm("L", 10, [85, 100, 105, 118, 120, 125, 130], [3, 4, 6, 5, 7, 8, 9]),
                    arm("L", 11, [85, 92, 99, 110, 115, 120, 128], [4, 5, 4, 6, 8, 7, 10])]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    assert any(k.startswith("F1") and ": L " in k for k in m), list(m)
    res["arms"][2]["nights"][-1]["harm"]["lost"] = 26
    assert score(res)["verdict"] == "FAIL"
    res["arms"][2]["nights"][-1]["harm"]["lost"] = 9
    res["arms"][2]["nights"][-1]["test"]["lucky"] = 100                       # learns too little: F3 fails
    assert score(res)["verdict"] == "FAIL"
    assert EPOCHS == {"S": 3, "L": 1}
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--arms", default="S,L")
    ap.add_argument("--seeds", default="10,11")
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
        a.nights, a.n_day, a.n_guess, a.n_test, a.n_guess_test, a.n_harm, a.n_kl = 1, 4, 4, 3, 3, 12, 4
        a.seed_shift, a.seeds = a.seed_shift or 60000, "10"
    run(a)


if __name__ == "__main__":
    main()
