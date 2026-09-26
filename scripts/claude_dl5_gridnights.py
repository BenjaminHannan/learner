#!/usr/bin/env python3
"""dl-5: can sleep learn puzzles too deep for guessing, from hits that go-back search finds?
(Fix-sleep thread with the thought-memory thread, 2026-09-26; marks: artifacts/claude-dl5-20260926/PASSMARKS.md)

Why. dl-2 (registered PASS) showed copy-practice nights teach the 1B the day's number puzzles, but its day finds hits by
30 separate guesses. On 5x5 Latin grids plain guessing finds none: in rv-385, 60 choices of starting over solved 0 of
160 grids, while going back one step with a code ban (revert_ban) solved 100. Ben's 12:48 UTC rule asks threads to
join functions; the thought-memory thread built the grid day (scripts/claude_gridday.py) and Fix sleep owns the nights.

ONE change from dl-2's S arm: the day is rv-385's revert_ban search on 150 fresh 5x5 grids (60 choices each), and the
practice pairs are (state on a solved grid's path, the correct next number) in rv-385's prompt and reply prefix.
The night is dl-2's night unchanged (claude_dl1_nights.train_copy: 3 epochs, lr 2e-4, batch 8, one growing LoRA r16).
Each arm searches with its own current model, so nights 2 onward search with the slept model. Arms:
  S  the day's solved-path pairs, right numbers.
  P  placebo: states along the true solution of that night's grids with a WRONG number (legal-looking when one
     exists), drawn from every grid of the day (a wrong number needs no solved grid) and sampled down to S's row count
     for the same seed and night, so S and P practise the same amount (dl-2 matched counts too). P runs no search.
  K  report only, one seed: the answer key's pairs for EVERY grid of the day (a ceiling; no search needed).
TEST: 60 fresh grids (seed 38990), every state along the true solution, the model's top-scoring number vs the key,
split into forced states (one number fits the visible row and column) and open states (two or more fit).
HARM: dl-1's 300 general items; lost = right at base and wrong now.

  python -B scripts/claude_dl5_gridnights.py --model M --out DIR        (registered run)
  python -B scripts/claude_dl5_gridnights.py --selftest
  python -B scripts/claude_dl5_gridnights.py --model M --out DIR --dev  (plumbing rehearsal, tiny counts, other seeds)
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
import claude_gridday as G  # noqa: E402
import claude_rv385 as R  # noqa: E402

TEST_SEED = 38990       # agreed with the thought-memory thread; dev states used 38980, dev day 38970
DAY_SEED = 39100        # day d of seed s: grids(DAY_SEED + shift + 100 * s + d)
DEV_SHIFT = 60000


class GridShim:
    """claude_dl1_nights.train_copy on grid rows: prompt(row) = the chat template around the row's messages."""

    def __init__(self, s):
        self.torch, self.tok, self.dev, self.model = s.torch, s.tok, s.dev, s.model

    def prompt(self, row) -> str:
        return self.tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True,
                                            enable_thinking=False)


def key_rows(seed, n) -> list:
    """K: the key's pairs for every grid of the day (same rows the search would give if it solved every grid)."""
    import random
    out = []
    for p in R.make_puzzles(seed, n, G.SIZE):
        out += G.pairs_from(p, random.Random(0))[0]
    return out


def placebo_rows(seed, n, k, tag) -> list:
    """P: wrong-number pairs on every grid of the day, sampled down to k rows (S's count for that seed and night)."""
    import random
    rng = random.Random(f"dl5-P|{tag}")
    rows = []
    for p in R.make_puzzles(seed, n, G.SIZE):
        rows += G.pairs_from(p, rng)[1]
    rng.shuffle(rows)
    return rows[:k]


def measure(s, m, a, panel, base_harm=None) -> dict:
    sc = G.score_states(s.tok, m, TEST_SEED + a.seed_shift, a.n_test)
    out = {"test": sc, "harm_now": D1.harm_scores(s, m, panel)}
    if base_harm is not None:
        out["harm"] = D1.flips(base_harm, out["harm_now"])
    return out


def save_adapter(m, path: Path, meta: dict) -> None:
    """The LoRA A/B tensors only (never pushed; copied back for the rv-386 gate and the made-up-claims probe)."""
    import hashlib
    import torch
    sd = {k: v.detach().cpu() for k, v in m.state_dict().items() if k.endswith(".A") or k.endswith(".B")}
    torch.save(sd, path)
    meta = dict(meta, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), tensors=len(sd))
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


def run_arm(s, gs, arm, seed, a, panel, base_harm, out, s_rows=None) -> dict:
    s.torch.manual_seed(seed)
    m = D1.fresh_model(s)
    nights = []
    for d in range(1, a.nights + 1):
        t0 = time.time()
        dseed = DAY_SEED + a.seed_shift + 100 * seed + d
        rec = {"night": d, "day_seed": dseed}
        if arm == "K":
            rows = key_rows(dseed, a.n_day)
        elif arm == "P":
            rows = placebo_rows(dseed, a.n_day, s_rows[d - 1], f"{seed}|{d}")
            rec["P_legal_wrong"] = sum(r["legal_wrong"] for r in rows)
        else:
            day = G.day(s.tok, m, dseed, a.n_day, a.budget)
            rec["day"] = day["stats"]
            rows = day["S"]
        rec["rows"] = len(rows)
        rec["train"] = D1.train_copy(gs, m, [(r, r["answer"]) for r in rows], seed * 1000 + d) if rows \
            else {"examples": 0}
        meas = measure(s, m, a, panel, base_harm)
        rec["test"], rec["harm"] = meas["test"], meas["harm"]
        rec["minutes"] = round((time.time() - t0) / 60, 1)
        nights.append(rec)
        print(f"[dl5] {arm} s{seed} night {d}: {json.dumps(rec)}", flush=True)
    if arm == "S" and a.save_adapters:
        save_adapter(m, out / f"dl5-S-s{seed}.pt", {"arm": arm, "seed": seed, "nights": a.nights,
                                                    "base": s.model.name_or_path, "lora": "claude_blurt2.add_lora"})
    del m
    if s.dev == "cuda":
        s.torch.cuda.empty_cache()
    return {"arm": arm, "seed": seed, "nights": nights}


def pts(sc, part="all") -> float:
    """Accuracy in points (0-100) on all, forced or open states."""
    if part == "all":
        return 100.0 * sc["right"] / max(sc["states"], 1)
    return 100.0 * sc[f"{part}_right"] / max(sc[f"{part}_states"], 1)


def score(res: dict) -> dict:
    """The registered marks (PASSMARKS.md)."""
    base = res["base"]["test"]
    by = {(r["arm"], r["seed"]): r["nights"] for r in res["arms"]}
    seeds = sorted({r["seed"] for r in res["arms"] if r["arm"] == "S"})
    fs = {sd: by[("S", sd)][-1] for sd in seeds}
    fp = {sd: by[("P", sd)][-1] for sd in seeds}
    b = pts(base)
    m = {"night0_pts": round(b, 1),
         "S_final_pts": [round(pts(fs[sd]["test"]), 1) for sd in seeds],
         "P_final_pts": [round(pts(fp[sd]["test"]), 1) for sd in seeds],
         "S_final_open_pts": [round(pts(fs[sd]["test"], "open"), 1) for sd in seeds],
         "P_final_open_pts": [round(pts(fp[sd]["test"], "open"), 1) for sd in seeds],
         "S_final_lost": [fs[sd]["harm"]["lost"] for sd in seeds],
         "S_night1_rows": [by[("S", sd)][0]["rows"] for sd in seeds]}
    m["G1 slept model better: S final >= night 0 + 15 points on each seed"] = \
        all(x >= b + 15 for x in m["S_final_pts"])
    m["G2 right answers caused it: S final >= P final + 10 points on each seed"] = \
        all(x >= y + 10 for x, y in zip(m["S_final_pts"], m["P_final_pts"]))
    m["G3 no harm: S final lost <= 20 of the base-right panel items on each seed"] = \
        all(x <= 20 for x in m["S_final_lost"])
    keys = [k for k in m if k[:1] == "G" and k[1].isdigit()]
    m["verdict"] = "INCONCLUSIVE" if min(m["S_night1_rows"]) < 100 else \
        ("PASS" if all(m[k] for k in keys) else "FAIL")
    m["proved_wrong"] = all(x <= y for x, y in zip(m["S_final_open_pts"], m["P_final_open_pts"]))
    return m


def run(a) -> None:
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = B2.Solver(a.model)
    s.model.name_or_path = a.model
    gs = GridShim(s)
    seeds = [int(x) for x in a.seeds.split(",")]
    panel = D1.harm_panel()[:a.n_harm]
    test_keys = {json.dumps(p["puz"]) for p in R.make_puzzles(TEST_SEED + a.seed_shift, a.n_test, G.SIZE)}
    day_keys = {json.dumps(p["puz"]) for sd in seeds for d in range(1, a.nights + 1)
                for p in R.make_puzzles(DAY_SEED + a.seed_shift + 100 * sd + d, a.n_day, G.SIZE)}
    res = {"config": {k: v for k, v in vars(a).items() if k != "model"}, "test_seed": TEST_SEED + a.seed_shift,
           "day_seed": DAY_SEED + a.seed_shift, "n_harm": len(panel), "test_grids_also_in_a_day": len(test_keys & day_keys)}
    bm = measure(s, s.model, a, panel)
    res["base"] = {"test": bm["test"], "harm_right": sum(bm["harm_now"])}
    print(f"[dl5] base: {json.dumps(res['base'])}", flush=True)
    res["arms"] = []
    plan = [(arm, sd) for arm in ("S", "P") for sd in seeds] + [("K", seeds[0])] * a.key_arm
    for arm, sd in plan:
        s_rows = [n["rows"] for r in res["arms"] if (r["arm"], r["seed"]) == ("S", sd) for n in r["nights"]]
        res["arms"].append(run_arm(s, gs, arm, sd, a, panel, bm["harm_now"], out, s_rows))
        (out / "dl5_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    res["marks"] = score(res)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "dl5_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["marks"], indent=1))


def selftest() -> None:
    import random
    p = R.make_puzzles(5, 1, G.SIZE)[0]
    S, P = G.pairs_from(p, random.Random(1))

    class Tok:
        def apply_chat_template(self, msgs, tokenize, add_generation_prompt, enable_thinking):
            assert not tokenize and add_generation_prompt and enable_thinking is False
            return "<u>" + msgs[0]["content"] + "</u><a>"

    class S0:
        torch = tok = dev = model = None
    gs = GridShim(S0())
    gs.tok = Tok()
    assert gs.prompt(S[0]) == "<u>" + S[0]["messages"][0]["content"] + "</u><a>"
    assert len(key_rows(5, 1)) == len(S) and key_rows(5, 1)[0]["answer"] == S[0]["answer"]
    pr = placebo_rows(5, 3, 7, "t")
    assert len(pr) == 7 and all(r["kind"] == "P" for r in pr) and pr == placebo_rows(5, 3, 7, "t")
    for r in pr:
        q = [x for x in R.make_puzzles(5, 3, G.SIZE) if x["pid"] == r["pid"]][0]
        assert r["value"] != q["sol"][r["cell"][0]][r["cell"][1]]

    def sc(right, states=100, forced=70, forced_right=None):
        fr = min(right, forced) if forced_right is None else forced_right
        return {"states": states, "right": right, "forced_states": forced, "forced_right": fr,
                "open_states": states - forced, "open_right": right - fr}

    def arm(name, sd, right, lost=5, rows=300, fr=None):
        return {"arm": name, "seed": sd, "nights": [{"rows": rows, "test": sc(right, forced_right=fr),
                                                      "harm": {"lost": lost}}]}
    res = {"base": {"test": sc(44)},
           "arms": [arm("S", 8, 70, fr=55), arm("S", 9, 66, fr=52), arm("P", 8, 50, fr=45), arm("P", 9, 48, fr=43)]}
    m = score(res)
    assert m["verdict"] == "PASS" and not m["proved_wrong"], m
    res["arms"][0]["nights"][0]["harm"]["lost"] = 21
    assert score(res)["verdict"] == "FAIL"
    res["arms"][0]["nights"][0]["harm"]["lost"] = 5
    res["arms"][1]["nights"][0]["test"] = sc(58, forced_right=52)
    assert score(res)["verdict"] == "FAIL"                                   # 58 < 44 + 15
    res["arms"][0]["nights"][0]["rows"] = 50
    assert score(res)["verdict"] == "INCONCLUSIVE"
    res = {"base": {"test": sc(44)},
           "arms": [arm("S", 8, 60, fr=58), arm("S", 9, 60, fr=58), arm("P", 8, 50, fr=45), arm("P", 9, 50, fr=45)]}
    assert score(res)["proved_wrong"]                                         # open: S 2 vs P 5 on both seeds
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--seeds", default="8,9")
    ap.add_argument("--nights", type=int, default=5)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--budget", type=int, default=G.BUDGET)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--n-harm", type=int, default=300)
    ap.add_argument("--key-arm", type=int, default=1)
    ap.add_argument("--save-adapters", type=int, default=1)
    ap.add_argument("--seed-shift", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dev:
        a.nights, a.n_day, a.n_test, a.n_harm, a.budget = 2, 3, 2, 12, 20
        a.seed_shift, a.seeds, a.save_adapters = a.seed_shift or DEV_SHIFT, "8", 0
    run(a)


if __name__ == "__main__":
    main()
