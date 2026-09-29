# RESULTS-h1: PARTIAL — TIME-STOP, NO VERDICT

Verdict first: **TIME-STOP, partial, no verdict.** The 480-minute cap was reached with 4 of 16 dev jobs complete
(graph loop arms only) and 4 stopped early (graph plain arms, 3 rungs each). Rank (0 of 8 jobs) never started. No dev
gate ran (each kind needs 8 adapt.json; graph has 4, rank has 0), no holdout was opened for any kind (no
holdout.started marker was written anywhere), no SCORE file exists, and no mark (M1–M4, C1) is computed here. All
counts below are raw dev-panel counts quoted from adapt.json / partial.json, integer "x of N" only.

## What ran, step by step (shown)

1. TREE AND SEAL (shown): `git archive origin/main scripts artifacts/claude-fewex-20260927
   artifacts/claude-dir-h1-heldout-20260928` into a fresh temp dir. `shasum -a 256 -c SEAL-code.sha256.txt`: 5 of 5 OK
   (scripts/claude_dir_h1_kinds.py, scripts/claude_dir_h1_marks.py, scripts/claude_dir_h1_bench.py,
   PASSMARKS.md, DESIGN.md). All four source checkpoints exist on the Mac under
   /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-fewex-20260927/runs/
   (qual-loop-s0, qual-loop-s1, qual-plain-s0, qual-plain-s1, each source.pt + source.json). Sealed code was never
   edited. No blind panel was opened, read, tuned on or quoted (nothing here needs one).
2. SELFTESTS (shown): kinds selftest printed "selftest ok" and every SHA-256 inside SELFTEST-kinds-run.log equals
   those in SELFTEST-kinds.log (all four panel fingerprints, all four pool digests: SHA-MATCH). Marks selftest
   printed "selftest ok". Bench torch selftest printed 4 "selftest ok" lines (graph loop, graph plain, rank loop,
   rank plain) plus weights lines loop 1645726 and plain 1619965, exactly as required.
3. SOURCES (shown): check-source printed {"V1": true, "V2": true}, 4 of 4 sources V1_ok and V2_ok
   (SOURCE-CHECK.json). source.pt SHA-256: loop-s0 d5f09b1dfbc65e4e018081be71305e7440468d869114f2205e2565a3e646a085,
   loop-s1 6cc51ee871a383668b365f63c80e9d9599a4c11faab08fed7e46747f7fb15673,
   plain-s0 e335364f0674deed09b41287567bc89dec00137b0636a712221a7689bb444b7f,
   plain-s1 e55a6e400e44b36e02fb9ce295168656046493be2ff0b4f200668c4a9c67052c. Weights 1645726 / 1619965.
4. TIMING PILOT (shown; uptime + `df -g /` checked first: 10 cores, 1-min load ~59, 104 GB free): per-batch seconds
   and projected training-only minutes per job: graph loop 1.839 s -> 125.5 min; graph plain 1.297 s -> 88.5 min;
   rank loop 0.530 s -> 36.2 min; rank plain 0.297 s -> 20.3 min. Plus 12 min scoring each: about 137.5 / 100.5 /
   48.2 / 32.3 min per job. C=4 (load was ~59, far above 2, so not 8). Projected wall (graph wave + rank wave, 4 at
   a time, longest job per wave): about 275 + 96 = about 371 min, under 420 -> proceed (not TOO-SLOW).
5. DEV RUNS (shown, partial): graph first, then rank; 4 at a time; `--threads 1`; OMP/MKL threads 1; fp32 CPU.
   - Wave 1 (graph loop, all 4 jobs: s0/s1 x pre/fresh), started 2026-09-28 23:54:39 UTC, finished ~06:05 UTC
     (~371 min wall each; adapt_done compute seconds 22303 to 22327). 4 of 4 completed: adapt.json + k*.pt (k0
     through k16384, 9 of 9) written. Zero non-zero exits, zero restarts.
   - 20-minute projection (shown): rung "seconds" ~3800 per rung x 8 rungs = ~30400 s (~507 min) + scoring, over
     the 480-minute TIME CAP -> reported here; per protocol jobs kept running until 30 min before the cap.
   - Wave 2 (graph plain, all 4 jobs), started 06:06:07 UTC, TIME-STOPped 07:15 UTC (~69 min each, 3 rungs each:
     k=1, 4, 16 scored). Stopped by exact PID: children 47780, 47781, 47782, 47783 killed, wrappers already exited;
     follow-up pgrep empty (shown). partial.json + partial k*.pt written (k0, k1, k4, k16, k64).
   - Rank: 0 of 8 jobs started (cap). Total in-cap: 8 of 16 jobs touched, 4 of 16 complete.
6. DEV GATES: never ran (shown). Graph has 4 of 8 adapt.json, rank 0 of 8; the gate command was correctly not run
   for either kind. No DEV-GATE file exists. Step-6 uptime/df re-check never applied (step 6 not reached); last
   readings at TIME-STOP 07:15 UTC: 1-min load ~202, disk 103 GB free.
7. HOLDOUT: never opened for any kind (shown). No holdout.json, no holdout.started marker. No model, rung, recipe
   or panel choice was changed at any point.
8. This file + SHA256-h1-RAW.txt (shown). No SCORE file exists, so no mark is quoted or computed by hand.

## Dev counts, graph kind, graded size 14 nodes (shown; quoted from adapt.json, n=300 each)

Loop arms (complete, 8 positive rungs + cold k=0). Every cell below is exact-answer "right of 300":

| run | k=0 | k=1 | k=4 | k=16 | k=64 | k=256 | k=1024 | k=4096 | k=16384 |
|---|---|---|---|---|---|---|---|---|---|
| loop-s0-pre | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 |
| loop-s0-fresh | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 |
| loop-s1-pre | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 |
| loop-s1-fresh | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 |

Plain arms (TIME-STOP partial; later rungs absent, never trained):

| run | k=0 | k=1 | k=4 | k=16 | k=64 | k=256+ |
|---|---|---|---|---|---|---|
| plain-s0-pre | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | not run |
| plain-s0-fresh | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | not run |
| plain-s1-pre | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | not run |
| plain-s1-fresh | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | 0 of 300 | not run |

Secondary sizes (shown; dev panel: 24 items at 12 nodes, 300 at 16 nodes), loop arms complete: 0 of 24 at 12 nodes
and 0 of 300 at 16 nodes on every rung of all 4 runs. Plain partials: 0 of 24 / 0 of 300 on rungs reached.
Learned-stop vs fixed-depth gap: fixed_right is 0 of N on every rung recorded above (gap 0; nothing learned to
compare). Mean rounds and cap hits per rung are in adapt.json (e.g. loop-s0-pre k=16384 mean_rounds 3.0, cap_hits
0 of 300; k=1 mean_rounds 13.4, cap_hits 0 of 300). Collapsed rungs: none computable (no rung is 30+ points below
both neighbours; all are 0). E50/E30: no rung reached 150 or 90 of 300 in any run (not reached everywhere).
F_eq / F_low: not computed by hand and no SCORE file exists to quote (all rung counts are 0 of 300).

Old-kind sums/grids counts, n=200 each (shown):

| run | before (grids, sums) | after k=64 | after k=16384 |
|---|---|---|---|
| loop-s0-pre | 199 of 200, 200 of 200 | 0 of 200, 0 of 200 | 0 of 200, 0 of 200 |
| loop-s1-pre | 200 of 200, 200 of 200 | 0 of 200, 0 of 200 | 0 of 200, 0 of 200 |
| loop-s0-fresh | 0 of 200, 0 of 200 | 0 of 200, 0 of 200 | 0 of 200, 0 of 200 |
| loop-s1-fresh | 0 of 200, 0 of 200 | 0 of 200, 0 of 200 | 0 of 200, 0 of 200 |
| plain-s0-pre (partial) | 193 of 200, 200 of 200 | 0 of 200, 0 of 200 | not run |
| plain-s1-pre (partial) | 190 of 200, 200 of 200 | 0 of 200, 0 of 200 | not run |
| plain-s*-fresh (partial) | 0 of 200, 0 of 200 | 0 of 200, 0 of 200 | not run |

(Suggested, not a verdict: practised arms forgot the old kinds completely by k=64 while learning nothing
measurable on graph. Untested: whether this is forgetting, collapse, or the optimiser leaving the source basin;
no mechanism was measured.)

## Kind verdicts and roll-up

None (TIME-STOP, partial). Per PASSMARKS.md: no PASS / REFUTED / NOT-SHOWN / SHOWN verdict is stated for either
kind, and no roll-up sentence is quotable. The four complete loop runs are consistent with a kind no arm learns
(all 32 positive-rung cells 0 of 300), which, had the full 8-arm gate run, points toward V3 failing
(INCONCLUSIVE), but that gate never ran and the plain arms never completed, so this is explicitly untested, not a
finding. Rank is fully untested (0 jobs).

## Required plain statements (shown)

Sleep was not run. The torch harness had never been run before step 2 of this job. The two new kinds'
learnability was unknown before the dev gate; rank's still is (never trained). Graph's learnability by loop arms
through full 8-rung adaptation is shown above (0 of 300 on every rung, both seeds, both inits); graph plain arms
and any gate/holdout outcome remain untested.

## Load, disk, time accounting (shown)

Wall minutes per job: graph loop ~371 min each (4 of 4 complete); graph plain ~69 min each (TIME-STOPped).
Run window 2026-09-28 23:50 UTC to 2026-09-29 07:16 UTC (~466 min, inside the 480 cap). 1-min load seen: ~46 at
start, ~59 at timing pilot, peaks ~296 mid-run, ~202 at TIME-STOP (other agents' work shared the 10-core host;
this job never exceeded 4 one-thread processes). Disk: 104 GB free before step 4, 103 GB free at TIME-STOP (limit
3 GB; job wrote ~351 MB of checkpoints: 56 .pt files). Checkpoints kept local at
/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-dir-h1-heldout-20260928/runs/graph/ (56 of 56
moved there; 0 .pt files in this pushed folder). Temp dir /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.3rCdT0rj9t
removed and confirmed gone. Logs show only the benign autograd UserWarning already present in the torch selftest;
no Traceback in any of the 8 job logs.

## Claim labels

Shown: seal, sources, selftests, timing, the rung/old-kind counts above, TIME-STOP procedure. Suggested: total
forgetting of old kinds by k=64 alongside zero graph accuracy. Untested: everything about rank; graph plain full
ladders; gates, holdouts, scores, marks, verdicts, and any claim about practised-vs-fresh or loop-vs-plain on
either new kind.
