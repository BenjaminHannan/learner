# Experiment 60 — results (registered wave, 2026-09-22): DICT FAILS, saturation penalty fixes the scalar

**Result first: D1 FAIL (DICT 0/3 exact), D4 FAIL (selector confident on both sides in only 1/3 seeds),
D2/D3 reported (SIGNED-SAT 1/3 fully exact incl. 512; control 3/3 exact everywhere incl. 512), D5 PASS.**

Seal verified before the run (SEAL.sha256.txt OK; PASSMARKS.md untouched). 9 trainings ran sequentially
(file mtimes interleave exactly with per-run train_seconds: 672.7 s compute over ~11.5 min wall, OMP=1,
Mac CPU). Sealed eval = HARD=1 reads, 100 fresh inputs/skill/length, 12 lengths x 6 skills = 72 cells.

## Per-seed table (exact = acc 1.00)

| seed | DICT sealed /72 | DICT failing cells | DICT 512 | SAT sealed /72 | SAT failing | SAT 512 | CTL sealed | CTL 512 |
|---|---|---|---|---|---|---|---|---|
| 6001 | 56/72 | OP1 (ROTL1) lens 7-64, OP3 (SWAP) lens 7,9,11,12,16,32,64 | 4/6 (OP1,OP3 0.00) | 71/72 | OP3@32 (0.02) | 5/6 (OP3 0.00) | 72/72 | 6/6 |
| 6002 | 66/72 | OP1 lens 10,11,12,16,32,64 only | 5/6 (OP1 0.00) | 71/72 | OP3@32 (0.01) | 5/6 (OP3 0.00) | 72/72 | 6/6 |
| 6003 | 58/72 | OP1 lens 9-64, OP3 lens 7,9,11,12,16,32,64 | 4/6 (OP1,OP3 0.00) | 72/72 | none | 6/6 | 72/72 | 6/6 |

OP0=REV, OP1=ROTL1, OP2=INC3, OP3=SWAP, OP4=FOLD, OP5=REV+INC1. Control is exact in all 216 sealed
cells + 18 probe cells. SIGNED-SAT seed 6003 is the first random-init arm ever fully exact incl. 512.

## Audit tables

DICT selector p(flip) per counter (8 counters; p(stay)=1-p):

| seed | p(flip) | > 0.9 (flip) | p(stay) > 0.9 |
|---|---|---|---|
| 6001 | .37,.26,.38,.32,.51,.26,.28,1.00 | 1 | 0 (max .74) |
| 6002 | 1.00,.10,.09,1.00,.55,.55,.69,.58 | 2 | 2 (.90,.91) |
| 6003 | .36,.35,.34,.36,.31,.36,.84,1.00 | 1 | 0 (max .69) |

SIGNED-SAT lams (tanh w): 6001: -1.00,.99,1,1,-1,-1,-1,-1; 6002: 1,1,-1.00,1,1,-1.00,1,1;
6003: -1.00,-1.00,-1.00,1.00,-1.00,-1.00,-1.00,-1. All |lam| >= 0.9996, both families every seed.

## Marks

- D1 FAIL: 0/3 DICT seeds all-exact <= 64 (need 3/3). Recorded as FAIL, never re-run.
- D2: SIGNED-SAT reported — 6003 72/72 + 6/6 at 512; 6001/6002 fail only SWAP@32 and SWAP@512. No mark.
- D3: control reported — 3/3 seeds 72/72 + 6/6 at 512. No mark; reference only.
- D4 FAIL: 1/3 DICT seeds have both p(flip) > 0.9 and p(stay) > 0.9 (need 3/3). The selector sits
  near 50/50 on most counters — the unsaturated trap moved one level up, as doc 65 section 4 warned.
- D5 PASS: 672.7 s train compute (~11.5 min sequential wall, verified) + seconds of eval compute
  (timed replica: 0.4 s/seed), far under 30 min. SIGNED-SAT kept (trainings never exceeded 30 min).

## Deviations

1. The previous agent ran the 9 trainings; I verified sequentiality from mtimes + train_seconds
   (each completion gap matches the next run's train time) and ran the sealed eval myself.
2. eval60.json mtime (~23:00) reflects session latency between my inspection steps, not compute:
   a timed single-seed replica of the identical code path takes 0.4 s, so eval compute is ~4 s total.

## Reproduce

From `scripts/`: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 FABLE43J_C=4 FABLE43J_K=2`;
`FABLE60_ARM=dict|signedsat|control ... python -B fable_counter60_dict.py --stage base --seed 600{1,2,3}
--out ../artifacts/fable-counter60-20260921/runs/$arm` (one at a time); then `FABLE43J_HARD=1 ...
python -B fable_counter60_eval.py --runs ../artifacts/fable-counter60-20260921/runs`.
Single changes live in `scripts/fable_counter60_dict.py` (DictCounter.cases + sat_penalty loss line).

## What it means / What it does not mean

It means the fixed {I, FLIP} dictionary fails worse than the scalar it was meant to rescue (0/3 vs
exp 59's 0/3, but DICT breaks two skills from train lengths while the scalar broke one only under
hardening), because the softmax selector repeats the saturation failure instead of fixing it; and it
means the one-line saturation penalty works — both lam families saturated in 3/3 seeds and produced
a fully exact random-init seed (6003 to 512). It does not mean dictionaries are dead (entries were
fixed here; learned dense matrices per doc 57 remain untested), and it does not touch the control:
43K-v2 is exact to 512 digits in 3/3 fresh seeds again.
