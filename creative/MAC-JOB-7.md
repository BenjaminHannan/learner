# Mac job 7: "keep the parts" (B2 s100 and s101, CPU, DEV only)

Roadmap decision 10-07 (section 7). Same seeds, rows and pool as jobs 5 and 6. DEV only: `test` and `labelled` never opened; `pool` is the sleep pool. No R or H arms. Never delete a checkpoint. Times in ET.

THE ONE CHANGE: every sleep (stepping stones, PC', each night) also replays the 2,048 warm add/mult solver rows; the replay half of each batch is split evenly between the skills replay and these rows (16 + 16 of the 32). The dose-grid visits widen once to 32.
Per parent: N' = warmed parent (job 5's warm4.pt) + the stepping-stone sleep with that replay. PARTS KEPT (else the job reports and stops): fresh add/mult reach@32 >= 50% for N' and after each night; N' passes cold start (reach@32 >= 14.5% with sameness at its best temperature); skills harm <= 2 points (N' against the warmed parent, every later model against N'). Pool temperature by the job-6 rule on N'. PC' = reference programs for every multi-step pool question (affine, sq_plus, double_add; one record each); dose chosen on DEV with PC' (lr {3e-4,1e-3} x visits {4,8,16,32}) by multi-step greedy first try then reach@4, among settings with harm <= 2 and fresh add/mult >= 50%; frozen. FEASIBILITY: PC' - N' multi-step greedy first try on the 154 multi-step DEV questions >= +10 points (a miss stops this parent: explanation (b)). CLIMB: W' night 1 from N' on N''s example-checked tries, then night 2 (the night-1 model samples the pool again, sleeps on its own checked tries), updates = visits x records / 32 per night. Reported: multi-step first try W'(night 2) - N' with paired bootstrap 95% interval, night 1, per kind, pooled, reach@4 and reach@32, records per kind, practised check and skills harm after each night. The decision rule (pass: >= +10 with interval above 0 on both parents; proved wrong: parts kept and upper end < +3 on both parents) is the roadmap thread's; the json carries a per-parent reading only.

## 1. Update the code
```
cd <your worktree for this repo> && git fetch origin claude/project-thread-2zeaoc && git checkout -B creative-pilot origin/claude/project-thread-2zeaoc
python3 -m creative.tests.test_c2_real && python3 -m creative.tests.test_stones && python3 -m creative.tests.test_c2_pilot && python3 -m creative.tests.test_c2_keep && python3 -m creative.tests.test_c2
```
All must end with ok lines (about 10 min). If one fails, stop and send the output.

## 2. Run (one process per parent; the two can run side by side)
```
for S in 100 101; do
  mkdir -p ~/creative/c2keep-s$S && cp ~/creative/c2dev-s$S/dev_floors.json ~/creative/c2keep-s$S/
  OMP_NUM_THREADS=4 nohup python3 -m creative.c2_keep \
    --ckpt ~/creative/ckpt/B2_s$S.pt --warmed ~/creative/c2stones-s$S/warm4.pt --out ~/creative/c2keep-s$S \
    --skills-train ~/custom-io/work/data/train.jsonl --skills-data ~/custom-io/work/data_big --device cpu \
    > ~/creative/c2keep-s$S.log 2>&1 &
done
```
Estimate (untested; job 6 took about 1.5 h per parent with 6 dose settings): 8 dose settings, each with a fresh add/mult check, and two nights: about 2.5-3.5 h per parent. `c2_keep.json` is saved after every stage and ends with `DONE` and a `verdict`, or a `stop` reason.

## 3. Send back (json and logs only, never checkpoints)
```
mkdir -p creative/results/c2keep
for S in 100 101; do cp ~/creative/c2keep-s$S/c2_keep.json creative/results/c2keep/s$S.json; cp ~/creative/c2keep-s$S.log creative/results/c2keep/s$S.log; done
git add creative/results && git commit -m "creative: C2 keep-the-parts results s100 s101" && git push origin HEAD:claude/project-thread-2zeaoc
```
Do not retry other settings on a miss. Report any step that ran past its estimate.
