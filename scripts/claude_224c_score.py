#!/usr/bin/env python3
"""Exp 224c scorer: reads the registered run outputs, prints/writes marks.

  python3 -B scripts/claude_224c_score.py --dir artifacts/claude-decline224c-20260922/runs --out <json>

Expected files in --dir:
  m1-b1-224c.json                (claude_224c_cases natural, B1 cases)
  cases-224-forced.json          (claude_224c_cases, loop224, forced)
  cases-224c-forced.json         (claude_224c_cases, loop224c, forced)
  cases-224c-natural.json        (claude_224c_cases, loop224c, natural)
  forced228-224c.json            (claude_determinism228_forced on loop224c)
  suitediff/SUITEDIFF218-SUMMARY.json + *-diff.json (fable_suitediff218 vs 224 rows)
  m5-b3.json                     (fable_decline224_b3 on the loop224c smoke)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fable_decline224 as DEC  # noqa: E402

Q1 = DEC.NEW_SENTENCES224["Q1"]
Q2 = DEC.NEW_SENTENCES224["Q2"]
B1_224 = ROOT / "artifacts/fable-decline224-20260922/224b/b1-224.json"
PRED_FLAKE_BACK = "bench132-4hop-031"  # 224's registered flake row


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def rows_by(p: Path) -> dict:
    return {r["id"]: r for r in load(p)["rows"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    d = Path(a.dir)
    res: dict = {}

    # M1
    base = rows_by(B1_224)
    new = rows_by(d / "m1-b1-224c.json")
    diff = [i for i in base if base[i]["reply"] != new.get(i, {}).get("reply")]
    by = {}
    for i, r in base.items():
        t = r["type"]
        by.setdefault(t, [0, 0])
        by[t][0] += 1
        by[t][1] += int(new[i]["reply"] == r["reply"])
    w = sum(len(r["writes"]) for r in new.values())
    res["M1"] = {"same_as_224_by_type": by, "reply_diffs": diff,
                 "writes": w, "pass": not diff and w == 0}

    # M2 / M3
    f224 = rows_by(d / "cases-224-forced.json")
    fc = rows_by(d / "cases-224c-forced.json")
    nc = rows_by(d / "cases-224c-natural.json")
    f228 = load(d / "forced228-224c.json")

    def sel(s):
        return [i for i in fc if fc[i]["set"] == s]

    m2 = sel("M2")
    m2_q1 = [(i, m) for i in m2 for m, rr in (("forced", fc), ("natural", nc))
             if rr[i]["is_q1"]]
    m2_wrong = [(i, m, rr[i]["stated_other_value"]) for i in m2
                for m, rr in (("forced", fc), ("natural", nc))
                if rr[i]["stated_other_value"]]
    h_q1 = [r["id"] for r in f228["rows"] if r["reply"].strip() == Q1]
    not_stored = [i for i in m2 if fc[i]["fact_stored"] is not True
                  or nc[i]["fact_stored"] is not True]
    subs = {}
    for i in m2:
        s = fc[i].get("sub") or "?"
        subs.setdefault(s, {"n": 0, "q1_224_forced": 0, "q1_224c_forced": 0})
        subs[s]["n"] += 1
        subs[s]["q1_224_forced"] += int(f224[i]["is_q1"])
        subs[s]["q1_224c_forced"] += int(fc[i]["is_q1"])
    res["M2"] = {"n_dialogs": len(m2), "q1_224c": m2_q1,
                 "wrong_value_224c": m2_wrong,
                 "q1_224_forced_for_contrast": sum(f224[i]["is_q1"]
                                                   for i in m2),
                 "by_sub": subs, "fact_not_stored": not_stored,
                 "harness228": {"n": f228["summary"]["n"],
                                "verdicts": f228["summary"]["verdicts"],
                                "q1_rows": h_q1,
                                "q2_rows": sum(r["reply"].strip() == Q2
                                               for r in f228["rows"])},
                 "pass": (len(m2) >= 30 and not m2_q1 and not m2_wrong
                          and not h_q1 and not not_stored)}

    m3 = sel("M3")
    reach = [i for i in m3 if f224[i]["is_q1"]]
    kept = [i for i in reach if fc[i]["is_q1"]]
    m3_wrong = [(i, m, rr[i]["stated_other_value"]) for i in m3
                for m, rr in (("forced", fc), ("natural", nc))
                if rr[i]["stated_other_value"]]
    res["M3"] = {"n": len(m3), "q1_reached_by_224_forced": len(reach),
                 "q1_kept_224c": len(kept),
                 "not_kept": [i for i in reach if i not in kept],
                 "wrong_value": m3_wrong,
                 "pass": (len(m3) >= 20 and len(reach) >= 20
                          and len(kept) >= 0.9 * len(reach)
                          and not m3_wrong)}
    for s in ("M2x", "M3x"):
        ids = sel(s)
        res[s + "_informational"] = {
            "n": len(ids),
            "q1_224_forced": sum(f224[i]["is_q1"] for i in ids),
            "q1_224c_forced": sum(fc[i]["is_q1"] for i in ids),
            "rows": {i: " ".join(fc[i]["reply"]) for i in ids}}
    res["writes_cases"] = sum(len(r["writes"]) for rr in (fc, nc)
                              for r in rr.values())

    # M4
    sd = d / "suitediff"
    summ = load(sd / "SUITEDIFF218-SUMMARY.json")
    moves, bad = [], 0
    for f in sorted(sd.glob("*-diff.json")):
        dj = load(f)
        for m in dj.get("moves", []):
            moves.append({"suite": dj.get("suite", f.stem), **{
                k: m.get(k) for k in ("id", "class", "base_verdict",
                                      "new_verdict", "base_reply",
                                      "new_reply")}})
        bad += int(dj.get("new_wrong", 0) or 0) + int(
            dj.get("new_wrong_write", 0) or 0) + int(dj.get("new_junk", 0)
                                                     or 0)
    unpred = []
    for m in moves:
        pred = (m["id"] == PRED_FLAKE_BACK
                and str(m.get("base_reply", "")).startswith(Q1[:30])) or (
            str(m.get("base_reply", "")).strip() == Q1
            and str(m.get("new_reply", "")).strip() == Q2)
        m["predicted"] = bool(pred)
        if not pred:
            unpred.append(m["id"])
    res["M4"] = {"moves": moves, "unpredicted": unpred, "bad_class_total":
                 bad, "summary_gate": summ.get("gate", summ.get("GATE")),
                 "pass": bad == 0 and not unpred}

    # M5
    b3 = load(d / "m5-b3.json")
    res["M5"] = {"pass": bool(b3.get("pass")), "rows": b3.get("rows")}
    res["verdict"] = "PASS" if all(res[k]["pass"] for k in
                                   ("M1", "M2", "M3", "M4", "M5")) else "FAIL"
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    for k in ("M1", "M2", "M3", "M4", "M5"):
        print(k, "PASS" if res[k]["pass"] else "FAIL",
              json.dumps({x: y for x, y in res[k].items()
                          if x not in ("rows", "moves", "by_sub")})[:600])
    print("VERDICT", res["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
