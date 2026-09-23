#!/usr/bin/env python3
"""Exp 280b registered scorer: 280b's rows vs 280's saved rows, exact moves.

  regscore <run_dir> <out.json>
Compares (timing fields ignored):
  sessions152 : <run>/sd/sessions152-diff.json + rows vs 280's saved rows
  bench       : <run>/sd/bench-diff.json
  rt136       : <run>/sd136/rt136-rows.json vs 280's saved rows (direct
                field-by-field row compare except wall-clock timing);
                vs-138j-base labels must equal 280's own labels exactly
                (modulo timing), as on 280.
  rt143       : <run>/rt143nogate-280b.json vs 280's run/rt143nogate-280.json
  verifier    : <run>/vp-280b.json vs 280's run/vp-280.json,
                <run>/vs-280b.json vs 280's run/vs-280.json
Predicted move ids come from the sealed predicted_moves280b.json
("sessions152" list; everything else predicted empty).
PASS only if the move list equals the predicted list exactly.
"""

import json
import re
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else None
OUTP = sys.argv[2] if len(sys.argv) > 2 else None

BASE280 = "artifacts/claude-capab280-20260923/run"
PRED = json.load(open("artifacts/claude-capab280b-20260923/"
                      "predicted_moves280b.json"))
PRED_IDS = set(PRED.get("sessions152", []))


def load(p):
    return json.load(open(p))


def main():
    res = {"predicted_ids": sorted(PRED_IDS), "problems": []}
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
        if not str(m.get("new_reply", m.get("reply", ""))):
            res["problems"].append(f"sessions152 {m.get('id')} empty new reply")
        if m.get("write_change"):
            res["problems"].append(f"sessions152 {m.get('id')} has write change")
    gate = load(f"{RUN}/sd/SUITEDIFF218-SUMMARY.json").get("gate", "")
    res["gate_sd"] = gate
    if gate != "GATE: clean":
        res["problems"].append(f"sessions152/bench gate: {gate}")
    bd = load(f"{RUN}/sd/bench-diff.json")
    res["bench"] = {"n_moves": bd.get("n_moves"),
                    "summary": bd.get("summary_line")}
    if bd.get("n_moves"):
        res["problems"].append(f"bench moves: {bd.get('moves')}")
    # rt136: direct row compare vs 280's saved rows (same method 280 used).
    def rows136(p):
        out = []
        for line in open(p):
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out
    new136 = rows136(f"{RUN}/sd136/rt136-rows.json")
    old136 = rows136(f"{BASE280}/sd136/rt136-rows.json")
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
    s28b = load(f"{RUN}/sd136/SUITEDIFF218-SUMMARY.json")
    s280 = load(f"{BASE280}/sd136/SUITEDIFF218-SUMMARY.json")
    g2 = s28b.get("gate", "")
    res["gate_rt136"] = g2
    res["gate_rt136_280"] = s280.get("gate", "")
    norm = lambda s: re.sub(r"seconds=[\d.]+", "seconds=X", str(s))
    if norm(s28b.get("summary_lines")) != norm(s280.get("summary_lines")):
        res["problems"].append(
            f"rt136 vs-base labels differ from 280: {s28b.get('summary_lines')}")
    # rt143: direct row compare vs 280's saved rows
    new143 = load(f"{RUN}/rt143nogate-280b.json")
    old143 = load(f"{BASE280}/rt143nogate-280.json")
    diffs143 = []
    for a, b in zip(new143, old143):
        for k in ("teach_replies", "triples", "reply", "expected"):
            if a.get(k) != b.get(k):
                diffs143.append((a.get("id"), k))
    res["rt143"] = {"n": len(new143), "diffs": diffs143}
    if diffs143:
        res["problems"].append(f"rt143 diffs: {diffs143}")
    # verifier probes: 0 changes predicted
    for tag, newp, oldp in (("vp", f"{RUN}/vp-280b.json",
                             f"{BASE280}/vp-280.json"),
                            ("vs", f"{RUN}/vs-280b.json",
                             f"{BASE280}/vs-280.json")):
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
