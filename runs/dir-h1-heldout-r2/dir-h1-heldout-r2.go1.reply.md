Starting sealed holdout run — verifying design and seals first.
Seal OK and sources present. Running selftests and source checks.
No competing run active. Proceeding with selftests.
All selftests pass. Running source check.
Sources verified (V1/V2 true). Load is 59, so C=4. Running timing pilot.
Wave 1 (4× graph-loop) running. Waiting (one blocking wait, ~70 min cap).
7 of 8 rungs done, all still 0/300. One rung left per job — waiting for wave-1 completion.
TIME-STOP point reached (07:14 UTC, ~30 min before cap). Stopping wave-2 jobs by exact PID and summarizing.
All processes stopped. Extracting rung tables from the completed loop jobs.
Copy-back staged. Now finalizing hashes, moving checkpoints local, and removing the temp dir.
pgrep shows 4 matches — verifying these aren't leftover training jobs.
Verdict first: **TIME-STOP, partial, no verdict.** The 480-minute cap hit with 4 of 16 dev jobs complete and 4 stopped early; no gate, no holdout, no scores, no marks.

**What completed (shown)**
- Seal: 5 of 5 OK. Sources: 4 of 4 present, check-source {"V1": true, "V2": true}.
- Selftests: kinds ok (SHA-MATCH on all panel/pool digests), marks ok, torch bench 4 ok lines + weights 1645726/1619965.
- Timing pilot: graph loop 125.5, graph plain 88.5, rank loop 36.2, rank plain 20.3 min training-only (+12 scoring). C=4 (load ~59). Projected wall ~371 min < 420, so proceeded.
- 20-min projection from rung seconds (~3800 s/rung × 8 ≈ 507 min + scoring) exceeded the cap → reported here, jobs kept running per protocol until T-30.

**Dev results (integer counts, dev panel)**
- Graph loop, 4 of 4 jobs complete (~371 min each, 0 restarts): every rung 0 of 300 at graded 14 nodes — all 36 cells (4 runs × 9 rungs incl. cold k=0), both seeds, both inits. Secondary sizes also 0 of 24 (12 nodes) / 0 of 300 (16 nodes) throughout. Old kinds: pre-arms went from 199–200 of 200 (both kinds) before adaptation to 0 of 200 by k=64 and stayed 0 of 200 at k=16384; fresh arms 0 of 200 throughout.
- Graph plain, 4 of 4 TIME-STOPped at ~69 min (k=1,4,16 scored): 0 of 300 everywhere reached; k=256+ never trained.
- Rank: 0 of 8 jobs started. No gate ran for either kind (graph 4/8, rank 0/8 adapt.json — correctly not run), no holdout opened (zero holdout.started markers), no SCORE files, no M1–M4/C1 computed. No verdict (PASS/REFUTED/NOT-SHOWN) is stated for either kind.
- Suggested only: practised arms forgot old kinds completely by k=64 while scoring 0 on graph; mechanism unmeasured. Rank fully untested. Sleep not run; torch harness never run before step 2; new-kind learnability was unknown up front.
- No job ever exited non-zero; logs show only the benign autograd warning from the selftest. No blind panel touched. Sealed code unedited. No commits/pushes by me.

**Cleanup (shown)**: 56 .pt files (~351 MB) kept local at `/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-dir-h1-heldout-20260928/runs/graph/`, 0 .pt in the pushed folder. Temp dir removed, confirmed gone. No training processes remain (pgrep empty). Disk 104→103 GB free; load seen 46→~296 (shared 10-core host, never more than 4 one-thread procs from me).

**PUSH (ready in worktree `artifacts/claude-dir-h1-heldout-20260928/`)**: RESULTS-h1.md (partial, TIME-STOP), SOURCE-CHECK.json, SHA256-h1-RAW.txt (4 adapt.json + SOURCE-CHECK.json; no holdout/GATE/SCORE exist), SELFTEST-kinds-run.log, runs/graph/ (4 adapt.json + 8 partial.json, no .pt), logs/ (8 job logs). DEV-GATE-graph.json, DEV-GATE-rank.json, SCORE-graph.json, SCORE-rank.json do not exist and are not pushed.
