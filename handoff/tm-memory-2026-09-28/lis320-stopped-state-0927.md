---
name: lis320-stopped-state-0927
description: Where lis-320 (Reading facts) stood when Ben stopped all threads at 14:30 UTC 09-27; how to resume the Luna full run
metadata:
  type: project
  modified: 2026-09-27T20:37:14.357Z
---
Ben stopped all threads at 14:30 UTC 09-27 ("give me a prompt to give individual chats to execute").

lis-320 state at the stop:
- Luna pilot 8 PASSED every mark (PILOT-REVIEW "Pilot 8", 8d70eb699).
- Full run: seed 324, 6000 dialogs. BASH-ONLY chunk jobs handoff/queue/claude-lis320-luna-cK-mac.md; chunk mechanics in ADDENDUM-11 and ADDENDUM-12 (6 parallel calls from chunk 2; back to 3 on any rate-limit sign).
- Chunks 1-4 landed on builder-outbox (full-luna/chunkK/): 792 of 6000 worded, 0 failed. Chunk 5 was queued at 14:06 UTC and not collected.
- Each chunk words about 200-230 dialogs at 6 calls. Chunk K+1 = chunk 1's file with K changed, LW=6, luna3.py, seals 6-12. The chain loop and its template live in the thread session's /tmp/claude-0/chunk; a new session must rebuild them from the chunk 5 file.
- FINAL, 19:58 UTC stop: chunks 1-10 landed (chunk 10 as claude-lis320-luna-c10b-mac, after c10's Mac git fetch failed): 2028 of 6000 worded, all parsed, rawcheck2 OK. No chunk 11 is queued; the next one is K=11 (copy c10b's file, change K).
- 14:34 UTC: Ben lifted the stop but set a usage rule: only research, launching tests, and reading results. The chain resumed from chunk 5 and wakes the thread only on a stop or at the end.
- Not done: the Mac DATA job (DATA.md with a sha256 pin); the vast training kit (a draft was never committed); training; blind judges; R1-R7/C1.
- Wrong-as-fact (uw-2) may train on an early cut: chunks 1..K with worded_ok >= 1500, agreed 10:2x UTC.
Related: [[ben-talks-only-to-thread-manager]]
