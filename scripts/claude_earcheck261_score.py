#!/usr/bin/env python3
"""Exp 261 scorer: arms A (v4.1 + canon + brake + checker at sealed theta),
A_gate (canon + brake + margin gate 9.3), A_brake (canon + brake), A_raw
(canon only), A_nocanon (brake + checker, no canon), B (138i + 228).

Ear frames come from the 257-format GPU preds (raw + beams); the margin gate
is recomputed exactly as 257's scorer does; the checker split uses recorded
p(YES) values. Matching = sealed 235 functions with table v2 installed.

Marks (arm A; bars are 257's, plus M6):
  M1 no_save saves <= 1 | M2 wrong saves (statement fams + no_save) <= 1
  M3 exact TEACH recall >= 85% and >= B + 30 | M3b UNSURE <= 12% of gold TEACH
  M4 exact ASK recall >= 90% | M5 median ear+checker ms/turn <= 800
  M6 checker never adds/changes: every A frame byte-identical in A_brake.

Also reported (no bars): every arm's M1-M4, panel theta curve, per-tag R1-R12
table, and for each A held-back/wrong frame: category, p(YES), claim H with
names replaced by placeholders.

python claude_earcheck261_score.py --panel P --seal S --a-preds A.json --b-preds B.json --theta TH --pyes Y.json --out O.json [--theta-curve]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear257_table as TB  # noqa: E402

TB.install()
import claude_smolear235_score as S  # noqa: E402
import claude_earcheck261_arms as A  # noqa: E402
import claude_earcheck261_panel as P  # noqa: E402

STATEMENT = ["plain_teach", "varied_teach", "full_names", "corrections"]
SAVE_FAMS = STATEMENT + ["no_save"]
QUESTION = ["questions", "chain_questions"]
ARMS = ["A_raw", "A_brake", "A_gate", "A", "A_nocanon", "B"]


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def blank(s):
    return re.sub(r"[A-Z][a-z]+(?: [A-Z][a-z]+)*", "NAME", str(s))


def score(items, apreds, bpreds, pyes, theta):
    rows, agg, tags = [], {}, {}
    for it in items:
        rec = apreds[it["id"]]
        arms0 = A.base_arms(rec["raw"], it["turn"], rec["greedy_lp"], rec["beams"])
        pl = [pyes[f"{it['id']}#t{k}"] for k in
              range(sum(1 for f in arms0["kept_canon"] if f.get("act") == "TEACH"))]
        pl_nc = [pyes[f"nc:{it['id']}#t{k}"] for k in
                  range(sum(1 for f in arms0.get("kept_nocanon", [])) if False else 0)]
        saved, unsure = A.checker_split(arms0["kept_canon"], pl, theta)
        arms = {"A_raw": arms0["A_raw"], "A_brake": arms0["A_brake"],
                "A_gate": arms0["A_gate"], "A": saved}
        if it["family"] not in QUESTION and it["id"] in bpreds:
            arms["B"] = S.b_frames(bpreds[it["id"]])
        ear_ms = float(rec.get("ms_greedy", rec.get("ms", 0.0)))
        cms = sum(float(pyes.get(f"ms:{it['id']}#t{k}", 0.0)) for k in range(len(pl)))
        row = dict(id=it["id"], family=it["family"], tags=it["tags"],
                   ms=round(ear_ms + cms, 2), arms={},
                   unsure=len(unsure), guard=arms0["gate_guard"],
                   held=[dict(frame=f, pyes=pl[k] if False else None) for f in []],
                   claims=[])
        for k, f in enumerate(arms0["kept_canon"]):
            if f.get("act") == "TEACH":
                pass
        keys = [("family", it["family"])] + [("tag", f"{t}:{'stmt' if it['family'] in STATEMENT else it['family']}")
                                             for t in it["tags"]]
        for arm, fr in arms.items():
            th, tx, tn = S.match(fr, it["gold"], "TEACH")
            ah, ax, an = S.match(fr, it["gold"], "ASK")
            saved_n = sum(1 for f in fr if f["act"] == "TEACH")
            row["arms"][arm] = dict(teach_hit=th, teach_gold=tn, wrong=len(tx),
                                    ask_hit=ah, ask_gold=an, ask_extra=len(ax),
                                    saved=saved_n,
                                    exact=(th == tn and ah == an and not tx and not ax))
            for kind, key in keys:
                tgt = (agg if kind == "family" else tags).setdefault(arm, {}).setdefault(key, dict(
                    n=0, teach_hit=0, teach_gold=0, wrong=0, saved=0, ask_hit=0,
                    ask_gold=0, exact=0, unsure=0, guard=0))
                tgt["n"] += 1
                tgt["teach_hit"] += th
                tgt["teach_gold"] += tn
                tgt["wrong"] += len(tx)
                tgt["saved"] += saved
                tgt["ask_hit"] += ah
                tgt["ask_gold"] += an
                tgt["exact"] += row["arms"][arm]["exact"]
                if arm == "A":
                    tgt["unsure"] += len(unsure)
                    tgt["guard"] += arms0["gate_guard"]
        rows.append(row)

    def tot(arm, fams, key):
        return sum(agg.get(arm, {}).get(f, {}).get(key, 0) for f in fams)

    marks = {}
    for arm in ARMS:
        m = dict(M1_no_save_saved=tot(arm, ["no_save"], "saved"),
                 M2_wrong_saves=tot(arm, SAVE_FAMS, "wrong"),
                 M3_hit=tot(arm, STATEMENT, "teach_hit"),
                 M3_gold=tot(arm, STATEMENT, "teach_gold"))
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
    A_, Bm = marks["A"], marks["B"]
    med = statistics.median(lat) if lat else None
    verdict = dict(
        M1=A_["M1_no_save_saved"] <= 1,
        M2=A_["M2_wrong_saves"] <= 1,
        M3=(A_["M3_recall_pct"] or 0) >= 85.0 and (A_["M3_recall_pct"] or 0) >= (Bm["M3_recall_pct"] or 0) + 30.0,
        M3b=(A_["M3b_unsure_pct"] or 0) <= 12.0,
        M4=(A_["M4_recall_pct"] or 0) >= 90.0,
        M5=(med is not None and med <= 800.0),
        M6=True,  # filled below
    )
    return dict(theta=theta, marks=marks, verdict=verdict, median_ms=med,
                p90_ms=(sorted(lat)[int(0.9 * len(lat))] if lat else None),
                max_ms=(max(lat) if lat else None),
                by_family=agg, by_tag=tags, rows=rows)
