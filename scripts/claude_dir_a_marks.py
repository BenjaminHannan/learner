#!/usr/bin/env python3
"""Dev gate and pass-mark arithmetic for the practice-breadth test (Director helper A, 2026-09-28).

Pure python. Marks are the ones in artifacts/claude-dir-a-breadth-20260928/PASSMARKS.md; every threshold below is a
constant copied from that file and is not to be changed after any score exists.

  python3 -B scripts/claude_dir_a_marks.py selftest
  python3 -B scripts/claude_dir_a_marks.py gate  --kind maze|graph|rank    writes DEV-GATE-<kind>.json (dev files only)
  python3 -B scripts/claude_dir_a_marks.py score --kind maze|graph|rank    writes SCORE-<kind>.json (needs gate PASS)
  python3 -B scripts/claude_dir_a_marks.py rollup                          prints the sentence the marks allow

Layout read (nothing is written except the two JSON files above):
  breadth arms   <ART>/runs/<kind>/<arm>-s<seed>-pre/{adapt,holdout}.json          (this test)
  two-kind arms  maze:  artifacts/claude-fewex-20260927/eq-runs/<arm>-s<seed>-<pre|fresh>/...   (RESULTS-EQ.md)
                 graph, rank: artifacts/claude-dir-h1-heldout-20260928/runs/<kind>/<arm>-s<seed>-<pre|fresh>/...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_dir_h1_marks as H   # F_eq, E50, collapsed, wins arithmetic (its selftest reproduces the maze table)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "claude-dir-a-breadth-20260928"
RUNGS = H.RUNGS
KINDS = ("maze", "graph", "rank")
GRADED = {"maze": "9", "graph": "14", "rank": "9"}
OLD_ROOT = {"maze": ROOT / "artifacts" / "claude-fewex-20260927" / "eq-runs",
            "graph": ROOT / "artifacts" / "claude-dir-h1-heldout-20260928" / "runs" / "graph",
            "rank": ROOT / "artifacts" / "claude-dir-h1-heldout-20260928" / "runs" / "rank"}

# ---- thresholds (PASSMARKS.md) ----
GAIN_POINTS = 5.0        # breadth loop over the two-kind loop, on F_eq and on F_few
PLAIN_POINTS = 5.0       # breadth loop over the breadth plain net (same practice)
FRESH_POINTS = 5.0       # breadth loop over the fresh loop
FLOOR_POINTS = 20.0      # breadth loop F_eq by itself
WIN_RUNGS = 5            # rungs of 8 on which breadth loop strictly beats the two-kind loop
NO_GAIN_POINTS = 2.0     # REFUTED on a kind when, in both seeds, the gain is below this
HURT_POINTS = 5.0        # HARMED on a kind when, in both seeds, breadth is this far BELOW the two-kind loop
CEILING_POINTS = 90.0    # a kind whose two-kind loop F_eq is already this high cannot show a gain: not counted
FEW_RUNGS = 4            # F_few = mean of k = 1, 4, 16, 64
V4_PLAIN_MIN = 270       # breadth plain at k = 16,384 on dev (of 300); below this the plain comparison is labelled
V3_LO, V3_HI, V3_SHARED = 0.10, 0.90, 3


def f_few(counts, n=300):
    return sum(H.pct(c, n) for c in counts[:FEW_RUNGS]) / FEW_RUNGS


def f_eq(counts, n=300):
    return H.f_eq(counts, n)


def seed_marks(c, n=300):
    """c: {'Bloop','Bplain','Aloop','Aplain','Floop','Fplain'} -> 8 counts each (one seed, holdout)."""
    F = {k: f_eq(v, n) for k, v in c.items()}
    W = {k: f_few(v, n) for k, v in c.items()}
    gain = F["Bloop"] - F["Aloop"]
    gain_few = W["Bloop"] - W["Aloop"]
    m = {
        "F_eq": {k: round(v, 2) for k, v in F.items()},
        "F_few": {k: round(v, 2) for k, v in W.items()},
        "BM1_eq_gain_over_two_kind_loop": round(gain, 2),
        "BM1_few_gain_over_two_kind_loop": round(gain_few, 2),
        "BM2_loop_minus_breadth_plain": round(F["Bloop"] - F["Bplain"], 2),
        "BM3_rungs_beating_two_kind_loop": H.wins(c["Bloop"], c["Aloop"]),
        "BM4_loop_minus_fresh_loop": round(F["Bloop"] - F["Floop"], 2),
        "BM4_breadth_loop_F_eq": round(F["Bloop"], 2),
        "report_two_kind_loop_minus_two_kind_plain": round(F["Aloop"] - F["Aplain"], 2),
        "report_breadth_plain_minus_two_kind_plain": round(F["Bplain"] - F["Aplain"], 2),
        "report_E50": {k: H.e_first(v, n, .5) for k, v in c.items()},
        "report_E30": {k: H.e_first(v, n, .3) for k, v in c.items()},
        "report_collapsed_rungs": {k: H.collapsed(v, n) for k, v in c.items()},
    }
    m["pass"] = {
        "BM1": gain >= GAIN_POINTS and gain_few >= GAIN_POINTS,
        "BM2": F["Bloop"] - F["Bplain"] >= PLAIN_POINTS,
        "BM3": m["BM3_rungs_beating_two_kind_loop"] >= WIN_RUNGS,
        "BM4": F["Bloop"] - F["Floop"] >= FRESH_POINTS and F["Bloop"] >= FLOOR_POINTS,
    }
    m["main_pass"] = all(m["pass"].values())
    m["no_gain"] = gain < NO_GAIN_POINTS
    m["harmed"] = gain <= -HURT_POINTS
    m["ceiling"] = F["Aloop"] >= CEILING_POINTS
    return m


def kind_verdict(hold, n=300):
    """hold: {seed: {'Bloop', ...: 8 counts}}"""
    per = {f"seed{s}": seed_marks(hold[s], n) for s in (0, 1)}
    if any(per[k]["ceiling"] for k in per):
        v = "CEILING"                       # not counted: the two-kind loop leaves no room
    elif all(per[k]["main_pass"] for k in per):
        v = "PASS"
    elif all(per[k]["harmed"] for k in per):
        v = "HARMED"
    elif all(per[k]["no_gain"] for k in per):
        v = "REFUTED"
    else:
        v = "NOT-SHOWN"
    only_fresh = (all(per[k]["pass"]["BM4"] for k in per) and all(per[k]["no_gain"] for k in per))
    return {"seeds": per, "verdict": v, "practice_helps_but_breadth_does_not": bool(only_fresh)}


def rollup(verdicts, plain_labels=None):
    """verdicts: {kind: kind_verdict result or a string status for a kind that did not qualify}."""
    valid = {k: v for k, v in verdicts.items() if isinstance(v, dict) and v["verdict"] != "CEILING"}
    n = len(valid)
    vs = [v["verdict"] for v in valid.values()]
    p, r, h = vs.count("PASS"), vs.count("REFUTED"), vs.count("HARMED")
    if n == 0:
        return {"outcome": "INCONCLUSIVE", "sentence": "no kind produced a usable comparison"}
    if p >= 2 and h == 0:
        out = "BREADTH-HELPS"
        s = (f"Spreading the same practice over ten kinds beat the two-kind practice on {p} of {n} held-out kinds, "
             f"in two seeds each")
    elif (r + h) >= 2:
        out = "PROVED-WRONG-HERE"
        s = (f"Spreading the same practice over ten kinds did not help on {r + h} of {n} held-out kinds "
             f"(no gain or harmed, both seeds)")
    elif p == 1 and h == 0:
        out = "ONE-KIND-ONLY"
        s = "Breadth beat the two-kind practice on one held-out kind only; not shown to be general"
    else:
        out = "NOT-SHOWN"
        s = "The comparison is mixed; breadth is not shown to help"
    if h >= 1:
        s += f"; breadth was HARMFUL (at least {HURT_POINTS} points below) on {h} kind(s)"
    labelled = [k for k, lab in (plain_labels or {}).items() if lab == "expressivity" and k in valid]
    if labelled:
        s += ("; the same-size plain-net comparison is labelled 'expressivity' on " + ", ".join(sorted(labelled)) +
              " and is not quoted there")
    return {"outcome": out, "sentence": s, "counts": {"valid": n, "PASS": p, "REFUTED": r, "HARMED": h}}


# ------------------------------ dev gate ------------------------------
def v3_shared(dev_b, dev_a, n=300):
    """rungs on which the breadth loop AND the two-kind loop are both strictly between 10% and 90% (dev)."""
    return [k for k, b, a in zip(RUNGS, dev_b, dev_a)
            if V3_LO * n < b < V3_HI * n and V3_LO * n < a < V3_HI * n]


def _load(path):
    return json.loads(Path(path).read_text())


def _counts(d, which, kind):
    table = d["rungs"] if which == "adapt" else d["scores"]
    key = GRADED[kind]
    return [table[str(k)][key]["right"] for k in RUNGS], table["1"][key]["n"]


def a_dir(kind, arm, init, seed):
    return OLD_ROOT[kind] / f"{arm}-s{seed}-{init}"


def b_dir(kind, arm, seed):
    return ART / "runs" / kind / f"{arm}-s{seed}-pre"


def load_all(kind, which):
    """{seed: {'Bloop','Bplain','Aloop','Aplain','Floop','Fplain'}}, n"""
    out, n = {}, 300
    for s in (0, 1):
        cs = {}
        for name, path in (("Bloop", b_dir(kind, "loop", s)), ("Bplain", b_dir(kind, "plain", s)),
                           ("Aloop", a_dir(kind, "loop", "pre", s)), ("Aplain", a_dir(kind, "plain", "pre", s)),
                           ("Floop", a_dir(kind, "loop", "fresh", s)), ("Fplain", a_dir(kind, "plain", "fresh", s))):
            cs[name], n = _counts(_load(path / f"{which}.json"), which, kind)
        out[s] = cs
    return out, n


def gate(kind):
    path = ART / f"DEV-GATE-{kind}.json"
    if path.exists():
        raise FileExistsError("dev gate already written")
    src = _load(ART / "SOURCE-CHECK.json")
    dev, n = load_all(kind, "adapt")
    shared = {f"s{s}": v3_shared(dev[s]["Bloop"], dev[s]["Aloop"], n) for s in (0, 1)}
    v3 = any(len(v) >= V3_SHARED for v in shared.values())
    v2k = all(_load(b_dir(kind, arm, s) / "adapt.json")["gradient_check_adapt"]["nonzero_all_except_halt"]
              for s in (0, 1) for arm in ("loop", "plain"))
    plain16k = {f"s{s}": dev[s]["Bplain"][-1] for s in (0, 1)}
    label = "few-example" if (all(v >= V4_PLAIN_MIN * n // 300 for v in plain16k.values())
                              and src["V1a_plain"]) else "expressivity"
    res = {"kind": kind, "V1a_loop": bool(src["V1a_loop"]), "V1a_plain": bool(src["V1a_plain"]),
           "V2": bool(src["V2"]), "V2k": bool(v2k), "V3_shared_rungs": shared, "V3": v3,
           "V4_breadth_plain_k16384_dev": plain16k, "plain_label": label,
           "dev_counts": {f"s{s}-{k}": c for s in (0, 1) for k, c in dev[s].items()}, "n": n}
    ok = res["V1a_loop"] and res["V2"] and res["V2k"] and v3
    res["verdict"] = "PASS" if ok else "INCONCLUSIVE"
    path.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("kind", "V1a_loop", "V1a_plain", "V2", "V2k", "V3", "plain_label", "verdict")}))


def score(kind):
    g = _load(ART / f"DEV-GATE-{kind}.json")
    if g["verdict"] != "PASS":
        raise ValueError("dev gate did not pass; holdout must stay sealed")
    hold, n = load_all(kind, "holdout")
    res = kind_verdict(hold, n)
    res["kind"] = kind
    res["plain_label"] = g["plain_label"]
    res["holdout_counts"] = {f"s{s}-{k}": c for s in (0, 1) for k, c in hold[s].items()}
    (ART / f"SCORE-{kind}.json").write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"kind": kind, "verdict": res["verdict"]}))


def cmd_rollup():
    verdicts, labels = {}, {}
    for k in KINDS:
        p = ART / f"SCORE-{k}.json"
        g = ART / f"DEV-GATE-{k}.json"
        if p.exists():
            verdicts[k] = _load(p)
            labels[k] = verdicts[k]["plain_label"]
        elif g.exists():
            verdicts[k] = "INCONCLUSIVE (dev gate: " + _load(g)["verdict"] + ")"
        else:
            verdicts[k] = "NOT RUN"
    print(json.dumps({"kinds": {k: (v["verdict"] if isinstance(v, dict) else v) for k, v in verdicts.items()},
                      **rollup(verdicts, labels)}, indent=2))


# ------------------------------ self-test ------------------------------
def selftest():
    A = H.MAZE_HOLDOUT
    two = {s: {"Aloop": A[(s, "loop-pre")], "Aplain": A[(s, "plain-pre")],
               "Floop": A[(s, "loop-fresh")], "Fplain": A[(s, "plain-fresh")]} for s in (0, 1)}

    def make(bloop, bplain):
        return {s: {"Bloop": bloop(s), "Bplain": bplain(s), **two[s]} for s in (0, 1)}
    # 1. F_few arithmetic on the published maze numbers: practised loop seed 0 = (1+0+28+137)/4/300*100
    assert round(f_few(A[(0, "loop-pre")]), 2) == round(100 * (1 + 0 + 28 + 137) / 4 / 300, 2)
    # 2. Breadth loop identical to the two-kind loop: gain 0 in both seeds -> REFUTED (below 2.0), never PASS.
    same = kind_verdict(make(lambda s: A[(s, "loop-pre")], lambda s: A[(s, "plain-pre")]))
    assert same["verdict"] == "REFUTED", same["verdict"]
    # 3. Breadth loop better by a clear margin on every rung: PASS (BM1..BM4). 60 counts of 300 more, capped at 300.
    up = lambda s: [min(300, c + 60) for c in A[(s, "loop-pre")]]
    win = kind_verdict(make(up, lambda s: A[(s, "plain-pre")]))
    assert win["verdict"] == "PASS", win["seeds"]["seed0"]["pass"]
    # 4. Gain on F_eq but not on F_few (only the top rungs improve) -> BM1 fails -> not PASS.
    top = lambda s: [c if i < 4 else min(300, c + 200) for i, c in enumerate(A[(s, "loop-pre")])]
    assert kind_verdict(make(top, lambda s: A[(s, "plain-pre")]))["verdict"] != "PASS"
    # 5. Breadth loop well below the two-kind loop in both seeds -> HARMED.
    down = lambda s: [max(0, c - 60) for c in A[(s, "loop-pre")]]
    assert kind_verdict(make(down, lambda s: A[(s, "plain-pre")]))["verdict"] == "HARMED"
    # 6. Seed 0 wins, seed 1 does not -> NOT-SHOWN (seeds are never pooled).
    mixed = kind_verdict(make(lambda s: up(s) if s == 0 else A[(s, "loop-pre")], lambda s: A[(s, "plain-pre")]))
    assert mixed["verdict"] == "NOT-SHOWN"
    # 7. Two-kind loop already at the ceiling: kind not counted.
    hi = {s: {"Aloop": [290] * 8, "Aplain": [280] * 8, "Floop": [100] * 8, "Fplain": [100] * 8,
              "Bloop": [295] * 8, "Bplain": [280] * 8} for s in (0, 1)}
    assert kind_verdict(hi)["verdict"] == "CEILING"
    # 8. Breadth loop that only beats a floor: BM4 needs F_eq >= 20 by itself.
    low = {s: {k: [c // 10 for c in v] for k, v in cs.items()} for s, cs in make(up, lambda s: A[(s, "plain-pre")]).items()}
    assert not kind_verdict(low)["seeds"]["seed0"]["pass"]["BM4"]
    # 9. Roll-up sentences.
    assert rollup({"maze": win, "graph": win, "rank": same})["outcome"] == "BREADTH-HELPS"
    assert rollup({"maze": same, "graph": same, "rank": win})["outcome"] == "PROVED-WRONG-HERE"
    assert rollup({"maze": win, "graph": same, "rank": "NOT RUN"})["outcome"] == "ONE-KIND-ONLY"
    assert rollup({"maze": "NOT RUN", "graph": "NOT RUN", "rank": "NOT RUN"})["outcome"] == "INCONCLUSIVE"
    assert "expressivity" in rollup({"maze": win, "graph": win, "rank": win},
                                    {"maze": "expressivity"})["sentence"]
    # 10. V3 shared rungs on the published maze dev ladders (two-kind loop is in band at 64, 256, 1,024?, ...)
    d = H.MAZE_DEV
    sh = v3_shared(d[(0, "loop-fresh")], d[(0, "loop-pre")])       # stand-in pair, arithmetic only
    assert sh == [64, 256, 4096], sh
    print(json.dumps({"same_as_two_kind": same["verdict"], "clear_win": win["verdict"], "harmed": "HARMED",
                      "seed_split": mixed["verdict"]}))
    print("selftest ok")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("selftest", "gate", "score", "rollup"))
    p.add_argument("--kind", choices=KINDS)
    a = p.parse_args()
    if a.cmd == "selftest":
        selftest()
    elif a.cmd == "rollup":
        cmd_rollup()
    else:
        if a.kind is None:
            p.error("--kind required")
        (gate if a.cmd == "gate" else score)(a.kind)


if __name__ == "__main__":
    main()
