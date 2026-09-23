#!/usr/bin/env python3
"""Exp 270b POST-SEAL panel scorer v2 (new file version, disclosed D7).

v1 (panel270b_score.json, superseded but kept) patched S.norm_subj with a
SYMMETRIC strip-one-s. That was wrong: it mangles correct s-name
predictions on the PRED side ("Louis"->"loui" vs gold "louiss"->"louis"),
scoring 5 correct arm-A frames as misses. v2 replaces it with
PRED-ANCHORED matching (writer's spec: gold keeps raw stems like "jamess";
"the scorer normalises"):

  subject HIT iff norm(pred) == norm(gold)
                 or (gold ends in "s" and norm(pred) == norm(gold)[:-1])
                 or (pred ends in "s" and norm(gold) == norm(pred)[:-1])
  (norm = S.norm_subj; length guard > 3; "<user>" unaffected.)

This rewards true-name predictions ("Louis" hits "louiss") without a
panel-mined keep-set, and treats both arms identically (glued raw spans
hit the same way). Relation matching is 261b's sealed Ruling-1
(rel_ok_narrower); values S.norm_val; greedy one-to-one like S.match.
M5 "new" uses the same subject rule (same_error classes).

Known artifact (disclosed, counted, not removed): a mangled span whose
stem equals gold-minus-s still matches ("Iri" hits "iris"); u270-003 arm A
is such a case (sealed normaliser lacks "iris" in S_NAMES270b). True M1 A
is reported-minus-1 alongside.

Arm frame pipeline (devscore.arm_frames: sealed base_arms ->
checker_split 0.25 -> 261b guard) is imported sealed and UNCHANGED; only
the matcher differs from v1. No arm re-ran: v2 re-scores the recorded
preds/pyes (270 D6 precedent). v1 file kept for the diff.

Usage: same args as v1; writes SCORE-V2 json.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_score as S  # noqa: E402
import claude_type270b_devscore as D  # noqa: E402 (sealed arm pipeline)
import claude_earcheck261b_scoremain as BSM  # noqa: E402 (Ruling-1)


def subj_hit(pn, gn):
    if pn == gn:
        return True
    if len(gn) > 3 and gn.endswith("s") and pn == gn[:-1]:
        return True
    if len(pn) > 3 and pn.endswith("s") and gn == pn[:-1]:
        return True
    return False


def frame_ok2(p, g):
    if p["act"] != g["act"]:
        return False
    if not subj_hit(S.norm_subj(p["subject"]), S.norm_subj(g["subject"])):
        return False
    prel = p["relation"] if isinstance(p["relation"], list) else [p["relation"]]
    if len(prel) != len(g["relation"]):
        return False
    for i, (pr, gr) in enumerate(zip(prel, g["relation"])):
        al = g["aliases"][i] if i < len(g["aliases"]) else []
        if not BSM.rel_ok_narrower(pr, gr, al):
            return False
    if g["act"] == "TEACH" and S.norm_val(p["value"]) != S.norm_val(g["value"]):
        return False
    return True


def match2(preds, golds, act):
    gl = [g for g in golds if g["act"] == act]
    used = [False] * len(gl)
    extra, hit = [], 0
    for p in [p for p in preds if p["act"] == act]:
        for i, g in enumerate(gl):
            if not used[i] and frame_ok2(p, g):
                used[i] = True
                hit += 1
                break
        else:
            extra.append(p)
    return hit, extra, len(gl)


def strip1(x):
    return x[:-1] if len(x) > 3 and x.endswith("s") else x


def same_error(f, b):
    if f.get("act") != b.get("act"):
        return False
    pf, pb = S.norm_subj(f.get("subject", "")), S.norm_subj(b.get("subject", ""))
    if not (pf == pb or pf == strip1(pb) or strip1(pf) == pb
            or strip1(pf) == strip1(pb)):
        return False
    rf = f["relation"]
    rf = " ".join(rf) if isinstance(rf, list) else str(rf)
    rb = b["relation"]
    rb = " ".join(rb) if isinstance(rb, list) else str(rb)
    if S.rkey(rf) != S.rkey(rb):
        return False
    if f.get("act") == "TEACH" and S.norm_val(f.get("value", "")) != S.norm_val(
            b.get("value", "")):
        return False
    return True


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--preds", required=True)
    ap.add_argument("--pyesA", required=True)
    ap.add_argument("--pyesB", required=True)
    ap.add_argument("--normmanifest", required=True)
    ap.add_argument("--theta", type=float, default=0.25)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    rows_in = [json.loads(x) for x in Path(a.rows).read_text(
        encoding="utf-8").splitlines() if x.strip()]
    preds = json.loads(Path(a.preds).read_text(encoding="utf-8"))["preds"]
    nman = json.loads(Path(a.normmanifest).read_text(encoding="utf-8"))
    pyesA = json.loads(Path(a.pyesA).read_text(encoding="utf-8"))["checks"]
    pyesB = json.loads(Path(a.pyesB).read_text(encoding="utf-8"))["checks"]
    pmapA = {k: (float(v["p"]), float(v.get("ms", 0.0)))
             for k, v in pyesA.items()}
    pmapB = {k: (float(v["p"]), float(v.get("ms", 0.0)))
             for k, v in pyesB.items()}
    rows = []
    for it in rows_in:
        gold = it["gold"]
        turnA = nman[it["id"]]["fixed"]
        turnB = it["turn"]
        fA, hA, uA, msA, _ = D.arm_frames(
            turnA, preds[it["id"] + "-norm"], pmapA, it["id"], a.theta)
        fB, hB, uB, msB, _ = D.arm_frames(
            turnB, preds[it["id"] + "-raw"], pmapB, it["id"], a.theta)
        thA, txA, tn = match2(fA, gold, "TEACH")
        ahA, axA, an = match2(fA, gold, "ASK")
        thB, txB, _ = match2(fB, gold, "TEACH")
        ahB, axB, _ = match2(fB, gold, "ASK")
        has_ask = any(g["act"] == "ASK" for g in gold)
        rows.append({"id": it["id"], "family": it["family"],
                     "reason": nman[it["id"]]["reason"],
                     "norm_ms": nman[it["id"]]["norm_ms"],
                     "teach": {"hitA": thA, "hitB": thB, "gold": tn,
                               "wrongA": len(txA), "wrongB": len(txB),
                               "exactA": (thA == tn and not txA)
                               if not has_ask else None,
                               "exactB": (thB == tn and not txB)
                               if not has_ask else None},
                     "ask": {"hitA": ahA, "hitB": ahB, "gold": an,
                             "extraA": len(axA), "extraB": len(axB),
                             "exactA": (ahA == an and not axA)
                             if has_ask else None,
                             "exactB": (ahB == an and not axB)
                             if has_ask else None},
                     "framesA": fA, "framesB": fB,
                     "frames_identical": fA == fB,
                     "new_wrong": [f for f in txA
                                   if not any(same_error(f, b)
                                              for b in txB)],
                     "note": it.get("note", "")})

    def fam(f):
        return [r for r in rows if r["family"] == f]

    cas = fam("casual")
    m1a = sum(1 for r in cas if r["teach"]["exactA"])
    m1b = sum(1 for r in cas if r["teach"]["exactB"])
    q = fam("casual_q")
    m2a = sum(1 for r in q if r["ask"]["exactA"])
    m2b = sum(1 for r in q if r["ask"]["exactB"])
    tr = fam("lower_trap")
    m3a = sum(r["teach"]["wrongA"] for r in tr)
    m3b = sum(r["teach"]["wrongB"] for r in tr)
    cl = fam("clean")
    m4i = sum(1 for r in cl if r["frames_identical"])
    newwrong_ids = sorted(r["id"] for r in rows if r["new_wrong"])
    ms = sorted(r["norm_ms"] for r in rows)
    med = statistics.median(ms)
    v = {"M1": (m1a >= 30 and (m1a - m1b) >= 15),
         "M2": (m2a >= 12),
         "M3": (m3a <= 1),
         "M4": (m4i == 30 and len(cl) == 30),
         "M5": (len(newwrong_ids) == 0),
         "M6": (med <= 20)}
    v["ALL"] = all(v.values())
    print(f"V2 M1 casual exact: A {m1a}/{len(cas)}  A261b {m1b}/{len(cas)} "
          f"margin {m1a - m1b} -> {'PASS' if v['M1'] else 'FAIL'}")
    print(f"V2 M2 casual_q ASK exact: A {m2a}/{len(q)}  "
          f"A261b {m2b}/{len(q)} -> {'PASS' if v['M2'] else 'FAIL'}")
    print(f"V2 M3 lower_trap wrong TEACH saves: A {m3a}  A261b {m3b} -> "
          f"{'PASS' if v['M3'] else 'FAIL'}")
    print(f"V2 M4 clean identical: {m4i}/{len(cl)} -> "
          f"{'PASS' if v['M4'] else 'FAIL'}")
    print(f"V2 M5 new wrong TEACH saves: {len(newwrong_ids)} {newwrong_ids} "
          f"-> {'PASS' if v['M5'] else 'FAIL'}")
    print(f"V2 M6 norm_ms median: {med} max: {max(ms)} -> "
          f"{'PASS' if v['M6'] else 'FAIL'}")
    print("V2 OVERALL:", "PASS" if v["ALL"] else "FAIL")
    for r in rows:
        flags = []
        if r["family"] == "casual" and not r["teach"]["exactA"]:
            flags.append("MISS-A")
        if r["family"] == "casual_q" and not r["ask"]["exactA"]:
            flags.append("MISS-A")
        if r["new_wrong"]:
            flags.append("NEWW")
        if r["family"] == "clean" and not r["frames_identical"]:
            flags.append("NONIDENT")
        if flags:
            fa = [(f["act"], f["subject"], f["relation"], f.get("value"))
                  for f in r["framesA"]]
            fb = [(f["act"], f["subject"], f["relation"], f.get("value"))
                  for f in r["framesB"]]
            print(f"{'+'.join(flags)} {r['id']} {r['family']} "
                  f"{r['note']} A={fa} B={fb}")
    Path(a.out).write_text(json.dumps(
        {"theta": a.theta, "matcher": "v2-pred-anchored", "verdict": v,
         "marks": {"M1": {"A": m1a, "A261b": m1b, "n": len(cas)},
                   "M2": {"A": m2a, "A261b": m2b, "n": len(q)},
                   "M3": {"A": m3a, "A261b": m3b},
                   "M4": {"identical": m4i, "n": len(cl)},
                   "M5": {"n": len(newwrong_ids), "ids": newwrong_ids},
                   "M6": {"median": med, "max": max(ms)}},
         "rows": rows}, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
