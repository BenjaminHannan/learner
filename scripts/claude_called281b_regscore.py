#!/usr/bin/env python3
"""Exp 281b registered scorer: 281b's rows vs 281's saved rows, exact moves.

  regscore <run_dir> <out.json>
Compares (timing fields ignored):
  sessions152 : <run>/sd/sessions152-diff.json + rows vs 281's saved rows
  bench       : <run>/sd/bench-diff.json
  rt136       : <run>/sd136/rt136-rows.json vs 281's run/sd136/rt136-rows.json
  rt143       : <run>/rt143nogate-281b.json vs 281's run/rt143nogate-281.json
  verifier    : <run>/vp-281b.json vs 281's run/vp-281.json,
                <run>/vs-281b.json vs 281's run/vs-281.json
Predicted: 0 suite moves everywhere; verifier vp/vs 0 changes (every
suite and probe turn is formal text, so the casual normaliser returns
None and the 281 path runs byte-identical).
Any moved unit, verdict flip, write change, or abstain-ward flip fails.
PASS only if the move list equals the predicted list exactly.
"""

import json
import re
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else None
OUTP = sys.argv[2] if len(sys.argv) > 2 else None

BASE281 = "artifacts/claude-called281-20260923/run"


def load(p):
    return json.load(open(p))


def main():
    res = {"predicted_ids": [], "problems": []}
    d = load(f"{RUN}/sd/sessions152-diff.json")
    moves = d.get("moves", [])
    res["sessions152"] = {
        "n_moves": d.get("n_moves"),
        "summary": d.get("summary_line"),
        "class_counts": d.get("class_counts"),
        "move_ids": [m.get("id", m.get("unit")) for m in moves],
    }
    if moves:
        res["problems"].append(
            f"sessions152 moves: {res['sessions152']['move_ids']}")
    gate = load(f"{RUN}/sd/SUITEDIFF218-SUMMARY.json").get("gate", "")
    res["gate_sd"] = gate
    if gate != "GATE: clean":
        res["problems"].append(f"sessions152/bench gate: {gate}")
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
    old136 = rows136(f"{BASE281}/sd136/rt136-rows.json")
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
    s281b = load(f"{RUN}/sd136/SUITEDIFF218-SUMMARY.json")
    s281 = load(f"{BASE281}/sd136/SUITEDIFF218-SUMMARY.json")
    res["gate_rt136"] = s281b.get("gate", "")
    norm = lambda s: re.sub(r"seconds=[\d.]+", "seconds=X", str(s))
    if norm(s281b.get("summary_lines")) != norm(s281.get("summary_lines")):
        res["problems"].append(
            f"rt136 vs-138j labels differ from 281: "
            f"{s281b.get('summary_lines')}")
    new143 = load(f"{RUN}/rt143nogate-281b.json")
    old143 = load(f"{BASE281}/rt143nogate-281.json")
    diffs143 = []
    for a, b in zip(new143, old143):
        for k in ("teach_replies", "triples", "reply", "expected"):
            if a.get(k) != b.get(k):
                diffs143.append((a.get("id"), k))
    res["rt143"] = {"n": len(new143), "diffs": diffs143}
    if diffs143:
        res["problems"].append(f"rt143 diffs: {diffs143}")
    for tag, newp, oldp in (
            ("vp", f"{RUN}/vp-281b.json", f"{BASE281}/vp-281.json"),
            ("vs", f"{RUN}/vs-281b.json", f"{BASE281}/vs-281.json")):
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
    print(f"rt136: n={res['rt136']['n']} diffs={res['rt136']['diffs']} "
          f"gate={res['gate_rt136']}")
    print(f"rt143: n={res['rt143']['n']} diffs={res['rt143']['diffs']}")
    print(f"vp diffs={res['vp']['diffs']} vs diffs={res['vs']['diffs']}")
    print("VERDICT:", res["verdict"])
    for p in res["problems"]:
        print("PROBLEM:", p[:300])
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
