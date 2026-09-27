Pilot queued — assembling the first 60 redo dialogs.
Seals check out — generating the seed sets.
Pre-flight done — checking run parameters before launch.
No director override on worker share — using W=3. Starting the 60-dialog pilot.
Pilot finished — now filtering and counting.
All counts green — copying artifacts back and writing results.
Verdict: RAN OK — Luna pilot complete, 60/60 dialogs worded, pushed path staged for the watcher.

| Mark | Count |
|---|---|
| Seal lines OK | 8/8 |
| Seed sha256 matches | 3/3 |
| Pick `left` (expected 315) | 315 |
| Luna selftest | ok (no network) |
| Routefilter selftest | ok |
| Pilot calls attempted | 60 |
| Pilot parsed | 60 |
| Pilot skipped | 0 |
| Pilot failed calls | 0 |
| `[y1tluna] call failed` lines | 0 |
| Route filter rows in / kept | 60 / 60 |
| raw_luna.jsonl lines | 60 |
| Rows parsed not null / null | 60 / 0 |
| Distinct dialog ids | 60 |
| Copy sha256 matches ($D vs worktree) | 3/3 |
| Temp tree removed, confirmed gone | 1/1 |
| Files staged (force-add, artifacts/ ignored) | 4 |

Every move: fetch ok → archives extracted to temp tree → seal 8/8 OK → seeds 2400 dialogs → split (1021 raw rows, 645 parsed kept, 1755 to redo) → pick (1755 redo, 1440 done, 315 left) → 3/3 sha256 match → selftests ok → uptime/df (33 GB free) → pilot W=3 single run 06:38:12–06:58:43 UTC, exit 0, totals `{"calls": 60, "parsed": 60, "skipped": 0, "failed_calls": 0, "batches": 3, "stopped": "done", "minutes": 20.5}` → route filter `{"rows": 60, "empty": 0, "r1": 0, "r2": 0, "kept": 60}` → counts → copied 3 files + wrote RESULTS-luna-pilot.md → rm -rf temp tree (confirmed gone) → git add -f 4 files. W=3 because no Director Luna-share override exists on origin/main, so the task default applied. No reruns.

Misses / deviations: none. No SEAL-MISMATCH, no SEED-MISMATCH, no errors, no timeout (20.5 min of 50; ~25 min of 70-min cap). One cosmetic note: the pilot log's per-dialog lines read `[glm320] ... ok` — that label is the script's own wording, recorded as-is. Branch never checked out or pushed; watcher pushes `artifacts/claude-y1t-20260926/luna`.

What it means in plain English: the new writer (GPT-6 Luna) successfully wrote the first 60 practice conversations out of 315 that the old writer couldn't finish. Every one came back usable and passed the filter. What it doesn't mean: nothing was graded or used for training here — this only proves the writer works, not that the conversations are good.

PUSH: artifacts/claude-y1t-20260926/luna
