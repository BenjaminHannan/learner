# Addendum 1 to PASSMARKS-C.md: review fixes (X1-X4, R1-R5), the GPU plan, and a loop control

Written 2026-09-28 23:49 UTC (`date -u`) by the thread that took the relation-net race over from the Director. **Nothing has been scored on a maze:**
`eq-runs/` does not exist in this folder, so no dev or holdout maze score of the relation net exists. This file, its report
script (scripts/claude_relnet_eq_report_add1.py, tested by `selftest` below), its GPU driver (scripts/claude_relnet_eq_gpu.py) and
the queue jobs are committed before any maze rung is scored. Nothing here changes after any dev score is seen. PASSMARKS-C.md
and its report script stay as written; where this file says otherwise, this file wins. Design, practice recipe, plug-in,
thresholds (+10 / +5 / 190 / 6 / 2%) and the eight-rung ladder are unchanged. Source of the fixes:
artifacts/claude-dir-h8-review-20260928/REVIEW.md (X1-X4, R1-R5) and reviews/chat-prompt-relnet-review-fixes-2026-09-28.md. I checked each
finding against the marks and the code (below). **None is rejected.** One thing is added that the review did not ask for: a loop
re-run on the same machine (change 3).

## The changes
1. **X1, sleep gates (shown to be inside the noise).** The old-kind gates after the k=64 and k=16,384 sleeps (mark 4 of PASSMARKS-C.md,
   lines 45-48) compare three-draw means. Draw 0 is the ladder's own sleep (in adapt.json); draws 1 and 2 use sleep seed
   `seed + k + 101` and `seed + k + 202`, the offsets of scripts/claude_fewex_distill_sleep.py, from the ladder's saved `k64.pt` /
   `k16384.pt` (scripts/claude_relnet_eq_gpu.py, `dev`), for the relation net and for the loop control. Per seed, branch and kind:
   the relation net's three-draw mean must be at least `comparator - max(6, 2 x SE)`, where `SE = sqrt(sd_r^2/3 + sd_c^2/3)` (sample SDs of
   the three draws each) and `comparator = max(loop-control three-draw mean, the recorded loop's single draw)`. The "before adaptation"
   gates (190 of 200; within 6 of the loop) have no draw noise (one fixed checkpoint, scored once) and stay as sealed.
   Noise (self-check 1): the same recipe on one net gave sums 174, 158, 134 and grids 104, 104, 94 after the k=64 sleep
   (REVIEW.md:48-52, recounted by H13 from artifacts/claude-distill-20260928/sleeps/*.json), a spread of about 14 of 200 on sums, larger than the sealed 6.
2. **X2, the words (fixes PASSMARKS-C.md:55-56 and scripts/claude_relnet_eq_race.py:100-101, which say "any").** "A maze gain made only by breaking an
   old-kind gate" is REJECTED **only if at least one seed gains and EVERY gaining seed breaks an old-kind gate.** A gaining seed is one whose `F_eq` is above the
   comparator of change 3. Old-kind gates are marks 4a, 4b and 6 below. The fix lives in the new report script; the old script is untouched and not used for the verdict.
3. **Comparator ("the loop") = the higher of two loops (self-check 3).** (a) the recorded baseline `eq-runs/loop-s{seed}-pre` of the ruler (F_eq 51.00 / 51.29,
   F_few 13.83 / 16.17, recounted from its holdout.json); (b) **a loop control**: the same qualified loop source (`qual-loop-s{seed}`) put through this
   addendum's own driver on the same machine, with sleep checkpoints kept and three sleep draws (jobs below). Reason: the recorded loop ran on the CPU
   with one sleep draw; the relation net will run on a GPU. Marks 1, 2 and 4b use the higher `F_eq` / `F_few` / old-kind count of the two loops; the sleep gates use change 1's comparator. Also
   reported, no mark: the difference from each loop separately. (The patch race's "loop with episodes" is not an arm of this test and is not used.)
4. **X3, few examples (self-check 5).** `F_few` = mean over k = 1, 4, 16, 64 of 100 x right / 300 on the 9x9 holdout, learned stop. **New required mark 2:** `F_few` at least +5 over
   the higher of the two loops, in both seeds, quoted next to `F_eq` in the verdict sentence (+5 as in H13's ADDENDUM-2: a real few-example gain of +12 on four rungs is about +6 on the eight-rung mean).
5. **X4, non-wins.** A non-PASS is "NOT PROMOTED (not shown)" unless **both seeds are at least 2 points below** the comparator on `F_eq`, which is REJECTED (replaces "no higher than the loop in both seeds").
   The per-seed differences are printed next to the verdict.
6. **R3, R4, R5, one line each.** R3: PASSMARKS-C.md:78-79's "about 4-6 times the loop per step" is stale; the measured cost is **12.1x per maze update** (41.3 s against 3.42 s at one thread) and 3.8x per practice step
   (TIMING-ESTIMATE.md); the verdict sentence says "at 12.1x the compute per maze update". R4: the verdict says **"on mazes"** (one held-out kind); a pair state may fit reachability, and the
   two-kind check is not part of this test. R5: practice used different thread counts (seed 0: 2 threads then 1 after the container restart, seed 1: 1 then 2; PRACTICE-LAUNCH.md), and both were resumed from step 6,000 / 2,000
   checkpoints, so float sums differ from a straight run and the two seeds are not bit-comparable; harmless, disclosed in RESULTS. Also disclosed: `source_steps` in source.json reads "unknown, resume.pt not on main"
   (resume.pt was never pushed; the finished 12,000 steps come from the practice script's crash note in scripts/claude_relnet_eq_guard.py's docstring, not from a file on main).
7. **R1, the GPU addendum.** See the next section.

## Marks as they now stand (each seed on its own, never pooled)
1. `F_eq`: relation net at least **+10** over the higher of the two loops.
2. `F_few`: relation net at least **+5** over the higher of the two loops.
3. `F_eq`: at least +5 over the practised plain net (recorded `plain-s{seed}-pre`, F_eq 33.79 / 33.58) and at least +5 over the relation net's own fresh copy.
4. Old kinds before maze adaptation: at least 190 of 200 each (4a) and not more than 6 of 200 below the higher of the two loops on each kind (4b).
5. Stored weights within 2% of the loop (1,644,198 against 1,645,726).
6. After the k=64 and after the k=16,384 sleep, each old kind: three-draw mean within `max(6, 2 x SE)` of change 1's comparator.
0. (validity) the relation net's training pool shares no layout with any dev or holdout panel (`support_panel_overlap` = 0 in adapt.json).
**PASS** = marks 0-6 hold in both seeds. **REJECTED** = both seeds at least 2 points below the comparator on `F_eq`, or a gain made only by breaking (change 2). Otherwise **NOT PROMOTED (not shown)**.
Report only: everything PASSMARKS-C.md lists as report only, `F_eq` and `F_few` of every arm, the difference from each loop, the loop control minus the recorded loop, the fixed-depth check, learned-stop gaps.

## MARKS SELF-CHECK (handoff/director-briefs/thread-helper-common.md)
1. **Bars above noise.** Loop F_eq differs by 0.29 between its two seeds (51.00 / 51.29) and F_few by 2.34 (13.83 / 16.17), recounted; the largest seed-to-seed swing of any design seen is 6.25 (sparse loop, REVIEW.md X4). +10 and +5 are above all three. Sleep gates: margin max(6, 2 x SE) from the draws themselves (X1).
2. **Every-seed reading:** change 2; a non-win is "not shown" unless both seeds are at least 2 points below (change 5). Tested by the selftest (a), (b), (d).
3. **Fair comparator:** the higher of the recorded loop and the same-machine loop control (change 3).
4. **A row a plain same-size net cannot pass:** 3a (plain gets F_eq 33.79 / 33.58, F_few 3.33 / 1.00 in the record); memorising is excluded by mark 0 (the training pool excludes every dev and holdout layout). No maze rule or kind label enters the plug-in (its docstring).
5. **F_few** is its own required row (mark 2, change 4).
6. **Sleep gates** use three draws per branch, margin max(6, 2 x SE) (mark 6, change 1).

## R1: the GPU addendum (strict fp32, TF32 off, CPU-equivalent smoke; $0)
- **Why (shown, TIMING-ESTIMATE.md):** about 54 h per dev run at one thread, about 216 core-hours for four runs, before the holdout. ADDENDUM-4 of the ruler (artifacts/claude-fewex-20260927/ADDENDUM-4.md, last paragraph) asks for this addendum before any new maze score.
- **Machine:** Ben's own GPU machine (BensPC, RTX 5070 Ti) through the queue, one job at a time, **$0, no rental** (Ben chose his own machines). The rental clause ("at most one rental, $4") is therefore unused.
- **What runs there:** scripts/claude_relnet_eq_gpu.py, which calls the harness's own pieces (pool, batches, scoring, sleep, holdout) and H13's resumable ladder; only the device changes: `torch.set_default_device("cuda")`; the net is built on the CPU (fresh copies keep the CPU-RNG weights) then moved; TF32 off for matmul and cudnn, highest matmul precision, no autocast, deterministic algorithms requested (warn only). Stage checkpoints are saved as CPU tensors so the harness's own `holdout` reads them.
- **Sources:** the two practised nets are on main (runs/relnet-s{0,1}/source.pt, sha256 in checkpoints-sha256.txt: b2988e2a..., 115f2451...); the jobs fetch main and check the sha256 before use (`check`); no rebuild. Their `source.json` comes from scripts/claude_relnet_eq_guard_srconly.py (queue job relnet-guard-mac) and must be on main before any ladder.
- **CPU-equivalence smoke (marks fixed now, untested; run before any maze rung):** `python -B scripts/claude_relnet_eq_gpu.py smoke --device cuda` runs seed 0's source net on the CPU and on the GPU, same code, and compares: (i) strict flags (TF32 off, all parameters float32 on the device); (ii) cell logits at rounds 1, 8, 48 and all 48 stop probabilities on 16 dev 9x9 mazes: max absolute difference at most 1e-3 (each); (iii) exact counts (right and fixed_right) on the 200 guard sums, 200 guard grids and the first 64 dev 9x9 mazes: within 1 of the CPU counts; (iv) after 2 maze batches (8 updates) from the source net: the whole-parameter update differs from the CPU update by at most 2% (relative norm), no single tensor by more than 10%, and the count on the first 64 dev 9x9 mazes within 2; (v) after 3 sleep steps: whole-parameter update difference at most 5%. The thresholds are my choice before any measurement (**untested**: I could not run a GPU here); the printed numbers, not my reading, decide. It also times a maze batch, a sleep step and 48-round inference and prints a projected run time (**suggested**, TIMING-ESTIMATE.md's formula).
- **If the smoke fails:** the job stops with SMOKE-FAIL and says so; no ladder starts on the GPU. **CPU plan:** the same driver with `--device cpu` (no other change), only the "pre" runs first: `python -B scripts/claude_relnet_eq_gpu.py dev --device cpu --seed S --loop-source-root DIR` per seed (order: relation net pre, loop control, then fresh), at one thread about 54 h per relation-net run (shown, TIMING-ESTIMATE.md) and roughly 4 h for a loop run (suggested: the sparse ladders, about the loop's cost, took 3.9 h); about 108 core-hours for the two "pre" runs, about 36 h at three cores. The recorded CPU loop then needs no control, but the sleep gates still do (draws are in the same command).
- **Disclosed:** a GPU run is not bit-identical to a CPU run; a resumed GPU run is not guaranteed bit-identical to an uninterrupted one (**untested**). The comparator's second loop (change 3) is run on the same GPU for exactly this reason. Old-kind scores, source guards and the practice all stay as run on the CPU.

## What runs, in order (queue jobs are committed HELD; the Director releases them)
1. `relnet-guard-mac`: source guard of both nets from source.pt (Mac CPU, small). A pre-check on the container that wrote this addendum gave sums4 200 and 200, grids5 199 and 199 of 200, fixed depth 16, all 19 matrices with a nonzero gradient, in both seeds (**shown** on that box, not the record; the job's source.json is).
2. `relnet-gpu-smoke-benspc`: the smoke above.
3. `relnet-dev-s0-benspc`, `relnet-dev-s1-benspc`: per seed, relation net pre, its four sleep draws, loop control, its four sleep draws, relation net fresh (resumable; rerun the same job as `-r2` after any stop).
4. The Director commits the dev records; then `relnet-holdout-benspc` (once per run, the harness's own `holdout_job`; HELD until the dev records are on main). Report: `python3 -B scripts/claude_relnet_eq_report_add1.py dev` then `holdout`.
The new report script is scripts/claude_relnet_eq_report_add1.py (`selftest`, `dev`, `holdout`); the old one is not used for the verdict.

## Reproduction (this addendum's own checks), 2026-09-28 23:49 UTC
`python3 -B scripts/claude_relnet_eq_report_add1.py selftest` writes add1-selftest.json in this folder (fake numbers; checks the words and the arithmetic, not any model). Pass: it prints `"all_expected": true`, meaning
(a) one seed that gains and breaks a gate plus one that gains and passes prints NOT PROMOTED (not shown) under the every-reading (the any-reading, not used, would print REJECTED); (b) both gain and both break -> REJECTED; (c) both gain and pass -> PASS;
(d) one seed slightly below and one above -> not shown; both at least 2 below -> REJECTED; (e) a relation net equal to the loop with one noisy sleep draw (-12) passes the three-draw gate; (f) `F_eq` well above its bar with `F_few` only +2 fails mark 2 only;
(g) when the recorded loop is the higher loop, the bar moves to it; (h) the sentence contains "12.1x the compute" and "on mazes".
