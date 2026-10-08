# PC job 1 (BensPC RTX 5070 Ti): rebuild the six parents, and re-score the research-loop sleep with the real harm measure

Needs nothing from the Screen A results, so it can run now. DEV only: C2 test, labelled and the research-loop holdout are never opened. No checkpoint is deleted.
Report times in ET. Nothing here pushes to main: results go to the branch `claude/friendly-bohr-z4dpfo`.

Why: (1) the confirm needs each parent's N built on one machine, and the cloud CPU is slow (about 50-80 s per 1,024-row update; the six-parent confirm would
take 8-10 hours). (2) The task says the research-loop sleep's harm was only checked with the pooled-5 guard. `rescore_harm` re-scores that exact sleep with
the harm measure (in_dist drop, family rule) against N and against the raw B2. It is the paired baseline for the 71.3% bar. The research loop ran it on a
32 GB RTX 5090; this card has 16 GB, so if a step runs out of GPU memory, stop and send the traceback (do not change settings).

## 1. Code, parents, data
```
cd <your worktree for this repo> && git fetch origin claude/friendly-bohr-z4dpfo claude/b2-confirm-checkpoints claude/creative-parents
git checkout -B consol origin/claude/friendly-bohr-z4dpfo
mkdir -p ~/consol/ckpt
for S in 100 101; do git show origin/claude/creative-parents:B2_s$S/checkpoint.pt > ~/consol/ckpt/B2_s$S.pt; done
for S in 200 201 202 203 204 205; do git show origin/claude/b2-confirm-checkpoints:custom_io/checkpoints/33-b2-confirm/B2_s$S/checkpoint.pt > ~/consol/ckpt/B2_s$S.pt; done
sha256sum ~/consol/ckpt/B2_s100.pt ~/consol/ckpt/B2_s101.pt
```
The first two hashes must be `18e4b0e0d87031bee230e9af6a861d5f09cae47985fb5df47d8a33020201bcf0` and `07aacb054f76360e9820160bb50891361db7ab965c4656a18a4ab2b767ae51ac`; if either differs, stop.
Skills data (the same build B2 trained on; the curriculum package is on branch `claude/project-thread-y0sxwe`):
```
git fetch origin claude/project-thread-y0sxwe && mkdir -p ~/consol/cur && git archive origin/claude/project-thread-y0sxwe skills_curriculum | tar -x -C ~/consol/cur
python3 -m custom_io.local_runner setup --work ~/consol/work --curriculum ~/consol/cur
```
If its hash check fails, stop. This gives `~/consol/work/data/train.jsonl` and `~/consol/work/data_big`.

## 2. Tests (about 5 min)
```
python3 -m creative.tests.test_consol
```
All 13 must print `ok`. If one fails, stop and send the output.

## 3. Rebuild the six parents' N (GPU, one at a time)
`fastsleep setup` = warm-up + stepping-stone sleep (job 6 steps 0-2). `--T 3.0` skips the pool-temperature scan (no arm reads the cached night).
```
export PYTHONPATH=$PWD
for S in 200 201 202 203 204 205; do
  python3 -m creative.fastsleep setup --ckpt ~/consol/ckpt/B2_s$S.pt --out ~/consol/parents/s$S --device cuda \
    --skills-train ~/consol/work/data/train.jsonl --skills-data ~/consol/work/data_big \
    --floors creative/results/fastsleep/consol/dev_floors.json --T 3.0 > ~/consol/setup-s$S.log 2>&1
done
```
Check each `setup.json`: the cloud CPU got warm-up last losses 1.35 / 1.27 / 1.41 and stepping-stone losses 0.61 / 0.47 / 0.51 for s200 / s201 / s202. A GPU
run will not match to the last digit; a loss above 2.0 or a crash means stop. Estimate (untested): 10-20 min per parent.

## 4. Re-score the research-loop sleep (report only)
```
export RL_PARENTS=~/consol/parents RL_SKILLS_TRAIN=~/consol/work/data/train.jsonl RL_SKILLS_DATA=~/consol/work/data_big RL_DEVICE=cuda
python3 -m creative.rl.rescore_harm --seeds 0 1 2 3 4 5 --b2-dir ~/consol/ckpt --out ~/consol/rescore --device cuda --threads 4 > ~/consol/rescore.log 2>&1
```
Each seed runs the research loop's own compliant sleep (about 2,400 TF; 8 min on a 5090) and scores C2 DEV, pooled-5 and the harm measure against N and B2.
Estimate on this card (untested): 10-25 min per seed. `~/consol/rescore/rescore.json` is rewritten after every seed.

## 5. Send back (json and logs only, never checkpoints)
```
mkdir -p creative/results/fastsleep/consol/pc1 && cp ~/consol/rescore/rescore.json ~/consol/rescore.log ~/consol/setup-s*.log creative/results/fastsleep/consol/pc1/
for S in 200 201 202 203 204 205; do cp ~/consol/parents/s$S/setup.json creative/results/fastsleep/consol/pc1/setup-s$S.json; done
git add creative/results/fastsleep/consol/pc1 && git commit -m "consol: PC job 1 results (six parents rebuilt, research-loop sleep re-scored with the harm measure)" && git push origin HEAD:claude/friendly-bohr-z4dpfo
```
Do not retry other settings on a miss. Report any step that ran past its estimate, and the GPU memory it used (`nvidia-smi`).
Keep the six `~/consol/parents/sNNN` folders: the confirm job will use them.
