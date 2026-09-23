# Experiment 59 PASSMARKS (sealed BEFORE the registered wave, 2026-09-22)

Spec: doc 57 sections 3-5. Two arms, 3 seeds each (5901/5902/5903), train
lengths 4-12 only (43K-v2 wide data). Sealed eval: per-seed exact-match
(accuracy == 1.00) per skill (OP0=REV, OP1=ROTL1, OP2=INC3, OP3=SWAP, OP4=FOLD,
OP5=REV+INC1) on lengths {4,5,6,7,8,9,10,11,12,16,32,64} with HARD=1 reads
(100 fresh inputs per skill per length, same RNG as the rig eval), plus a 512
probe (20 inputs per skill, report only, never gates). Per-counter lam logged
after training for every SIGNED seed.

- C1: SIGNED 3/3 seeds exact on all 6 skills at every length <= 64. Gate: PASS
  iff 9/9 (3 seeds x 3 length-bands {4-12, 16, 32, 64}) all-exact; one non-exact
  cell = FAIL, recorded as FAIL, never re-run into a pass.
- C2: CONTROL (43K-v2 unchanged, balanced start) reported per seed, same table.
  No mark; reference only.
- C3 audit: every SIGNED seed has >= 1 counter with lam < -0.9 (flip found) AND
  >= 1 counter with lam > 0.9 (stay found). Gate: PASS iff 3/3 seeds.
- C4: whole wave (6 trainings + eval) < 30 min wall-clock, run sequentially
  (one training process at a time), OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, Mac CPU.

Falsification (doc 57 section 5), checked and stated in RESULTS.md: proposal
falsified if any seed shows train-length failure on odd/even-dependent skills
(not just long-length decay), or audit finds no counter with lam < -0.9, or the
512 probe fails while 64 passes identically in both arms (readout, not counter).

Reproduce: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 FABLE43J_C=4 FABLE43J_K=2;
for s in 5901 5902 5903; do FABLE59_ARM=signed uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B fable_counter59_signed.py
--stage base --seed $s --out artifacts/fable-counter59-20260921/runs/signed; done
(same with FABLE59_ARM=control and --out .../runs/control); then FABLE43J_HARD=1
... python -B fable_counter59_eval.py --runs artifacts/fable-counter59-20260921/runs
(all from scripts/).

## What it means / What it does not mean

It means the bar for the signed-scalar replacement is fixed before seeing data:
exact everywhere <= 64 in all 3 signed seeds, both counter families auditable in
lam, control reported but unmarked. It does not mean a PASS proves the idea
general (3 seeds, one rig, position-clock parity only) or that a FAIL kills
signed transitions generally (doc 57 escalates to the SD-SSM dictionary, not
back to hand-leaning).
