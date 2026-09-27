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
