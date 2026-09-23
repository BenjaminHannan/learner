# Experiment 59 — results (registered wave, 2026-09-22): FAIL

**Result first: the signed-scalar counter does not replace the balanced start.
C1 FAIL (0/3 signed seeds all-exact under HARD=1; every failure is OP1/ROTL1),
C3 FAIL (flip found 3/3, stay saturated 0/3), C2 control 3/3 exact everywhere
including the 512 probe, C4 PASS (410 s train, sequential, OMP=1).**

Seal verified before the run (SEAL.sha256.txt). 6 trainings, one process at a
time, Mac CPU. Sealed eval = HARD=1 reads, 100 fresh inputs/skill/length.

## Per-seed table (sealed cells: 12 lengths x 6 skills = 72; exact = acc 1.00)

| seed | SIGNED sealed | SIGNED failing cells | SIGNED 512 probe | CONTROL sealed | CONTROL 512 |
|---|---|---|---|---|---|
| 5901 | 65/72 | OP1 at 9,10,11,12,16,32,64 (0.11-0.00) | 5/6 (OP1 0.00) | 72/72 | 6/6 |
| 5902 | 68/72 | OP1 at 5,7,9,11 (0.16-0.00) | 6/6 | 72/72 | 6/6 |
| 5903 | 66/72 | OP1 at 10,11,12,16,32,64 (0.13-0.00) | 5/6 (OP1 0.00) | 72/72 | 6/6 |

OP0=REV, OP1=ROTL1, OP2=INC3, OP3=SWAP, OP4=FOLD, OP5=REV+INC1. Every non-exact
cell in the wave is OP1; the other five skills are exact at every length in all
6 runs. With soft reads (HARD=0, in-training eval) SIGNED is 72/72 + 64 exact
in all 3 seeds — the failure appears only when lam is hardened to +/-1.

## Lam audit (tanh(w), 8 counters: 0-3 forward, 4-7 backward)

| seed | lams | < -0.9 (flip) | > 0.9 (stay) |
|---|---|---|---|
| 5901 | -1.00, 0.73, 0.50, -1.00, -0.57, -0.12, -0.13, -0.10 | 2 | 0 |
| 5902 | 0.69, 0.00, -1.00, -1.00, -0.74, -0.08, -0.08, -0.11 | 2 | 0 |
| 5903 | -1.00, -0.99, 0.76, -0.99, -0.24, -0.13, -0.40, -0.11 | 3 | 0 |

## Marks

- C1 FAIL: 0/3 signed seeds exact at all lengths <= 64 (need 3/3).
- C2: control reported — 3/3 seeds 72/72 sealed plus 6/6 at 512. No mark.
- C3 FAIL: 3/3 seeds have lam < -0.9, 0/3 have lam > 0.9 (need both, 3/3).
- C4 PASS: 410 s wall for 6 trainings + minutes of eval, sequential, OMP=1.

## Falsification (doc 57 section 5), checked

1. Train-length failure on an odd/even-dependent skill: MET under the sealed
   gate — OP1 fails at train lengths 9-12 (5901/5903) and 5,7 (5902). ROTL1 is
   the skill that needs the stay/last-place counter, which never saturated.
2. No counter with lam < -0.9: NOT met — flip found in all 3 seeds.
3. 512 fails while 64 passes identically in both arms: NOT met — 512 fails only
   where 64 already fails (signed 5901/5903); control passes 512 fully. The
   failure is counter/hardening, not readout.
Verdict: the proposal is falsified as a drop-in replacement. Per doc 57, the
escalation is the SD-SSM-style dense-matrix dictionary, not back to hand-leaning.

## Deviations

1. Eval first wrote to `scripts/artifacts/...` (relative `--runs` path while
   running from `scripts/`); moved to the registered folder; per-run stdout
   logs were lost in cleanup — checkpoints, JSONs, eval59.json intact.
2. PASSMARKS reproduce uses `runs/signed` + `runs/control` subdirs (names would
   collide in one dir). No deviation in training, seeds, data, or eval inputs.

## Reproduce

From `scripts/`: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 FABLE43J_C=4
FABLE43J_K=2`; `FABLE59_ARM=signed|control ... python -B
fable_counter59_signed.py --stage base --seed 590{1,2,3} --out
../artifacts/fable-counter59-20260921/runs/{signed,control}`; then
`FABLE43J_HARD=1 ... python -B fable_counter59_eval.py --runs
../artifacts/fable-counter59-20260921/runs`. Single change lives in
`cases()` of `scripts/fable_counter59_signed.py`.

## What it means / What it does not mean

It means the tanh-scalar geometry keeps the flip family (found 3/3 from random
signs, no hand start) but does not pull the stay family to saturation, and the
soft-read solution leans on unsaturated lam values that hardening destroys —
so doc 57's "gradient pushes |lam|->1" prediction was wrong for the stay side.
It does not mean signed transitions are dead (flip worked; the fix is a
saturation-forcing init/loss or the dense dictionary), and it does not touch
the control: 43K-v2 is exact to 512 digits in 3/3 fresh seeds.
