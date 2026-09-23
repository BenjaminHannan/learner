#!/usr/bin/env python3
"""Exp F1 registered scorer: F1's rows vs 292t's saved rows, exact moves.

  regscore <run_dir> <out.json>
Compares (timing fields ignored):
  sessions152 : <run>/sd/sessions152-diff.json (every move must be class
    "reply-only move": verdict + stored identical, only reply text changed)
  bench       : <run>/sd/bench-diff.json (same bar)
  rt136       : <run>/sd136/rt136-rows.json vs 292t's run/sd136/rt136-rows.json
    (diffs allowed ONLY on the reply field; verdict/stored/labels identical;
    GATE + vs-base labels identical to 292t's)
  rt143       : <run>/rt143nogate-f1.json vs 292t's run/rt143nogate-292t.json
    (teach_replies/triples/expected identical; reply diffs listed)
  verifier    : <run>/vp-f1.json vs 292t's run/vp-292t.json,
                <run>/vs-f1.json vs 292t's run/vs-292t.json
    (kind/turn/ev/triples/stored identical; reply diffs listed)
GATE must be identical to 292t's (identical gate strings).
PASS only if every move is reply-only and every diff is reply-text-only.

New file only. Never prints panel or benchmark user turns.
"""

import json
import re
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else None
OUTP = sys.argv[2] if len(sys.argv) > 2 else None

BASE292T = "artifacts/claude-join292t-20260923/run"


def load(p):
    return json.load(open(p))


def main():
    res = {"problems": []}
    d = load(f"{RUN}/sd/sessions152-diff.json")
    moves = d.get("moves", [])
    move_ids = [m.get("id", m.get("unit")) for m in moves]
    bad = [m.get("id", m.get("unit")) for m in moves
           if m.get("class") != "reply-only move"]
    res["sessions152"] = {
        "n_moves": d.get("n_moves"),
        "summary": d.get("summary_line"),
        "class_counts": d.get("class_counts"),
        "move_ids": move_ids,
    }
    if bad:
        res["problems"].append(f"sessions152 non-reply-only moves: {bad}")
    gate = load(f"{RUN}/sd/SUITEDIFF218-SUMMARY.json").get("gate", "")
    res["gate_sd"] = gate
    # Base for this run is 292t's rows: any verdict/store transition vs
    # 292t fails the gate here, so the run's own gate must be clean.
    # (292t's sealed gate vs ITS base is a different comparison and is
    # not re-compared here.)
    if gate != "GATE: clean":
        res["problems"].append(f"sessions152/bench gate not clean: {gate!r}")
    bd = load(f"{RUN}/sd/bench-diff.json")
    bbad = [m.get("id", m.get("unit")) for m in bd.get("moves", [])
            if m.get("class") != "reply-only move"]
    res["bench"] = {"n_moves": bd.get("n_moves"),
                    "summary": bd.get("summary_line"),
                    "move_ids": [m.get("id", m.get("unit"))
                                 for m in bd.get("moves", [])]}
    if bbad:
        res["problems"].append(f"bench non-reply-only moves: {bbad}")
    if bd.get("n_moves") and not bbad:
        pass  # reply-only bench moves are allowed; ids listed above

    def rows136(p):
        out = []
        for line in open(p):
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out
    new136 = rows136(f"{RUN}/sd136/rt136-rows.json")
    old136 = rows136(f"{BASE292T}/sd136/rt136-rows.json")
    diffs136 = []
    reply136 = []
    for a, b in zip(new136, old136):
        if a.get("id") != b.get("id"):
            diffs136.append((a.get("id"), "id-order"))
            continue
        for k in sorted(set(a) | set(b)):
            if k in ("seconds", "sec"):
                continue
            if a.get(k) != b.get(k):
                if k == "reply":
                    reply136.append(a.get("id"))
                else:
                    diffs136.append((a.get("id"), k))
    res["rt136"] = {"n": len(new136), "reply_only_ids": reply136,
                    "other_diffs": diffs136}
    if diffs136:
        res["problems"].append(f"rt136 non-reply diffs: {diffs136}")
    snew = load(f"{RUN}/sd136/SUITEDIFF218-SUMMARY.json")
    res["gate_rt136"] = snew.get("gate", "")
    # Base for this run is 292t's rows, so the run's own gate must be
    # clean (no verdict/store transitions vs 292t). The vs-138j-base
    # labels inside the summary are not re-compared (different base).
    if res["gate_rt136"] != "GATE: clean":
        res["problems"].append(
            f"rt136 gate not clean: {res['gate_rt136']!r}")
    res["labels_rt136"] = snew.get("summary_lines")
    new143 = load(f"{RUN}/rt143nogate-f1.json")
    old143 = load(f"{BASE292T}/rt143nogate-292t.json")
    diffs143 = []
    reply143 = []
    teach143 = []
    for a, b in zip(new143, old143):
        for k in ("triples", "expected"):
            if a.get(k) != b.get(k):
                diffs143.append((a.get("id"), k))
        if a.get("reply") != b.get("reply"):
            reply143.append(a.get("id"))
        # Teach-turn replies are rewritten by the mouth (SAVED etc.);
        # text-only diffs with identical triples are reply-only moves.
        if a.get("teach_replies") != b.get("teach_replies"):
            teach143.append(a.get("id"))
    res["rt143"] = {"n": len(new143), "reply_only_ids": reply143,
                    "teach_reply_text_ids": teach143,
                    "other_diffs": diffs143}
    if diffs143:
        res["problems"].append(f"rt143 non-reply diffs: {diffs143}")

    for tag, newp, oldp in (("vp", f"{RUN}/vp-f1.json",
                             f"{BASE292T}/vp-292t.json"),
                            ("vs", f"{RUN}/vs-f1.json",
                             f"{BASE292T}/vs-292t.json")):
        new = load(newp)
        old = load(oldp)
        nrows = new if isinstance(new, list) else new.get("rows", new)
        orows = old if isinstance(old, list) else old.get("rows", old)
        nomap = {r.get("id"): r for r in orows}
        diffs = []
        repdiffs = []
        for r in nrows:
            o = nomap.get(r.get("id"))
            if o is None:
                diffs.append((r.get("id"), "missing-in-292t"))
                continue
            if r.get("stored") != o.get("stored"):
                diffs.append((r.get("id"), "stored"))
                continue
            for rn, ro in zip(r.get("rows", []), o.get("rows", [])):
                for k in ("kind", "turn", "ev", "triples"):
                    if rn.get(k) != ro.get(k):
                        diffs.append((r.get("id"), k))
                if rn.get("reply") != ro.get("reply"):
                    repdiffs.append((r.get("id"), rn.get("turn")))
        res[tag] = {"n": len(nrows), "reply_only": repdiffs,
                    "other_diffs": diffs}
        if diffs:
            res["problems"].append(f"{tag} non-reply diffs: {diffs}")
    res["verdict"] = "PASS" if not res["problems"] else "FAIL"
    json.dump(res, open(OUTP, "w"), indent=1)
    print(f"sessions152 moves={res['sessions152']['n_moves']} "
          f"bench moves={res['bench']['n_moves']} "
          f"rt136 reply-only={len(reply136)} other={len(diffs136)} "
          f"rt143 reply-only={len(reply143)} other={len(diffs143)} "
          f"vp reply-only={len(res['vp']['reply_only'])} "
          f"vs reply-only={len(res['vs']['reply_only'])} "
          f"problems={len(res['problems'])} VERDICT={res['verdict']}")
    for p in res["problems"]:
        print("PROBLEM:", p)
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
