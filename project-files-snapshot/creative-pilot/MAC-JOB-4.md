# Mac job 4: C2 DEV cold-start gate (B2 s100 and s101, CPU)

C1 is retired (leave `creative/results/` as is). This is the first C2 run. It reads only the DEV split (256 held-out-kind questions: affine, square, sq_plus, last_digit, double_add). `test`, `pool` and `labelled` stay sealed and are never opened. Never delete a checkpoint. Times in ET.

What it does (all disclosed): (1) the parent sleeps once on 2,048 solver-program rows for the practised kinds add and mult (4 visits, lr 3e-4, skills replay on, same sleep as C1's warm-up); (2) 32 plain samples per DEV question at T in {0.5, 0.7, 1.0, 1.4}, no mask, repeats kept, in sampling order; (3) the gate: reach@32 >= 10% AND >= 3x the value-blind floor, and >= 4 distinct rule-following programs per question. The best temperature by reach@32 is used for the verdict (picked on DEV, which is the tuning split; every temperature is in the file). An untested-by-us detail: value-blind floors use 4,000 random programs per question, so a floor under about 0.03% reads as 0.

## 1. Update the code
```
cd <your worktree for this repo> && git fetch origin claude/project-thread-2zeaoc && git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c2_real && python3 -m creative.tests.test_c2
```
Both must end with ok lines (a few minutes). If one fails, stop and send the output.

## 2. Run (one process per parent; the two can run side by side)
```
for S in 100 101; do
  OMP_NUM_THREADS=4 nohup python3 -m creative.c2_dev \
    --ckpt ~/creative/ckpt/B2_s$S.pt --out ~/creative/c2dev-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl --device cpu \
    > ~/creative/c2dev-s$S.log 2>&1 &
done
```
Estimate (untested): warm-up 256 updates, about 15-30 min; floors about 15-25 min per parent (cached); sampling 4 temperatures x 8,192 samples, about 10-20 min each. Expect 1.5-2.5 h per parent. The log prints a line per temperature and ends with `VERDICT ...`.

Also run the comparison without warm-up (raw parent), once per parent, after the main run:
```
for S in 100 101; do python3 -m creative.c2_dev --ckpt ~/creative/ckpt/B2_s$S.pt --out ~/creative/c2dev-nowarm-s$S --no-warm --device cpu > ~/creative/c2dev-nowarm-s$S.log 2>&1; done
```
Reading the result (no decisions for you): `c2_dev.json` has `verdict`, `best_temperature`, and per temperature `reach32`, `floor_reach32`, `reach4`, `luck`, `distinct_rules`, `by_kind`. Do not retry other settings on a miss: a miss means "cold start (stepping stones first)" or "sameness" per the roadmap and goes back to the roadmap thread.

## 3. Send back (json and logs only, never checkpoints)
```
mkdir -p creative/results/c2dev
for S in 100 101; do for P in c2dev c2dev-nowarm; do cp ~/creative/$P-s$S/c2_dev.json creative/results/c2dev/$P-s$S.json; cp ~/creative/$P-s$S.log creative/results/c2dev/; done; done
git add creative/results && git commit -m "creative: C2 DEV cold-start results s100 s101" && git push origin HEAD:claude/project-thread-2zeaoc
```
Report any step that ran past its estimate.
