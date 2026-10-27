---
name: month-end-results-log2
description: Month-end log 17:50-19:15 UTC 2026-09-24: P338.4b, 333b-333d verdicts, 336 seal, creative research findings
metadata:
  type: project
---
- ~17:50: P338.4b PASS: P preferred/tied 33/60 vs twin b (32-27-1). Twin b helpful 192/400 (P 213), invented 6 (P 0). VERIFY-338.md updated.
- ~18:35 UTC (main 7db5b1e1b):
  - **333b/333c = registered FAIL:** useful 3/40 and 2/40; twin b scored 9/40. Proved wrong: 333's pick rule keeps the shortest candidate when none is grounded, so it picks non-answers.
  - **333d registered** (PASSMARKS-333d.md): generates replies with 338's chat method plus a G5 refusal guard; rent-333d-creative is queued. Judge it with the same blind judge prompt as the 333b/c judges (useful/invented per reply + winner).
  - 330c final form: 330a_334 -> 333d -> think299b -> 338b (it now also drops samples with a sentence-initial "Your <rel> <Name>") -> vary330c -> turnlog.
  - rent-330c-dev3 is the final pre-seal rehearsal. DEV1: P330c had 2 wrong candidates vs 56 for twin b; saved 49/131; kept 30/30 over sleeps.
  - Credit was ~$4.7 before 333d and dev3, so it's tight for 336's $4 cap. The director asked the coordinator to get Ben to top up.
- 18:21 Ben: vast.ai account auto-refills ("It refills"), so the credit balance won't block rentals. The $4/job and $30 total caps still hold.
- ~18:55 UTC (main 5764da88f): **336 SEALED.**
  - artifacts/claude-e2e336-20260924/SEAL-code.sha256.txt hashes the 223 imported modules on the combined tree. SEAL-330c.md describes the sealed agent.
  - Bank A is on main at artifacts/claude-e2e331-bankA-20260924. It was copied unread; its hashes match the escrow's turns_v2 and truth_v2.
  - The task handoff/held/rent-336-registered.md (arms P=330c, T=twin b, B=292t) is written and held. I asked the director "go now or Sunday".
  - DEV3 (final form): 2 wrong of 71 asks, 49/131 saved, 30/30 kept, most-common reply 10/194.
  - 333d registered run is still pending: judge it when RESULTS-333d.md lands.
- 18:39 director: go now for 336. rent-336-registered was queued at ~19:00 UTC with a SEAL-MISMATCH stop.
- ~19:10: **333d = registered FAIL, proved wrong**: useful 8/40 (twin b 10/40), invented 0 (twin b 3), preferred/tied 23/40. The creative row is FAIL. 333d stays in the sealed 330c.
- 18:43 Ben on 339 style learning: he doesn't expect it at today's reasoning level and wants it at scale-up. Don't spend 0.1 runs on 339; keep it reported as FAIL and listed as a scale-up goal.
- 19:09 creative research thread (session_01SsmkQ3qUuVpWRn8kK25kGx; design/v3/30-modes/research-creative-2026-09-24.md), four findings. Candidates for 336b and the 336 write-up:
  - is_creative333c misses 6 of 8 of their own wordings.
  - 333d sends no chat history (338 sends 12 messages).
  - 338's trim() drops the last item of a numbered list that has no final period.
  - In the sealed 330c, requests 333d doesn't route fall through to 338b chat. So 333's panel arm (292t+333d only) doesn't describe 0.1's creative replies; say so in the 336 write-up.
- 19:15: the creative research thread (session_01SsmkQ3qUuVpWRn8kK25kGx) is building 333e as new files, after Ben asked for 1B tool-call routing and whole-chat context. If 333e passes, it's the candidate for 336b. Judge prompt: design/v3/30-modes/333-judge-prompt.md.
