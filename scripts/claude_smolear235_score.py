#!/usr/bin/env python3
"""Exp 235 scorer: arms A (SmolLM ear, raw and after the brake) and B (138i).

python claude_smolear235_score.py --panel P --a-preds A.json --b-preds B.json --out SCORE.json

Matching (fixed before the seal):
- subject/value: lower-case, edge punctuation trimmed, spaces collapsed, a
  leading "the/a/an" dropped; values also drop a trailing "years old".
  First-person subjects {i, me, my, myself, mine, user} are one entity
  (the notebook stores them as USER).
- relation hop: the predicted relation matches a gold hop when its canonical
  table name equals the canonical name (via table v1 names + aliases) of the
  gold relation or of any listed gold alias, or when the plain strings match
  after lower-casing and treating _ - and space alike.
- a gold frame is matched at most once (greedy, in gold order).
Marks (see PASSMARKS.md):
  M1 no_save: TEACH frames saved (A after brake) <= 1.
  M2 wrong saves across statement families (plain_teach, varied_teach,
     full_names, corrections, no_save): TEACH frames kept that match no gold
     TEACH frame of that item <= 2 (A after brake).
  M3 exact TEACH-frame recall on plain_teach+varied_teach+full_names+corrections:
     A >= 80% and A >= B + 15 points.
  M4 exact ASK-frame recall on questions+chain_questions: A >= 80%.
  M5 GPU median latency per turn <= 300 ms.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_smolear235_model as E  # noqa: E402  (parse_frames, brake, canon_rel only)
import claude_smolear235_panel as P  # noqa: E402

STATEMENT = ["plain_teach", "varied_teach", "full_names", "corrections"]
SAVE_FAMS = STATEMENT + ["no_save"]
QUESTION = ["questions", "chain_questions"]
FIRST = {"i", "me", "my", "myself", "mine", "user"}


def norm(s):
    s = " ".join(str(s or "").strip(" \t\"'.,;:!?()[]{}").split()).lower()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    return s


def norm_subj(s):
    n = norm(s)
    return "<user>" if n in FIRST else n


def norm_val(s):
    n = norm(s)
    return re.sub(r"\s+years?\s+old$", "", n)


def rkey(s):
    return re.sub(r"[\s_\-]+", " ", str(s).strip().lower())


def rel_ok(pred, gold, aliases):
    pc = E.canon_rel(pred) or pred
    for c in [gold] + list(aliases or []):
        if rkey(c) == rkey(pc) or rkey(c) == rkey(pred):
            return True
        cc = E.canon_rel(c)
        if cc is not None and cc == pc:
            return True
    return False


def frame_ok(p, g):
    if p["act"] != g["act"]:
        return False
    if norm_subj(p["subject"]) != norm_subj(g["subject"]):
        return False
    prel = p["relation"] if isinstance(p["relation"], list) else [p["relation"]]
    if len(prel) != len(g["relation"]):
        return False
    for i, (pr, gr) in enumerate(zip(prel, g["relation"])):
        al = g["aliases"][i] if i < len(g["aliases"]) else []
        if not rel_ok(pr, gr, al):
            return False
    if g["act"] == "TEACH" and norm_val(p["value"]) != norm_val(g["value"]):
        return False
    return True


def match(preds, golds, act):
    """Returns (matched_gold_count, unmatched_pred_frames)."""
    gl = [g for g in golds if g["act"] == act]
    used = [False] * len(gl)
    extra, hit = [], 0
    for p in [p for p in preds if p["act"] == act]:
        for i, g in enumerate(gl):
            if not used[i] and frame_ok(p, g):
                used[i] = True
                hit += 1
                break
        else:
            extra.append(p)
    return hit, extra, len(gl)


def b_frames(rec):
    out = []
    for s, r, v in rec.get("triples", []):
        out.append(dict(act="TEACH", subject=("me" if s == "USER" else s), relation=r, value=v))
    return out


def pct(a, b):
    return round(100.0 * a / b, 1) if b else None


def score(items, apreds, bpreds):
    rows = []
    agg = {}
    for it in items:
        rec = apreds.get(it["id"], {"raw": "", "ms": None})
        raw_frames = E.parse_frames(rec["raw"])
        kept, dropped = E.brake(raw_frames, it["turn"])
        raw_ok = [f for f in raw_frames if f["act"] in ("TEACH", "ASK")]
        arms = {"A_raw": raw_ok, "A": kept}
        if it["family"] not in QUESTION and it["id"] in bpreds:
            arms["B"] = b_frames(bpreds[it["id"]])
        row = dict(id=it["id"], family=it["family"], turn=it["turn"], raw=rec["raw"], ms=rec.get("ms"),
                   kept=kept, dropped=[(f, why) for f, why in dropped],
                   b=bpreds.get(it["id"]), gold=it["gold"], arms={})
        for arm, fr in arms.items():
            th, tx, tn = match(fr, it["gold"], "TEACH")
            ah, ax, an = match(fr, it["gold"], "ASK")
            row["arms"][arm] = dict(teach_hit=th, teach_gold=tn, teach_extra=len(tx),
                                    ask_hit=ah, ask_gold=an, ask_extra=len(ax),
                                    teach_saved=sum(1 for f in fr if f["act"] == "TEACH"),
                                    exact_turn=(th == tn and ah == an and not tx and not ax))
            a = agg.setdefault(arm, {}).setdefault(it["family"], dict(
                n=0, teach_hit=0, teach_gold=0, wrong_saves=0, teach_saved=0, ask_hit=0,
                ask_gold=0, ask_extra=0, exact_turns=0))
            a["n"] += 1
            a["teach_hit"] += th
            a["teach_gold"] += tn
            a["wrong_saves"] += len(tx)
            a["teach_saved"] += sum(1 for f in fr if f["act"] == "TEACH")
            a["ask_hit"] += ah
            a["ask_gold"] += an
            a["ask_extra"] += len(ax)
            a["exact_turns"] += row["arms"][arm]["exact_turn"]
        rows.append(row)

    def tot(arm, fams, key):
        return sum(agg.get(arm, {}).get(f, {}).get(key, 0) for f in fams)

    marks = {}
    for arm in ("A_raw", "A", "B"):
        m = {}
        m["M1_no_save_teach_frames"] = tot(arm, ["no_save"], "teach_saved")
        m["M2_wrong_saves_statement_families"] = tot(arm, SAVE_FAMS, "wrong_saves")
        m["M3_teach_hit"] = tot(arm, STATEMENT, "teach_hit")
        m["M3_teach_gold"] = tot(arm, STATEMENT, "teach_gold")
        m["M3_recall_pct"] = pct(m["M3_teach_hit"], m["M3_teach_gold"])
        if arm != "B":
            m["M4_ask_hit"] = tot(arm, QUESTION, "ask_hit")
            m["M4_ask_gold"] = tot(arm, QUESTION, "ask_gold")
            m["M4_recall_pct"] = pct(m["M4_ask_hit"], m["M4_ask_gold"])
            m["question_family_stray_teach_frames"] = tot(arm, QUESTION, "teach_saved")
        marks[arm] = m
    lat = [r["ms"] for r in rows if r["ms"] is not None]
    A, B = marks["A"], marks["B"]
    verdict = dict(
        M1=A["M1_no_save_teach_frames"] <= 1,
        M2=A["M2_wrong_saves_statement_families"] <= 2,
        M3=(A["M3_recall_pct"] or 0) >= 80.0 and (A["M3_recall_pct"] or 0) >= (B["M3_recall_pct"] or 0) + 15.0,
        M4=(A["M4_recall_pct"] or 0) >= 80.0,
        M5=(statistics.median(lat) <= 300.0) if lat else False,
    )
    verdict["ALL"] = all(verdict.values())
    return dict(marks=marks, by_family=agg, verdict=verdict,
                gpu_median_ms=statistics.median(lat) if lat else None, rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--a-preds", required=True)
    ap.add_argument("--b-preds", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    items = P.load_panel(a.panel)
    ap_ = json.loads(Path(a.a_preds).read_text())
    ap_ = ap_.get("preds", ap_)
    bp = json.loads(Path(a.b_preds).read_text())
    res = score(items, ap_, bp)
    Path(a.out).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(dict(marks=res["marks"], verdict=res["verdict"],
                          gpu_median_ms=res["gpu_median_ms"]), indent=1))


if __name__ == "__main__":
    main()
