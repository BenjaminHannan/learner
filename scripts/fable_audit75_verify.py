"""Audit 75: re-derive Exp29 RESULTS table + Exp46 install counts from saved JSON.

Read-only over other agents' artifacts; writes only to stdout (caller redirects
into artifacts/fable-audit75-20260921/). Stdlib only.
"""
import json
import glob
import sys

W = "/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27"


def check29():
    g = json.load(open(W + "/artifacts/fable-newnames29-20260921/gates.json"))
    lines = []
    lines.append("verdict=%s reason=%s" % (g["verdict"], g["reason"]))
    lines.append("F_seeds_passed=%s L_seeds_passed=%s control=%s" % (
        g["F_seeds_passed"], g["L_seeds_passed"], g["control_seeds_passed"]))
    # RESULTS.md table, column F (10,000; gated): expected R values per cell/seed
    expF = {
        "c1": [512, 511, 511], "c2": [510, 509, 507], "c3": [504, 507, 507],
        "c4": [503, 503, 501], "c5": [504, 504, 503], "c6": [503, 508, 508],
        "p12-1": [511, 510, 509], "p12-2": [501, 501, 503],
        "p12-3": [498, 496, 503], "s3": [507, 503, 503],
    }
    bad = 0
    for cell, vals in expF.items():
        for i, seed in enumerate(["2106", "2107", "2108"]):
            got = g["F"][seed]["cells"][cell]["R"]
            if got != vals[i]:
                bad += 1
                lines.append("MISMATCH F-%s %s: RESULTS %s JSON %s" % (seed, cell, vals[i], got))
    lines.append("F-table cells checked=30 mismatches=%d" % bad)
    # paired worst for F
    worst = min(
        (g["F"][s]["cells"][c]["paired_delta"], s, c)
        for s in ["2106", "2107", "2108"] for c in expF)
    lines.append("F worst paired_delta=%s (RESULTS claims -11 on 2106 p12-3)" % (worst,))
    # L and F6 pass counts from JSON
    for arm in ["L", "F"]:
        passed = [s for s in ["2106", "2107", "2108"] if g[arm][s]["passed"]]
        lines.append("%s passed seeds=%s" % (arm, passed))
    f6pass = sum(1 for s in ["2106", "2107", "2108"]
                 if all(g["F6"][s][c] is True or (isinstance(g["F6"][s], dict))
                        for c in [])) if False else "n/a"
    # F6 verdicts live under table['F6'] keyed by seed string
    lines.append("F6 per-seed: %s" % json.dumps(
        {s: {"passed": v.get("passed"), "failed": v.get("failed_cells")} for s, v in g["F6"].items()}
        if isinstance(g.get("F6"), dict) and "2106" in g.get("F6", {}) else g.get("F6")))
    # control all 512
    cbad = sum(1 for s in ["2106", "2107", "2108"] for c in expF
               if g["control"][s]["cells"][c]["R"] != 512)
    lines.append("control non-512 cells=%d (RESULTS claims 0)" % cbad)
    # integrity problems
    lines.append("integrity problems=%s" % g["integrity"]["problems"][:3])
    return lines


def check46():
    lines = []
    batches = {"batch1": ["4102", "4103", "4104", "4105", "4106"],
               "batch2": ["4107", "4108", "4109", "4110", "4111"]}
    total_wrong = 0
    for b, seeds in batches.items():
        for wrong in [0, 2, 4, 20]:
            inst = 0
            n = 0
            for s in seeds:
                d = json.load(open(W + "/artifacts/fable-hardgate46-20260921/runs/hard-seed%s.json" % s))
                for r in d["rows"]:
                    if r["wrong"] == wrong:
                        n += 1
                        inst += r["installed"] is True
                        if r.get("installed") and (
                                r.get("audit_disagree_of_60", 0) > 0
                                or (r.get("fresh_accuracy") is not None
                                    and r["fresh_accuracy"] < 0.99)):
                            total_wrong += 1
                            lines.append("WRONG-INSTALL %s seed %s word %s" % (b, s, r["word"]))
            lines.append("%s wrong=%d installed=%d/%d" % (b, wrong, inst, n))
    lines.append("total wrong installs=%d (RESULTS claims 0/120)" % total_wrong)
    # every installed row: audit 0 and fresh 1.00?
    nonperfect = 0
    for f in glob.glob(W + "/artifacts/fable-hardgate46-20260921/runs/hard-seed*.json"):
        for r in json.load(open(f))["rows"]:
            if r.get("installed"):
                if r.get("audit_disagree_of_60") != 0 or r.get("fresh_accuracy") != 1.0:
                    nonperfect += 1
                    lines.append("NONPERFECT %s %s audit=%s fresh=%s" % (
                        r["seed"], r["word"], r.get("audit_disagree_of_60"),
                        r.get("fresh_accuracy")))
    lines.append("installed rows with audit!=0 or fresh!=1.00: %d" % nonperfect)
    return lines


if __name__ == "__main__":
    out = ["== EXP29 =="] + check29() + ["== EXP46 =="] + check46()
    sys.stdout.write("\n".join(out) + "\n")
