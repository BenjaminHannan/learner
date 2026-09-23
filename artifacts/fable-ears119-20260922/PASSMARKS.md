# PASSMARKS — Exp 119: ears length/distribution coverage (Muse PREP)

Written and hashed **before any registered run** (smoke included: the 50-update
Mac smoke runs only after the seal). Artifact dir:
`artifacts/fable-ears119-20260922/`. Design doc:
`design/v3/30-modes/119-ears-length-coverage-muse.md`. Date: 2026-09-22.

## 0. The one change vs exp 47 (diagnosis refs: docs 95 §1, 107)

Exp 47 trained on all WebRED-train rows, but at MAX_LEN 96 with short synthetic
rows while real sentences are ~4x longer (WebRED web-positive median 134 chars
vs CAL 35). On long real text confidence collapses (1,494/1,806 below 0.3) and
relations go wrong (38.8% match; SimpleWiki raw exact 9/11/10). The ONE CHANGE:
(a) MAX_LEN 96 -> **192**, covering **99.372%** of WebRED-train
(81,005/81,517) and **99.9995%** of the SimpleWiki86 corpus sentences
(199,999/200,000; the single over-long row is 304 tokens) under SciBERT
WordPiece (measured 2026-09-22, Mac CPU, sealed snapshot below); the SimpleWiki
corpus is `data/open/simplewiki86` (sentences.jsonl), NOT the reading94 panel.
(b) The 60k synthetic pool rows keep 47's generator + POOL_SEED stream (same
facts) but are lengthened with appended distractor clauses to target lengths
sampled uniform-over-rows from the WebRED-train token-length histogram
(empirical distribution; capped at 190). Appending never moves gold char
spans; a clause is kept only if `flags_of()` is unchanged.
Everything else is 47 verbatim: SciBERT encoder, FrameEars head, 517 classes,
hearsay augmentation p=0.10, 2 epochs, batch 32, AdamW lr 3e-5 cosine, wd
0.01, clip 1.0, bf16 on CUDA, freeze 0, CAL golden-section temperatures, 47
tau rule (tau0 -> tau_exec = 1-(1-tau0)/2, ensemble + singles).

## 1. Fixed recipe (all sealed)

- Encoder: `allenai/scibert_scivocab_uncased`, snapshot
  `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1` (same as 47) + our `FrameEars`
  head, N_REL=517 (`fable_ears47_data.CLASSES`, imported read-only).
- Pool (`fable_ears119_data.py --build-pool`, runs on BensPC): 60k
  length-matched synth (RNG_LEN stream 11900) + all WebRED-train
  span-reachable rows at MAX_LEN 192. Identity gates (else prep FAILs, no
  seed trains): synth rows == 60,000; kept total >= 140,903 (47's kept;
  a wider window must drop less); dropped <= 614; median token length of
  the lengthened synth in [38, 48] (WebRED-train median 41).
- Seeds **11901, 11902, 11903**; steps = 2 * ceil(kept/32) (forecast
  ~8,810-8,850 vs 47's 8,808). BensPC work dir `C:\Users\benja\ears119\`.
- Temperatures: `fit_temperatures` (golden-section) on the sealed exp-47 CAL
  panel (`artifacts/fable-ears47-20260921/panels/cal.json`), same as 47.
- Thresholds: 47 §4 rule on CAL (ensemble tau0/tau_exec + per-seed singles).
- Panel scoring (`fable_ears119_score.py --score47/--score-panel`): 47
  `is_correct`/verdict definitions; reading94 triple match = exp-106
  normaliser (direction ignored, missing object -> "").

## 2. The marks (per seed, never averaged; verdict = ALL gated marks pass)

Carried exp-47 marks (ensemble verdicts), SEEN corrected per doc 95 §2
(executable = STATE-gold with concrete non-OPEN/UNSURE relation; t_seen
executable = **654**, asserted in the scorer; bar = ceil(0.90*654) = **589**):

- **SAFE:** silent wrong writes over t-seen+t-new+t-trap+t-hard = **0**.
- **NEG:** wneg STATE-only EXECUTE writes / 2,092 <= **2 %**.
- **SEEN:** t-seen correct >= **1,940/2,000** AND executable STATE rows
  correctly EXECUTED >= **589/654**.
- **NEW:** t-new correct >= **2,400/3,000** AND STATE correctly EXECUTED >=
  **784** (bar reachable per doc 95; unchanged).
- **NAMES:** t-hard correct >= **300/500**.
- **ASK:** wrong EXECUTED questions on t-seen+t-new <= **25**.
- **WEB:** wclosed (n=46) executed >= **28** AND exact >= **85 %** of executed.
- **NEWREL:** wnewrel EXECUTE with a concrete seen relation / 1,500 <= **1 %**.
- **ECHO** (recorded only): echoed wrong writes over the 6,500 <= 65.
- **Exp-118 leftover brake:** `artifacts/fable-brake118-20260922/RESULTS.md`
  was ABSENT at seal time — sealed WITHOUT it (no 118 gate applies).
- **W1:** wclosed ensemble executed >= **23/46** AND silent wrong writes = **0**.
- **W2:** reading94 panel (held-out; 400 sentences / 312 triples / 245
  NO_FACT), per seed at its own tau_exec_single: correct writes >= **30**
  AND wrong writes <= **5 %** of writes (writes > 0 required), in **>= 2/3
  seeds**.
- **W3:** reading94 raw exact STATE frames (ungated single decode, strict 106
  match) >= **3x exp-107**: 11901 >= **27**, 11902 >= **33**, 11903 >= **30**
  (positional vs 4701/4702/4703 = 9/11/10), in **>= 2/3 seeds**.
- **T-CLOCK** (recorded only, not gated): 3-seed wave (first training step to
  last score write, excl. file copies) < **2700 s**; forecast ~30-42 min,
  confidence MEDIUM (anchor: 47 measured 14.8/7.9/7.9 min/seed at width 96
  static padding; 119 pads per-batch dynamically to ~batch max, so FLOPs are
  comparable; first-seed compile + longer tail rows are the stated risk).

Exp verdict = PASS iff SAFE ∧ NEG ∧ SEEN ∧ NEW ∧ NAMES ∧ ASK ∧ WEB ∧ NEWREL ∧
W1 ∧ W2 ∧ W3. A registered FAIL is recorded as FAIL, never re-run into a pass.

## 3. Pre-registered deviations

1. No Qwen practice sentences (same as 47 §2.13).
2. Per-batch dynamic padding in the trainer (masked compute is mathematically
   identical; keeps the wave in budget at width 192). Step count, order RNG,
   schedule grid, loss all unchanged.
3. MAX_LEN/encode overrides live in `fable_ears119_data.py` (D.MAX_LEN = 192,
   `_wp_encode` default); 47/109 files untouched.
4. Mac smoke (seed 11900, 50 updates, discarded) is not a registered seed; it
   proves loss falls WITH long rows and the eval path runs.
5. `panel.jsonl` is copied to BensPC for scoring ONLY, never for
   training/tuning/calibration.
6. Exp-118 brake absent at seal (see §2); no 118 gate applies.

## 4. Predictions

P119.1–P119.6 in `artifacts/fable-predictions-ledger.md`, appended before the
run (see that file).
