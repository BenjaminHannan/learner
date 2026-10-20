# RUN CARD R1, stage 1: Muon against AdamW on village data (DRAFT, NOT SEALED)

Drafted 2026-10-20 from `R1-STAGE1-BID.md` and the coordinator's 10-20 rulings:
- lr option (i), both arms at 1e-3;
- F = 3.15e16 if it fits the $2.50 stop at the re-quote, otherwise the largest F that fits, fixed before sealing;
- $0 GO on P1–P3;
- booking at most $2.80, only after P1–P3 pass review, this card is sealed, and a re-quote is done;
- the seal hash and the quote go to the coordinator before booking;
- the rental needs Ben's click.

**Nothing here has run on a GPU.** `artifacts/claude-steals-20261017/r1-stage1/SEAL.sha256.txt` will hold three
sha256s:
- this file;
- the runner;
- the package (`premonition/*.py`, `learnlab/**/*.py`, `memorylab/**/*.py`, by path and content).

## Question
At equal training wall-clock on one GPU, does Muon (Moonshot's RMS-matched recipe, at AdamW's lr) give D a lower
held-out village loss than AdamW, without giving up retrieval?

## Arms (one change)
- **A0:** D, full preset (d = 128, 2,130,516 parameters with the v2 tokenizer, as counted on the build below),
  every steal flag off.
  `train.train_d` with AdamW at lr 1e-3.
- **A1:** the same, with `optimizer="muon"` (`muon.MuonAdamW`: Muon on the hidden matrices, AdamW elsewhere), lr 1e-3.

At a seed both arms are bit-identical at init and read the same batches in the same order. The FLOP charge depends
only on the batches and the curriculum, so the step counts are equal. This is tested by `PairedInitTest` and by the
P1 test. Scoring checks it again: if the arms of a seed differ in steps or FLOPs, the result is NOT SCORED.

## Setup
- **Data:** the step-1 village build, `large` (100,000 train visits, 1,000 validation visits), seed 0, and the v2
  tokenizer (`data/tokenizer/premonition-tok-v2.json`, git-tracked). Each run records:
  - the data tag (it includes the writer digest);
  - the tokenizer sha256;
  - the name-detector digest.

  All six runs must share them. The build is generated on the box by `premonition_steals_r1_stage1.py build`.
  - **Measured here on CPU (4 workers, $0):** 1,239 s, 1.4 GB, tag `large-seed0-e00cd820504d`. The writer digest is
    part of the tag, so a box build that differs shows up as a different tag.
  - **Caches** (106.6M label-free train tokens) and the detector: 102 s more, paid inside the first run.
- **Training:** `train_d` defaults apart from the optimizer:
  - warmup 100, grad clip 1.0, bf16 autocast on CUDA;
  - max_tokens 55,000, max_visits 48, 4 calibration batches;
  - the curriculum: gold 0–5%, teacher 5–30%, own 30–100%;
  - log every 50 steps.
- **Parent:** a paired fresh start.
- **Seeds:** 0, 1, 2. The arm order alternates (A0 then A1 at seeds 0 and 2, A1 then A0 at seed 1). The arms of a seed
  run back to back on the same box.
- **F, stage 1b's FLOP budget, set by a rule fixed now and applied by the sealed runner (`price`):**
  - F is the largest value whose projected stage-1b box time, at the booked box's $/h, costs at most 0.8 × $2.50 =
    $2.00. It is never above 3.15e16, and it is rounded down to two significant figures.
  - The projected box time is built from stage 1a's measurements. Per run, it is:
    - steps at F × that arm's measured s/step;
    - plus (⌊steps/500⌋ + 1) evaluations × the measured seconds per evaluation;
    - plus the start-up with the caches already built (the faster arm's start-up).
  - That per-run figure is multiplied over 3 seeds × 2 arms. Added once on top:
    - the first run's extra start-up, which covers building the caches and the name detector;
    - the measured village build time;
    - 900 s for copy-off.
  - `price` writes `PRICE.json`. It refuses if even F_min = 3.15e15 does not fit.
  - The sealed run reads F only from `PRICE.json`, and every run is bound to its sha256.
  - Before running, the sealed run checks the file. It must have:
    - this runner's rule;
    - F in [3.15e15, 3.15e16];
    - 1a's gate met;
    - a projection within $2.00.
  - The 1b pack refuses a box dearer than the $/h F was priced at.
  - Why a rule and not a number: D's GPU seconds per step have never been measured, so no honest F can be priced
    before stage 1a. **[COORDINATOR]** accept the rule, or name F.
  - **Measured here (CPU FLOP fit, 200 batches of the build):**
    - FLOPs per step: 0.64e12 gold, 0.86e12 teacher, 1.28e12 own; 1.14e12 over the curriculum.
    - Batches carry about 48.9k tokens.
    - So F = 3.15e16 is about 27,560 steps per run, about 1.35B tokens, or **12.6 epochs** of the train cache.
    - Spec §9.7 asks for at most about 3 epochs for the contenders. **[COORDINATOR]** note: at F_max this run repeats
      the data about 4× more than that guidance.
- **Machine:** one Vast RTX 5090, on-demand, never interruptible, reliability ≥ 0.98.
- **Runner:** `scripts/premonition_steals_r1_stage1.py`, run unchanged from the sealed version.
  - It refuses a sealed directory whose seal does not match its own hash or the card's.
  - It refuses `--unsealed` or `--flop-budget` in a sealed directory.
  - It refuses to reuse a run made with other settings, code or data.
  - Each run is bound by content hash to the runner, the card, and premonition/, learnlab/ and memorylab/. The commit is
    recorded, not binding.

## Stages, each gated on the one before
- **1a, a timing smoke, hard stop $0.30.** Unsealed, in its own directory:
  - It runs `run --unsealed --flop-budget F_1a --seeds 0` (both arms).
  - F_1a = 300 × the full preset's mean FLOPs per step on this build: 300 × 1.14e12 ≈ **3.4e14**.
  - It gives each arm's s/step, s per evaluation and start-up on the GPU, and the build time. These are the inputs
    of `price`.
  - **Gate to 1b:** Muon's s/step ≤ 1.25 × AdamW's, so that wall-clock does not swallow the comparison. D's s/FLOP
    is reported.
  - The coordinator gets `PRICE.json` (F, projected $) before 1b starts.
- **1b, the card, hard stop $2.50.** Six runs at F in the sealed directory, then evaluation, the manifest and
  copy-off.
- **Both stages (`scripts/claude_r1s1_rent.py`):**
  - The job's run step has its own deadline: 0.8 × the hours the stop buys at the booked $/h, minus 15 minutes. The
    outputs are therefore exported before the stop.
  - The controller stops the box at DONE or FAIL. It reads the export, checkpoints included, from the stopped box
    (vread2's route).
  - It destroys the box only after every file passes its sha256 check.
  - `create` sends only with `--yes`, which is Ben's click. It refuses an offer dearer than the pack's $/h, and it
    refuses when it cannot read the instance list for the duplicate check.
- **[COORDINATOR]** choose:
  - 1b on the 1a box after your F reply, which saves the build (about 21 minutes) and idles at about $0.45/h
    meanwhile;
  - or 1b on a fresh box.

## Primary readout
- **Held-out village loss:**
  - the weighted training loss `loss`, in teacher mode, with 4 fixed loops;
  - computed in fp32, eval mode, under `no_grad`;
  - on the 256 fixed validation visits that `train_d` evaluates (the first 256 of the build), averaged over visits
    (each batch weighted by its visit count);
  - with the distractor seed of batch i fixed at 1234 + i.
- **Schedule:** it is evaluated every 500 steps and at the end, inside `train_d`'s validation hook (`eval_extra`).
- **Training clock:** the sum of the log windows' seconds. `MiniTrainer.train` moves a window's start past any
  evaluation, so evaluation time is off the clock. A test pins this with deliberate sleeps.
- **T\*** = the shorter arm's training seconds. Each arm's loss is linearly interpolated at T\*.
- **d_s** = loss(A0, T\*) − loss(A1, T\*).

## Bar (all three, Q42's loss rule)
1. mean(d) − 2·SD(d)/√3 > 0.
2. d_s > 0 in at least 2 of 3 seeds.
3. mean(d) ≥ 3% of A0's mean loss at T\*.

## Guards
- **G-ACC:** A1's final `validate` accuracy (own retrieval, the same 256 visits) is more than 3 points below A0's in
  at least 2 of 3 seeds → trip. **[COORDINATOR]** No village primary score was named, so this uses `validate`
  accuracy, as the bid proposed.
- **G-RET (pass-blocking):** final `validate` gold recall@4. Either of these is a trip:
  - (a) pooled mean recall@4(A1) < 0.8 × pooled mean recall@4(A0);
  - (b) A1 is more than 0.10 below A0 in at least 2 of 3 seeds.

  Recall@4 missing in any run also counts as a trip.

## Verdicts (checked in this order)
1. **DID NOT TRAIN:** any non-finite loss (the final training losses, or any held-out loss). This wins over
   everything below, including the NOT SCORED conditions. When the runs are not the card's either, it says so:
   "DID NOT TRAIN (and not the card's runs: …)".
2. **NOT SCORED:** any of these. Where the arms pair up, the numbers are still written, as "would be":
   - the directory is unsealed;
   - the seeds are not exactly 0–2, or an arm is missing or repeated;
   - the settings are not the card's;
   - the runs are bound to different code, data or price, or to code other than the sealed runner, card and package;
   - the runs used different torch versions;
   - no `PRICE.json` binds F;
   - a run did not complete, or missed the FLOP budget tolerance;
   - the arms of a seed differ in steps or FLOPs.
3. **NOT COUNTED (retrieval guard):** the bar holds and G-RET trips.
4. **NOT COUNTED (accuracy guard):** the bar holds, G-RET holds, and G-ACC trips.
5. **PASS:** the bar, G-RET and G-ACC all hold.
6. **PROVED WRONG:** mean(d) + 2·SD(d)/√3 < 0.
7. **NOT SHOWN:** anything else.

## Required rows (per seed and arm, in the run JSONs and `RESULT.json`)
- **Run totals:** steps, FLOPs, training seconds, wall seconds, s per training step, and s per step in each log
  window.
- **Losses:** the held-out loss curve with its components (lm, ask, ans, halt), and the final training losses.
- **Final `validate`:** accuracy, accuracy with gold cards, recall@4 and random recall@4, asked_rate, loops_mean,
  and halt_rate.
- **At every evaluation:** accuracy and recall@4.
- **Scoring:** loss at T\*, the equal-step final loss, d_s, and every guard value.
- ms per optimizer step is not measured inside the card's runs: timing it needs a CUDA sync that would perturb the
  clock. The CPU bench (`premonition_steals_muon_bench.py`) and 1a's s/step stand in for it.

## What would prove it wrong
- A1 behind A0 at T\* by more than 2 SE.
- Or a loss gain that G-RET voids. That would mean Muon buys the answer-path gain by giving up retrieval, which is
  the risk stage 0 hinted at (toy recall@4 about 0.33 under Muon).

## Prediction (a guess, unchanged from the bid)
A1 PASS on loss, with G-RET holding narrowly. P(G-RET trips) ≈ 0.35.
