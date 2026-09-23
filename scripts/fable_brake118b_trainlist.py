#!/usr/bin/env python3
"""Exp 118b — derive the brake allow-list from the exp-47 TRAINING pool.

Reads ONLY training inputs (never any sealed panel):
  * synth training sentences regenerated with the exp-47 data builder
    (fable_ears47_data.synth_pool_rows — the same generator + seeds the ears
    were trained on), with gold char spans from gold_from_synth slots;
  * WebRED train rows (webred_pool_rows — the other half of the ears' pool).
Never touches artifacts/fable-diag95-20260921 (CAL or test panels).

Rule (per brief): a word is allowed if it appears OUTSIDE the gold
subject/value spans in >= K training sentences and inside a gold VALUE span
in < J fraction of the sentences containing it. ("Relation" has no char span
in the frame schema — the relation is a class label — so spans = subject +
value/object char spans. Span-less rows, e.g. NO_FACT/UNSURE golds, have every
word outside by definition.)

Word tokenisation is byte-identical to the brake (regex
[A-Za-z]+('[A-Za-z]+)?, possessive stripped, lowercased, len >= 2).

Output: JSON with per-word counts + candidate lists for a K,J grid.
K,J themselves are fixed by fable_brake118b_tune.py on CAL only.

Run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_brake118b_trainlist.py --out \
    artifacts/fable-brake118b-20260922/fable_brake118b_trainlist.json [--limit N]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_ears47_data as D  # noqa: E402 (training-pool builder, read-only)
import fable_brake118_leftover as B118  # noqa: E402 (V1 set + word regex, read-only)

SNAP = ("/Users/ben-hannan/.cache/huggingface/hub/models--allenai--"
        "scibert_scivocab_uncased/snapshots/24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1")

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

K_GRID = (3, 5, 10, 20, 30, 50)
J_GRID = (0.01, 0.02, 0.05)


def words_of(text):
    out = []
    for m in _WORD_RE.finditer(text):
        w = m.group(0).casefold()
        if w.endswith("'s"):
            w = w[:-2]
        if len(w) < 2:
            continue
        out.append((w, m.start(), m.end()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    import fable_ears47_encoder as ENC
    _, tok, _ = ENC.load(SNAP)

    rng = random.Random(D.POOL_SEED + 7)
    synth_rows = D.synth_pool_rows(tok, rng)
    webred_rows = list(D.webred_pool_rows())
    if a.limit:
        synth_rows = synth_rows[:a.limit]
        webred_rows = webred_rows[:a.limit]

    # Identity gate vs the BensPC training pool (registered-log: kept=140903
    # dropped=614 with no --qwen). encode_row filters identically.
    n_in = n_sent = n_drop = 0
    n_sent_total = n_drop_total = 0
    per_word_sent = Counter()   # sentences containing w
    per_word_out = Counter()    # sentences where w appears outside gold spans
    per_word_inval = Counter()  # sentences where w appears inside gold VALUE span
    train_items = []  # (text, subj_span|None, val_span|None)

    def add_training(text, subj, val):
        for w, ws, we in words_of(text):
            pass  # counted below per sentence set
        seen, out, inval = set(), set(), set()
        for w, ws, we in words_of(text):
            seen.add(w)
            in_subj = subj is not None and ws < subj[1] and we > subj[0]
            in_val = val is not None and ws < val[1] and we > val[0]
            if in_val:
                inval.add(w)
            if not in_subj and not in_val:
                out.add(w)
        for w in seen:
            per_word_sent[w] += 1
        for w in out:
            per_word_out[w] += 1
        for w in inval:
            per_word_inval[w] += 1

    for row in synth_rows:
        n_sent_total += 1
        e = D.encode_row(row, tok)
        if e is None:
            n_drop_total += 1
            continue
        g = row["gold47"]
        subj = tuple(g["subj"]) if g.get("subj") else None
        val = tuple(g["obj"]) if g.get("obj") else None
        add_training(row["text"], subj, val)
        n_in += 1
    for row in webred_rows:
        n_sent_total += 1
        e = D.encode_row(row, tok)
        if e is None:
            n_drop_total += 1
            continue
        subj = tuple(row["subj_chars"]) if row.get("subj_chars") else None
        val = tuple(row["obj_chars"]) if row.get("obj_chars") else None
        add_training(row["text"], subj, val)
        n_in += 1

    v1 = set(B118.FUNCTION_WORDS_V1)
    stats = {}
    for w, ns in per_word_sent.items():
        stats[w] = {"n": ns, "out": per_word_out.get(w, 0),
                    "inval": per_word_inval.get(w, 0)}
    cands = {}
    for k in K_GRID:
        for jj in J_GRID:
            lst = sorted(w for w, ns in per_word_sent.items()
                         if w not in v1
                         and per_word_out.get(w, 0) >= k
                         and per_word_inval.get(w, 0) / ns < jj)
            cands[f"K{k}_J{jj}"] = lst

    out = {"scope": "TRAINING POOL ONLY (exp-47 builder; no panel reads)",
           "pool_identity": {"synth_n": len(synth_rows),
                             "webred_n": len(webred_rows),
                             "kept": n_in, "dropped": n_drop_total,
                             "expect_kept": 140903, "expect_dropped": 614,
                             "limited": bool(a.limit)},
           "n_words": len(stats),
           "word_stats": stats,
           "candidates": {k: {"n": len(v), "words": v}
                          for k, v in cands.items()},
           "spot": {w: stats.get(w, {"n": 0, "out": 0, "inval": 0})
                    for w in ("aside", "write", "just", "know", "fact",
                              "moment", "new", "down", "say", "told")}}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"kept": n_in, "dropped": n_drop_total,
                      "n_words": len(stats),
                      "cand_sizes": {k: len(v) for k, v in cands.items()},
                      "spot": out["spot"]}, indent=1))
    print("WROTE", a.out)


if __name__ == "__main__":
    main()
