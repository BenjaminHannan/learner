#!/usr/bin/env python3
"""Exp 118b tuning (CAL split ONLY — never touches any test panel).

For each (K,J) candidate list from fable_brake118b_trainlist.json, measures
with allow = V1 + candidates(K,J):
  * blocked-correct: CAL STATE-gold rows the sealed pipeline EXECUTEs correctly
    (ensemble at sealed tau + each single at its own tau) that the brake would
    refuse — want ~0 (B3 allows <=10% drop vs exp-47 sealed numbers).
  * blocked-wrong: CAL wrong writes at tau=0 (ensemble + singles) the brake
    would refuse — want 100%.
  * aside-in-list flag (reported; B1 decides).

Selection rule (registered in PASSMARKS.md before scoring): lexicographic —
(1) blocked_wrong == max over grid; (2) min blocked_correct; (3) smaller list;
(4) aside-free; (5) larger K, then smaller J.

Reads ONLY artifacts/fable-diag95-20260921/fable_diag95_rows.json panels.cal
plus the training-derived candidate JSON (training inputs, not panels).
Tokenizer only (no model weights, no inference).

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_brake118b_tune.py --out \
    artifacts/fable-brake118b-20260922/fable_brake118b_tune_cal.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_score as S  # noqa: E402 (sealed verdict logic, read-only)
import fable_bert_loader as L  # noqa: E402 (tokenizer only)
import fable_brake118_leftover as B  # noqa: E402 (V1 + brake logic, read-only)

SNAP = ("/Users/ben-hannan/.cache/huggingface/hub/models--allenai--"
        "scibert_scivocab_uncased/snapshots/24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1")
ROWS = Path("artifacts/fable-diag95-20260921/fable_diag95_rows.json")
CANDS = Path("artifacts/fable-brake118b-20260922/fable_brake118b_trainlist.json")
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
    cal = D["panels"]["cal"]["rows"]  # CAL ONLY by construction
    cand_data = json.loads(CANDS.read_text(encoding="utf-8"))
    cands = {k: v["words"] for k, v in cand_data["candidates"].items()}

    ch_of = {}
    for r in cal:
        _, ch = tok.encode(r["text"], 96)
        ch_of[r["n"]] = ch

    # sealed verdicts once (independent of the allow-list)
    ens_v, sng_v = {}, {}
    correct_total = {"ensemble": 0, "single": [0, 0, 0]}
    correct_rows = []  # (n, level, text, frame)
    for r in cal:
        g = gold_of(r)
        ps = [parse_of(r, s) for s in range(3)]
        v, fr = S.verdict_ensemble(ps, TAU_ENS)
        ens_v[r["n"]] = (v, fr)
        if v == "EXECUTE" and g["act"] == "STATE" and S.same_frame(fr, g):
            correct_total["ensemble"] += 1
            correct_rows.append((r["n"], "ensemble", r["text"], fr))
        for s in range(3):
            vs, frs = S.verdict_single(ps[s], TAU_SINGLE[s])
            sng_v[(r["n"], s)] = (vs, frs)
            if vs == "EXECUTE" and g["act"] == "STATE" and S.same_frame(frs, g):
                correct_total["single"][s] += 1
                correct_rows.append((r["n"], f"single-{4701 + s}", r["text"], frs))
    # wrong writes at tau=0 (verdicts independent of allow-list)
    wrong_rows = []
    for r in cal:
        g = gold_of(r)
        ps = [parse_of(r, s) for s in range(3)]
        v, fr = S.verdict_ensemble(ps, 0.0)
        if v == "EXECUTE" and fr is not None and fr["act"] in WRITE_ACTS \
                and not S.same_frame(fr, g):
            wrong_rows.append((r["n"], "ensemble", r["text"], fr))
        for s in range(3):
            vs, frs = S.verdict_single(ps[s], 0.0)
            if vs == "EXECUTE" and frs is not None and frs["act"] in WRITE_ACTS \
                    and not S.same_frame(frs, g):
                wrong_rows.append((r["n"], f"single-{4701 + s}", r["text"], frs))
    n_wrong = len(wrong_rows)

    v1 = set(B.FUNCTION_WORDS_V1)
    real_allow = B.ALLOW_WORDS
    results = {}
    try:
        for key, words in sorted(cands.items()):
            B.ALLOW_WORDS = v1 | set(words)
            bc = sum(1 for (n, lv, t, fr) in correct_rows
                     if B.leftover_blocks(t, fr, ch_of[n])[0])
            bw = sum(1 for (n, lv, t, fr) in wrong_rows
                     if B.leftover_blocks(t, fr, ch_of[n])[0])
            results[key] = {"K": int(key.split("_")[0][1:]),
                            "J": float(key.split("_")[1][1:]),
                            "list_n": len(words),
                            "blocked_correct": bc,
                            "blocked_wrong": bw,
                            "n_wrong": n_wrong,
                            "aside_in_list": ("aside" in words)}
    finally:
        B.ALLOW_WORDS = real_allow

    # registered selection: max blocked_wrong, then min blocked_correct,
    # then smaller list, then aside-free, then larger K, smaller J.
    def rank(kv):
        k, r = kv
        return (-r["blocked_wrong"], r["blocked_correct"], r["list_n"],
                int(r["aside_in_list"]), -r["K"], r["J"])
    winner = sorted(results.items(), key=rank)[0][0]

    out = {"scope": "CAL ONLY (n=%d)" % len(cal),
           "allow_list": "FUNCTION_WORDS_V1 + training-pool candidates(K,J)",
           "correct_exec_total": correct_total,
           "n_wrong_at_tau0": n_wrong,
           "grid": results,
           "selection_rule": ("max blocked_wrong, then min blocked_correct, "
                              "then smaller list, then aside-free, "
                              "then larger K, smaller J"),
           "winner": winner,
           "winner_list_n": results[winner]["list_n"],
           "winner_words": cands[winner]}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"correct_total": correct_total, "n_wrong": n_wrong,
                      "grid": {k: {kk: v[kk] for kk in
                               ("list_n", "blocked_correct", "blocked_wrong",
                                "aside_in_list")} for k, v in results.items()},
                      "winner": winner}, indent=1))
    print("WROTE", a.out)


if __name__ == "__main__":
    main()
