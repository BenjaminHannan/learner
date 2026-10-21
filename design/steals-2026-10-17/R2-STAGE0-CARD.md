# RUN CARD R2, stage 0: `fetch_gate` on the far-fact toy (SEALED before the run; amended and re-sealed 10-20, twice)

**Third amendment, 10-20, under the coordinator's GO for the fix round, before any run on real settings.**
- Scoring now refuses runs that were not made under this seal by this runner, card and package. It also refuses runs
  made under different torch versions, and A1 runs whose gate readouts are missing.
- DID NOT TRAIN keeps its SMOKE / UNSEALED labels.
- A run is saved before its gate readouts are taken.
- A run with no real loss counts as DID NOT TRAIN.
- A sealed directory refuses off-card settings.
- The package hash is the sha256 of `PACKAGE.sha256`, a `sha256sum`-checkable file list kept beside the seal.

**Second amendment, 10-20, under the coordinator's ruling "SIMPLIFY", before any run on real settings.** The extension
is removed: exactly seeds 0–2, verdict on 3 seeds. Runs are bound by content hash (runner, card, package), not the
commit; the package hash is in the seal; unsealed runs are labelled UNSEALED. A log line can no longer fail before its
run is saved, every run's settings are checked, the decoder gate is read once on real answer positions, and only
`--score` writes `result.json`. This is stricter than before, and no card run has happened.

**Amendment, 10-20, under the coordinator's ruling, before any run on real settings.** A focused review found three
blocking problems in the first seal (3b31d19a5): "at chance" ignored chance, G3 read the preloaded path, and the
extension rule was not enforced. The fixes are below, and the card was re-sealed. The only runs before the
amendment were 8-step plumbing smokes, outside the sealed directory.


Written 2026-10-20, before any R2 training. It carries the card in `REPORT.md` ("RUN CARD R2", with its blanks
filled by Q43) and fixes the remaining operational details. It is approved under the coordinator's 10-20 ruling:
$0, CPU in this cloud container, run after R1 stage 0, after one focused built-in review of the runner and this card.
`SEAL.sha256.txt` in `artifacts/claude-steals-20261017/r2-stage0/` holds three sha256s, taken before the run: this
file's, the runner's, and that of `PACKAGE.sha256` (the package file list beside it).

## Question
Does a per-head sigmoid gate on fetched card values and on the decoder's cross-attention move D's toy answers off
chance, through the cards?

## Arms (one change)
- **A0:** D, tiny preset, every steal flag off.
- **A1:** the same config with `fetch_gate=True`. That adds +1,544 parameters at d = 128 (fewer at the tiny
  preset).

At each seed, every shared weight and the RNG stream are identical between the arms. This is tested in
`PairedInitTest`.

## Setup
- **Each run:** `premonition.train.train_toy("D", steps=1500, seed=s)`. That is the toy's registered setup: AdamW,
  lr 3e-3, warmup 20, 16 visits per batch, and a FLOP budget of about 1,500 batches. The step count lands near
  1,500, not exactly on it.
- **Seeds:** exactly 0, 1, 2. There is no extension: the verdict is on 3 seeds, and any other set of runs is NOT
  SCORED.
- **Runner:** `scripts/premonition_steals_r2_stage0.py`, run unchanged from the sealed version.
  - The seal holds three hashes: this card's, the runner's, and the package's. The package hash is the sha256 of
    `PACKAGE.sha256`, which lists every `premonition/*.py` and `learnlab/**/*.py` file with its sha256 and can be
    checked with `sha256sum -c`. The runner refuses to run if any of the three differs from the current files.
  - A sealed directory takes only the card's settings.
  - Without a seal it runs only with `--unsealed`, and the verdict is labelled UNSEALED. A sealed directory never
    takes `--unsealed`.
  - **Binding:** every run is bound to those three content hashes. The commit is recorded, not binding.
  - **Scoring** (`--score`, which trains nothing, is the only writer of `result.json`) needs:
    - every run to carry the current runner, card and package hashes, and the current seal;
    - each run to be made in the sealed directory;
    - one torch version across all runs;
    - A1's gate readouts present in every A1 run;
    - every run to have the card's settings (1,500 steps, 16 visits).

    If any of the first four fails, the result is NOT SCORED.

    If the settings are off, the verdict is labelled a smoke; if a run was made outside the sealed directory, it is
    labelled UNSEALED.
- **Machine:** CPU. The readout is accuracy, not time, so the arms may run in separate processes.

## Primary readout
Held-out toy answer accuracy with the model's own retrieval: `validate(...)["accuracy"]` on the 4 held-out batches
(seed s + 1000), as `train_toy` scores them. Chance is 6.25%.

d_s = acc(A1, s) − acc(A0, s).

## Bar (all three)
1. mean(d) − 2·SD(d)/√n > 0.
2. mean(d) ≥ 0.03 (3 points).
3. d_s > 0 in at least 2 of the 3 seeds.

## Guards (pooled over the scored seeds)
- **G1, gold-card gain:** mean over seeds of [gold-card accuracy(A1) − gold-card accuracy(A0)] ≥ mean(d). The gain
  must also show when the gold cards are handed in.
- **G2, retrieval:** mean recall@4(A1) ≥ 0.8 × mean recall@4(A0).
- **G3, through the cards:** the mean card gate (sigmoid, all heads) must be ≥ 0.2 on gold-card rows **the model
  fetched itself** in `answer()`, pooled over seeds.
  - This is the path that produces the own-retrieval accuracy.
  - **Fewer than 30 such rows counts as a trip.**
  - Reported, not judged:
    - the gate on preloaded gold cards (`answer_with_gold`);
    - the decoder cross-attention gate, from one teacher-mode pass with 4 fixed loops. It is read once per run, on
      real answer positions only.
  - G2 is unreadable if recall@4 is missing in every run of an arm, and unreadable counts as a trip.

## Verdicts (checked in this order)
1. **DID NOT TRAIN:** any non-finite final training loss, or a run with no training loss at all. This wins over
   every other outcome, but it keeps the SMOKE / UNSEALED labels, and it names any NOT SCORED reasons as well.
2. **GAIN NOT COUNTED (bypassed the cards):** the bar holds and G1 or G3 trips.
3. **NOT COUNTED (retrieval guard G2):** the bar holds, G1 and G3 hold, and G2 trips.
4. **PASS:** the bar, G1, G2 and G3 all hold.
5. **PROVED WRONG:** mean(d) + 2·SD(d)/√n < 0, **or** both arms at chance: in every seed, both arms'
   accuracy ≤ chance + 2 points (≤ 8.25%) **and** |d_s| < 1 point.
6. **NOT SHOWN:** anything else.

A smoke (any run off the card's settings) or an unsealed directory or run labels the verdict ("SMOKE, …",
"UNSEALED: …"). A labelled verdict is never the card's.

## Required rows (per seed and arm, in the JSON)
- steps, seconds, parameters
- final losses (loss, lm, ask, ans, halt)
- accuracy, gold-card accuracy, recall@4 (and random recall@4), asked_rate, loops_mean, halt_rate
- for A1, the gate means per head:
  - card gate on gold rows and on wrong rows, from both `answer_with_gold` and own `answer`
  - the decoder cross-attention gate
- d_s and every guard value (in `result.json`)

## What would prove it wrong
mean(d) + 2·SD(d)/√n < 0, or both arms at chance in every seed (as defined above). The second would mean that
gating is not what stops D's decoder from using its cards.

## Prediction (written before the run, unchanged from the card)
NOT SHOWN, with both arms near chance. P(PASS) ≈ 0.25.

R1 stage 0 found that AdamW-trained D stays at chance on this toy (4–6%). A1 here also trains with AdamW, so a
both-at-chance PROVED WRONG is the most likely single outcome.
