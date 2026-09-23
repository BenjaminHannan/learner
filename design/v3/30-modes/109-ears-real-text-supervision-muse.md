# 109 — Ears real-text supervision PREP (Muse; GPU wave launched by Claude)

Status: PREP complete on Mac CPU. No BensPC GPU job started here; the 3-seed
wave, calibration, and panel scoring are specified exactly for Claude.
PASSMARKS sealed (`69644d…06e4`); predictions P109.1–P109.6 in the ledger.

## 1. Goal (one sentence)

Give the GPU wave everything it needs to test whether rung-2 ears trained with
real-text supervision — same SciBERT + FrameEars architecture as exp 47, gate
calibrated on real WebRED text instead of synthetic CAL — read the 400-sentence
real Wikipedia panel better than the 9–11/312 raw-exact of exp 107.

## 2. Premise correction (verified, not assumed)

The work order said rung 2 "was trained only on template/synthetic sentences".
The sealed exp-47 record contradicts this: pool = 60,000 synth + all WebRED
train (registered-log: kept=140903 dropped=614; RESULTS §1). The relation
classes already contain all 481 WebRED-train Wikidata names, and WebRED
negatives already train NO_FACT. So the honest ONE CHANGE is narrower: keep
that mix and those labels, move CALIBRATION (temperatures + gate) from the
synthetic CAL to a sealed real-text WebRED-dev split, and measure on the
held-out panel. Nothing else moves (same encoder, head, recipe, seeds differ).

## 3. Data (builder: `scripts/fable_ears109_data.py`)

- Pool rebuild (`--build-pool`, runs on BensPC): same generator functions,
  same POOL_SEED+7 stream, same tokenizer as 47, plus a panel-overlap filter.
  Identity gate: kept=140903, dropped=614, excluded=0 — else prep FAILs and no
  seed trains.
- Calibration split (`--build-cal`, sealed): ALL of WebRED dev, 3,898 rows
  (1,806 pos / 2,092 neg) with gold47 labels; sha in PASSMARKS §1. Disjoint
  from training by split construction.
- Overlap audit (Mac, no model): WebRED train∩panel = 0 sentences,
  dev∩panel = 0, panel = 400/312/245 as specified. Caveat: 40/3,898 cal rows
  (1.0%) are exact (sentence, relation, label) duplicates of train rows — a
  property of the published WebRED splits. Bias direction: slightly
  optimistic gate (seen surfaces score higher conf), i.e. anti-conservative
  for recall marks, conservative for safety marks. Stated, not hidden.
- Label audit: all 481 train-occurring Wikidata names already in the 517
  classes → label set NOT extended (a second change). Verified, in RESULTS.
- Alias table (secondary view only): `{"country": "located in the
  administrative territorial entity"}` — the single mapping with direct
  exp-107 evidence; everything else identity. Sealed sha in PASSMARKS.

## 4. Training + calibration + scoring (all sealed in PASSMARKS)

- `fable_ears109_train.py`: 47's loop verbatim (2 epochs, batch 32, lr 3e-5
  cosine, bf16, freeze 0 → 8,808 steps/seed), seeds 10901–10903, asserts the
  recipe and CUDA, fits temps on calwebred, prints step-200 tokens/s.
- `fable_ears109_score.py --calibrate`: per-seed tau_op = min-conf of the
  largest cal prefix with wrong/k ≤ 0.05 (most-correct wins ties); +inf if
  none. `--score-panel`: R1 raw exact ≥ 94 (≥2/3 seeds); R2 NO_FACT EXECUTE
  writes ≤ 25 (3/3); R3 ≤ 5% wrong AND ≥ 30 correct (≥2/3); R4 template
  correct within 5 pts of sealed 47 singles (all 6); R5 wave < 1800 s.
- Panel is copied to BensPC for scoring ONLY (pre-registered deviation D4).

## 5. Mac smoke (the only training on the Mac; discarded)

100 updates, real SciBERT fp32, 96 short rows (all WebRED-train): loss
22.16 → 5.52 (step 50) → 4.76; full-subset 22.88 → 2.88. Eval path runs on
20 panel sentences ("runs" only, no scores). 0.707 s/step.

## 6. Timing (R5)

Anchor on 47's GPU measurements (same recipe/hardware): 0.054–0.108 s/step,
full seeds 14.8/7.9/7.9 min. 109 = same 8,808 steps/seed → training ≈ 24–31
min + calibrate/score ≈ 3–6 min → wave ≈ 27–37 min vs the 30-min bar.
Confidence LOW-MEDIUM: passes only if every seed holds the fast rate and
seeds launch back-to-back. Forecast P109.5 = 0.55 stands as written.

## 7. Forecasts (ledger, before the run)

P109.1 R1 ≥94 in ≥2/3 (0.15 — needs 9× the 47 baseline). P109.2 R2 3/3
(0.40). P109.3 R3 ≥2/3 (0.25 — exp 107 found 0 correct at ≤5% for 47 ears).
P109.4 R4 all 6 (0.70 — same mix). P109.5 R5 (0.55). P109.6 overlap = 0
(0.90 — resolves TRUE in PREP).

## 8. What this does and does not claim

Does: whether WebRED-calibrated rung-2 ears read real sentences better while
holding template behaviour. Does not: that any panel number transfers to
papers, that the gate is optimal, or that the ears "understand" anything.
A registered FAIL stops the line per PASSMARKS §2.
