#!/usr/bin/env python3
"""Marks of the five-days-five-kinds test, as code (artifacts/opus-manager-20260929/five-days/PASSMARKS.md is the text).
Reads only the raw JSON that scripts/opus_fd_run.py writes; pure python, no torch. Numbers are fixed here BEFORE any run.

  python3 -B scripts/opus_fd_marks.py selftest
  python3 -B scripts/opus_fd_marks.py score --runs artifacts/opus-manager-20260929/five-days/runs --out SCORE.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
import tempfile
from pathlib import Path

RUNGS = (1, 4, 16, 64, 256, 1024, 4096, 16384)
BAR = {200: 20, 300: 60}          # night-5 gain bar over the 16-store arm, counts of 200 / of 300 (PASSMARKS, noise section)
WRONG_GAIN = {200: 5, 300: 8}     # "within 5 of 200" (8 of 300 is the same 2.5 percent)
MARGIN_FLOOR, MARGIN_SD = 6, 2    # margin = max(6, 2 x SE)
LEARNED_FRAC = .30                # a day kind counts as learned if its day-end score is at least 30 percent, in BOTH loop arms
F_FEW_TOL, F_EQ_TOL = 10.5, 8.0   # noise bars (artifacts/claude-dir-lr-20260928/NOISE.md): 2 x 5.23 and 2 x 3.96
DROP_WRONG = 15.0                 # plasticity loss is "real" if the F_eq probe falls by more than this (F_few cannot: it starts at 14 to 16)
PLAIN_GAP_300 = 60                # loop probe at k=64 must beat the plain probe by this (of 300)
MIN_ELIGIBLE = 4                  # of the 6 earlier-kind rows, per seed
SEEDS = (0, 1)
STORE_PER_KIND_SERVED = 4         # fresh puzzles per old kind per update


def mean(x):
    return sum(x) / len(x)


def var(x):
    m = mean(x)
    return sum((v - m) ** 2 for v in x) / (len(x) - 1)


def f_eq(counts, n=300):
    return mean([c / n * 100 for c in counts])


def f_few(counts, n=300):
    return mean([c / n * 100 for c in counts[:4]])


def _read(p):
    return json.loads(Path(p).read_text())


def load_chain(root, arm, mode, seed):
    d = Path(root) / f"{arm}-{mode}-s{seed}"
    if not (d / "chain-done.json").exists():
        raise FileNotFoundError(f"{d}/chain-done.json")
    plan = _read(d / "plan.json")
    final = len(plan["plan"])
    return {"plan": plan, "day": {i: _read(d / f"day{i}.json") for i in range(1, final + 1)},
            "night": {i: _read(d / f"night{i}.json") for i in range(1, final + 1)},
            "probe": {i: _read(d / f"probe{i}.json") for i in range(1, final + 1)}}


def load_ref(root, arm, seed):
    return _read(Path(root) / f"ref-{arm}-s{seed}" / "night0-probe.json")


def probe_counts(rec):
    return [rec["rungs"][str(k)]["right"] for k in RUNGS]


def k64_draws(chain):
    p = chain["probe"][len(chain["plan"]["plan"])]
    return [p["rungs"]["64"]["right"]] + [p["extra_draws"][j]["64"]["right"] for j in sorted(p["extra_draws"])]


def night5_rows(chain, names):
    """{name: (draw scores, n)} at the last night."""
    dr = chain["night"][len(chain["plan"]["plan"])]["draws"]
    return {n: ([d["scores"][n]["right"] for d in dr], dr[0]["scores"][n]["n"]) for n in names}


def clean_check(chain):
    """VOID reasons: fewer than 3 draws, a fresh stream that overlaps a panel/support/store/probe item, wrong stream size."""
    bad = []
    steps = chain["plan"]["cfg"]["night_steps"]
    want_draws = chain["plan"]["cfg"]["draws"]
    for i, nt in chain["night"].items():
        if len(nt["draws"]) < want_draws or want_draws < 3 and chain["plan"]["cfg"].get("dev_n") is None:
            bad.append(f"night{i}: {len(nt['draws'])} draws")
        for dr in nt["draws"]:
            for n, st in dr.get("fresh", {}).items():
                if st["overlap_with_forbidden"] != 0:
                    bad.append(f"night{i} draw{dr['draw']} {n}: overlap {st['overlap_with_forbidden']}")
                if st["served"] != steps * STORE_PER_KIND_SERVED:
                    bad.append(f"night{i} draw{dr['draw']} {n}: served {st['served']}")
    return bad


def row_test(a, b, n):
    """a = store-arm draws, b = fresh-arm draws (counts). d = mean(b) - mean(a); SE = sqrt(var_a/na + var_b/nb)."""
    d = mean(b) - mean(a)
    se = math.sqrt(var(a) / len(a) + var(b) / len(b))
    margin = max(MARGIN_FLOOR, MARGIN_SD * se)
    return {"mean_store": round(mean(a), 2), "mean_fresh": round(mean(b), 2), "d": round(d, 2), "se": round(se, 2),
            "margin": round(margin, 2), "bar": BAR[n], "n": n,
            "pass": d >= BAR[n] and d > margin, "ceilinged": mean(a) > n - BAR[n],
            "wrong_side": d < WRONG_GAIN[n]}


def evaluate(root):
    out = {"seeds": {}, "verdict": None, "reasons": []}
    void, res_seed = [], {}
    for s in SEEDS:
        try:
            ch = {(a, m): load_chain(root, a, m, s) for a in ("loop", "plain") for m in ("store", "fresh")}
            ref = {a: load_ref(root, a, s) for a in ("loop", "plain")}
        except FileNotFoundError as e:
            void.append(f"seed {s}: missing {e}")
            continue
        for k, c in ch.items():
            void += [f"seed {s} {k[0]}-{k[1]}: {x}" for x in clean_check(c)]
        plan = ch[("loop", "store")]["plan"]["plan"]
        earlier = ["sums4", "grids5"] + plan[:4]
        cur = plan[4]
        R = {}
        for arm in ("loop", "plain"):
            st, fr = night5_rows(ch[(arm, "store")], earlier + [cur]), night5_rows(ch[(arm, "fresh")], earlier + [cur])
            R[arm] = {n: row_test(st[n][0], fr[n][0], st[n][1]) for n in earlier + [cur]}
        for n in earlier:
            if n in plan:
                d = plan.index(n) + 1
                learned = all(ch[("loop", m)]["day"][d]["scores_before_night"][n]["right"]
                              >= LEARNED_FRAC * ch[("loop", m)]["day"][d]["scores_before_night"][n]["n"]
                              for m in ("store", "fresh"))
            else:
                learned = True
            R["loop"][n]["learned"] = learned
            R["loop"][n]["eligible"] = learned and not R["loop"][n]["ceilinged"]
        eligible = [n for n in earlier if R["loop"][n]["eligible"]]
        rows_ok = all(R["loop"][n]["pass"] for n in eligible)
        informative = ({"sums4", "grids5", "maze"} <= set(eligible) if "maze" in plan else {"sums4", "grids5"} <= set(eligible)) \
            and len(eligible) >= MIN_ELIGIBLE
        # plasticity probes (chain net = draw 0): night-0 reference vs night 5, per loop arm
        p0 = probe_counts(ref["loop"])
        pl = {}
        for m in ("store", "fresh"):
            p5 = probe_counts(ch[("loop", m)]["probe"][len(plan)])
            pl[m] = {"F_few_0": round(f_few(p0), 2), "F_few_5": round(f_few(p5), 2),
                     "F_few_change": round(f_few(p5) - f_few(p0), 2),
                     "F_eq_0": round(f_eq(p0), 2), "F_eq_5": round(f_eq(p5), 2),
                     "F_eq_change": round(f_eq(p5) - f_eq(p0), 2),
                     "k64_night_by_night_draw0": [ch[("loop", m)]["probe"][i]["rungs"]["64"]["right"]
                                                  for i in range(1, len(plan) + 1)]}
        plast_few = pl["fresh"]["F_few_change"] >= -F_FEW_TOL
        plast_eq = pl["fresh"]["F_eq_change"] >= -F_EQ_TOL
        lf, pf = mean(k64_draws(ch[("loop", "fresh")])), mean(k64_draws(ch[("plain", "fresh")]))
        plain_row = lf >= pf + PLAIN_GAP_300
        plain_gain = [n for n in earlier if R["plain"][n]["pass"]]
        res_seed[s] = {"plan": plan, "rows_loop": R["loop"], "rows_plain": R["plain"], "eligible": eligible,
                       "informative": informative, "gain_rows_pass": rows_ok, "plasticity": pl,
                       "plast_F_few_pass": plast_few, "plast_F_eq_pass": plast_eq,
                       "plain_row": {"loop_fresh_k64_mean": round(lf, 2), "plain_fresh_k64_mean": round(pf, 2),
                                     "gap": round(lf - pf, 2), "need": PLAIN_GAP_300, "pass": plain_row},
                       "plain_gain_rows_that_pass": plain_gain,
                       "wrong1": len(eligible) >= 3 and all(R["loop"][n]["wrong_side"] for n in eligible),
                       "wrong2": pl["store"]["F_eq_change"] < -DROP_WRONG and pl["fresh"]["F_eq_change"] < -DROP_WRONG,
                       "report_ref_day_scores": {d: _read(Path(root) / "ref-loop-s%d" / f"ref-day{d}.json")["score"]["right"]
                                                 for d in range(2, 6)
                                                 if (Path(root) / "ref-loop-s%d" / f"ref-day{d}.json").exists()}}
    out["seeds"] = res_seed
    out["void_reasons"] = void
    if void or len(res_seed) < 2:
        out["verdict"] = "VOID"
        return out
    both = lambda k: all(res_seed[s][k] for s in SEEDS)
    if both("wrong1"):
        out["verdict"] = "PROVED WRONG"
        out["reasons"].append("store size is not the limit: every eligible earlier kind gained less than 5 of 200 (8 of 300) in both seeds")
    elif both("wrong2"):
        out["verdict"] = "PROVED WRONG"
        out["reasons"].append("plasticity loss is real: F_eq probe fell by more than 15 points in both loop arms in both seeds")
    elif both("informative") and both("gain_rows_pass") and both("plast_F_few_pass") and both("plast_F_eq_pass") \
            and both_plain(res_seed):
        out["verdict"] = "PASS"
    else:
        out["verdict"] = "NOT SHOWN"
        if not both("informative"):
            out["reasons"].append("too few informative earlier-kind rows (kind not learned, ceilinged, or fewer than 4 eligible)")
    out["architecture_note"] = ("plain net gains as well (not architecture-specific)"
                                if all(len(res_seed[s]["plain_gain_rows_that_pass"]) >= MIN_ELIGIBLE for s in SEEDS)
                                else "plain net does not gain on 4 or more earlier rows in both seeds")
    return out


def both_plain(rs):
    return all(rs[s]["plain_row"]["pass"] for s in SEEDS)


# ---------------------------------------------------------------- selftest on synthetic raw files
def _synth(root, gain200, gain300, drop, plain_gap=100, overlap=0, learned=True, seeds=SEEDS, rung_noise=0):
    """Write raw files in the run's format. gain*: night-5 fresh minus store for 200/300-count rows; drop: F_few change
    of the fresh arm at night 5 (store arm falls by drop_store)."""
    plan = ["maze", "graph", "rank", "compose", "odd"]
    rng = random.Random(3)
    for s in seeds:
        for arm in ("loop", "plain"):
            base0 = [1, 0, 28, 137, 256, 271, 257, 274] if arm == "loop" else [2, 8, 1, 29, 124, 217, 227, 203]
            d = Path(root) / f"ref-{arm}-s{s}"
            d.mkdir(parents=True, exist_ok=True)
            (d / "night0-probe.json").write_text(json.dumps({"rungs": {str(k): {"right": c, "n": 300} for k, c in zip(RUNGS, base0)}}))
            for mode in ("store", "fresh"):
                c = Path(root) / f"{arm}-{mode}-s{s}"
                c.mkdir(parents=True, exist_ok=True)
                (c / "chain-done.json").write_text("{}")
                (c / "plan.json").write_text(json.dumps({"plan": plan, "cfg": {"night_steps": 512, "draws": 3, "dev_n": None}}))
                for i in range(1, 6):
                    names = ["sums4", "grids5"] + plan[:i]
                    (c / f"day{i}.json").write_text(json.dumps({"scores_before_night": {
                        n: {"right": (150 if learned else 5) if n in plan else 200, "n": 300 if n in ("maze", "graph", "rank") else 200}
                        for n in names}}))
                    draws = []
                    for j in range(3):
                        sc = {}
                        for n in names:
                            N = 300 if n in ("maze", "graph", "rank") else 200
                            store = int(0.10 * N) + rng.randint(-2, 2)
                            g = (gain300 if N == 300 else gain200) if (mode == "fresh" and arm == "loop" and i == 5) else 0
                            if arm == "plain" and mode == "fresh" and i == 5:
                                g = 2
                            sc[n] = {"right": store + g + rng.randint(-2, 2), "n": N}
                        draws.append({"draw": j, "scores": sc, "fresh": {n: {"served": 2048, "skipped": 0,
                                      "overlap_with_forbidden": overlap if (mode == "fresh" and j == 0 and n == "sums4") else 0}
                                      for n in names[:-1]} if mode == "fresh" else {}})
                    (c / f"night{i}.json").write_text(json.dumps({"draws": draws}))
                    if i < 5:
                        rec = {"rungs": {"64": {"right": 130, "n": 300}}}
                    else:
                        kk = max(0.0, 1 - drop / 51.0)            # drop = F_eq points lost (night-0 F_eq is 51.0)
                        cnt = [int(x * kk) for x in base0] if arm == "loop" else list(base0)
                        rec = {"rungs": {str(k): {"right": v, "n": 300} for k, v in zip(RUNGS, cnt)},
                               "extra_draws": {"1": {"64": {"right": cnt[3]}}, "2": {"64": {"right": cnt[3]}}}}
                        if arm == "plain" and plain_gap == 0:
                            for kk in ("64",):
                                rec["rungs"][kk]["right"] = 137
                                rec["extra_draws"]["1"][kk]["right"] = 137
                                rec["extra_draws"]["2"][kk]["right"] = 137
                    (c / f"probe{i}.json").write_text(json.dumps(rec))


def selftest():
    tmp = Path(tempfile.mkdtemp(prefix="opus-fd-marks-"))
    try:
        cases = [("PASS", dict(gain200=45, gain300=110, drop=0)),
                 ("NOT SHOWN", dict(gain200=12, gain300=30, drop=0)),                 # gain real but under the bars
                 ("NOT SHOWN", dict(gain200=45, gain300=110, drop=0, plain_gap=0)),   # plain row fails: not architecture-specific
                 ("NOT SHOWN", dict(gain200=45, gain300=110, drop=11)),               # F_eq probe falls 11 (over the 8.0 tolerance, under 15)
                 ("NOT SHOWN", dict(gain200=45, gain300=110, drop=0, learned=False)),  # kinds not learned: uninformative
                 ("PROVED WRONG", dict(gain200=1, gain300=2, drop=0)),                # store size is not the limit
                 ("PROVED WRONG", dict(gain200=45, gain300=110, drop=20)),            # F_eq falls 20 in both arms and both seeds
                 ("VOID", dict(gain200=45, gain300=110, drop=0, overlap=3)),          # fresh stream overlapped a panel
                 ("VOID", dict(gain200=45, gain300=110, drop=0, seeds=(0,)))]         # a seed is missing
        for want, kw in cases:
            d = tmp / f"case{len(list(tmp.iterdir()))}"
            _synth(d, **kw)
            got = evaluate(d)["verdict"]
            assert got == want, (want, got, kw)
            print(json.dumps({"case": kw, "verdict": got}), flush=True)
        # one-seed-only success is not a PASS (every seed must pass)
        d = tmp / "one-seed"
        _synth(d, gain200=45, gain300=110, drop=0)
        for arm, mode in (("loop", "fresh"),):
            p = d / f"{arm}-{mode}-s1" / "night5.json"
            j = json.loads(p.read_text())
            for dr in j["draws"]:
                for n in dr["scores"]:
                    dr["scores"][n]["right"] = 20
            p.write_text(json.dumps(j))
        assert evaluate(d)["verdict"] == "NOT SHOWN"
        # arithmetic checks
        assert abs(f_eq([1, 0, 28, 137, 256, 271, 257, 274]) - 51.0) < .01          # RESULTS-EQ holdout practised loop seed 0
        assert abs(f_few([1, 0, 28, 137, 0, 0, 0, 0]) - 13.83) < .01
        print(json.dumps({"selftest": "ok", "cases": len(cases) + 1}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "score"))
    p.add_argument("--runs", type=Path)
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    if a.cmd == "selftest":
        return selftest()
    res = evaluate(a.runs)
    text = json.dumps(res, indent=2, sort_keys=True)
    if a.out:
        a.out.write_text(text + "\n")
    print(text)
    print("VERDICT:", res["verdict"])


if __name__ == "__main__":
    main()
