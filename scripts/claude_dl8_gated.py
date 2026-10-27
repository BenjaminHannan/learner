#!/usr/bin/env python3
"""dl-8: does a night that practises only what the model still finds hard keep the learning and cut the forgetting,
beyond simply training on fewer rows? (Fix-sleep thread, 2026-09-26; marks: artifacts/claude-dl8-20260926/PASSMARKS.md)

Why. dl-6 (registered FAIL) showed forgetting and learning both track the total amount trained: one epoch per night
halved both (report-only dose split). dl-5 learned grids in one night and then only forgot. Brain first: sleep
strengthens what is new or still weak, driven by prediction error; what is already consolidated is not re-trained.
Silicon version: before training, each of the night's practice rows is scored by the CURRENT model (its loss on the
checked answer, no gradient); only the harder half is practised.

ONE change from dl-2's night (claude_dl1_nights.train_copy, 3 epochs, lr 2e-4, batch 8, one growing LoRA): the rows
it trains on. Arms, all on the same day and the same code-checked rows:
  S  every row (dl-2's night).
  E  the half of the rows with the HIGHEST current loss (error-gated).
  R  a random half of the rows (dose control: same number of rows as E, chosen without looking at loss).
E vs R separates "which rows" from "how many rows". The puzzle instruction is GLM 5.3 Flash's
(artifacts/claude-glmframes-20260926/frames.json, sha256 pinned in claude_dl6c_glmframe), not Claude's; targets are
the 1B's own expressions, checked by code (no sentence frame). Seeds 14 and 15, 7 nights, TEST seed 3190, HARM = the
300-item panel (lost = right at base, wrong now). BensPC job (Ben 18:42: no new rentals).

  python -B scripts/claude_dl8_gated.py --selftest
  python -B scripts/claude_dl8_gated.py --model M --out DIR        (registered run)
  python -B scripts/claude_dl8_gated.py --model M --out DIR --dev  (plumbing rehearsal)
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
import claude_blurt1 as B1  # noqa: E402
import claude_dl6c_glmframe as G  # noqa: E402

TEST_SEED = 3190
ARMS = ("S", "E", "R")


def row_losses(s, m, rows) -> list[float]:
    """The current model's mean answer-token loss on each (puzzle, expression) row, no gradient."""
    import claude_dl1_nights as D1
    out = []
    m.eval()
    with s.torch.no_grad():
        for p, expr in rows:
            pr, full = D1._ids(s, p, expr)
            ids = full.unsqueeze(0).to(s.dev)
            lab = ids.clone()
            lab[0, :len(pr)] = -100
            out.append(float(m(input_ids=ids, labels=lab).loss))
    return out


def pick(arm, rows, losses, seed) -> list:
    if arm == "S" or not rows:
        return list(rows)
    k = len(rows) // 2
    if arm == "E":
        order = sorted(range(len(rows)), key=lambda i: (-losses[i], i))
        return [rows[i] for i in sorted(order[:k])]
    return random.Random(seed).sample(list(rows), k)


def run_arm(s, arm, seed, a, test, panel, replies, base_harm) -> dict:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    s.torch.manual_seed(seed)
    m = D1.fresh_model(s)
    nights, prev = [], base_harm
    for d in range(1, a.nights + 1):
        t0 = time.time()
        day = B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * seed + d, a.n_day)
        groups = D1.gather(s, m, day, a.n_guess)
        right = D1.copy_examples(groups)
        losses = row_losses(s, m, right) if arm == "E" else []
        rows = pick(arm, right, losses, seed * 1000 + d)
        rec = {"night": d, "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_right_guesses": sum(sum(g["rewards"]) for g in groups), "right_examples": len(right),
               "trained_rows": len(rows)}
        if losses:
            rec["loss_median_all"] = round(sorted(losses)[len(losses) // 2], 4)
            rec["loss_min_kept"] = round(sorted(losses, reverse=True)[len(rows) - 1], 4) if rows else None
        rec["train"] = D1.train_copy(s, m, rows, seed * 1000 + d) if rows else {"examples": 0}
        meas = D1.measure(s, m, test, a.n_guess_test, panel, replies)
        rec["test"] = {k: meas[k] for k in ("lucky", "reached", "greedy")}
        rec["harm"] = D1.flips(base_harm, meas["harm"])
        rec["harm_vs_prev"] = D1.flips(prev, meas["harm"])
        rec["harm_items"] = meas["harm"]
        prev = meas["harm"]
        rec["kl"] = meas["kl"]
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl8] {arm} s{seed} night {d}: " + json.dumps({k: v for k, v in rec.items() if k != "harm_items"}),
              flush=True)
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md)."""
    L0 = res["base"]["lucky"]
    seeds = sorted({r["seed"] for r in res["arms"]})
    fin = {(r["arm"], r["seed"]): r["nights"][-1] for r in res["arms"]}
    lost = {a: [fin[(a, sd)]["harm"]["lost"] for sd in seeds] for a in ARMS}
    luck = {a: [fin[(a, sd)]["test"]["lucky"] for sd in seeds] for a in ARMS}
    gain = {a: sum(luck[a]) - len(seeds) * L0 for a in ARMS}
    m = {"L0": L0, "final_lost": lost, "final_lucky": luck, "gain_over_L0": gain}
    m["H1 forgetting cut: E final lost <= 0.5 x S final lost (sums), and each E seed < each S seed"] = \
        sum(lost["E"]) <= 0.5 * sum(lost["S"]) and max(lost["E"]) < min(lost["S"])
    m["H2 still learns: E final lucky >= 2 x L0 on each seed, and E gain >= 0.8 x S gain"] = \
        all(x >= 2 * L0 for x in luck["E"]) and gain["E"] >= 0.8 * gain["S"]
    m["H3 which rows matter, not only how many: E gain >= R gain + 0.1 x S gain, and E lost <= R lost (sums)"] = \
        gain["E"] >= gain["R"] + 0.1 * gain["S"] and sum(lost["E"]) <= sum(lost["R"])
    keys = [k for k in m if k[:1] == "H" and k[1].isdigit()]
    m["verdict"] = ("INCONCLUSIVE" if L0 < 10 or sum(lost["S"]) < 20 else
                    ("PASS" if all(m[k] for k in keys) else "FAIL"))
    m["proved_wrong"] = (abs(gain["E"] - gain["R"]) <= 0.2 * max(abs(gain["R"]), 1)
                         and abs(sum(lost["E"]) - sum(lost["R"])) <= 0.2 * max(sum(lost["R"]), 1))
    return m


def run(a) -> None:
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    frame = G.glm_frame()
    B1.puzzle_prompt = G.make_prompt(frame)            # Solver.prompt looks it up on the module
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    seeds = [int(x) for x in a.seeds.split(",")]
    keys = {(tuple(p["nums"]), p["target"]) for sd in seeds for d in range(1, a.nights + 1)
            for p in B2.puzzles(D1.DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day)}
    test = [p for p in B2.puzzles(TEST_SEED + a.seed_shift, a.n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in keys][:a.n_test]
    panel = D1.harm_panel()[:a.n_harm]
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "n_test": len(test), "n_harm": len(panel),
           "temp": D1.TEMP, "test_seed": TEST_SEED, "frame": frame, "frame_sha256": G.FRAMES_SHA256}
    base = s.model
    replies = [(q, D1.free_answer(s, q, base, 40)) for q in
               (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:a.n_kl]]
    bm = D1.measure(s, base, test, a.n_guess_test, panel)
    res["base"] = {k: bm[k] for k in ("lucky", "reached", "greedy")}
    res["base"]["harm_right"] = sum(bm["harm"])
    res["base_harm_items"] = bm["harm"]
    print(f"[dl8] base: {res['base']}", flush=True)
    res["arms"] = []
    for arm in a.arms.split(","):
        for sd in seeds:
            res["arms"].append(run_arm(s, arm, sd, a, test, panel, replies, bm["harm"]))
            (out / "dl8_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    if set(a.arms.split(",")) >= set(ARMS):
        res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl8_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res.get("marks", {}), indent=1))


def selftest() -> None:
    def arm(name, sd, lucky, lost):
        return {"arm": name, "seed": sd, "nights": [{"test": {"lucky": v}, "harm": {"lost": l}}
                                                     for v, l in zip(lucky, lost)]}
    res = {"base": {"lucky": 60},
           "arms": [arm("S", 14, [100, 140], [10, 26]), arm("S", 15, [100, 150], [10, 24]),
                    arm("E", 14, [100, 138], [5, 10]), arm("E", 15, [100, 140], [5, 11]),
                    arm("R", 14, [90, 110], [5, 12]), arm("R", 15, [90, 112], [5, 13])]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    res["arms"][4]["nights"][-1]["test"]["lucky"] = 138
    res["arms"][5]["nights"][-1]["test"]["lucky"] = 140
    res["arms"][4]["nights"][-1]["harm"]["lost"] = 10
    res["arms"][5]["nights"][-1]["harm"]["lost"] = 11
    m = score(res)
    assert m["verdict"] == "FAIL" and m["proved_wrong"], m
    rows = [(i, str(i)) for i in range(10)]
    assert pick("E", rows, [float(i) for i in range(10)], 1) == rows[5:]
    assert len(pick("R", rows, [], 1)) == 5 and pick("S", rows, [], 1) == rows
    f = G.make_prompt("Use {NUMS} to make {TARGET}.")
    assert f({"nums": [1, 2], "target": 3})[0]["content"] == "Use 1, 2 to make 3."
    assert G.glm_frame().count("{NUMS}") == 1
    print("dl8 selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--arms", default="S,E,R")
    ap.add_argument("--seeds", default="14,15")
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
        a.seed_shift, a.seeds = a.seed_shift or 60000, "14"
    run(a)


if __name__ == "__main__":
    main()
