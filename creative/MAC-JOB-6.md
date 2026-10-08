# Mac job 6: C2b DEV pilot (B2 s100 and s101, CPU, DEV only)

Roadmap decision 10-07 (section 7). N = the stepping-stone parent (job 5's SS arm, rebuilt with the same seed and rows from job 5's warm4.pt). DEV only. `test` and `labelled` are never opened; `pool` is the sleep pool. Never delete a checkpoint. Times in ET.

What one process does per parent (all disclosed; the roadmap thread owns every decision):
1. Pool temperature: DEV gate on N over T in {0.5, 0.7, 1.0, 1.4, 2.0, 3.0, 4.0, 6.0} (4.0 and 6.0 widen the grid once). T = best DEV reach@32 among temperatures that pass sameness (>= 4 distinct rule-following programs).
2. N samples the 1,024 pool questions 32 times at T (plain, no mask, repeats kept). Arms: W = tries that fit every example (<= 2 distinct per question); R = tries that fail the example check (same questions, same count); H = R's tries relabelled with what they compute on the shown examples; PC = the kind's reference solver program for W's questions (same count). The corrupt-every-key test rebuilds W, R, H and PC with every answer key corrupted and requires identical records (`leak_test` in the json).
3. Sleep dose chosen on DEV with PC only: lr {3e-4, 1e-3} x visits {4, 8, 16}, updates = visits x records / 32, pooled-5 skills harm vs N <= 2 points; pick = best DEV pooled greedy first try (fits AND right), then reach@4; frozen for every arm.
4. PC FEASIBILITY GATE: PC minus N greedy first try (fits and right), pooled on DEV, >= +15 points. If it misses, this parent STOPS and reports (`stop`, `pc_gate`); do not retry.
5. W, R, H at the frozen dose, the same updates for every arm. For N and every arm on DEV: greedy first try (fits, right) per kind and pooled, reach@4 and reach@32 (32 plain samples with repeats at T), the practised-kind check (256 fresh add/mult at T=1.0), pooled-5 skills harm vs N, plus paired-bootstrap 95% intervals for W-N and W-R and the per-kind label ("PASS, near-copy kinds only" if the pooled gain is carried by square and last_digit alone).
6. Night 2 (REPORT ONLY): W's model samples the pool again at T, sleeps again on its new hits (same dose), and reports per-kind reach@32 and first try.

## 1. Update the code
```
cd <your worktree for this repo> && git fetch origin claude/project-thread-2zeaoc && git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c2_real && python3 -m creative.tests.test_stones && python3 -m creative.tests.test_c2_pilot
```
All must end with ok lines (a few minutes). If one fails, stop and send the output.

## 2. Run (one process per parent; the two can run side by side)
```
for S in 100 101; do
  mkdir -p ~/creative/c2pilot-s$S && cp ~/creative/c2dev-s$S/dev_floors.json ~/creative/c2pilot-s$S/
  OMP_NUM_THREADS=4 nohup python3 -m creative.c2_pilot \
    --ckpt ~/creative/ckpt/B2_s$S.pt --warmed ~/creative/c2stones-s$S/warm4.pt --out ~/creative/c2pilot-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl --skills-data ~/custom-io/work/data_big --device cpu \
    > ~/creative/c2pilot-s$S.log 2>&1 &
done
```
(`--warmed` is job 5's warm4.pt; if it is missing the warm-up is re-made. The floors copy avoids recomputing them.) Estimate (untested, from jobs 4 and 5): N rebuild about 10 min, 8-temperature gate about 30 min, pool sampling about 15 min, dose grid (6 PC sleeps of 172-750 updates plus evals and skills scores) about 2-3 h, then PC, W, R, H and night 2 about 1.5-2 h: 4-6 h per parent, longer if both share the CPU. The log prints a line per stage; `c2_pilot.json` is saved after every stage and ends with `DONE` or a `stop` reason.

## 3. Send back (json and logs only, never checkpoints)
```
mkdir -p creative/results/c2pilot
for S in 100 101; do cp ~/creative/c2pilot-s$S/c2_pilot.json creative/results/c2pilot/s$S.json; cp ~/creative/c2pilot-s$S.log creative/results/c2pilot/s$S.log; done
git add creative/results && git commit -m "creative: C2b DEV pilot results s100 s101" && git push origin HEAD:claude/project-thread-2zeaoc
```
Do not retry other settings on a miss. Report any step that ran past its estimate.
