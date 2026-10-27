#!/usr/bin/env python3
"""Marks of T3 (newer-weighted rehearsal across three nights) as code. Pure python, no torch.

Rules and reasons: artifacts/claude-dir-t3-recency-20260928/PASSMARKS.md (sealed before any run). Constants are the sealed
numbers; change none after a score is seen.
  python3 scripts/claude_dir_t3_marks.py selftest
  python3 scripts/claude_dir_t3_marks.py report [--dir DIR]      (reads DIR/dirt3-seed*.json, default the artifacts folder's runs/)
"""
from __future__ import annotations

import glob
import json
import math
import statistics as st
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "artifacts" / "claude-dir-t3-recency-20260928" / "runs"
DRAWS = ("0", "1", "2")
HARM = ("harm_sums4", "harm_grids5")
REP = ("rep_sums6", "rep_sums8", "rep_sums10", "rep_grids6")
# sealed numbers (reasons in PASSMARKS.md)
GRID_BAR = 24            # of 400: 2 x the night-to-night SD of S on day tests (11.7 grids, 11.2 sums; slp358n3 raw files)
SUMS_SLACK = 12          # sums have ~19 of 400 left above S (S after night 3 is 376 to 388): a no-harm gate, not a gain row
MARGIN_FLOOR = 6         # margin = max(6, 2 x SE), SE from the 3 draws
HARM_SLACK = 6           # harm_* >= N - 6 (slp358n3's own limit)
REP_SLACK = 15           # of 200, rep_* >= N - 15 (dir-h6 M3c)
LOST_MAX = 15            # of 300, every night, every draw (slp358n3's own limit)
FLOOR_ABOVE_N = 40       # a net with no night cannot pass: W day_grids >= N + 40 (S - N was +69 to +169 on 4 seeds)
WRONG_AT_MOST = 6        # proved wrong: W gain over the comparator <= +6 on every seed


def mean(x):
    return sum(x) / len(x)


def var(x):
    return st.variance(x) if len(x) > 1 else 0.0


def margin(a, b):
    return max(MARGIN_FLOOR, 2 * math.sqrt((var(a) + var(b)) / 3))


def right(m, night, arm, test):
    return m["morning"][str(night)][arm][test]["right"]


def arm_draws(m, night, a, test):
    return [right(m, night, f"{a}{d}", test) for d in DRAWS]


def one_seed(m):
    """every mark for one seed's JSON"""
    n3 = "3"
    out = {"seed": m["seed"]}
    g = {a: arm_draws(m, n3, a, "day_grids") for a in "SUW"}
    s = {a: arm_draws(m, n3, a, "day_sums") for a in "SUW"}
    comp = max("SU", key=lambda a: mean(g[a]))
    out["grids"] = {"S": mean(g["S"]), "U": mean(g["U"]), "W": mean(g["W"]), "comparator_arm": comp,
                    "gain": mean(g["W"]) - mean(g[comp]), "margin": margin(g["W"], g[comp])}
    scomp = max("SU", key=lambda a: mean(s[a]))
    out["sums"] = {"S": mean(s["S"]), "U": mean(s["U"]), "W": mean(s["W"]), "gain": mean(s["W"]) - mean(s[scomp])}
    out["sums"]["ok"] = out["sums"]["gain"] >= -SUMS_SLACK
    nb = right(m, 3, "N", "day_grids")
    out["floor"] = {"N": nb, "W": mean(g["W"]), "ok": mean(g["W"]) >= nb + FLOOR_ABOVE_N}
    out["harm"] = {t: {"N": right(m, 3, "N", t), "W": mean(arm_draws(m, n3, "W", t))} for t in HARM}
    out["harm_ok"] = all(v["W"] >= v["N"] - HARM_SLACK for v in out["harm"].values())
    out["rep"] = {t: {"N": right(m, 3, "N", t), "W": mean(arm_draws(m, n3, "W", t))} for t in REP}
    out["rep_ok"] = all(v["W"] >= v["N"] - REP_SLACK for v in out["rep"].values())
    lost = [m["lost"][str(n)][f"W{d}"][t] for n in (1, 2, 3) for d in DRAWS for t in HARM]
    out["lost_max_W"] = max(lost)
    out["lost_ok"] = max(lost) <= LOST_MAX
    out["integrity"] = {"night1_batches_identical_SUW": all(m["night1_batches_identical_SUW"].values()),
                        "plan_identical_U_W": all(m["plan_identical_U_W"].values())}
    return out


def report(dirpath):
    files = sorted(glob.glob(str(Path(dirpath) / "**" / "dirt3-seed*.json"), recursive=True))
    seeds = []
    for f in files:
        m = json.loads(Path(f).read_text())
        try:
            seeds.append(one_seed(m))
        except (KeyError, ValueError):
            pass                                             # an unfinished seed is dead: reported, never replaced
    res = {"seeds_found": len(files), "seeds_scored": len(seeds)}
    if len(seeds) < 3:
        res["verdict"] = "VOID (fewer than 3 seeds finished all arms, all draws, all nights)"
        return res
    gains = [x["grids"]["gain"] for x in seeds]
    need = 3 if len(seeds) == 4 else len(seeds)
    m1 = {"mean_gain": mean(gains), "bar": GRID_BAR, "seeds_above_margin": sum(x["grids"]["gain"] > x["grids"]["margin"] for x in seeds)}
    m1["ok"] = m1["mean_gain"] >= GRID_BAR and m1["seeds_above_margin"] >= need
    gates = {"sums_no_harm_seeds": sum(x["sums"]["ok"] for x in seeds), "sums_need": need,
             "floor_every_seed": all(x["floor"]["ok"] for x in seeds), "harm_every_seed": all(x["harm_ok"] for x in seeds),
             "lost_every_night_draw": all(x["lost_ok"] for x in seeds), "rep_every_seed": all(x["rep_ok"] for x in seeds),
             "integrity": all(all(x["integrity"].values()) for x in seeds)}
    gates_ok = (gates["sums_no_harm_seeds"] >= need and gates["floor_every_seed"] and gates["harm_every_seed"]
                and gates["lost_every_night_draw"] and gates["rep_every_seed"])
    wrong = all(x <= WRONG_AT_MOST for x in gains)
    if not gates["integrity"]:
        verdict = "VOID (integrity flags false: night-1 batches or the U and W plans differ)"
    elif m1["ok"] and gates_ok:
        verdict = "PASS"
    elif wrong:
        verdict = "PROVED WRONG"
    else:
        verdict = "NOT SHOWN"
    hurt = sum(x["grids"]["gain"] < -x["grids"]["margin"] for x in seeds)
    res.update({"verdict": verdict, "M1_grids": m1, "gates": gates, "report_only_seeds_W_below_comparator_by_more_than_margin": hurt,
                "report_only_U_minus_S_grids": [x["grids"]["U"] - x["grids"]["S"] for x in seeds], "per_seed": seeds})
    return res


# ------------------------------------------------------------------ selftest
def _seed_json(seed, gS, gU, gW, sums=(380, 380, 380), n_grids=290, harm_w=300, lost=0, ident=True):
    arms = {"N": {"day_grids": {"right": n_grids}, "day_sums": {"right": 250}, **{t: {"right": 300} for t in HARM},
                  **{t: {"right": 195} for t in REP}}}
    for a, gv, sv in (("S", gS, sums), ("U", gU, sums), ("W", gW, sums)):
        for d in DRAWS:
            arms[f"{a}{d}"] = {"day_grids": {"right": gv[int(d)]}, "day_sums": {"right": sv[int(d)]},
                               "harm_sums4": {"right": harm_w if a == "W" else 300}, "harm_grids5": {"right": 300},
                               **{t: {"right": 195} for t in REP}}
    lostd = {a + d: {t: lost for t in HARM} for a in "SUW" for d in DRAWS}
    return {"seed": seed, "morning": {"1": arms, "2": arms, "3": arms}, "lost": {"1": lostd, "2": lostd, "3": lostd},
            "night1_batches_identical_SUW": {d: ident for d in DRAWS}, "plan_identical_U_W": {d: ident for d in DRAWS}}


def _run(seeds):
    with tempfile.TemporaryDirectory() as tmp:
        for m in seeds:
            (Path(tmp) / f"dirt3-seed{m['seed']}.json").write_text(json.dumps(m))
        return report(tmp)


def selftest():
    same = (360, 360, 360)
    up = (395, 395, 395)
    r = _run([_seed_json(s, same, same, up) for s in (13, 14, 15, 16)])
    assert r["verdict"] == "PASS", r
    r = _run([_seed_json(s, same, same, same) for s in (13, 14, 15, 16)])
    assert r["verdict"] == "PROVED WRONG", r["verdict"]
    r = _run([_seed_json(13, same, same, up)] + [_seed_json(s, same, same, (370, 370, 370)) for s in (14, 15, 16)])
    assert r["verdict"] == "NOT SHOWN", r["verdict"]                  # +10 on three seeds: above 6, below the bar
    r = _run([_seed_json(s, same, same, up, harm_w=290) for s in (13, 14, 15, 16)])
    assert r["verdict"] == "NOT SHOWN", r["verdict"]                  # gain but harm gate broken: never "proved wrong"
    r = _run([_seed_json(s, same, up, up) for s in (13, 14, 15, 16)])   # U already at 395: W must beat the higher comparator
    assert r["verdict"] == "PROVED WRONG", r["verdict"]
    r = _run([_seed_json(s, same, same, up, n_grids=380) for s in (13, 14, 15, 16)])
    assert r["gates"]["floor_every_seed"] is False and r["verdict"] == "NOT SHOWN", r["verdict"]   # W not 40 above no-night
    r = _run([_seed_json(s, same, same, up, ident=False) for s in (13, 14, 15, 16)])
    assert r["verdict"].startswith("VOID"), r["verdict"]
    r = _run([_seed_json(s, same, same, up) for s in (13, 14)])
    assert r["verdict"].startswith("VOID"), r["verdict"]
    r = _run([_seed_json(s, same, same, up, lost=20) for s in (13, 14, 15, 16)])
    assert r["gates"]["lost_every_night_draw"] is False and r["verdict"] == "NOT SHOWN", r["verdict"]
    print("t3 marks selftest ok: 9 cases")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "selftest":
        selftest()
    elif len(sys.argv) >= 2 and sys.argv[1] == "report":
        d = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else RUNS
        print(json.dumps(report(d), indent=1, default=str))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
