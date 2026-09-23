#!/usr/bin/env python3
"""Exp 280 registered scorer: 280's rows vs 260's saved rows, exact moves.

  regscore <run_dir> <out.json>
Compares (timing fields ignored):
  sessions152 : <run>/sd/sessions152-diff.json + rows vs 260's saved rows
  bench       : <run>/sd/bench-diff.json
  rt136       : <run>/sd136/rt136-diff.json + rows
  rt143       : <run>/rt143nogate-280.json vs 260's run/rt143nogate-n.json
  verifier    : <run>/vp-280.json vs 260's run/vp-n.json,
                <run>/vs-280.json vs 260's run/vs-n.json
Predicted: exactly 3 reply-only sessions152 moves
  (S2-casual-friends turn1 "what can you do",
   S3-teachers-correction turn0 "heyy, what can you do?",
   S4-pets-identity turn9 "what can you do?"), each old C24 reply ->
  sealed CAN280, verdict UNHELPFUL on both arms, 0 write changes;
  0 moves everywhere else; 0 abstain-ward flips.
PASS only if the move list equals the predicted list exactly.
"""

import json
import re
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else None
OUTP = sys.argv[2] if len(sys.argv) > 2 else None

BASE260 = "artifacts/claude-openers260-20260922/run"
PRED_IDS = {"S2-casual-friends#1", "S3-teachers-correction#0",
            "S4-pets-identity#9"}


def load(p):
    return json.load(open(p))


def main():
    res = {"predicted_ids": sorted(PRED_IDS), "problems": []}
    # sessions152 diff from suitediff218
    d = load(f"{RUN}/sd/sessions152-diff.json")
    moves = d.get("moves", [])
    res["sessions152"] = {
        "n_moves": d.get("n_moves"),
        "summary": d.get("summary_line"),
        "class_counts": d.get("class_counts"),
        "move_ids": [m.get("id", m.get("unit")) for m in moves],
    }
    got = {m.get("id", m.get("unit")) for m in moves}
    if got != PRED_IDS:
        res["problems"].append(f"sessions152 move ids {sorted(got)} != predicted")
    for m in moves:
        if (m.get("new_verdict", m.get("verdict")) != "UNHELPFUL" or
                m.get("base_verdict") != "UNHELPFUL"):
            res["problems"].append(f"sessions152 {m.get('id')} verdict not UNHELPFUL/UNHELPFUL: {m}")
        if m.get("write_change"):
            res["problems"].append(f"sessions152 {m.get('id')} has write change")
    gate = load(f"{RUN}/sd/SUITEDIFF218-SUMMARY.json").get("gate", "")
    res["gate_sd"] = gate
    if gate != "GATE: clean":
        res["problems"].append(f"sessions152/bench gate: {gate}")
    bd = load(f"{RUN}/sd/bench-diff.json")
    res["bench"] = {"n_moves": bd.get("n_moves"), "summary": bd.get("summary_line")}
    if bd.get("n_moves"):
        res["problems"].append(f"bench moves: {bd.get('moves')}")
    # rt136: direct row compare vs 260's saved rows (260 registered no
    # suitediff rt136 rows vs 138m either; labels come from the 138j base).
    # Method deviation (same as 260): compare rows field-by-field except
    # wall-clock timing.
    def rows136(p):
        out = []
        for line in open(p):
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out
    new136 = rows136(f"{RUN}/sd136/rt136-rows.json")
    old136 = rows136(f"{BASE260}/sd136/rt136-rows.json")
    diffs136 = []
    for a, b in zip(new136, old136):
        if a.get("id") != b.get("id"):
            diffs136.append((a.get("id"), "id-order"))
            continue
        for k in sorted(set(a) | set(b)):
            if k in ("seconds", "sec"):
                continue
            if a.get(k) != b.get(k):
                diffs136.append((a.get("id"), k))
    res["rt136"] = {"n": len(new136), "diffs": diffs136}
    if diffs136:
        res["problems"].append(f"rt136 diffs: {diffs136}")
    # vs-138j-base labels must equal 260's own labels exactly (modulo
    # timing): the vs-138j gate is NOT clean on either arm (16 inherited
    # moves, identical counts), so the gate string itself is informational.
    s280 = load(f"{RUN}/sd136/SUITEDIFF218-SUMMARY.json")
    s260 = load(f"{BASE260}/sd136/SUITEDIFF218-SUMMARY.json")
    g2 = s280.get("gate", "")
    res["gate_rt136"] = g2
    res["gate_rt136_260"] = s260.get("gate", "")
    norm = lambda s: re.sub(r"seconds=[\d.]+", "seconds=X", str(s))
    if norm(s280.get("summary_lines")) != norm(s260.get("summary_lines")):
        res["problems"].append(
            f"rt136 vs-base labels differ from 260: {s280.get('summary_lines')}")
    # rt143: direct row compare vs 260's saved rows
    new143 = load(f"{RUN}/rt143nogate-280.json")
    old143 = load(f"{BASE260}/rt143nogate-n.json")
    diffs143 = []
    for a, b in zip(new143, old143):
        for k in ("teach_replies", "triples", "reply", "expected"):
            if a.get(k) != b.get(k):
                diffs143.append((a.get("id"), k))
    res["rt143"] = {"n": len(new143), "diffs": diffs143}
    if diffs143:
        res["problems"].append(f"rt143 diffs: {diffs143}")
    # verifier probes: 0 changes predicted
    for tag, newp, oldp in (("vp", f"{RUN}/vp-280.json", f"{BASE260}/vp-n.json"),
                            ("vs", f"{RUN}/vs-280.json", f"{BASE260}/vs-n.json")):
        new = load(newp)
        old = load(oldp)
        diffs = []
        newrows = new if isinstance(new, list) else new.get("rows", new)
        oldrows = old if isinstance(old, list) else old.get("rows", old)
        for a, b in zip(newrows, oldrows):
            if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
                diffs.append(a.get("id", "?"))
        res[tag] = {"diffs": diffs}
        if diffs:
            res["problems"].append(f"{tag} diffs: {diffs}")
    res["verdict"] = "PASS" if not res["problems"] else "FAIL"
    json.dump(res, open(OUTP, "w"), indent=1)
    print(f"sessions152: {res['sessions152']}")
    print(f"bench: {res['bench']} gate={gate}")
    print(f"rt136: {res['rt136']} gate={g2}")
    print(f"rt143: n={res['rt143']['n']} diffs={res['rt143']['diffs']}")
    print(f"vp diffs={res['vp']['diffs']} vs diffs={res['vs']['diffs']}")
    print("VERDICT:", res["verdict"])
    for p in res["problems"]:
        print("PROBLEM:", p[:300])
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
