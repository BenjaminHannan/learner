# RUN CARD R1, stage 1: Muon against AdamW on village data (DRAFT, NOT SEALED)

Drafted 2026-10-20 from `R1-STAGE1-BID.md` and the coordinator's 10-20 rulings:
- lr option (i), both arms at 1e-3;
- F is set by the sealed rule below, not a number. F_MAX = 7.5e15 (spec §9.7's ~3-epoch limit), F_min = 3.15e15;
- **one job, one box, one cap of $2.80 in total.** The box builds once and runs the 1a timing, then the sealed
  `price`. 1b starts on its own, only if the gate passes and F ≥ F_min. Otherwise the job exports and stops, and the
  box is destroyed after the pull;
- $0 GO on P1–P3;
- booking only after P1–P3 pass review, this card is sealed, and a re-quote is done;
- the seal hash and the quote go to the coordinator before booking, and `PRICE.json` (with its sha256) as 1b starts;
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
- **F, stage 1b's FLOP budget, set by a rule fixed now (accepted by the coordinator) and applied on the box by the
  sealed runner's `price`:**
  - **The budget for 1b** is the smaller of two amounts: 0.8 × the 1b stop of $2.50 ($2.00), and the $2.80 cap less
    the dollars already spent.
    - Spent = the box seconds so far × the box's $/h.
    - The box seconds are the job's elapsed time plus a 900 s pre-job allowance for the image pull and the start.
  - **F** is the largest value in [F_min = 3.15e15, F_MAX = 7.5e15] whose projected 1b cost fits that budget.
    - It is rounded down to two significant figures, and never below F_min.
    - F_MAX is about 3 passes over the train cache (7.5e15 / 1.14e12 FLOPs per step × 48.9k tokens ≈ 322M tokens,
      ≈ 3.0 × 106.6M).
  - **The projected 1b box time** is built from stage 1a's measurements on the same box. Per run it is:
    - steps at F × that arm's measured s/step;
    - plus (⌊steps/500⌋ + 1) evaluations × the measured seconds per evaluation;
    - plus the start-up with the caches already built (the faster arm's).

    The per-run figure is summed over 3 seeds × 2 arms, and 900 s of copy-off is added. The build and the caches are
    already paid in 1a, so they are not counted again.
  - **`price` writes `PRICE.json`** every time, with "go" and the reason. It exits 0 for go, 3 when 1a's gate fails,
    and 4 when even F_min does not fit.
  - **The sealed 1b run reads F only from `PRICE.json`**, and every run is bound to its sha256. Before running, it
    checks the file. It must have:
    - this runner's rule;
    - go;
    - F in [F_min, F_MAX];
    - 1a's gate met;
    - a projection within $2.00;
    - spent + projected within $2.80.
  - **`price` takes only 1a runs** made by `run --timing` with this runner, card and package.
  - **Why a rule and not a number:** D's GPU seconds per step have never been measured, so no honest F can be priced
    before stage 1a.
  - **Measured here (CPU FLOP fit, 200 batches of the build):**
    - FLOPs per step: 0.64e12 gold, 0.86e12 teacher, 1.28e12 own; 1.14e12 over the curriculum.
    - Batches carry about 48.9k tokens.
    - So F_MAX is about 6,560 steps per run, and F_min about 2,760.
- **Machine:** one Vast RTX 5090, on-demand, never interruptible, reliability ≥ 0.98.
- **Runner:** `scripts/premonition_steals_r1_stage1.py`, run unchanged from the sealed version.
  - It refuses a sealed directory whose seal does not match its own hash or the card's.
  - It refuses `--unsealed` or `--flop-budget` in a sealed directory.
  - It refuses to reuse a run made with other settings, code or data.
  - Each run is bound by content hash to the runner, the card, and premonition/, learnlab/ and memorylab/. The commit is
    recorded, not binding.

## The job: one box, one cap of $2.80 (`scripts/claude_r1s1_rent.py`, stage `1ab`)
1. **Build** the village once (`build`).
2. **1a, the timing** (`run --timing`):
   - unsealed, in `out/1a`, seed 0, both arms;
   - the card's settings at F_1a = 300 × 1.14e12 ≈ **3.4e14** (about 300 steps per arm);
   - it gives each arm's s/step, s per evaluation and start-up on this GPU.
3. **`price`** (the sealed rule above) writes `out/1b/PRICE.json` and prints its sha256 in the log, which goes to
   the coordinator as 1b starts.
   - **Gate:** Muon's s/step ≤ 1.25 × AdamW's, so that wall-clock does not swallow the comparison. D's s/FLOP is
     reported.
   - If the gate fails or even F_min does not fit, the job exports and stops ("GATE"). The box is then destroyed
     after the pull, and that is reported.
4. **1b, the card:** six runs at F in the sealed directory `out/1b` (`run --price`), then the manifests and the
   export.
5. **The controller:**
   - **The run's deadline** counts from the instance's billing start: 0.9 × the hours the $2.80 cap buys at the
     box's $/h, minus 15 minutes for the export and a 900 s pre-job allowance. Outputs are therefore exported before
     the stop. `pack` refuses a box where that deadline cannot cover the build, 1a and an hour of 1b.
   - **Stops:** it stops the box only on the closing DONE, FAIL or GATE mark, which is printed after the export. It
     also stops it at the $2.80 hard stop, and when `waitlog` times out; that limit is never shorter than the box's
     deadline.
   - **Pull:** it reads the export, checkpoints included, from the stopped box (vread2's route).
   - **Destroy:** only after every file passes its sha256 check.
   - **`create`** sends only with `--yes`, which is Ben's click. It refuses an offer dearer than the pack's $/h, and
     when it cannot read the instance list for the duplicate check.

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
