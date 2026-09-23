#!/usr/bin/env python3
"""Exp 235b scorer. Arms on the 235b panel:
  A_raw   = greedy ear frames (no brake)
  A_brake = greedy ear + brake            (= the 235 registered arm)
  A       = greedy ear + brake + gate     (tau read from the sealed tau file)
  B       = 138i + 228 rules (statement families only)
Matching = the sealed 235 scorer's functions (claude_smolear235_score.match/frame_ok/b_frames),
gold via claude_smolear235b_panel.load_panel (schema check -> exit 3; chain fix built in).
The panel's `clear` flag is ignored (clear:false items count fully).

Marks (A):
  M1  no_save: TEACH frames saved <= 1
  M2  wrong saves (saved TEACH matching no gold TEACH frame of the item) across
      plain_teach + varied_teach + full_names + corrections + no_save <= 1
  M3  exact TEACH recall on plain_teach + varied_teach + full_names + corrections >= 85 %
      and >= B + 30 points
  M3b UNSURE TEACH frames (margin gate + ASK-within-tau) on those 4 statement families
      <= 12 % of their gold TEACH frames (GUARD_Q blocks reported separately, not UNSURE)
  M4  exact ASK recall on questions + chain_questions >= 90 %
  M5  median GPU ms per turn (greedy + brake + beams + gate) <= 300

python claude_smolear235b_score.py --panel P --a-preds A.json --b-preds B.json --tau-file TAU.json --out S.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402
import claude_smolear235b_beam as B  # noqa: E402
import claude_smolear235b_panel as P  # noqa: E402

STATEMENT = ["plain_teach", "varied_teach", "full_names", "corrections"]
SAVE_FAMS = STATEMENT + ["no_save"]
QUESTION = ["questions", "chain_questions"]
ARMS = ["A_raw", "A_brake", "A", "B"]


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def score(items, apreds, bpreds, tau):
    rows, agg, tags = [], {}, {}
    for it in items:
        rec = apreds[it["id"]]
        g = B.gate(it["turn"], rec["raw"], rec["greedy_lp"], [tuple(x) for x in rec["beams"]], tau)
        arms = {"A_raw": [f for f in E.parse_frames(rec["raw"]) if f["act"] in ("TEACH", "ASK")],
                "A_brake": g["kept_brake"], "A": g["saved"]}
        if it["family"] not in QUESTION and it["id"] in bpreds:
            arms["B"] = S.b_frames(bpreds[it["id"]])
        row = dict(id=it["id"], family=it["family"], tags=it["tags"], ms=rec.get("ms"), arms={},
                   unsure=len(g["unsure"]), guard=len(g["guard"]),
                   margins=[m if m != float("inf") else "inf" for m in g["margins"]])
        keys = [("family", it["family"])] + [("tag", f"{t}:{'stmt' if it['family'] in STATEMENT else it['family']}")
                                            for t in it["tags"]]
        for arm, fr in arms.items():
            th, tx, tn = S.match(fr, it["gold"], "TEACH")
            ah, ax, an = S.match(fr, it["gold"], "ASK")
            saved = sum(1 for f in fr if f["act"] == "TEACH")
            row["arms"][arm] = dict(teach_hit=th, teach_gold=tn, wrong=len(tx), ask_hit=ah, ask_gold=an,
                                    ask_extra=len(ax), saved=saved,
                                    exact=(th == tn and ah == an and not tx and not ax))
            for kind, key in keys:
                tgt = (agg if kind == "family" else tags).setdefault(arm, {}).setdefault(key, dict(
                    n=0, teach_hit=0, teach_gold=0, wrong=0, saved=0, ask_hit=0, ask_gold=0,
                    exact=0, unsure=0, guard=0))
                tgt["n"] += 1
                tgt["teach_hit"] += th
                tgt["teach_gold"] += tn
                tgt["wrong"] += len(tx)
                tgt["saved"] += saved
                tgt["ask_hit"] += ah
                tgt["ask_gold"] += an
                tgt["exact"] += row["arms"][arm]["exact"]
                if arm == "A":
                    tgt["unsure"] += len(g["unsure"])
                    tgt["guard"] += len(g["guard"])
        rows.append(row)

    def tot(arm, fams, key):
        return sum(agg.get(arm, {}).get(f, {}).get(key, 0) for f in fams)

    marks = {}
    for arm in ARMS:
        m = dict(M1_no_save_saved=tot(arm, ["no_save"], "saved"),
                 M2_wrong_saves=tot(arm, SAVE_FAMS, "wrong"),
                 M3_hit=tot(arm, STATEMENT, "teach_hit"), M3_gold=tot(arm, STATEMENT, "teach_gold"))
        m["M3_recall_pct"] = pct(m["M3_hit"], m["M3_gold"])
        if arm != "B":
            m["M4_hit"] = tot(arm, QUESTION, "ask_hit")
            m["M4_gold"] = tot(arm, QUESTION, "ask_gold")
            m["M4_recall_pct"] = pct(m["M4_hit"], m["M4_gold"])
            m["question_stray_teach"] = tot(arm, QUESTION, "saved")
        if arm == "A":
            m["M3b_unsure"] = tot(arm, STATEMENT, "unsure")
            m["M3b_unsure_pct"] = pct(m["M3b_unsure"], m["M3_gold"])
            m["guard_blocked_statement"] = tot(arm, STATEMENT, "guard")
            m["unsure_no_save"] = tot(arm, ["no_save"], "unsure")
            m["guard_no_save"] = tot(arm, ["no_save"], "guard")
        marks[arm] = m
    lat = [r["ms"] for r in rows if r["ms"] is not None]
    A, Bm = marks["A"], marks["B"]
    med = statistics.median(lat) if lat else None
    verdict = dict(
        M1=A["M1_no_save_saved"] <= 1,
        M2=A["M2_wrong_saves"] <= 1,
        M3=(A["M3_recall_pct"] or 0) >= 85.0 and (A["M3_recall_pct"] or 0) >= (Bm["M3_recall_pct"] or 0) + 30.0,
        M3b=(A["M3b_unsure_pct"] or 0) <= 12.0,
        M4=(A["M4_recall_pct"] or 0) >= 90.0,
        M5=(med is not None and med <= 300.0),
    )
    verdict["ALL"] = all(verdict.values())
    return dict(tau=tau, marks=marks, verdict=verdict, median_ms=med, by_family=agg, by_tag=tags, rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--b-preds", required=True)
    ap.add_argument("--tau-file", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = P.load_panel(a.panel)
    tau = json.loads(Path(a.tau_file).read_text())["tau"]
    apd = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))
    if apd["summary"].get("tau") != tau:
        raise SystemExit(f"a-preds were run with tau {apd['summary'].get('tau')}, sealed tau {tau}")
    res = score(items, apd["preds"], json.loads(Path(a.b_preds).read_text()), tau)
    res["gpu_summary"] = apd["summary"]
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(dict(tau=tau, marks=res["marks"], verdict=res["verdict"], median_ms=res["median_ms"]), indent=1))


if __name__ == "__main__":
    main()
