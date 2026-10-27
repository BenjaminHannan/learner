# y1t top-up run note (Answering-from-memory thread, written 2026-09-27 00:23 UTC, while the Mac job runs)

**What is running:** handoff/queue/y1t-topup-mac.md (ADDENDUM-3 with route updates 1 and 2), on Ben's Mac, $0.
- Launched 2026-09-26 22:12:30 UTC (watcher log on origin/builder-outbox status/watcher.txt, "18:12:30 launch
  y1t-topup-mac", Mac clock UTC-4), right after lis320-pilot4-mac pushed at 22:12:28 UTC.
- Route: Reading facts' scripts/claude_lis320_glm_oclow.py (helper v1.1 with "--variant low"), 3 workers, batches of 40,
  --max-minutes 150, --max-failed 50, job time cap 170 minutes.
- Work: the 1,755 dialogs in seeds_redo.jsonl, one try each (failed or unparsed rows are written and skipped on resume).

**What can be seen mid-run:** nothing per call. raw_new.jsonl and topup.log stay in the job's temp dir until the job
copies and the watcher pushes artifacts/claude-y1t-20260926/topup/. The watcher status at 00:20 UTC lists
y1t-topup-mac as running.

**Expected finish (estimate, not measured on this job):**
- Pilot 4 on the same wrapper: 60 calls in 3.1 minutes at 6 workers (58 parsed, 0 failed), about 3.2 calls a minute per
  worker. At 3 workers that is about 10 calls a minute, so about 1,450 of 1,755 dialogs by the 150-minute mark.
- So the likely end is "stopped": "time" shortly after 00:42 UTC (the last batch finishes), pushed by about 01:00 UTC,
  with roughly 300 dialogs left. The Mac's load (73-156 in the watcher log) and the other opencode jobs may make it slower.
- If it stops on "time": the resume job (handoff/held/y1t-topup2-mac.md, same steps, reads topup/raw_new.jsonl back and
  skips written rows) goes to the queue within the same 3-worker share, with the Director told. About 30 minutes more.
- If it stops on "failed": no rerun (job rule); the errors are reported to the Thread manager and the Director.

**After the rows land (in this order):** count them; merge in the cloud (claude_y1t_topup.py merge, lis-320 check,
y1t items step, into glm2/); the G1b filter (claude_y1t_gate2.py filter); the data gate (G2/G3 seed 4034, G4 seed 4036,
blind agents, sealed marks); commit gate/GATE-RESULT.md; only then point benspc-y1t at glm2's items and ask the
Director to release it. The gate can run tonight in the cloud once the rows are pushed.

**Estimate correction (00:25 UTC, after the Thread manager's review):** the estimate above uses only pilot 4, which ran
on a quieter Mac. Pilot 5 on the same wrapper (origin/builder-outbox artifacts/claude-lis320-20260926/pilot5/RESULTS.md)
took 7.4 minutes for 60 calls at 5 workers under load 71-79, about 1.6 calls a minute per worker. So the range is:
- pilot 4 rate: about 1,450 of 1,755 done by the 150-minute mark, about 300 left;
- pilot 5 rate: about 730 done (3 workers x 1.6 x 150), about 1,025 left.
Tonight's Mac runs four opencode jobs at once, so the pilot 5 end is the likelier one. At that rate the leftover needs
about 210 minutes, more than one resume job's 150-minute stop, so a second resume (the same job under the next free
names) may follow. When the rows land, the resume is sized from this job's own calls a minute (calls / minutes in its
totals line), and the Director is told its expected length when it is queued.

**Landed (checked 01:06 UTC; origin/builder-outbox topup/RESULTS-mac.md, pushed by the watcher 00:46 UTC):**
- Totals line: {"calls": 1440, "parsed": 1360, "skipped": 0, "failed_calls": 0, "batches": 36, "stopped": "time",
  "minutes": 151.6}. 9.5 calls a minute at 3 workers, close to the pilot 4 end of the estimate, not the pilot 5 end.
- Checked here: 1,440 rows, 1,440 distinct dialog ids, all in seeds_redo.jsonl (the first 1,440 in its order), 1,360
  parsed, all model "opencode-go/glm-5.3-flash" with temperature null; 315 dialogs left.
- The job's two deviations (the tree lacked design/v3/60-listener/relation-names.txt; $PY did not split under zsh) are
  fixed in the resume job, queued at 01:07 UTC (handoff/queue/y1t-topup2-mac.md, bab560397).
- Preview, counts only, not the gate's input (the gate waits for the resume so G4 is drawn on the final items):
  merge 2,085 rows; y1t items 1,514 train and 260 dev; after the G1b filter 1,502 train and 257 dev.
