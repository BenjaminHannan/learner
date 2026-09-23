#!/usr/bin/env python3
"""Exp 264 -- registered scorer: 261b's sealed scorer (Ruling 1 included) plus
the QA arm, in a new wrapper that also reports wrong saves per saved fact and
per turn.

Arms from GPU ear preds + recorded QA answers (+ recorded pYES for the A261b
diagnostic):
  A_brake brake -> canonicalise (261 sealed)
  A261b   brake -> canon -> YES/NO checker(0.25, prompt B) -> guard (261b's A)
  A       brake -> canon -> QA checker (value+owner+relation) -> guard (reg.)
  B       138i + 228 (statement families)

Matching = 261b's sealed scorer with Ruling 1 (imported, not reimplemented).
Marks, arm A: M1 no_save saves <= 1; M2 wrong saves <= 1; M3 exact TEACH
recall >= 85% and >= B + 30; M3b held back (QA UNSURE + guard) <= 12% of gold
TEACH; M4 exact ASK recall >= 90%; M5 median ear+QA+guard ms/turn <= 800;
M6 every A frame byte-identical in A_brake.
Also reported (no bars): per-fact and per-turn wrong-save rates for every arm,
per family, per tag, and each held/wrong frame by category only.

python claude_earcheck264_scoremain.py --panel P --seal S --a-preds A.json --b-preds B.json --qa Q.json [--pyes Y.json ...] --out O.json [--no-sha]
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
import claude_earcheck261_arms as A261  # noqa: E402
import claude_earcheck261_scoremain as M261  # noqa: E402
import claude_earcheck261b_scoremain as M261B  # noqa: E402
import claude_earcheck264_arms as BA  # noqa: E402
import claude_earcheck264_panel as P  # noqa: E402

STATEMENT = M261.STATEMENT
SAVE_FAMS = M261.SAVE_FAMS
QUESTION = M261.QUESTION


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def blank(s):
    return re.sub(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b", "NAME", str(s))


def build_qa_texts(item_id, n_teach, qamap):
    """qamap: {checkid: (text, ms)} with checkid '<id>#t<k>#q<q>' or with src
    prefix for dev. Returns {k: (av, ao, ar, ms)} and summed ms."""
    out, tot = {}, 0.0
    for k in range(n_teach):
        rec = {}
        for q in ("value", "owner", "relation"):
            cid = f"{item_id}#t{k}#q{q}"
            if cid in qamap:
                t, ms = qamap[cid]
                rec[q] = (t, float(ms))
        if len(rec) == 3:
            tot += rec["value"][1] + rec["owner"][1] + rec["relation"][1]
            out[k] = (rec["value"][0], rec["owner"][0], rec["relation"][0],
                      rec["value"][1] + rec["owner"][1] + rec["relation"][1])
    return out, tot


def score(items, apreds, bpreds, qamap, pmap):
    S.rel_ok = M261B.rel_ok_narrower
    try:
        rows, agg, tags = [], {}, {}
        m6_bad = 0
        details = []
        for it in items:
            rec = apreds[it["id"]]
            arms0 = A261.base_arms(rec["raw"], it["turn"], rec["greedy_lp"], rec["beams"])
            kept_canon = arms0["kept_canon"]
            n_teach = sum(1 for f in kept_canon if f.get("act") == "TEACH")
            qa_texts, qa_ms = build_qa_texts(it["id"], n_teach, qamap)
            a_frames, a_guard_held, _, a_qa_unsure, _, gms = BA.qa_arm(kept_canon, qa_texts)
            pl = [float(pmap[f"{it['id']}#t{k}"][0]) for k in range(n_teach)] if n_teach else []
            saved261, _ = A261.checker_split(kept_canon, pl, BA.THETA_261B) if n_teach else ([f for f in kept_canon], [])
            a261b_frames, a261b_guard_held = BA.apply_guard(saved261)[:2]
            for f in a_frames:
                if not any(f == b for b in arms0["A_brake"]):
                    m6_bad += 1
            ear_ms = float(rec.get("ms_greedy", rec.get("ms", 0.0)))
            ms = round(ear_ms + qa_ms + gms, 2)
            arms = dict(A=a_frames, A261b=a261b_frames, A_brake=arms0["A_brake"])
            if it["family"] not in QUESTION and it["id"] in bpreds:
                arms["B"] = S.b_frames(bpreds[it["id"]])
            stmt = it["family"] in STATEMENT
            n_unsure = (len(a_qa_unsure) + len(a_guard_held)) if stmt else 0
            row = dict(id=it["id"], family=it["family"], tags=it["tags"], ms=ms,
                       arms={}, unsure=n_unsure,
                       qa_unsure=len(a_qa_unsure) if stmt else 0,
                       guard_held=len(a_guard_held) if stmt else 0)
            keys = [("family", it["family"])] + [
                ("tag", f"{t}:{'stmt' if stmt else it['family']}") for t in it["tags"]]
            for arm, fr in arms.items():
                th, tx, tn = S.match(fr, it["gold"], "TEACH")
                ah, ax, an = S.match(fr, it["gold"], "ASK")
                saved_n = sum(1 for f in fr if f["act"] == "TEACH")
                turns_wrong = 1 if tx else 0
                row["arms"][arm] = dict(teach_hit=th, teach_gold=tn, wrong=len(tx),
                                        ask_hit=ah, ask_gold=an, ask_extra=len(ax),
                                        saved=saved_n, turns_wrong=turns_wrong,
                                        exact=(th == tn and ah == an and not tx and not ax))
                for kind, key in keys:
                    tgt = (agg if kind == "family" else tags).setdefault(arm, {}).setdefault(key, dict(
                        n=0, teach_hit=0, teach_gold=0, wrong=0, saved=0,
                        turns_wrong=0, ask_hit=0, ask_gold=0, exact=0, unsure=0))
                    tgt["n"] += 1
                    tgt["teach_hit"] += th
                    tgt["teach_gold"] += tn
                    tgt["wrong"] += len(tx)
                    tgt["saved"] += saved_n
                    tgt["turns_wrong"] += turns_wrong
                    tgt["ask_hit"] += ah
                    tgt["ask_gold"] += an
                    tgt["exact"] += row["arms"][arm]["exact"]
                    if arm == "A" and stmt:
                        tgt["unsure"] += n_unsure
            kept_list = [f for f in arms0["A_brake"] if f.get("act") == "TEACH"]
            for k, f in enumerate(kept_list):
                held_qa = not any(f == s for s in a_frames) and any(
                    {kk: vv for kk, vv in h.items()
                     if kk not in ("why", "qa_failed", "a_value", "a_owner",
                                   "a_relation", "guard")} == f
                    for h in list(a_qa_unsure) + list(a_guard_held))
                th1, tx1, _ = S.match([f], it["gold"], "TEACH")
                if held_qa or tx1:
                    hrec = next((h for h in list(a_qa_unsure) + list(a_guard_held)
                                 if {kk: vv for kk, vv in h.items()
                                     if kk not in ("why", "qa_failed", "a_value",
                                                   "a_owner", "a_relation",
                                                   "guard")} == f), {})
                    cat = hrec.get("guard") or (
                        "qa:" + "+".join(hrec.get("qa_failed", []))
                        if hrec.get("qa_failed") else "checker-passed")
                    details.append(dict(
                        id=it["id"], family=it["family"], tags=it["tags"],
                        status="HELD" if held_qa else "WRONG", category=cat))
            rows.append(row)

        def tot(arm, fams, key):
            return sum(agg.get(arm, {}).get(f, {}).get(key, 0) for f in fams)

        marks = {}
        for arm in ("A", "A261b", "A_brake", "B"):
            m = dict(M1_no_save_saved=tot(arm, ["no_save"], "saved"),
                     M2_wrong_saves=tot(arm, SAVE_FAMS, "wrong"),
                     M3_hit=tot(arm, STATEMENT, "teach_hit"),
                     M3_gold=tot(arm, STATEMENT, "teach_gold"))
            m["M3_recall_pct"] = pct(m["M3_hit"], m["M3_gold"])
            m["M2_saved_facts"] = tot(arm, SAVE_FAMS, "saved")
            m["M2_per_fact"] = round(m["M2_wrong_saves"] / m["M2_saved_facts"], 4) \
                if m["M2_saved_facts"] else None
            nturns = sum(agg.get(arm, {}).get(f, {}).get("n", 0) for f in SAVE_FAMS)
            m["M2_turns_wrong"] = tot(arm, SAVE_FAMS, "turns_wrong")
            m["M2_per_turn"] = round(m["M2_turns_wrong"] / nturns, 4) if nturns else None
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
        return dict(marks=marks, verdict=verdict, median_ms=med,
                    p90_ms=(sorted(lat)[int(0.9 * len(lat))] if lat else None),
                    max_ms=(max(lat) if lat else None), m6_mismatch=m6_bad,
                    by_family=agg, by_tag=tags, rows=rows, details=details,
                    narrower_map={k: sorted(v) for k, v in M261B.NARROWER.items()})
    finally:
        S.rel_ok = M261B._ORIG_REL_OK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--b-preds", required=True)
    ap.add_argument("--qa", required=True)
    ap.add_argument("--pyes", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-sha", action="store_true")
    a = ap.parse_args()
    items = P.load_panel(a.panel, seal=a.seal, check_sha=not a.no_sha)
    apd = json.loads(Path(a.a_preds).read_text(encoding="utf-8"))
    qd = json.loads(Path(a.qa).read_text(encoding="utf-8"))
    qamap = {cid: (v["text"], v.get("ms", 0.0))
             for cid, v in qd["checks"].items()}
    pmap = {}
    for path in a.pyes:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for cid, v in d["checks"].items():
            pmap[cid] = (float(v["p"]), float(v.get("ms", 0.0)))
    res = score(items, apd["preds"], json.loads(Path(a.b_preds).read_text()),
                qamap, pmap)
    res["gpu_summary"] = apd["summary"]
    res["qa_summary"] = qd["summary"]
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(dict(marks=res["marks"], verdict=res["verdict"],
                          median_ms=res["median_ms"]), indent=1))


if __name__ == "__main__":
    main()
