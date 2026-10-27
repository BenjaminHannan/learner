#!/usr/bin/env python3
"""Exp 261 -- registered scorer (clean implementation; see RESULTS for the
superseded draft). Arms from GPU ear preds + recorded checker p(YES):

  A_raw     parse -> canonicalise (no brake)
  A_brake   brake -> canonicalise
  A_gate    brake -> margin gate (tau 9.3, recomputed exactly as 257) -> canon
  A         brake -> canon -> checker(theta): TEACH saved iff p(YES) >= theta
  A_nocanon brake (no canon) -> checker(theta)
  B         138i + 228 (statement families)

Matching = sealed 235 functions, table v2. Marks M1-M5 (257 bars; M5 median
ear+checker ms <= 800) + M6 (every A frame byte-identical in A_brake).
Reports: every arm's M1-M4, panel theta curve, per-tag table, and for each A
held-back/wrong frame: category, p(YES), blanked claim H.

python claude_earcheck261_scoremain.py --panel P --seal S --a-preds A.json --b-preds B.json --theta TH --pyes Y.json [--pyes2 Y2.json] --out O.json
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
import claude_smolear235_model as E  # noqa: E402
import claude_smolear235_score as S  # noqa: E402
import claude_earcheck261_arms as A  # noqa: E402
import claude_earcheck261_canon as C  # noqa: E402
import claude_earcheck261_panel as P  # noqa: E402

STATEMENT = ["plain_teach", "varied_teach", "full_names", "corrections"]
SAVE_FAMS = STATEMENT + ["no_save"]
QUESTION = ["questions", "chain_questions"]
ARMS = ["A_raw", "A_brake", "A_gate", "A", "A_nocanon", "B"]


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def blank(s):
    return re.sub(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b", "NAME", str(s))


def arm_set(it, rec, pmap, theta):
    """Return dict arm -> (saved_frames, unsure_list, p_list)."""
    arms0 = A.base_arms(rec["raw"], it["turn"], rec["greedy_lp"], rec["beams"])
    kept_nc = [f for f in E.brake(E.parse_frames(rec["raw"]), it["turn"])[0]]
    n_teach = sum(1 for f in arms0["kept_canon"] if f.get("act") == "TEACH")
    n_nc = sum(1 for f in kept_nc if f.get("act") == "TEACH")
    pl = [float(pmap[f"{it['id']}#t{k}"][0]) for k in range(n_teach)]
    cms = [float(pmap[f"{it['id']}#t{k}"][1]) for k in range(n_teach)]
    pl_nc = [float(pmap[f"nc:{it['id']}#t{k}"][0]) for k in range(n_nc)]
    saved, unsure = A.checker_split(arms0["kept_canon"], pl, theta)
    saved_nc, unsure_nc = A.checker_split(kept_nc, pl_nc, theta)
    return (dict(A_raw=arms0["A_raw"], A_brake=arms0["A_brake"],
                 A_gate=arms0["A_gate"], A=saved, A_nocanon=saved_nc),
            unsure, unsure_nc, pl, cms)


def score(items, apreds, bpreds, pmap, theta):
    rows, agg, tags = [], {}, {}
    m6_bad = 0
    details = []
    for it in items:
        rec = apreds[it["id"]]
        arms, unsure, unsure_nc, pl, cms = arm_set(it, rec, pmap, theta)
        if it["family"] not in QUESTION and it["id"] in bpreds:
            arms["B"] = S.b_frames(bpreds[it["id"]])
        for f in arms["A"]:
            if not any(f == b for b in arms["A_brake"]):
                m6_bad += 1
        ear_ms = float(rec.get("ms_greedy", rec.get("ms", 0.0)))
        ms = round(ear_ms + sum(cms), 2)
        row = dict(id=it["id"], family=it["family"], tags=it["tags"], ms=ms,
                   arms={}, unsure=len(unsure))
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
                    ask_gold=0, exact=0, unsure=0))
                tgt["n"] += 1
                tgt["teach_hit"] += th
                tgt["teach_gold"] += tn
                tgt["wrong"] += len(tx)
                tgt["saved"] += saved_n
                tgt["ask_hit"] += ah
                tgt["ask_gold"] += an
                tgt["exact"] += row["arms"][arm]["exact"]
                if arm == "A":
                    tgt["unsure"] += len(unsure)
        # details: held-back + wrong frames of A (category, p, blanked claim)
        ti = 0
        pmap_frame = {}
        for f in arms["A_brake"]:
            if f.get("act") == "TEACH":
                pmap_frame[id(f)] = None
        kept_list = [f for f in arms["A_brake"] if f.get("act") == "TEACH"]
        for k, f in enumerate(kept_list):
            h = C.render_claim(f["subject"], f["relation"], f["value"])
            held = not any(f == s for s in arms["A"])
            th1, tx1, _ = S.match([f], it["gold"], "TEACH")
            if held or tx1:
                details.append(dict(id=it["id"], family=it["family"],
                                    tags=it["tags"], status="HELD" if held else "WRONG",
                                    pyes=pl[k], claim=blank(h)))
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
        M6=(m6_bad == 0),
    )
    verdict["ALL"] = all(verdict.values())
    # panel theta curve (recorded pYES, no re-query)
    curve = []
    for ti100 in range(0, 21):
        th = round(ti100 * 0.05, 2)
        hit = gold = wrong = nonq = 0
        for it in items:
            rec = apreds[it["id"]]
            arms, _, _, _, _ = arm_set(it, rec, pmap, th)
            h, x, n = S.match(arms["A"], it["gold"], "TEACH")
            hit += h
            gold += n
            wrong += len(x)
            if not any(g["act"] == "ASK" for g in it["gold"]):
                nonq += 1
        curve.append(dict(theta=th, recall=round(hit / gold, 4) if gold else None,
                          wrong=wrong,
                          wrong_rate=round(wrong / nonq, 4) if nonq else None))
    return dict(theta=theta, marks=marks, verdict=verdict, median_ms=med,
                p90_ms=(sorted(lat)[int(0.9 * len(lat))] if lat else None),
                max_ms=(max(lat) if lat else None), m6_mismatch=m6_bad,
                by_family=agg, by_tag=tags, rows=rows, details=details,
                theta_curve=curve)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--b-preds", required=True)
    ap.add_argument("--theta", type=float, required=True)
    ap.add_argument("--pyes", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-sha", action="store_true")
    a = ap.parse_args()
    items = P.load_panel(a.panel, seal=a.seal, check_sha=not a.no_sha)
    apd = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))
    pmap = {}
    for path in a.pyes:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for cid, v in d["checks"].items():
            pmap[cid] = (float(v["p"]), float(v.get("ms", 0.0)))
    res = score(items, apd["preds"], json.loads(Path(a.b_preds).read_text()),
                pmap, a.theta)
    res["gpu_summary"] = apd["summary"]
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(dict(theta=a.theta, marks=res["marks"],
                          verdict=res["verdict"], median_ms=res["median_ms"]),
                     indent=1))


if __name__ == "__main__":
    main()
