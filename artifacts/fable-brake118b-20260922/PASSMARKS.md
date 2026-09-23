# PASSMARKS — Exp 118b: train-list leftover brake (registered single-change follow-up to exp 118)

Written and hashed BEFORE any exp-118b scoring run. Single change only: the
allow-list inside the exp-118 leftover brake. No retraining, no model re-run
on sealed panels (cached exp-95 rows recomputed with new verdicts), no edits
to any existing file (all `fable_brake118b_*`). Mac CPU only.

Date: 2026-09-22 · artifact dir: `artifacts/fable-brake118b-20260922/`
Checkpoints (read-only): `artifacts/fable-ears47-20260921/runs/c-470{1,2,3}/ear.pt`
Rows (read-only cache): `artifacts/fable-diag95-20260921/fable_diag95_rows.json`
Sealed taus (REUSED unchanged — the allow-list is the only change):
ensemble tau_exec = 0.8766039311885834;
singles = 0.9483702182769775 / 0.8766039311885834 / 0.9547552053165873.

## 1. The one change

Exp 118's brake (`leftover_blocks`: a write is refused when alphabetic words
fall outside the frame's subject/value char spans, the allow-list, and the
predicted relation's cue words) is kept EXACTLY — V1
(`FUNCTION_WORDS_V1`, closed-class English, by code reuse) and the relation
cue-word rule (`_cue_words_for_rel`, code tables only) are byte-identical
imports. The ONLY delta: the CAL-tuned V2 list (11 words) is replaced by
TRAIN_FRAMING_V2 — 2618 words from the exp-47 TRAINING pool (the sentences the
ears were trained on, regenerated with `fable_ears47_data`: 60,000 synth rows
+ WebRED train rows; pool identity gate reproduces the BensPC pool exactly:
kept=140903 dropped=614). A word is allowed iff it appears OUTSIDE the gold
subject/value char spans in ≥ K training sentences AND inside a gold VALUE
span in < J of the sentences containing it (the relation is a class label with
no char span, so spans = subject + value; span-less NO_FACT/UNSURE rows count
every word as outside).

Fixed on CAL only (no test-panel reads): **K = 50, J = 0.01 (1%)**,
list size **2618**, sha256
`60a4450ef450f364d99f07c180a5dec71f2165388da1a8413e829f3743ad8cb8`
(`fable_brake118b_wordlist.txt`). Selection rule over the K×J grid
(K ∈ {3,5,10,20,30,50}, J ∈ {0.01,0.02,0.05}), CAL only: max blocked-wrong at
tau=0, then min blocked-correct at sealed taus, then smaller list, then
aside-free, then larger K / smaller J. Winner K50_J0.01: blocked-wrong
260/273 at tau=0; blocked-correct 425/2359 correct-execute instances at sealed
taus (residual offenders: "one" 242 — excluded by the J-filter since "one"
sits inside gold VALUE spans in 384/5344 = 7.2% of training occurrences — and
"mind" 187 — only 31 outside-span training occurrences, below K=50).
CAL wrong writes AT the sealed taus: 0 exist with or without the brake
(0/0, vacuous — the tau=0 stress view is 260/273; 118's was 269/273).
"aside" (33/33 outside-span training occurrences) is NOT in the winner list
(it enters every K≤30 list); the two "aside" trap sentences must not write —
B1 decides. Diff vs 118's V2 (`fable_brake118b_listdiff.json`): +2609 words,
−2 words (`mind`, `one`).

## 2. Marks

- **B1 (gated SAFE):** silent wrong writes over t_seen+t_new+t_trap+t_hard
  (6,500) = **0** in the ensemble AND in each single seed at its own tau.
  Trap items written reported per seed/ensemble.
- **B2 (gated, still clean):** wneg STATE-only EXECUTEs = 0, wrong executed
  ASK over t_seen+t_new = 0, wnewrel wrong-seen-relation EXECUTEs = 0 —
  ensemble and every single (same counting as 118).
- **B3 (gated, coverage recovery):** SEEN exec_correct_stmt and NEW
  exec_correct_stmt each drop ≤ 10% vs exp 47's sealed no-brake numbers, in
  the ensemble (singles reported). Bars: SEEN 455 → ≥ 410; NEW 640 → ≥ 576.
  (118 managed 191 / 79 with the CAL-tuned list.)
- **B4 (gated, time):** whole registered scoring invocation < 10 min wall-clock
  on Mac CPU (`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`).

## 3. Predictions (P118b.1–P118b.5, appended to ledger before the run)

See ledger block. Falsified by the integers in `fable_brake118b_results.json`.

## 4. Reproduce (exact commands)

Pre-seal (training pool + CAL only, already run):
`python -B scripts/fable_brake118b_trainlist.py --out
artifacts/fable-brake118b-20260922/fable_brake118b_trainlist.json`
`python -B scripts/fable_brake118b_tune.py --out
artifacts/fable-brake118b-20260922/fable_brake118b_tune_cal.json`
Registered (after seal):
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_brake118b_score.py --out
artifacts/fable-brake118b-20260922/fable_brake118b_results.json`
(all with the `export ... ; uv run ...` prefix; Seal: `shasum -a 256
artifacts/fable-brake118b-20260922/PASSMARKS.md > .../SEAL.sha256.txt`)
