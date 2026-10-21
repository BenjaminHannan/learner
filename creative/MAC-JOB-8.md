# Mac job 8: "more tries where it's stuck" (B2 s100 and s101, CPU, DEV only)

See roadmap section 7 (decided 10-07). One change against job 7, blind to rule kind: each night every pool question is sampled 32 times at T 3.0; every pool question with no example-fitting try then gets 480 more tries at T 3.0 (512 in all); questions that already have a fitting try get nothing more. Records = at most 2 distinct fitting tries per question. Frozen from job 7: start from N' (Nprime.pt), pool T 3.0, dose lr 1e-3 x 32 visits (updates = 32 x records / 32 per night), every sleep replays the warm add/mult rows and the skills data (16 + 16 of 32), night 2 starts from the night-1 model and resamples the pool with it using the same two-pass search. DEV only; test and labelled never opened; no R/H/PC arms. Never delete a checkpoint. Times in ET.

## 1. Update and test
```
cd <your worktree for this repo> && git fetch origin claude/project-thread-2zeaoc && git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c2_keep && python3 -m creative.tests.test_c2_stuck
```
Both must end with ok lines (about 2 min). If one fails, stop and send the output.

## 2. Run (one process per parent, side by side)
```
for S in 100 101; do
  OMP_NUM_THREADS=4 nohup python3 -m creative.c2_stuck \
    --nprime ~/creative/c2keep-s$S/Nprime.pt --out ~/creative/c2stuck-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl --skills-data ~/custom-io/work/data_big --device cpu \
    > ~/creative/c2stuck-s$S.log 2>&1 &
done
```
(If a Nprime.pt is missing, add `--ckpt ~/creative/ckpt/B2_s$S.pt --warmed ~/creative/c2stones-s$S/warm4.pt`: N' is then rebuilt exactly as job 7 did and the json says so.) The search-check threshold (75 multi-step records on s100, 90 on s101) is read from the `--out` name. Estimate (untested): about 600-700 stuck questions x 480 tries per night, 1.5-2.5 h per parent. `c2_stuck.json` is saved after every stage and ends with `DONE` and a per-parent `verdict`, or a `stop` reason.

## 3. Send back (json and logs only, never checkpoints)
```
mkdir -p creative/results/c2stuck
for S in 100 101; do cp ~/creative/c2stuck-s$S/c2_stuck.json creative/results/c2stuck/s$S.json; cp ~/creative/c2stuck-s$S.log creative/results/c2stuck/s$S.log; done
git add creative/results && git commit -m "creative: C2 stuck-search results s100 s101" && git push origin HEAD:claude/project-thread-2zeaoc
```
Do not retry other settings on a miss. Report any step that ran past its estimate.
