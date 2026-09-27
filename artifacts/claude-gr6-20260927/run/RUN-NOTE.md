# gr-6 run note (PASSMARKS-gr6 "Where it runs"; ADDENDUM-gr5-3's rules)

- First STEP line: STEP start 2026-09-27T01:30:06Z (from `date -u` inside chain.sh).
- Chain PID 12014 (bash artifacts/claude-gr6-20260927/cpu/chain.sh), launched once.
- Container: this Claude Code cloud session's container, 4 CPUs, torch 2.14.0+cpu, 4 threads.
- Cap end: 2026-09-27T07:30:06Z, 6 hours after the first STEP line. At the cap the chain is stopped by exact PID and
  whatever finished is reported as PARTIAL.
- Restarts: none so far. A reclaim means a restart from the start under the same seals, noted here.
- 2026-09-27T01:30:43Z: seals and selftests passed; training started.
- 2026-09-27T01:32:03Z: answers to the Thread manager's three questions (01:31 UTC); nothing sealed was changed.
  1. The 30 format-dev messages in the pre-seal smoke are gr-5's, built by the same code lines: 10 from 358b3's free
     smoke panel (artifacts/claude-panel-rsn358b3-smoke-20260926), 10 fresh code requests (make_requests seeds
     487004-487007) and 10 rt-02d no-square dev cases. None came from the blind writer. The smoke could not have used
     the writer's material: its rows file was made at 01:22:16Z and the smoke ended before the writer's file existed
     (written 01:28:22Z, sealed 01:28:48Z in 6ba05adae). The 4 practice rows were from gr-6's own training rows, and
     the `run` smoke used 2 made-up one-word messages. So there is no overlap with the panel's 20 formats, and no
     model output on panel material was seen before the run.
  2. L6's U1 will be reported split by sep_seen: 17 formats x 3 = 51 squares whose cell separator a training layout
     uses, and 3 x 3 = 9 whose separator none does (score/gr6_score.json unseen_exact_by sep_seen / sep_new; the blind
     recount counts them too). A U1 gain is not claimed as transfer to new separators without that split.
  3. The 8 lookalikes that hold a square by read_latin are reported for L6 and G5 only (read as a square, same grid,
     none; PASSMARKS-gr6), and they are counted nowhere else. R2 is on the other 52.
- 2026-09-27T02:30:35Z: training is still running (STEP train at 01:30:08Z; about 2 hours expected).
- 2026-09-27T03:22:17Z: training finished (111.8 minutes; 1072 rows x 3 epochs; mean loss by epoch 0.1586, 0.0124, 0.0062; adapter sha256 54feb2fd..., 16568343 bytes, kept off git). The dev step started at 03:22:09Z.
- 2026-09-27T03:58:16Z: DEV-FAIL. The dev step (03:22:09Z) read 103 of 123 held-out squares exactly (the stop rule needed 111), 14 as a wrong grid and 6 as none; 139 of 139 held-out none rows as none; 51 of 64 squares in the dev-only layouts (11 wrong, 2 none); format dev 30 of 30. The dev split ran (clean 85 of 103, shared 18 of 20) and the chain stopped at 03:57:57Z as the marks fix (STEP stop). No registered task ran; the blind panel was not spent. A post-hoc breakdown of the misses on practice rows only (scripts/claude_gr6_devdiag.py, report only) started at 2026-09-27T03:58:16Z.
