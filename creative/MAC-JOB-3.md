# Mac job 3: MASKED DEV pilot (B2 s100 and s101, CPU)

Replaces pilot 2 (plain sampler, now finished: PC gate missed on both parents; keep it as the labelled "plain sampler" comparison and never pool it with this run).
Nothing touches T1, T1b or X. Never delete a checkpoint. Times in ET.

What is new: every try, the temperature choice and the DEV gates now use the level-4 used-number + exact-division mask (`creative/legal.py`, from PR #45; `--level 4` is the default). Warm-up unchanged (1,500 two-number + 1,500 three-number puzzles, 4 visits, skills replay on). Follower floor is now uniform over exact legal programs (4.02% per try on DEV); aim gate = luck / rules_share >= 0.0804; F1 uses B2's PLAIN greedy try (the masked first try and the plain sampler's own rules share are reported beside it for the warmed parent and every PC learning rate); the temperature grid widens down to about 0.09 if the choice lands on the low edge. PC gate unchanged (PC/N >= 1.6 and PC-N >= +3 points) but now judged HERE, on both parents, with the masked sampler at the masked temperature and skills replay on. Pilot 2 stays a labelled plain-sampler comparison, never pooled.

PC dose grid (roadmap decision 10-06, added after the pilot 2 PC miss): lr {3e-4, 1e-3} x visits per record {4, 8, 16} = updates 172 / 344 / 688 (updates = visits x 1,377 / 32). lr 3e-3 and 1e-2 are dropped (they cost skills 9-14 and 50-68 points in pilot 2). The pick is the best masked DEV luck among settings whose pooled-5 skills harm vs the warmed parent is <= 2 points; if the pick lands on 16 visits the pilot tries 32 once (1,376 updates) and re-picks. Then lr and visits are frozen (in T1 every arm uses updates = visits x W's record count / 32).

## 1. Update the code (parents, skills data and earlier tests are in place from jobs 1 and 2)
```
cd <your worktree for this repo> && git fetch origin claude/project-thread-2zeaoc && git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c1 && python3 -m creative.tests.test_c2 && python3 -m creative.tests.test_pilot && python3 -m creative.tests.test_legal
```
All four must end with ok lines (about 6 min). If one fails, stop and send the output.

## 2. Pilot (CPU, one process per parent; the two can run side by side, about 2-4 GB each plus ~1.5 GB replay rows)
```
for S in 100 101; do
  OMP_NUM_THREADS=4 nohup python3 -m creative.cli pilot \
    --ckpt ~/creative/ckpt/B2_s$S.pt --out ~/creative/pilot3-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl \
    --skills-data ~/custom-io/work/data_big --device cpu --level 4 \
    > ~/creative/pilot3-s$S.log 2>&1 &
done
```
Estimate (untested, from pilot 2's 55 min for 375 warm-up + 688 PC updates): the grid is 6 sleeps (2,408 updates in all) plus 6 scored evals with the extra plain-sampler reports, so expect 3-4.5 h per parent (about an hour more if 32 visits is tried, and more if the two parents share the CPU). The log prints one `pc` line per setting as it finishes. `pilot.json` is saved after every stage; `notes` in it records that the mask was chosen after the DEV numbers, that it applies to every arm, and that T1 and T1b were never read.

Reading the result (no decisions for you): `ladder_rungs[0].gate` has signal_ok / aim_ok / sameness_ok and the temperature choice (`temperature.evaluated`, with rules_share, reach4, distinct_rules per T); on a failed gate the pilot stops with LADDER FAILED and writes the numbers (do not retry other settings). If it passes: `warmed.headroom` and `pc_n` (N: masked luck, twin luck, reach@4, plain and masked first try, plain luck / legal share / hit rate among legal, loss split), `pc_grid` (one row per lr x visits with the same fields, skills harm, `within_skills_limit`, and the sleep loss split into puzzle rows vs replay rows measured after the sleep), `pc_choice`, `pc_gate` (passes = PC/N >= 1.6 and PC-N >= +3 points).
Stop rules: if the masked PC misses on either parent at every setting within the 2-point skills limit (or no setting is within the limit), C1 stops with T1 and T1b sealed and the result goes back to the roadmap thread. If it passes on both parents, the setting is frozen and the power simulation runs before sealing (not part of this job).

## 3. Send back (pilot.json and logs only, never checkpoints)
```
mkdir -p creative/results/pilot3-s100 creative/results/pilot3-s101
for S in 100 101; do cp ~/creative/pilot3-s$S/pilot.json ~/creative/pilot3-s$S.log creative/results/pilot3-s$S/; done
git add creative/results && git commit -m "creative: pilot 3 results s100 s101 (masked sampler)" && git push origin HEAD:claude/project-thread-2zeaoc
```
Report any step that ran past its estimate.
