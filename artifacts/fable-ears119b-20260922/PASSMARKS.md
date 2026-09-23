# PASSMARKS — Exp 119b: ears relation-namespace remap retrain (Muse PREP)

Written and hashed **before any registered run** (audit + Mac smoke run only
after the seal). Artifact dir: `artifacts/fable-ears119b-20260922/`. Design
doc: `design/v3/30-modes/119b-ears-remap-muse.md`. Date: 2026-09-22.
Reading94 is untouched: the remap was built only from training sources
(WebRED frames relations.json + WebRED-train sentences + SimpleWiki86
training sentences); no panel sentence was used (see remap.json).

## 0. The one change vs exp 119 (diagnosis ref: doc 119d, ranked fix 1)

On 312 real reading94 triples the 119 ears got the relation wrong 224 times
(top: "located in ..." -> country 80; demonym+job -> citizenship; birth/death
dates swapped), exact 0; real text W2 = 0 writes on 3/3 seeds. The ONE CHANGE:
training-label relation remap, closed list (remap.json, identical REMAP dict
in `fable_ears119_data.py` -> `fable_ears119b_data.py`):

- `country` -> `located in the administrative territorial entity`
- `city` -> `located in the administrative territorial entity`
- `birthplace` -> `place of birth`
- `job` -> `occupation`

Span-preserving renames only; every target is a registered 517-class name.
Documented exclusions (NOT remapped, with reasons in remap.json): country of
citizenship (spans differ), birth/death swap (contextual), capital direction,
contains-inverse, other out-of-inventory relations. Everything else is 119
verbatim: MAX_LEN 192, lengthened 60k synth (same RNG_LEN stream 11900),
all WebRED-train rows, SciBERT + FrameEars, 517 classes, 2 epochs, batch 32,
AdamW lr 3e-5 cosine, wd 0.01, clip 1.0, bf16 on CUDA, freeze 0, CAL
temperatures, 47 tau rule, seeds **11911, 11912, 11913** (119's 11901-11903
renamed; same recipe, same scorer).

## 1. Fixed recipe (all sealed)

- Encoder: `allenai/scibert_scivocab_uncased`, snapshot
  `24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1` (same as 47/119) + our
  `FrameEars` head, N_REL=517 (`fable_ears47_data.CLASSES`, imported
  read-only).
- Pool (`fable_ears119b_data.py --build-pool`, runs on BensPC): 60k
  length-matched synth (RNG_LEN stream 11900) with remapped golds + all
  WebRED-train span-reachable rows at MAX_LEN 192 with remapped golds.
  Identity gates (else prep FAILs, no seed trains): synth rows == 60,000;
  kept total >= 140,903; dropped <= 614; median token length of the
  lengthened synth in [38, 48].
- Seeds **11911, 11912, 11913**; steps = 2 * ceil(kept/32) (forecast
  ~8,810-8,850). BensPC work dir `C:\Users\benja\ears119b\`.
- Temperatures: `fit_temperatures` (golden-section) on the sealed exp-47 CAL
  panel (`artifacts/fable-ears47-20260921/panels/cal.json`), same as 47/119.
- Thresholds: 47 §4 rule on CAL (ensemble tau0/tau_exec + per-seed singles).
- Panel scoring (`fable_ears119_score.py --score47/--score-panel`, unchanged):
  47 `is_correct`/verdict definitions; reading94 triple match = exp-106
  normaliser (direction ignored, missing object -> "").

## 2. The marks (per seed, never averaged; verdict = ALL gated marks pass)

Copied verbatim from `artifacts/fable-ears119-20260922/PASSMARKS.md` §2 (seed
ids 11901/11902/11903 renamed 11911/11912/11913; positional W3 bars follow
their seeds). Carried exp-47 marks (ensemble verdicts), SEEN corrected per
doc 95 §2 (executable = STATE-gold with concrete non-OPEN/UNSURE relation;
t_seen executable = **654**, asserted in the scorer; bar = ceil(0.90*654) =
**589**):

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
  was ABSENT at 119 seal time — sealed WITHOUT it (no 118 gate applies).
- **W1:** wclosed ensemble executed >= **23/46** AND silent wrong writes = **0**.
- **W2:** reading94 panel (held-out; 400 sentences / 312 triples / 245
  NO_FACT), per seed at its own tau_exec_single: correct writes >= **30**
  AND wrong writes <= **5 %** of writes (writes > 0 required), in **>= 2/3
  seeds**.
- **W3:** reading94 raw exact STATE frames (ungated single decode, strict 106
  match) >= **3x exp-107**: 11911 >= **27**, 11912 >= **33**, 11913 >= **30**
  (positional vs 4701/4702/4703 = 9/11/10), in **>= 2/3 seeds**.
- **T-CLOCK** (recorded only, not gated): 3-seed wave (first training step to
  last score write, excl. file copies) < **2700 s**; forecast ~30-42 min,
  confidence MEDIUM (same anchor as 119).

Exp verdict = PASS iff SAFE ∧ NEG ∧ SEEN ∧ NEW ∧ NAMES ∧ ASK ∧ WEB ∧ NEWREL ∧
W1 ∧ W2 ∧ W3. A registered FAIL is recorded as FAIL, never re-run into a pass.

## 3. Falsifier (doc 119d ranked-fix-1 clause; scored by the director)

After the remap, relation-wrong on the diagnosis panel stays >= **50 %** of
non-exact triples -> the head, not the labels, is at fault. Scored with
`scripts/fable_ears119d_diagnose.py` on seed **11911** (buckets_312:
relation-wrong / (312 - exact) >= 0.50). At 119d baseline the rate was
224/312 = 71.8 % (seed 11901); the remap must move it below half.

## 4. Pre-registered deviations

1. No Qwen practice sentences (same as 47 §2.13, 119 D1).
2. Per-batch dynamic padding in the trainer (same as 119 D2).
3. MAX_LEN/encode overrides plus REMAP live in `fable_ears119b_data.py`
   (47/109/119 files untouched).
4. Mac smoke (seed 11910, 50 updates, discarded) is not a registered seed;
   it proves loss falls WITH remapped labels and the eval path runs.
5. `panel.jsonl` is copied to BensPC for scoring ONLY, never for
  training/tuning/calibration (same as 119 D5).
6. Exp-118 brake absent at seal (same as 119 D6); no 118 gate applies.
7. Label audit (200 random training-source rows, no encoder) runs after the
   seal; it reports pair counts only, no threshold or model decision.

## 5. Predictions

P119b.1–P119b.7 in `artifacts/fable-predictions-ledger.md`, appended before
the run (see that file).
