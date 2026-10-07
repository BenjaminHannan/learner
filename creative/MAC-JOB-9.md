# Mac job 9: the real C2b (B2 s200..s205, CPU, two parents at a time)

Roadmap section 7, "Decided (10-07): the real C2b goes ahead" (ruling 9d25a6fbb8). Code: `creative/c2b.py`, tests `creative/tests/test_c2b.py`. Never delete a checkpoint or a model file. Times in ET.

What one parent does (all resumable; a re-run skips every finished stage): raw B2 -> warm-up (2,048 warm add/mult rows, 4 visits, lr 3e-4, skills replay, seed 0) -> N' (stepping-stone sleep with add/mult replay, as job 7) -> pool temperature T (job 6 rule, DEV, per N') -> two nights for four arms on the 1,024 pool questions. Dose lr 1e-3 x 32 visits, 16 skills + 16 warm add/mult replay per 32.
- W: job 8's search (32 tries, then 480 more where no try fits), at most 2 distinct fitting tries per question.
- R: same questions and same count as W's that night, tries that FAIL the example check, from the model's own 32 pass-1 tries (no pass 2).
- H: R's tries relabelled with what they compute on the shown examples.
- M (reported only): N' plus a memory of W's night-1 records and 512 old notes, answer note off, chain-5 harm guard every night; weights never change.
Night 2 for every arm samples with that arm's own night-1 model. Training never opens the sealed test split (DEV is used only to pick T).

## 1. Update and test
```
cd <your worktree for this repo> && git fetch origin claude/project-thread-2zeaoc && git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c2b && python3 -m creative.tests.test_c2_stuck
```
Both must end with ok lines (about 1 min each). If one fails, stop and send the output.

## 2. Train (one process per parent; two at a time)
B2 checkpoints for s200..s205: branch `claude/b2-confirm-checkpoints` (f41d0f7d5); put them at `~/creative/ckpt/B2_s20X.pt`. If the fast-sleep confirm's `warm.pt` is on this machine (`.../confirm/s20X/warm.pt`), add `--warmed` with it; if not, leave `--warmed` off and the script rebuilds that warm-up exactly (same rows, visits, lr, seed) and says so in `train.json`.
```
for S in 200 201; do
  OMP_NUM_THREADS=4 nohup python3 -m creative.c2b train \
    --ckpt ~/creative/ckpt/B2_s$S.pt --out ~/creative/c2b/s$S \
    --skills-train ~/custom-io/work/data/train.jsonl --skills-data ~/custom-io/work/data_big --device cpu \
    > ~/creative/c2b/s$S.log 2>&1 &
done
```
Then the same for 202+203 and 204+205 (or start the next parent in a free slot as soon as one finishes). Each parent ends with a line `PARENT DONE` and a file `complete.json`. Estimate (untested): about 3 to 3.5 h per parent, about 10 h for six with two at a time. The PC GPU can take some parents after q39 finishes (add `--device cuda`); if the run is split across machines, copy each parent's folder (setup.json, Nprime.pt, W2.pt, R2.pt, H2.pt, M_final.pt, complete.json) into ONE root folder before scoring.

Check progress any time (opens nothing): `python3 -m creative.c2b check --root ~/creative/c2b`

## 3. Score the sealed test split (ONCE, only when all 6 parents x 4 arms exist)
```
OMP_NUM_THREADS=8 python3 -m creative.c2b score --root ~/creative/c2b \
  --skills-train ~/custom-io/work/data/train.jsonl --skills-data ~/custom-io/work/data_big --device cpu
```
This refuses to run (and does not open the test split) if any parent or arm is missing, and refuses a second pass once `REPORT.json` exists. It is resumable per parent after a crash (`test/s20X.json`). About 2 to 3 min per model, 30 models. Do not run it early, do not re-run it with other settings.

## 4. Send back (json and logs only, never models)
```
mkdir -p creative/results/c2b
for S in 200 201 202 203 204 205; do mkdir -p creative/results/c2b/s$S; cp ~/creative/c2b/s$S/{train.json,setup.json} creative/results/c2b/s$S/; cp ~/creative/c2b/s$S.log creative/results/c2b/s$S.log; done
cp ~/creative/c2b/REPORT.json creative/results/c2b/; cp -r ~/creative/c2b/test creative/results/c2b/test
git add creative/results && git commit -m "creative: real C2b results" && git push origin HEAD:claude/project-thread-2zeaoc
```
REPORT.json carries numbers and per-parent readings only; the roadmap thread gives the verdict. Report any step that ran past its estimate. Do not retry other settings after a miss.
