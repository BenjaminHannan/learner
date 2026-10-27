#!/usr/bin/env python3
"""Exp 118 tuning (CAL split ONLY — never touches any test panel).

Measures the V1 leftover brake on sealed CAL rows:
  * blocked-correct: CAL STATE-gold rows the sealed pipeline EXECUTEs correctly
    (ensemble at sealed tau + each single at its own tau) that the brake would
    refuse — must be ~0 (B3 allows <=5% drop).
  * blocked-wrong: CAL wrong writes at tau=0 (ensemble + singles) the brake
    would refuse — want 100%.
Then proposes minimal framing-word additions: words occurring as leftovers in
blocked-correct rows that never solely rescue a CAL wrong-write row.

Reads ONLY artifacts/fable-diag95-20260921/fable_diag95_rows.json panels.cal.
Tokenizer only (no model weights, no inference).

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_brake118_tune.py --out artifacts/fable-brake118-20260922/fable_brake118_tune_cal.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_score as S  # noqa: E402 (sealed verdict logic, read-only)
import fable_bert_loader as L  # noqa: E402 (tokenizer only)
import fable_brake118_leftover as B  # noqa: E402 (brake under test)

SNAP = ("/Users/ben-hannan/.cache/huggingface/hub/models--allenai--"
        "scibert_scivocab_uncased/snapshots/24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1")
ROWS = Path("artifacts/fable-diag95-20260921/fable_diag95_rows.json")
TAU_ENS = 0.8766039311885834
TAU_SINGLE = [0.9483702182769775, 0.8766039311885834, 0.9547552053165873]
WRITE_ACTS = {"STATE", "RETRACT"}


def parse_of(r, s):
    d = r["seeds"][s]
    f = d["frame"]
    fr = {"act": f["act"], "rel": f["rel"],
          "subj": tuple(f["subj"]) if f["subj"] else None,
          "obj": tuple(f["obj"]) if f["obj"] else None, "dir": f["dir"]}
    return {"frame": fr, "conf": d["conf"], "ok4": d["ok4"], "ok5": d["ok5"],
            "forced_echo": d["forced_echo"]}


def gold_of(r):
    g = r["gold"]
    return {"act": g["act"], "rel": g["rel"],
            "subj": tuple(g["subj"]) if g["subj"] else None,
            "obj": tuple(g["obj"]) if g["obj"] else None, "dir": g["dir"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tok = L.WordPiece(SNAP + "/vocab.txt")
    D = json.loads(ROWS.read_text(encoding="utf-8"))
    cal = D["panels"]["cal"]["rows"]
    chspans_of = {}
    for r in cal:
        _, ch = tok.encode(r["text"], 96)
        chspans_of[r["n"]] = ch

    # brake with V1 allow-list only (ignore any V2 committed later)
    v1_allow = set(B.FUNCTION_WORDS_V1)
    real_allow = B.ALLOW_WORDS
    B.ALLOW_WORDS = v1_allow
    try:
        blocked_correct = []   # (n, text, level, leftover words)
        correct_total = {"ensemble": 0, "single": [0, 0, 0]}
        for r in cal:
            g = gold_of(r)
            ch = chspans_of[r["n"]]
            ps = [parse_of(r, s) for s in range(3)]
            v, fr = S.verdict_ensemble(ps, TAU_ENS)
            if v == "EXECUTE" and g["act"] == "STATE" and S.same_frame(fr, g):
                correct_total["ensemble"] += 1
                blk, _, lo = B.leftover_blocks(r["text"], fr, ch)
                if blk:
                    blocked_correct.append({"n": r["n"], "text": r["text"],
                                            "level": "ensemble",
                                            "leftovers": sorted(set(lo))})
            for s in range(3):
                vs, frs = S.verdict_single(ps[s], TAU_SINGLE[s])
                if vs == "EXECUTE" and g["act"] == "STATE" and S.same_frame(frs, g):
                    correct_total["single"][s] += 1
                    blk, _, lo = B.leftover_blocks(r["text"], frs, ch)
                    if blk:
                        blocked_correct.append({"n": r["n"], "text": r["text"],
                                                "level": f"single-{4701 + s}",
                                                "leftovers": sorted(set(lo))})
        # wrong writes at tau=0
        wrong_rows = {"ensemble": [], "single": [[], [], []]}
        for r in cal:
            g = gold_of(r)
            ch = chspans_of[r["n"]]
            ps = [parse_of(r, s) for s in range(3)]
            v, fr = S.verdict_ensemble(ps, 0.0)
            if v == "EXECUTE" and fr is not None and fr["act"] in WRITE_ACTS \
                    and not S.same_frame(fr, g):
                blk, _, lo = B.leftover_blocks(r["text"], fr, ch)
                wrong_rows["ensemble"].append({"n": r["n"], "text": r["text"],
                                               "blocked": blk,
                                               "leftovers": sorted(set(lo))})
            for s in range(3):
                vs, frs = S.verdict_single(ps[s], 0.0)
                if vs == "EXECUTE" and frs is not None and frs["act"] in WRITE_ACTS \
                        and not S.same_frame(frs, g):
                    blk, _, lo = B.leftover_blocks(r["text"], frs, ch)
                    wrong_rows["single"][s].append({"n": r["n"], "text": r["text"],
                                                    "blocked": blk,
                                                    "leftovers": sorted(set(lo))})
    finally:
        B.ALLOW_WORDS = real_allow

    offend = Counter()
    for b in blocked_correct:
        offend.update(b["leftovers"])
    # candidate additions: leftover words in blocked-correct rows that never
    # appear in ANY cal wrong row's leftover set (so adding them cannot unblock
    # a wrong write)
    wrong_lo_words = Counter()
    for w in wrong_rows["ensemble"]:
        wrong_lo_words.update(w["leftovers"])
    for s in range(3):
        for w in wrong_rows["single"][s]:
            wrong_lo_words.update(w["leftovers"])
    safe_adds = sorted([w for w in offend if w not in wrong_lo_words])
    risky = sorted([(w, c) for w, c in offend.items() if w in wrong_lo_words])

    out = {
        "scope": "CAL ONLY (n=%d)" % len(cal),
        "allow_list": "FUNCTION_WORDS_V1 only",
        "correct_exec_total": correct_total,
        "blocked_correct_n": len(blocked_correct),
        "blocked_correct": blocked_correct,
        "offending_words_in_blocked_correct": dict(offend),
        "wrong_at_tau0": {
            "ensemble": {"n": len(wrong_rows["ensemble"]),
                         "blocked": sum(1 for w in wrong_rows["ensemble"] if w["blocked"])},
            "single": [{"seed": 4701 + s, "n": len(wrong_rows["single"][s]),
                        "blocked": sum(1 for w in wrong_rows["single"][s] if w["blocked"])}
                       for s in range(3)],
        },
        "wrong_leftover_word_counts": dict(wrong_lo_words.most_common(40)),
        "proposed_safe_additions": safe_adds,
        "risky_offenders_also_in_wrong": risky,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"correct_total": correct_total,
                      "blocked_correct_n": len(blocked_correct),
                      "offend": dict(offend.most_common(30)),
                      "wrong_ens": out["wrong_at_tau0"]["ensemble"],
                      "wrong_single": out["wrong_at_tau0"]["single"],
                      "safe_adds": safe_adds, "risky": risky}, indent=1))
    print("WROTE", a.out)


if __name__ == "__main__":
    main()
