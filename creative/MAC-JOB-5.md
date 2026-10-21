# Mac job 5: C2 stepping stones (B2 s100 and s101, CPU, DEV only)

Roadmap decision (10-06, after job 4's cold-start stop): C2 goes to stepping stones, not retirement. DEV only. `test` and `labelled` are never opened; `pool` is read only for the report-only PC arm. Never delete a checkpoint. Times in ET.

What one process does per parent (all disclosed):
0. Warm the raw parent (2,048 add/mult solver rows, 4 visits, lr 3e-4, skills replay = job 4's warm-up; this is N). Practised-kind check: 256 FRESH add/mult questions (new salt, none in the warm split), 32 plain samples at T=1.0, reach@32 and first try. If reach@32 < 50%: re-warm with 16 visits, run the plain DEV gate on it; if that passes by itself the run stops with "under-warmed" (C2b would start from it, no stones); otherwise every arm starts from the 16-visit parent.
1. Arms from the base, the same sleep each (4 visits, lr 3e-4, skills replay, 2,048 records = 256 updates): SS = stepping stones (easier variants: affine a=2 or b in {1,2}; sq_plus and double_add with b in {1,2}; x mod k for k in 2..5; reference program <= 3 steps; params in no sealed split; 512 rows per kind); P = placebo (2,048 more fresh add/mult rows); PC = report only (full-difficulty held-out-kind solver programs from the POOL split; the pool has 1,024 questions, so each is used twice as two records).
2. The same DEV gate on N, SS, P, PC: 32 plain samples per question with repeats, no mask, T in {0.5, 0.7, 1.0, 1.4}, widened with 2.0 and 3.0 when the best T is the top edge (job 4's was). Per kind: reach@32, reach@4, luck, distinct rule-following programs; greedy first try (fits / right) per kind. Also recorded: how many DEV questions a stepping-stone rule fits with a different answer (`stones.dev_conflicts`).
The temperature is picked on DEV (tuning split) per arm; every temperature is in the file. The decision rule is fixed in the roadmap and applied by the roadmap thread, not you: SS passes cold start + sameness on BOTH parents -> SS parent is C2b's N; SS misses on either parent -> C2 retires; SS minus P >= +5 points reach@32 is reported (stepping stones, not just more practice); anything else goes back to the roadmap thread. `summary` in the json has the numbers.

## 1. Update the code
```
cd <your worktree for this repo> && git fetch origin claude/project-thread-2zeaoc && git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c2_real && python3 -m creative.tests.test_stones
```
Both must end with ok lines (about 2 min). If one fails, stop and send the output.

## 2. Run (one process per parent; the two can run side by side)
```
for S in 100 101; do
  OMP_NUM_THREADS=4 nohup python3 -m creative.c2_stones \
    --ckpt ~/creative/ckpt/B2_s$S.pt --out ~/creative/c2stones-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl \
    --floors ~/creative/c2dev-s$S/dev_floors.json --device cpu \
    > ~/creative/c2stones-s$S.log 2>&1 &
done
```
(`--floors` reuses job 4's value-blind floors; if that file is missing it computes them again, about 20 min.) Estimate (untested, from job 4): warm-up and check about 40 min, then 4 gate runs (N, SS, P, PC) at about 20-40 min each and 3 sleeps of about 20-30 min each, so about 3-5 h per parent; add about 1.5 h if the 16-visit re-warm and its gate trigger, and about 20 min per gate run if 2.0 and 3.0 are added. The log prints one line per temperature and `SUMMARY` at the end (or `STOP under-warmed`). `c2_stones.json` is saved after every stage.

## 3. Send back (json and logs only, never checkpoints)
```
mkdir -p creative/results/c2stones
for S in 100 101; do cp ~/creative/c2stones-s$S/c2_stones.json creative/results/c2stones/s$S.json; cp ~/creative/c2stones-s$S.log creative/results/c2stones/s$S.log; done
git add creative/results && git commit -m "creative: C2 stepping stones results s100 s101" && git push origin HEAD:claude/project-thread-2zeaoc
```
Do not retry other settings on a miss. Report any step that ran past its estimate.
