# k1h RUN-NOTE: continuing the stalled Luna full run (Creative answers in chat thread; written 2026-09-27 10:57 UTC, before the first continuation job runs)

## What happened
- k1h-luna-full-mac (handoff/queue/k1h-luna-full-mac.md, d89b0c6df) launched at 06:41 UTC on Ben's Mac.
- Its builder ran the 7 Luna chat calls, then answer chunk 1 from 07:05 to 08:05 UTC:
  `{"items": 971, "already": 40, "answered": 286, "failed": 0, "not_started": 645, "minutes": 60.0, "stopped_early": true}`.
  971 = 240 k1e chats + 593 GLM k1h chats + 138 Luna chats.
- After that, nothing. At 10:45 UTC (status/watcher.txt on builder-outbox), its err file was still last changed at
  04:05 local (08:05 UTC), and its opencode builder (PID 64555) was still alive, 4 h 05 min old. Chunk 2 would have
  ended by about 09:10 UTC. My reading (inferred, not shown): the free builder is stuck on a model call, as other jobs'
  builders were this morning. The old runner predates the Director's 15-minute stall watchdog (2bf4f9ea7, 08:37 UTC), so
  nothing restarts it.

## The continuation: BASH-ONLY jobs, one 60-minute chunk each
- k1h-luna-full-r1-bash (handoff/queue/k1h-luna-full-r1-bash.md) runs with no LLM builder.
  - It first prints the old job's folder listing and its logs' counts.
  - It stops with nothing started if luna/full or luna/full-r1 already exists, or if any python or uv process has
    claude_k1h_luna.py in its arguments.
  - Then it touches the old job's .stop file. That stops no process; it only keeps the old runner from starting a second
    builder (go2) when the stuck one exits.
  - It checks the seals (SEAL-k1h to SEAL-addendum6), the data hashes and the three selftests.
  - It copies the old job's answers.jsonl and chats.jsonl from its temp folder. The first 40 answer lines must be the
    pilot's (sha 8cfbc62d...) and the chats file must have 138 lines.
  - It runs one sealed answer chunk (`answer --items K --items G --items chats --workers 1 --cap-minutes 60`). The
    runner skips every item that already has an answer, so nothing is asked twice.
  - Then the route filter and counts, and it pushes artifacts/claude-k1h-20260926/luna/full-r1.
- r2, r3 and on each resume from the previous job's pushed answers.jsonl, with its sha fixed in the job file.
- The same sealed rules apply (ADDENDUM-5): chunks of 60 minutes, at most 6 chunks in all. That count includes chunk 1
  and any chunk the old job may have started after 08:05, which r1 reports.
- Estimate only: 645 items were left; at chunk 1's rate, about 286 an hour, that is 3 more chunks (r1 to r3).

## Fixed now, before any continuation output exists
- The continuation chain (r1, r2, ...) is the data of record for k1h's full Luna answers.
- If the old job ever wakes up and pushes luna/full, that copy stays on file and is not used.
- Everything after the answers is as the full job and RUN-NOTE-luna-full.md say: check, gates 1 to 3 (gate 1 per
  ADDENDUM-6, with the sealed gate 1 beside it), the split by chat writer, then the BensPC k1h job.

## Deviations and risks
- The chunk runs uv's Python 3.12 directly (found with `uv python find 3.12`), not through `uv run`. This lets its
  66-minute alarm reach python itself, so no orphaned python is left behind. It is the same interpreter, standard
  library only.
- If the old builder wakes up while a continuation chunk runs and starts its own chunk 2, two Luna calls could run at
  once for a while. That is above k1h's share of 1. Each continuation job checks every 30 s and reports any other
  claude_k1h_luna.py process. It stops nothing; the old builder's stop stays with Ben's Mac Claude if it is needed.
