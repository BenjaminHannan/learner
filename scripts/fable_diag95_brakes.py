#!/usr/bin/env python3
"""Exp 95 brake-breakdown follow-up (stdlib only, no torch, no model).

Reads fable_diag95_rows.json; decomposes WHY non-executed rows were blocked
(forced_echo / ok4 / ok5 / disagree / low conf) using the sealed verdict logic.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

TAU_EXEC = 0.8766039311885834
TAU_ECHO = 0.5
ABSTAIN = {"UNSURE", "NO_FACT"}
BINS = [0.0, 0.3, 0.5, 0.65, 0.75, 0.85, TAU_EXEC, 1.0001]
BIN_NAMES = ["[0,.3)", "[.3,.5)", "[.5,.65)", "[.65,.75)",
             "[.75,.85)", "[.85,tau)", "[tau,1]"]


def fkey(f):
    if f["act"] in ABSTAIN:
        return ("act", f["act"])
    return (f["act"], f["rel"],
            tuple(f["subj"]) if f["subj"] else None,
            tuple(f["obj"]) if f["obj"] else None, f["dir"])


def block_reason(seeds):
    """Why is this row not EXECUTEd at TAU_EXEC (assuming concrete acts)?"""
    fr = [s["frame"] for s in seeds]
    agree3 = all(fkey(fr[0]) == fkey(f) for f in fr[1:])
    all_ok = all(s["ok4"] and s["ok5"] for s in seeds)
    no_echo = not any(s["forced_echo"] for s in seeds)
    conf = min(s["conf"] for s in seeds)
    if all_ok and agree3 and no_echo and conf >= TAU_EXEC:
        return "would_execute"
    reasons = []
    if not agree3:
        reasons.append("disagree")
    if not all_ok:
        if any(not s["ok4"] for s in seeds):
            reasons.append("ok4_leftover")
        if any(not s["ok5"] for s in seeds):
            reasons.append("ok5_validator")
    if not no_echo:
        reasons.append("forced_echo_OPEN")
    if conf < TAU_EXEC:
        reasons.append("low_conf")
    return "+".join(reasons)


def hist_of(confs):
    h = [0] * (len(BINS) - 1)
    for c in confs:
        for b in range(len(BINS) - 1):
            if BINS[b] <= c < BINS[b + 1]:
                h[b] += 1
                break
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = json.loads(Path(a.rows).read_text(encoding="utf-8"))
    T = {}

    for pname in ("t_seen", "t_new"):
        rows = [r for r in D["panels"][pname]["rows"]
                if r["gold"]["act"] == "STATE"]
        blocked = {}
        above = []
        for r in rows:
            br = block_reason(r["seeds"])
            if br != "would_execute":
                blocked[br] = blocked.get(br, 0) + 1
                if min(s["conf"] for s in r["seeds"]) >= TAU_EXEC:
                    above.append(br)
        T[pname + "_blocked"] = dict(sorted(blocked.items(), key=lambda kv: -kv[1]))
        T[pname + "_blocked_above_tau"] = dict(
            sorted(Counter(above).items(), key=lambda kv: -kv[1]))

    # wpos: full-panel conf hist (ensemble min-conf) for STATE-gold rows + blocks
    wrows = D["panels"]["wpos"]["rows"]
    confs = [min(s["conf"] for s in r["seeds"]) for r in wrows]
    T["wpos_conf_hist"] = {"bins": BIN_NAMES, "counts": hist_of(confs)}
    T["wpos_blocked"] = dict(sorted(Counter(
        block_reason(r["seeds"]) for r in wrows).items(), key=lambda kv: -kv[1]))
    # wpos rel-match: seed rows with act STATE and rel == gold relation
    hit = tot = 0
    for r in wrows:
        for s in r["seeds"]:
            if s["frame"]["act"] == "STATE":
                tot += 1
                hit += s["frame"]["rel"] == r["gold"]["rel"]
    T["wpos_state_rel_match"] = {"hit": hit, "tot": tot}
    # wpos: how many STATE-gold rows have 3/3 STATE agreement?
    agr = sum(1 for r in wrows
              if all(s["frame"]["act"] == "STATE" for s in r["seeds"]))
    T["wpos_3way_state_agree"] = agr

    # CAL #4994 per-seed confs (the tau-setting row)
    cal = D["panels"]["cal"]["rows"]
    hit4994 = [r for r in cal if r["n"] == 4994]
    assert len(hit4994) == 1
    r = hit4994[0]
    T["cal_4994"] = {"text": r["text"], "family": r["family"],
                     "seeds": [{"act": s["frame"]["act"], "rel": s["frame"]["rel"],
                                "conf": s["conf"]} for s in r["seeds"]]}

    # P95.1 count (computed here from rows to keep analyze untouched)
    w10 = D["panels"]["wpos"]["rows"][:10]
    n_state_rel = sum(
        1 for r in w10 for s in r["seeds"]
        if s["frame"]["act"] == "STATE" and s["frame"]["rel"] == r["gold"]["rel"])
    T["P951_count"] = {"state_rel_match": n_state_rel, "of": 30}

    Path(a.out).write_text(json.dumps(T, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print(json.dumps(T, indent=1)[:3000])


if __name__ == "__main__":
    main()
