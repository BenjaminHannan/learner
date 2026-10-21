# Mac job 2: DEV-only pilot with the rewritten gates (B2 s100 and s101, CPU)

Replaces the pilot run of MAC-JOB.md (same setup, new defaults). Nothing touches T1, T1b or X. Never delete a checkpoint. Times in ET.
What changed: warm-up is 1,500 two-number + 1,500 three-number puzzles, 4 visits, one rung only; gates are signal (>= 100 practice puzzles solved), aim (luck / rules_share >= 0.082) and sameness (>= 4); rules_share is reported, not gated; marks and the PC gate are re-scaled (PC/N >= 1.6 and PC-N >= +3 points).

## 1. Update the code (the parents, skills data and tests from job 1 are already in place)
```
cd ~/learner && git fetch origin claude/project-thread-2zeaoc && git checkout creative-pilot && git reset --hard origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c1 && python3 -m creative.tests.test_c2 && python3 -m creative.tests.test_pilot
```
All three must print ok lines (about 5 min). If one fails, stop and send the output. The parent hashes were already checked (s100 18e4b0e0..., s101 07aacb05...).

## 2. Pilot (CPU, one process per parent; can run beside diagnose.py if memory allows, about 2-4 GB each plus ~1.5 GB for the replay rows; otherwise queue after it)
```
for S in 100 101; do
  OMP_NUM_THREADS=4 nohup python3 -m creative.cli pilot \
    --ckpt ~/creative/ckpt/B2_s$S.pt --out ~/creative/pilot2-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl \
    --skills-data ~/custom-io/work/data_big --device cpu \
    > ~/creative/pilot2-s$S.log 2>&1 &
done
```
Defaults now: `--ladder 1500`, fallbacks off. Estimate (untested): about 40 min for the warm-up and gate, then about 4 learning-rate sleeps plus up to 2 widenings at roughly 10-15 min each on CPU, so 1.5-2.5 h per parent. `pilot.json` is saved after every stage, `warmed.pt` is kept, and `notes` in it records that the gates were rewritten after seeing DEV numbers.

Reading the result (no decisions for you): `ladder_rungs[0].gate` has signal_ok / aim_ok / sameness_ok; if it fails, the pilot stops with "LADDER FAILED" and writes the numbers (do not retry with other settings). If it passes, `warmed` has headroom (luck, first try), the aim check, skills and warm-up harm; `pc_grid` the learning-rate sleeps; `pc_gate` the verdict (passes = PC/N >= 1.6 and PC-N >= +3). If PC misses on both parents, stop and report; nothing is sealed.

## 3. Send back
```
mkdir -p creative/results/pilot2-s100 creative/results/pilot2-s101
for S in 100 101; do cp ~/creative/pilot2-s$S/pilot.json ~/creative/pilot2-s$S.log creative/results/pilot2-s$S/; done
git add creative/results && git commit -m "creative: pilot 2 results s100 s101 (rewritten gates)" && git push origin HEAD:claude/project-thread-2zeaoc
```
(pilot.json and logs only, never checkpoints.) Report any step that ran past its estimate.
