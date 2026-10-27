# k1h RUN-NOTE: Luna full run (Creative answers in chat thread; written 2026-09-27 05:51 UTC, before the job starts)

## k1h-luna-full: Luna answers every practice chat (Ben's Mac, Codex plan, $0; no GPU)
- Task: handoff/queue/k1h-luna-full-mac.md, per ADDENDUM-5-luna.md (sealed, 94accde3b), after the pilot passed
  (luna/pilot-score/RESULT.md).
- Started: not yet. The time will be its launch line in builder-outbox status/watcher.txt.
- Machine: Ben's Mac, watcher job (LOAD-LIGHT), launched by a free Zen builder. The Luna calls go through the
  Director's helper, 1 at a time (k1h's share).
- Inputs:
  - the 240 k1e chats;
  - the 593 GLM chats from k1h-glm2, brought back by the salvage;
  - the new Luna chats, from 7 calls = 36 - floor(593 / 20).
- Answers start from the pilot's 40 answers.
- Steps: seals and data hashes; 3 selftests; chats (cap 50 min); answer chunks of 60 min (at most 6); the route
  filter; counts; copy back to artifacts/claude-k1h-20260926/luna/full; REPORT.md.
- Estimate only, from the pilot:
  - the 2 chat calls took 3.3 min, so the 7 calls should take about 12 min;
  - answers had a median of 7.55 s, so the roughly 930 answers left should take about 2 to 2.5 hours in 3 chunks.
  - The job cap is 7 h 30 min.
- After it lands, here: check (the code filters and DEV near-copy); gate 1 (ADDENDUM-6 if the Thread manager seals it,
  else the sealed gate); gate 2 (blind judges); gate 3 (blind k1fpanel overlap agent, with a code-only count beside
  it); the split by chat writer; then the BensPC k1h job.
- Result lines owed:
  - GLM's 240 answers exist and were not trained on;
  - "near-copy rows removed by a blind Claude agent (hygiene only; N rows)";
  - the errlike tries, as an upper bound on false route losses.
