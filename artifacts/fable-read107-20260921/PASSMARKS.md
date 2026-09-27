# PASSMARKS — Exp 107: reading behind the gate (DIAGNOSTIC, sealed before any inference)

Date: 2026-09-22 · dir: `artifacts/fable-read107-20260921/` · selector:
`scripts/fable_read107_behind_gate.py` (new file, prefix `fable_read107_`;
imports the sealed rung-2 decoder + exp-106 loading/scoring code read-only,
never edited). Inference only, Mac CPU, no training, no notebook writes.
This is a MEASUREMENT ONLY: no gates, no pass/fail claim about the ears.

Test gold: `data/open/reading94/panel.jsonl` (400 hand-labelled held-out
Simple English Wikipedia sentences: 155 with >= 1 in-inventory triple,
312 triples over 48 relations; 245 NO_FACT). Rung-2 ears seeds 4701/4702/4703
(checkpoints `artifacts/fable-ears47-20260921/runs/c-<seed>/ear.pt`,
SciBERT snapshot from the HF cache). Every seed reported separately,
never averaged.

## 0. Raw frame (fixed definition)

Per sentence/seed, the single UNGATED decode (`S47.decode`) is the raw
reading. A raw STATE frame = `frame["act"] == "STATE"`, regardless of
confidence, brakes, or verdict. Confidence = `parse["conf"]` (the same
min-of-softmaxes score the gate uses). Triples via the exp-106 normaliser
(casefold/strip/collapse-whitespace on relation/subject/object; direction
ignored; missing object → "").

## 1. What will be measured (per seed 4701/4702/4703, integers)

- M1: every raw STATE frame scored vs that sentence's gold triple set:
  (a) exact-correct (normalised triple is a member of the gold set);
  (b) relation-right-but-span-wrong (gold non-empty, normalised relation
  matches some gold triple's relation, triple not exact);
  (c) wrong relation (gold non-empty, relation matches none);
  (d) invented (gold set empty, NO_FACT sentence). a+b+c+d = # raw STATE.
- M2: confidence distribution of correct (a) vs wrong (b+c+d) frames:
  decile cut points (10th..90th percentiles) + min/max + counts per 0.1 bin;
  plus the best achievable operating point: sweep thresholds over conf,
  rank frames high→low, report the largest #exact-correct with
  wrong/(correct+wrong) <= 1% and <= 5% (threshold, correct, wrong, total).
  Descriptive only; the certified gate stays as sealed.
- M3: top 15 wrong (non-exact) STATE frames verbatim (highest conf first:
  sentence, predicted triple, gold, conf); top 10 proposed relations on
  real text (counts) vs top 10 gold relations (counts over 312 triples).
- M4: the same four M1 counts restricted to the 87 sentences rung-1 could
  not encode (toy-vocab `D1.encode` returns None; reproduced with the
  exp-106 code path, seed 4301's rng; asserted == 87 before scoring).
- Also recorded: raw act histogram (STATE/NO_FACT/UNSURE/ASK/RETRACT/?)
  per seed; # sentences with no raw STATE frame.

## 2. Predictions P107.1–P107.4 (ledger, before the run)

- P107.1 (0.95): raw STATE counts replay exp 106 exactly: 276 / 306 / 288
  for seeds 4701 / 4702 / 4703. Falsified by any different count.
- P107.2 (0.70): exact-correct raw STATE frames <= 20 per seed (<= 20/312
  recall behind the gate). Falsified by any seed with >= 21 exact.
- P107.3 (0.60): at <= 5% wrong, the best operating point yields <= 10
  correct in every seed. Falsified by any seed with >= 11 correct at <= 5%.
- P107.4 (0.70): invented frames are the majority of raw STATE frames in
  every seed (> 50% of raw STATE on the 245 NO_FACT sentences' share).
  Falsified by any seed with invented <= 50% of its raw STATE frames.

## 3. Run rule

One registered run: `scripts/fable_read107_behind_gate.py --snapshot
<scibert-snapshot> --out artifacts/fable-read107-20260921/fable_read107_results.json`.
Mac CPU, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B …`. No thresholds are changed or certified here.
