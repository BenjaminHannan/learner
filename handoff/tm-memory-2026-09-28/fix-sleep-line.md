---
name: fix-sleep-line
description: Fix-sleep thread (cmsg_01FuvegZXjMmeUzStiEFVnEWDjPgDy9L2RU9kjo7B9cnHs) state 2026-09-25 ~06:50 UTC: slp-360..368 verdicts, what is queued, key limits
metadata:
  type: project
  modified: 2026-09-25T03:53:35.753Z
---
Owns sleep as self-improvement (Ben 00:32 UTC 09-25). Road map: design/v3/30-modes/365-sleep-roadmap.md (status table at end).

- 360 scrap layer (guessed rows go to <state>/scrap360, not notebook): registered FAIL on a mark typo; behaviour OK.
- 361 whole-night undo: PASS. 367 idle sleep (sleeps when idle, never inside a turn): PASS 5/5, recounted.
- 364 self-check gate: registered FAIL (13/20 bad nights caught, bar 18; 0/20 clean rejected; sleeper's own flag 0/20).
- 368 write lock (main notebook refuses writes while the sleeper runs): PASS 5/5, recounted. It fixes 364's 2 leaks.
- 366 six-night scorecard: PASS 5/5, recounted. Limits: both seeds are the same world, and taught facts are sampled (120 cap).
- 364b gate v2: registered FAIL (caught 17/20, but its deep-copy sandbox broke later teaching on 20/20 honest nights).
- 364c gate v3 (forked sandbox): registered FAIL on 39/40 main-log mark (one fault wrote the file directly); caught 18/20 vs v1 11/20, 0/20 honest rejected; missed both made-up-answer faults.
- 369 restore (puts back main notebook files + objects after a night that changed them): PASS 5/5, recounted.
- 364d gate v4: registered FAIL 15/20 (its L2/U rules fired on no bench night). 364e gate v5 (+ other phrasings F, yes/no Y, two-step E, fact-less people Z): registered FAIL 11:00 UTC, 17/20 vs v1 9/20, 0/20 honest rejected, replies unchanged; misses = spelled-out word questions, extra word installed without evidence, reverse "Whose R is X?". Best stack: 360+368+369+361+v5.
- 363 practice school (the reasoner trains on puzzles built from taught facts) is sealed and queued for BensPC as handoff/queue/slp-363-train.md.
  - Arms: NOSLEEP, PLAIN, PLACEBO (scrambled grades), SCHOOL; seeds 2; --base 296 --arm plain.
  - Judged on a school panel from world 364417. Never generate that world locally.
- KEY LIMIT (336b rental): today's word-route sleeper learns only from queued bare word-question episodes. Ordinary chat never queues 8, so 0/360 sleeps attempted learning. 360/361/366/367 worlds are built to feed it; 363 is the path to real learning.
- Local runs use the combined tree in the session scratchpad (builder-outbox + main). base-seed4102.pt and self122_head.pt were rebuilt there.

**Why:** a new session must not re-run or re-claim these.
**How to apply:** read 363's RESULTS when BensPC finishes. 362 (re-read the day) stays parked until the reading thread's reader improves. See [[sleep-research-2026-09-24]], [[month-end-results]].
- Ben 11:03 UTC 09-25 (answering the gate-vs-learning card): "Switch to learning, but I think as long as sleep improves the model, it's fine." So: stop the self-check gate chase (best = v5); sleep's bar is that it improves the model. 363w (school night inside idle sleep, tiny CPU) = registered FAIL on no-harm (seed 1 -20/600 on panel; narrow self-check). 363x (+ fixed general set vs start) = PASS 5/5 seeds 3-4, recounted; no learning claim. Learning test = 363 on BensPC (6th in queue 11:36). Then run the 363x night at full size.
- From Creative (15:06 UTC, blurt-3 PASS, artifacts/claude-blurt2-20260925/VERIFY-blurt3.md): sleeping on repeated KNOWN answers collapsed the 1B's guess variety (puzzles reached 27 -> 3-4 of 66); sleeping on new checked hits kept it. Relevance: school nights should mix fresh checked items, not replay a few known ones.
- Ben 19:38 UTC 09-25 (via coordinator): until ~23:40 UTC threads ask him NOTHING; take own initiative; shared $7 rental budget for the window (tell Director job+cap before launch; ≤$4/job). BensPC free to use. New model downloads still wait for Ben.
- 20:05 UTC 09-25: dl-1 registered (be716e08c): 1B, 3 nights, arms S copy / R REINFORCE group-baseline / Z shuffled rewards; 300-item harm panel (flips) + KL; rental rent-dl1 $3 cap (Director told). Research note reviews/sleep-nights-research-2026-09-25/REPORT.md (Q8: per-kind adapters for fast day's-work gains). Road map 365 status 20:05.
- 20:01: Director cut rent-dl1 to $1.50 (stop $1.35, ~2.3 GPU h at $0.57/h); the $7 window is full. If dl-1 stops early, finished arms are kept (order S,R,Z x seeds 0,1); rerun missing arms on BensPC.
- 20:28: lis-319 whole-conversation reader = verified PASS (main 69bce2363). For a night re-read (362, parked): Reader319.read_dialog(pairs) in scripts/claude_lis319_read.py, weights BensPC C:/Users/benja/lis319/work/run/merged, read-only, 0.995 gate.
- 20:34 Creative: ask-24 PROVED WRONG. A hits-only night erased "none" (0/78 impossible); adding 40 code-verified "none" examples made it say none everywhere (78/78 impossible and 70-71/71 solvable). Lesson for nights: "can't" examples must come from code proof or a judge, never the model's own word, and they need solvable twins weighted to teach WHEN.
- 21:33 Creative (main 7355c96de): blurt-5s PROVED WRONG. Exact-solver answers to newly won puzzles did as well as or better than own lucky hits (fresh 184, solved in 30 tries: W 110 mean, E 118, base 77). Good night material = right answers on NEW puzzles from any exact source; repeats collapse coverage. blurt-4 hindsight PROVED WRONG (H 140 vs W 221 lucky; wrong relabels P equal), though puzzles hit rose (lead only).
- 00:1x UTC 09-26: dl-1 = registered FAIL (verified, main 6e250996e): REINFORCE lost; copy practice S improved all 6 nights (lucky 69->160/169, reached 35->44/58, general panel 200->210-229). dl-2 registered (7 copy nights S vs wrong-answer placebo P, seeds 2,3, marks W1-W5), rent-dl2 $2 cap (Director told). Split with Sleep research (23:58): I own 1B nights; they own small-reasoner nights (358).
- 00:20 09-26: slp-363 VOID (never ran: sealed notebook log opens in text mode, so Windows \r\n fails read-back) and RETIRED (relations; small-reasoner nights now belong to Sleep research's 358). Note artifacts/claude-slp363-20260925/STATUS-void.md.
