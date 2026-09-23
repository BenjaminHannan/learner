#!/usr/bin/env python3
"""Exp 280m registered scorer: 280m's rows vs 260's saved rows, exact moves.

  regscore <run_dir> <out.json>
Compares (timing fields ignored):
  sessions152 : <run>/sd/sessions152-diff.json + rows vs 260's saved rows
  bench       : <run>/sd/bench-diff.json
  rt136       : <run>/sd136/rt136-rows.json vs 260's run/sd136/rt136-rows.json
  rt143       : <run>/rt143nogate-280m.json vs 260's run/rt143nogate-n.json
  verifier    : <run>/vp-280m.json vs 260's run/vp-n.json,
                <run>/vs-280m.json vs 260's run/vs-n.json
Predicted (the union of the pieces' registered moves, nothing else):
  sessions152 exactly 280's 3 reply-only moves (S2-casual-friends#1,
  S3-teachers-correction#0, S4-pets-identity#9, sealed CAN280 text,
  stored identical, 0 write changes); bench/rt136/rt143 0 moves;
  verifier vp exactly N06 (281) + E04 (282); vs 0 changes.
GATE must be as clean as 260's (identical gate strings).
PASS only if the move list equals the predicted list exactly.
"""

import json
import re
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else None
OUTP = sys.argv[2] if len(sys.argv) > 2 else None

BASE260 = "artifacts/claude-openers260-20260922/run"
PRED_SESSIONS = ["S2-casual-friends#1", "S3-teachers-correction#0",
                 "S4-pets-identity#9"]
PRED_VP = ["E04", "N06"]
PRED_N06_REPLY = "Tomas's boss is Mirela."


def load(p):
    return json.load(open(p))


def main():
    res = {"predicted_ids": [], "problems": []}
    d = load(f"{RUN}/sd/sessions152-diff.json")
    moves = d.get("moves", [])
    move_ids = [m.get("id", m.get("unit")) for m in moves]
    res["sessions152"] = {
        "n_moves": d.get("n_moves"),
        "summary": d.get("summary_line"),
        "class_counts": d.get("class_counts"),
        "move_ids": move_ids,
    }
    if sorted(move_ids) != sorted(PRED_SESSIONS):
        res["problems"].append(
            f"sessions152 moves {move_ids} != predicted {PRED_SESSIONS}")
    gate = load(f"{RUN}/sd/SUITEDIFF218-SUMMARY.json").get("gate", "")
    gate260 = load(f"{BASE260}/sd/SUITEDIFF218-SUMMARY.json").get("gate", "")
    res["gate_sd"] = gate
    res["gate_sd_260"] = gate260
    if gate != gate260:
        res["problems"].append(
            f"sessions152/bench gate differs from 260: {gate!r} vs "
            f"{gate260!r}")
    bd = load(f"{RUN}/sd/bench-diff.json")
    res["bench"] = {"n_moves": bd.get("n_moves"),
                    "summary": bd.get("summary_line")}
    if bd.get("n_moves"):
        res["problems"].append(f"bench moves: {bd.get('moves')}")

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
    s280m = load(f"{RUN}/sd136/SUITEDIFF218-SUMMARY.json")
    s260 = load(f"{BASE260}/sd136/SUITEDIFF218-SUMMARY.json")
    res["gate_rt136"] = s280m.get("gate", "")
    res["gate_rt136_260"] = s260.get("gate", "")
    if res["gate_rt136"] != res["gate_rt136_260"]:
        res["problems"].append(
            f"rt136 gate differs from 260: {res['gate_rt136']!r} vs "
            f"{res['gate_rt136_260']!r}")
    norm = lambda s: re.sub(r"seconds=[\d.]+", "seconds=X", str(s))
    if norm(s280m.get("summary_lines")) != norm(s260.get("summary_lines")):
        res["problems"].append(
            f"rt136 vs-base labels differ from 260: "
            f"{s280m.get('summary_lines')}")
    new143 = load(f"{RUN}/rt143nogate-280m.json")
    old143 = load(f"{BASE260}/rt143nogate-n.json")
    diffs143 = []
    for a, b in zip(new143, old143):
        for k in ("teach_replies", "triples", "reply", "expected"):
            if a.get(k) != b.get(k):
                diffs143.append((a.get("id"), k))
    res["rt143"] = {"n": len(new143), "diffs": diffs143}
    if diffs143:
        res["problems"].append(f"rt143 diffs: {diffs143}")
    for tag, newp, oldp in (("vp", f"{RUN}/vp-280m.json",
                             f"{BASE260}/vp-n.json"),
                            ("vs", f"{RUN}/vs-280m.json",
                             f"{BASE260}/vs-n.json")):
        new = load(newp)
        old = load(oldp)
        diffs = []
        newrows = new if isinstance(new, list) else new.get("rows", new)
        oldrows = old if isinstance(old, list) else old.get("rows", old)
        for a, b in zip(newrows, oldrows):
            if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
                diffs.append(a.get("id", "?"))
        res[tag] = {"diffs": diffs}
        if tag == "vp":
            if sorted(diffs) != sorted(PRED_VP):
                res["problems"].append(
                    f"vp diffs {diffs} != predicted {PRED_VP}")
            else:
                for a in newrows:
                    if a.get("id") == "N06":
                        qrows = [r for r in a.get("rows", [])
                                 if r.get("kind") == "Q"]
                        if (len(qrows) != 1
                                or qrows[0].get("reply") != PRED_N06_REPLY):
                            res["problems"].append(
                                f"N06 Q reply not predicted: {qrows}")
                        if a.get("stored") != [["Tomas", "boss",
                                                "Mirela"]]:
                            res["problems"].append(
                                f"N06 store changed: {a.get('stored')}")
        elif diffs:
            res["problems"].append(f"vs diffs: {diffs}")
    res["verdict"] = "PASS" if not res["problems"] else "FAIL"
    json.dump(res, open(OUTP, "w"), indent=1)
    print(f"sessions152: {res['sessions152']}")
    print(f"bench: {res['bench']} gate={gate} (260: {gate260})")
    print(f"rt136: {res['rt136']} gate={res['gate_rt136']} "
          f"(260: {res['gate_rt136_260']})")
    print(f"rt143: n={res['rt143']['n']} diffs={res['rt143']['diffs']}")
    print(f"vp diffs={res['vp']['diffs']} vs diffs={res['vs']['diffs']}")
    print("VERDICT:", res["verdict"])
    for p in res["problems"]:
        print("PROBLEM:", p[:300])
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
