# k1h RUN-NOTE: Luna pilot (Creative answers in chat thread; written 2026-09-27 04:05 UTC, before the job starts)

## k1h-luna-pilot: 40 Luna answers and 2 Luna chat calls (Ben's Mac, Codex plan, $0; no GPU)
- Task: handoff/queue/k1h-luna-pilot-mac.md, sealed in ADDENDUM-5-luna.md (SEAL-addendum5.sha256.txt).
- Started: not yet. It runs when the Mac watcher launches it; the time is its launch line in builder-outbox status/watcher.txt.
- Machine: Ben's Mac, watcher job, launched by a free Zen builder; the Luna calls go through the Director's helper
  (codex exec, read-only sandbox, empty temp folder). Working folder: a new mktemp folder, removed at the end.
- Steps: seals (6 files), 3 offline selftests, 40 answers 1 at a time (cap 45 min), the route filter, 2 chat calls
  (cap 20 min), counts, copy back to artifacts/claude-k1h-20260926/luna/pilot, REPORT.md.
- Estimate only: the helper's selftest took 10.9 s for 3 short calls at once; an answer prompt is about 1,000
  characters and a reply is under 120 words, so a guess of 10 to 40 s a call gives 7 to 27 min for the 40 answers,
  plus a few minutes for 2 chat calls. Hard caps: 45 + 20 min for the calls (plus one try's timeout each), 90 min for
  the job.
- After it lands (here, not on the Mac): P1 and P2 by `claude_k1h_luna.py pilot-packet`, P3 by two blind judges and
  judge 3, then `pilot-score`. Results go to the Thread manager.
