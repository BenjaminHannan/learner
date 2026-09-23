#!/usr/bin/env python3
"""Exp 270b -- dev scorer (sealed).

Scores arm A (normaliser + 261b's A) beside arm A261b (261b's A exactly:
brake -> canon -> YES/NO checker at sealed theta 0.25, prompt B -> 261b span
guard) on the builder's own dev turns. Both arms use the identical sealed
code path (261 arms + 261b guard + 235 match with 261b's Ruling-1 narrower
patch); only the turn text and ear preds differ.

Marks (brief bars):
  M1 casual exact TEACH >= 30/40 and >= A261b+15  (dev: /64 + margin)
  M2 casual_q ASK >= 12/15                        (dev: /16)
  M3 lower_trap wrong saves <= 1                  (dev: /24, extras only)
  M4 clean byte-identical frames A vs A261b       (dev: /24)
  M5 0 new wrong saves vs A261b overall
  M6 median added normaliser time <= 20 ms
Plus sname/seen diagnostics (the keep-s fix; no bars).

Usage: python -B scripts/claude_type270b_devscore.py --dev D --preds P --pyesA YA --pyesB YB --normmanifest N --theta 0.25 --out REPORT.json
pyes files: {checks: {cid: {p, ms}}} (sealed checker client output).
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck261b_arms as BA  # noqa: E402
import claude_earcheck261b_scoremain as BSM  # noqa: E402 (Ruling-1 map)

THETA_DEFAULT = 0.25


def arm_frames(turn, rec, pmap, row_id, theta):
    arms0 = A261.base_arms(rec["raw"], turn, rec["greedy_lp"],
                           rec["beams"])
    kept = arms0["kept_canon"]
    n_teach = sum(1 for f in kept if f.get("act") == "TEACH")
    pl = [float(pmap[f"{row_id}#t{k}"][0]) for k in range(n_teach)]
    cms = [float(pmap[f"{row_id}#t{k}"][1]) for k in range(n_teach)]
    saved, unsure = A261.checker_split(kept, pl, theta)
    guarded, held, gms = BA.apply_guard(saved)
    ear_ms = float(rec.get("ms_greedy", rec.get("ms", 0.0)))
    ms = round(ear_ms + sum(cms) + gms, 2)
    return guarded, held, unsure, ms, arms0["A_brake"]


def conv_gold(g):
    fr = {"act": g["act"], "subject": str(g["subject"]),
          "relation": [str(x) for x in g["relation"]],
          "aliases": [[str(y) for y in x] for x in g["aliases"]]}
    if g["act"] == "TEACH":
        fr["value"] = str(g["value"])
    return fr


def frame_key(f):
    """Normalised identity for M5 new-wrong comparison (case-insensitive)."""
    rel = f["relation"]
    rel = " ".join(rel) if isinstance(rel, list) else str(rel)
    key = (S.norm_subj(f.get("subject", "")), S.rkey(rel))
    if f.get("act") == "TEACH":
        key = key + (S.norm_val(f.get("value", "")),)
    return (f.get("act"),) + key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--preds", required=True)
    ap.add_argument("--pyesA", required=True)
    ap.add_argument("--pyesB", required=True)
    ap.add_argument("--normmanifest", required=True)
    ap.add_argument("--theta", type=float, default=THETA_DEFAULT)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    S.rel_ok = BSM.rel_ok_narrower
    try:
        return run(a)
    finally:
        S.rel_ok = BSM._ORIG_REL_OK


def run(a):
    items = [json.loads(x) for x in Path(a.dev).read_text(
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
    for it in items:
        gold = [conv_gold(g) for g in it["gold"]]
        turnA = nman[it["id"]]["fixed"]
        turnB = it["turn"]
        fA, hA, uA, msA, brA = arm_frames(
            turnA, preds[it["id"] + "-norm"], pmapA, it["id"], a.theta)
        fB, hB, uB, msB, brB = arm_frames(
            turnB, preds[it["id"] + "-raw"], pmapB, it["id"], a.theta)
        thA, txA, tn = S.match(fA, gold, "TEACH")
        ahA, axA, an = S.match(fA, gold, "ASK")
        thB, txB, _ = S.match(fB, gold, "TEACH")
        ahB, axB, _ = S.match(fB, gold, "ASK")
        exactA_T = (thA == tn and not txA) if not any(
            g["act"] == "ASK" for g in gold) else None
        exactB_T = (thB == tn and not txB) if not any(
            g["act"] == "ASK" for g in gold) else None
        exactA_Q = (ahA == an and not axA) if any(
            g["act"] == "ASK" for g in gold) else None
        exactB_Q = (ahB == an and not axB) if any(
            g["act"] == "ASK" for g in gold) else None
        newwrong = [f for f in txA
                    if frame_key(f) not in {frame_key(b) for b in txB}]
        newwrong_q = [f for f in axA
                      if frame_key(f) not in {frame_key(b) for b in axB}]
        rows.append({"id": it["id"], "family": it["family"],
                     "turn": it["turn"], "fixed": turnA,
                     "reason": nman[it["id"]]["reason"],
                     "norm_ms": nman[it["id"]]["norm_ms"],
                     "teach": {"hitA": thA, "hitB": thB, "gold": tn,
                               "wrongA": len(txA), "wrongB": len(txB),
                               "exactA": exactA_T, "exactB": exactB_T},
                     "ask": {"hitA": ahA, "hitB": ahB, "gold": an,
                             "extraA": len(axA), "extraB": len(axB),
                             "exactA": exactA_Q, "exactB": exactB_Q},
                     "framesA": fA, "framesB": fB,
                     "frames_identical": fA == fB,
                     "new_wrong": newwrong, "new_wrong_q": newwrong_q,
                     "msA": msA, "msB": msB,
                     "note": it.get("note", "")})
    rep: dict = {"theta": a.theta, "rows": rows}

    def fam(f):
        return [r for r in rows if r["family"] == f]

    cas = fam("casual")
    m1a = sum(1 for r in cas if r["teach"]["exactA"])
    m1b = sum(1 for r in cas if r["teach"]["exactB"])
    sn = fam("sname")
    m1s_a = sum(1 for r in sn if r["teach"]["exactA"])
    m1s_b = sum(1 for r in sn if r["teach"]["exactB"])
    se = fam("seen")
    m1e_a = sum(1 for r in se if r["teach"]["exactA"])
    q = fam("casual_q")
    m2a = sum(1 for r in q if r["ask"]["exactA"])
    m2b = sum(1 for r in q if r["ask"]["exactB"])
    tr = fam("lower_trap")
    # M3/M5 count TEACH saves only (ASK frames never write). ASK extras on
    # traps are reported separately (ear reading a "?"-less turn as a
    # question is not a save).
    m3a = sum(r["teach"]["wrongA"] for r in tr)
    m3b = sum(r["teach"]["wrongB"] for r in tr)
    m3a_q = sum(r["ask"]["extraA"] for r in tr)
    cl = fam("clean")
    m4i = sum(1 for r in cl if r["frames_identical"])
    newwrong_ids = sorted(r["id"] for r in rows if r["new_wrong"])
    newwrong_q = sorted(r["id"] for r in rows if r["new_wrong_q"])
    ms = sorted(r["norm_ms"] for r in rows)
    med = statistics.median(ms) if ms else None
    rep["marks"] = {
        "M1_casual_exact": {"A": m1a, "n": len(cas), "A261b": m1b,
                            "margin": m1a - m1b},
        "M1_sname_exact": {"A": m1s_a, "n": len(sn), "A261b": m1s_b},
        "M1_seen_exact": {"A": m1e_a, "n": len(se)},
        "M2_ask_exact": {"A": m2a, "n": len(q), "A261b": m2b},
        "M3_trap_wrong_saves": {"A": m3a, "A261b": m3b},
        "M4_clean_identical": {"identical": m4i, "n": len(cl)},
        "M5_new_wrong_saves": {"n": len(newwrong_ids), "ids": newwrong_ids},
        "M6_norm_ms_median": med, "M6_norm_ms_max": max(ms) if ms else None,
    }
    print(f"M1 casual TEACH exact: A {m1a}/{len(cas)}  "
          f"A261b {m1b}/{len(cas)}  margin {m1a - m1b}")
    print(f"M1 sname exact: A {m1s_a}/{len(sn)}  A261b {m1s_b}/{len(sn)}")
    print(f"M1 seen exact: A {m1e_a}/{len(se)}")
    print(f"M2 casual_q ASK exact: A {m2a}/{len(q)}  A261b {m2b}/{len(q)}")
    print(f"M3 lower_trap wrong TEACH saves: A {m3a}  A261b {m3b}  "
          f"(ASK extras on traps, not saves: A {m3a_q})")
    print(f"M4 clean identical frames: {m4i}/{len(cl)}")
    print(f"M5 new wrong TEACH saves: {len(newwrong_ids)} {newwrong_ids} "
          f"(new ASK extras, not saves: {newwrong_q})")
    print(f"M6 norm_ms median: {med} max: {max(ms) if ms else None}")
    for r in rows:
        flag = ""
        if r["family"] in ("casual", "sname", "seen") and not r["teach"]["exactA"]:
            flag = "MISS-A"
        if r["family"] == "casual_q" and not r["ask"]["exactA"]:
            flag = "MISS-A"
        if r["new_wrong"]:
            flag += "+NEWW"
        if r["family"] == "clean" and not r["frames_identical"]:
            flag += "+NONIDENT"
        if flag:
            print(f"{flag} {r['id']} {r['family']} {r['note']} "
                  f"raw={r['turn']!r} fixed={r['fixed']!r} "
                  f"framesA={r['framesA']} framesB={r['framesB']}")
    Path(a.out).write_text(json.dumps(rep, indent=1, default=str),
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
