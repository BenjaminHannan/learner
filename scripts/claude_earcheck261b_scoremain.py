#!/usr/bin/env python3
"""Exp 261b -- registered scorer: 261's sealed scorer plus Ruling 1, plus the guard.

Ruling 1 (design/v3/30-modes/261b-decision.md): a TEACH frame whose relation is
in the gold relation's table-v2 "narrower" list counts as a hit, not a wrong
save. Implemented as a narrow wrapper around the sealed 235 rel_ok: everything
else (subject/value matching, greedy one-to-one matching, all arms, all marks)
is 261's sealed scorer, called unchanged.

Arms from GPU ear preds + recorded checker p(YES):
  A_raw     parse -> canonicalise (no brake)            [261 sealed]
  A_brake   brake -> canonicalise                       [261 sealed]
  A_gate    brake -> margin gate (tau 9.3) -> canon     [261 sealed]
  A261      brake -> canon -> checker(0.25, prompt B)   [261's A exactly]
  A         A261 -> span guard (registered 261b arm)
  A_nocanon brake (no canon) -> checker                 [261 sealed]
  B         138i + 228 (statement families)

Marks, arm A (same bars as 261): M1 no_save saves <= 1; M2 wrong saves <= 1;
M3 exact TEACH recall >= 85% and >= B + 30; M3b UNSURE <= 12% of gold TEACH;
M4 exact ASK recall >= 90%; M5 median ear+checker+guard ms/turn <= 800;
M6 every A frame byte-identical in A261.

python claude_earcheck261b_scoremain.py --panel P --seal S --a-preds A.json --b-preds B.json --theta TH --pyes Y.json [--pyes2 ...] --out O.json [--no-sha]
"""
from __future__ import annotations

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
import claude_earcheck261_scoremain as M261  # noqa: E402
import claude_earcheck261_canon as C261  # noqa: E402
import claude_earcheck261b_arms as BA  # noqa: E402
import claude_earcheck261b_panel as P  # noqa: E402

STATEMENT = M261.STATEMENT
SAVE_FAMS = M261.SAVE_FAMS
QUESTION = M261.QUESTION

_ORIG_REL_OK = S.rel_ok


def _narrower_map():
    m = {}
    for r in E._TABLE["relations"]:
        nar = [str(x) for x in r.get("narrower", [])]
        if nar:
            m[r["name"]] = set(nar)
    return m


NARROWER = _narrower_map()


def rel_ok_narrower(pred, gold, aliases):
    """Sealed rel_ok plus Ruling 1: pred relation in gold's narrower list."""
    if _ORIG_REL_OK(pred, gold, aliases):
        return True
    try:
        pc = E.canon_rel(pred)
    except Exception:
        pc = None
    try:
        gc = E.canon_rel(gold)
    except Exception:
        gc = None
    if pc is None:
        pc = S.rkey(pred)
    if gc is None:
        return False
    return pc in NARROWER.get(gc, set())


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def score(items, apreds, bpreds, pmap, theta):
    """Score with Ruling 1 active. Returns dict with A261 base + A (guarded)."""
    S.rel_ok = rel_ok_narrower
    try:
        base = M261.score(items, apreds, bpreds, pmap, theta)
        rows, agg, tags = [], {}, {}
        m6_bad = 0
        details = []
        guard_held_total = 0
        for it in items:
            rec = apreds[it["id"]]
            arms, unsure, _, pl, cms = M261.arm_set(it, rec, pmap, theta)
            a261 = arms["A"]
            aframes, held, gms = BA.apply_guard(a261)
            for f in aframes:
                if not any(f == b for b in a261):
                    m6_bad += 1
            ear_ms = float(rec.get("ms_greedy", rec.get("ms", 0.0)))
            ms = round(ear_ms + sum(cms) + gms, 2)
            stmt = it["family"] in STATEMENT
            n_guard_stmt = sum(1 for _ in held) if stmt else 0
            guard_held_total += sum(1 for _ in held)
            row = dict(id=it["id"], family=it["family"], tags=it["tags"], ms=ms,
                       unsure_checker=len(unsure), guard_held=len(held))
            keys = [("family", it["family"])] + [
                ("tag", f"{t}:{'stmt' if stmt else it['family']}") for t in it["tags"]]
            th, tx, tn = S.match(aframes, it["gold"], "TEACH")
            ah, ax, an = S.match(aframes, it["gold"], "ASK")
            saved_n = sum(1 for f in aframes if f["act"] == "TEACH")
            row["teach"] = dict(hit=th, gold=tn, wrong=len(tx), saved=saved_n)
            row["ask"] = dict(hit=ah, gold=an, extra=len(ax))
            row["exact"] = (th == tn and ah == an and not tx and not ax)
            for kind, key in keys:
                tgt = (agg if kind == "family" else tags).setdefault(key, dict(
                    n=0, teach_hit=0, teach_gold=0, wrong=0, saved=0, ask_hit=0,
                    ask_gold=0, exact=0, unsure=0, guard_held=0))
                tgt["n"] += 1
                tgt["teach_hit"] += th
                tgt["teach_gold"] += tn
                tgt["wrong"] += len(tx)
                tgt["saved"] += saved_n
                tgt["ask_hit"] += ah
                tgt["ask_gold"] += an
                tgt["exact"] += row["exact"]
                if stmt:
                    tgt["unsure"] += len(unsure) + len(held)
                    tgt["guard_held"] += len(held)
            kept_list = [f for f in arms["A_brake"] if f.get("act") == "TEACH"]
            for k, f in enumerate(kept_list):
                h = next((x for x in held
                          if {kk: vv for kk, vv in x.items()
                              if kk not in ("why", "guard", "pyes")} == f), None)
                th1, tx1, _ = S.match([f], it["gold"], "TEACH")
                claim = M261.blank(C261.render_claim(
                    f["subject"], f["relation"], f["value"]))
                if h is not None:
                    details.append(dict(
                        id=it["id"], family=it["family"], tags=it["tags"],
                        status="GUARD_HELD", category=h.get("guard"),
                        pyes=pl[k], claim=claim))
                elif tx1:
                    details.append(dict(
                        id=it["id"], family=it["family"], tags=it["tags"],
                        status="WRONG", category="checker-passed",
                        pyes=pl[k], claim=claim))
            rows.append(row)

        def tot(fams, key):
            return sum(agg.get(f, {}).get(key, 0) for f in fams)

        m = dict(M1_no_save_saved=tot(["no_save"], "saved"),
                 M2_wrong_saves=tot(SAVE_FAMS, "wrong"),
                 M3_hit=tot(STATEMENT, "teach_hit"),
                 M3_gold=tot(STATEMENT, "teach_gold"))
        m["M3_recall_pct"] = pct(m["M3_hit"], m["M3_gold"])
        m["M4_hit"] = tot(QUESTION, "ask_hit")
        m["M4_gold"] = tot(QUESTION, "ask_gold")
        m["M4_recall_pct"] = pct(m["M4_hit"], m["M4_gold"])
        m["question_stray_teach"] = tot(QUESTION, "saved")
        m["M3b_unsure"] = tot(STATEMENT, "unsure")
        m["M3b_unsure_pct"] = pct(m["M3b_unsure"], m["M3_gold"])
        m["M3b_guard_held_stmt"] = tot(STATEMENT, "guard_held")
        lat = [r["ms"] for r in rows if r["ms"] is not None]
        med = statistics.median(lat) if lat else None
        bmarks = base["marks"]["B"]
        verdict = dict(
            M1=m["M1_no_save_saved"] <= 1,
            M2=m["M2_wrong_saves"] <= 1,
            M3=(m["M3_recall_pct"] or 0) >= 85.0
            and (m["M3_recall_pct"] or 0) >= (bmarks["M3_recall_pct"] or 0) + 30.0,
            M3b=(m["M3b_unsure_pct"] or 0) <= 12.0,
            M4=(m["M4_recall_pct"] or 0) >= 90.0,
            M5=(med is not None and med <= 800.0),
            M6=(m6_bad == 0),
        )
        verdict["ALL"] = all(verdict.values())
        curve = []
        for ti100 in range(0, 21):
            th = round(ti100 * 0.05, 2)
            hit = gold = wrong = nonq = 0
            for it in items:
                rec = apreds[it["id"]]
                armsets, _, _, _, _ = M261.arm_set(it, rec, pmap, th)
                kept_a, _, _ = BA.apply_guard(armsets["A"])
                h, x, n = S.match(kept_a, it["gold"], "TEACH")
                hit += h
                gold += n
                wrong += len(x)
                if not any(g["act"] == "ASK" for g in it["gold"]):
                    nonq += 1
            curve.append(dict(theta=th, recall=round(hit / gold, 4) if gold else None,
                              wrong=wrong,
                              wrong_rate=round(wrong / nonq, 4) if nonq else None))
        out = dict(theta=theta, marks_A=m, verdict=verdict, median_ms=med,
                   p90_ms=(sorted(lat)[int(0.9 * len(lat))] if lat else None),
                   max_ms=(max(lat) if lat else None), m6_mismatch=m6_bad,
                   guard_held_total=guard_held_total,
                   by_family=agg, by_tag=tags, rows=rows, details=details,
                   theta_curve_A=curve, A261=base,
                   narrower_map={k: sorted(v) for k, v in NARROWER.items()})
    finally:
        S.rel_ok = _ORIG_REL_OK
    return out


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
    print(json.dumps(dict(theta=a.theta, marks_A=res["marks_A"],
                          verdict=res["verdict"], median_ms=res["median_ms"],
                          A261_verdict=res["A261"]["verdict"]), indent=1))


if __name__ == "__main__":
    main()
