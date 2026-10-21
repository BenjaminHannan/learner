# Mac job: creative pilot on B2 s100 and s101 (CPU, DEV only)

Nothing here touches T1, T1b or X (they stay sealed). No GPU. Do not delete any checkpoint.
Report times in ET.

## 1. Get the code and the two parents
```
cd ~/learner 2>/dev/null || git clone https://github.com/BenjaminHannan/learner ~/learner && cd ~/learner
git fetch origin claude/project-thread-2zeaoc claude/creative-parents
git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
mkdir -p ~/creative/ckpt
for S in 100 101; do git show origin/claude/creative-parents:B2_s$S/checkpoint.pt > ~/creative/ckpt/B2_s$S.pt; done
git show origin/claude/creative-parents:SHA256SUMS
shasum -a 256 ~/creative/ckpt/*.pt
```
Hashes must be s100 `18e4b0e0d87031bee230e9af6a861d5f09cae47985fb5df47d8a33020201bcf0`, s101 `07aacb054f76360e9820160bb50891361db7ab965c4656a18a4ab2b767ae51ac`. If either differs, stop and tell the thread.

## 2. Skills data (for the replay half of every sleep and the skills-harm check)
Use the existing custom_io build (same data B2 trained on):
```
python3 -m custom_io.local_runner setup --work ~/custom-io/work --curriculum .
```
This gives `~/custom-io/work/data/train.jsonl` and `~/custom-io/work/data_big/dev/in_dist.jsonl`. If its hash check fails, stop and tell the thread (do not substitute other data).

## 3. Tests (~5 min, CPU)
```
python3 -m creative.tests.test_c1 && python3 -m creative.tests.test_c2 && python3 -m creative.tests.test_pilot
```
All three must print OK. If any fails, stop and send the output.

## 4. Pilot (torch + numpy only, device cpu; MPS is untested, do not use it)
Prefer one parent per run, both can run side by side (about 2-4 GB each, plus ~1.5 GB for the 200k replay rows):
```
for S in 100 101; do
  OMP_NUM_THREADS=4 nohup python3 -m creative.cli pilot \
    --ckpt ~/creative/ckpt/B2_s$S.pt --out ~/creative/pilot-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl \
    --skills-data ~/custom-io/work/data_big --device cpu \
    > ~/creative/pilot-s$S.log 2>&1 &
done
```
Estimate 1.5 to 3 h per parent. `pilot.json` is saved after every stage, so a crash keeps partial results; `warmed.pt` is kept in the out folder.

What the run does by itself (no decisions needed from you):
1. DEV gate on the raw parent. 2. Warm-up ladder: 1,500 two-number puzzles + 1,500 / 3,000 / 6,000 three-number puzzles; the smallest rung that passes the signal gate (>= 50% of tries rule-following and accepted tries on >= 100 distinct practice puzzles) wins. 3. Temperature re-chosen on the warmed parent. 4. lr grid for the PC arm with skills replay on; edge widening by x3 up to twice. 5. PC gate: PC minus N luck >= +10 points.
Fallbacks are automatic: (a) warmed parent does not fit its own warm-up puzzles -> 16 visits per record; (b) it fits but fails DEV -> dreams; (c) otherwise it stops and writes the numbers.
Do not lower the gate and do not change the recipe. If the PC gate misses on BOTH s100 and s101, nothing is sealed; just report.

## 5. Send back
Commit only `pilot.json` and the log (never checkpoints) on branch `claude/project-thread-2zeaoc`:
```
mkdir -p creative/results/pilot-s100 creative/results/pilot-s101
for S in 100 101; do cp ~/creative/pilot-s$S/pilot.json ~/creative/pilot-s$S.log creative/results/pilot-s$S/; done
git add creative/results && git commit -m "creative: pilot results s100 s101" && git push origin HEAD:claude/project-thread-2zeaoc
```
Also copy both `pilot.json` to `/mnt/project-files/creative-pilot/` if reachable, then tell the thread. Note any step that ran longer than the estimate.
