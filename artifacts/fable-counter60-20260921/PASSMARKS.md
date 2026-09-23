# Experiment 60 PASSMARKS (sealed BEFORE the registered wave, 2026-09-22)

Spec: doc 65. Three arms, 3 seeds each (6001/6002/6003): DICT (fixed {I, FLIP}
dictionary + learned 2-way selector, s_c ~ N(0,1)), SIGNED-SAT (exp-59 scalar +
0.01*(1-lam^2) loss penalty), CONTROL (43K-v2 unchanged, balanced start). Train
lengths 4-12 only (43K-v2 wide data). Sealed eval: per-seed exact-match
(accuracy == 1.00) per skill (OP0=REV, OP1=ROTL1, OP2=INC3, OP3=SWAP, OP4=FOLD,
OP5=REV+INC1) on lengths {4,5,6,7,8,9,10,11,12,16,32,64} with HARD=1 reads
(100 fresh inputs per skill per length, same RNG as the rig eval), plus a 512
probe (20 inputs per skill, report only, never gates). Selector probs logged
for every DICT seed; lams for every SIGNED-SAT seed.

- D1: DICT 3/3 seeds exact on all 6 skills at every length <= 64. Gate: PASS
  iff 9/9 (3 seeds x 3 length-bands {4-12, 16, 32, 64}) all-exact; one non-exact
  cell = FAIL, recorded as FAIL, never re-run into a pass.
- D2: SIGNED-SAT reported per seed, same table plus lam audit. No mark.
- D3: CONTROL reported per seed, same table. No mark; reference only.
- D4 selector audit: every DICT seed has >= 1 counter with p(flip) > 0.9 AND
  >= 1 counter with p(stay) > 0.9. Gate: PASS iff 3/3 seeds.
- D5: whole wave (9 trainings + eval) < 30 min wall-clock, run sequentially
  (one training process at a time), OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, Mac
  CPU. If 9 trainings exceed 30 min, drop SIGNED-SAT and record it.

Reproduce: export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 FABLE43J_C=4 FABLE43J_K=2;
for s in 6001 6002 6003; do for arm in dict signedsat control; do
FABLE60_ARM=$arm uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B fable_counter60_dict.py --stage base --seed $s --out
../artifacts/fable-counter60-20260921/runs/$arm; done; done (all from
scripts/, one training at a time); then FABLE43J_HARD=1 ... python -B
fable_counter60_eval.py --runs ../artifacts/fable-counter60-20260921/runs.

## What it means / What it does not mean

It means the bar for the dictionary replacement is fixed before seeing data:
exact everywhere <= 64 in all 3 DICT seeds, both selector families confident in
every seed, the saturation-penalty arm and the control reported but unmarked.
It does not mean a PASS proves the idea general (3 seeds, one rig,
position-clock parity only) or that a FAIL kills dictionaries generally (the
selector could still sit at 50/50 — that is what D4 distinguishes).
