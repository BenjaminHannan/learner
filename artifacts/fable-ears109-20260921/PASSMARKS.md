# PASSMARKS — Exp 109: ears real-text supervision (Muse PREP)

Written and hashed **before any registered run**. Artifact dir:
`artifacts/fable-ears109-20260921/`. Design doc:
`design/v3/30-modes/109-ears-real-text-supervision-muse.md`.
Date: 2026-09-22.

## 0. Premise correction (from the sealed exp-47 record, not a new claim)

Exp 47 did NOT train on synthetic sentences only: its sealed pool was 60,000
synth + all WebRED train (registered-log: kept=140903 dropped=614; RESULTS §1:
"2 passes over 140,903 practice sentences (60,000 made-up + all WebRED
training rows)"). The ONE CHANGE in exp 109 is therefore: keep that same
training mix (rebuilt identically, plus a panel-overlap filter) and the same
517 relation classes, but fit temperatures AND the gate operating point on a
sealed real-text WebRED-dev split disjoint from training, and measure success
on the held-out reading94 panel (400 sentences / 312 gold triples / 245
NO_FACT), which is never trained, tuned, calibrated, or picked-checkpoints on.

## 1. Fixed recipe (all sealed)

- Architecture + encoder: SAME as exp 47 — SciBERT
  (`allenai/scibert_scivocab_uncased`, snapshot
  `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1`) + our `FrameEars` head,
  N_REL=517 (`fable_ears47_data.CLASSES`, imported read-only).
- Pool: `fable_ears109_data.py --build-pool` = 60k synth (POOL_SEED 47100,
  hearsay augmentation p=0.10) + all WebRED-train span-reachable rows MINUS
  panel-overlapping rows. Identity gate: kept=140903, dropped=614,
  excluded=0 (exp 47's sealed values). If the rebuild differs, prep FAILs and
  no seed trains.
- Seeds **10901, 10902, 10903**; 2 epochs, batch 32, AdamW lr 3e-5 cosine,
  wd 0.01, clip 1.0, bf16 autocast on CUDA, freeze 0 → 8,808 steps/seed.
  BensPC work dir `C:\Users\benja\ears109\`.
- Temperatures: `fit_temperatures` on `calwebred.json` (ALL of WebRED dev:
  3,898 rows = 1,806 pos + 2,092 neg; sha256
  `0842a465c3005e3ddce6c7b6780c63f3523ca1abf9d755fdd2707fe60a58c97f`).
- Operating point tau_op per seed (`fable_ears109_score.py --calibrate`):
  decode calwebred; candidate writes = frame act ∈ {STATE,RETRACT}, ok4+ok5,
  no forced echo; gold = 106-normalised (relation, subj-span, obj-span) triple
  for positives, empty set for negatives; rank by conf desc; among prefixes
  with wrong/k ≤ 0.05 pick the one with most correct (ties → larger k);
  tau_op = that prefix's min conf; conf ≥ tau_op writes. No qualifying prefix
  or zero candidates → tau_op = +inf (writes nothing).
- Panel scoring (`--score-panel`): single-seed `verdict_single` at the seed's
  own tau_op; triple match = exp-106 normaliser (casefold/strip/collapse-ws,
  direction ignored, missing object → ""); correct write = triple ∈ the
  sentence's gold set (≤ 1 correct per sentence; recall denominator 312).
- Alias view (SECONDARY, UNREGISTERED): repeat R1/R3 with the predicted
  relation mapped through `relation_aliases.json`
  (`{"country": "located in the administrative territorial entity"}`, sha256
  `2ab3413da8c5305316cfbe9dd7cb8656a369094f66f9de1fab4813a43c3b6754`;
  every other name maps to itself). Reported only, never gated.

## 2. The marks (per seed s ∈ {10901, 10902, 10903}, never averaged)

- **R1:** raw exact-correct frames (ONE ungated `S47.decode` per sentence,
  STATE frames only, strict 106 match) ≥ **94** of the 312 gold facts in
  **≥ 2/3 seeds**.
- **R2:** EXECUTE writes (seed tau_op) on the 245 NO_FACT sentences ≤ **25**
  **in 3/3 seeds** (ECHO is not a write).
- **R3:** at the seed's WebRED-calibrated tau_op: panel wrong writes ≤ **5 %**
  of writes AND ≥ **30** correct writes, in **≥ 2/3 seeds**. Zero writes →
  FAIL (via the ≥ 30 clause); wrong-rate reported null, never 0%.
- **R4:** exp-47 `t_seen`/`t_new` single-seed `correct` (same `is_correct`
  definition, scored at the seed's own tau_op) drops by ≤ **5** points vs the
  sealed exp-47 numbers, positionally 10901→4701, 10902→4702, 10903→4703 —
  in all 6 comparisons:

  | seed | t_seen base | t_seen bar | t_new base | t_new bar |
  |---|---|---|---|---|
  | 10901 | 1953 | ≥ 1948 | 2658 | ≥ 2653 |
  | 10902 | 1956 | ≥ 1951 | 2645 | ≥ 2640 |
  | 10903 | 1954 | ≥ 1949 | 2680 | ≥ 2675 |

- **R5:** 3-seed wave (first training step to last score write, excluding file
  copies) < **1800 s** wall-clock on the RTX 5070 Ti.
- Exp verdict = PASS iff R1 ∧ R2 ∧ R3 ∧ R4 ∧ R5 all pass. A registered FAIL is
  recorded as FAIL, never re-run into a pass.

## 3. Pre-registered deviations

1. Training rows come from WebRED **train.jsonl only** (the brief lists
   {train,dev} as sources; dev is reserved as the calibration split so the
   gate stays disjoint from training, per the brief's own rule).
2. The relation label set is NOT extended: the prep audit verifies every
   Wikidata name occurring in WebRED train is already one of the 517 classes
   (extending it would be a second change). Result in RESULTS.md.
3. Mac smoke (seed 10900, 100 updates, discarded checkpoint) is not a
   registered seed; it proves loss falls and the eval path runs.
4. Scoring may run on BensPC (checkpoints live there); `panel.jsonl` is copied
   there for scoring ONLY, never for training/tuning/calibration.
5. R4 compares correct-counts across different gates (47's CAL tau vs 109's
   WebRED tau_op): the gate is part of the one change, stated here.

## 4. Predictions

P109.1–P109.6 in `artifacts/fable-predictions-ledger.md`, appended before the
run (see that file).
