---
name: month-end-results-log
description: Detailed log of month-end (330-349) results on 2026-09-24 afternoon and evening (338, 339, 333-333d, twin b, 336 seal)
metadata:
  type: project
---

State at ~17:30 UTC 2026-09-24 (month-end thread). The older running log is [[month-end-line]].

- **338 open conversation = registered FAIL** (artifacts/claude-chat338-20260924/VERIFY-338.md, main c57c5ab0b).
  - PASS: gave-up turns 3/400 (was 303); invented facts 0.
  - FAIL: grammar 95.8%/95.0% vs a 99% bar. The 1B replies are ~97% clean; the old template lines are ~82%.
  - FAIL: natural and helpful 213/400 vs a bar of 320. The 1B turns score 193/300; the agent's own turns 20/100.
  - FAIL: 3 non-teach saves. They come from the reader, and B has the same 3.
  - P vs B: 58-0-2. Memory in chat: ask_known right 3/15.
- **TWIN HANDICAP:** scripts/claude_e2e336_twin.py never turned thinking off. 400/400 of its 338 replies (and 766/768 in 339) start with `<think>`, and 201/400 never finish.
  - P338.4 (56/60 vs T) is PASS as registered, but it is meaningless.
  - Fix: scripts/claude_e2e336_twinb.py plus scripts/claude_twinb_wrap.py (run any runner through the wrap).
  - 336 uses twin b (PASSMARKS-addendum-twinb.md). P338.4b and P333.5b are registered with the same bars.
  - handoff/queue/rent-twinb.md re-runs T only ($1.50). After it lands, run blind pair judges (P338.4b) and the per-turn judge on the twin b T.
- **339 style = registered FAIL** (VERIFY-339.md): 17/40 vs a bar of 32; 2/20 control lives saved something. It is not a learned layer in 0.1.
- 333 creative: re-queued as rent-333b-creative (it was running at 16:44). Its T arm uses the old twin, so P333.5b needs rent-twinb's run-twinb arm_T. Disclose the 2-item blindness slip at its verification.
- Judge method that worked: 6 parallel blind Opus agents, with packets in scratchpad/judge338 and keys in scratchpad/keys338. Grammar canaries were caught 40/40 by both graders.
- Next: build the 338b person-question guard (no yes/no answers about the user's people), the 330c builder (think299b joined for safety), and the 336 task (rental, $4 cap).
- ~17:55 UTC (main 2f5ee992c): scripts/claude_e2e330c.py:build_330c = 330a_cre -> think299b -> 338b (scripts/claude_chat338b_agent.py, the person-question guard: an honest "not sure" instead of the 1B on recall/people questions; diverts 69/71 DEV asks and 0 creative turns, tests 3/3) -> nb-323 turn log LAST. 339 and the mouth are not joined. rent-330c-dev is queued (P330c vs twin b on DEV, report only). Next: check the DEV result, seal the code (SEAL-code), commit bank A from /mnt/project-files/escrow-331/A to main without reading it, and queue 336 on a rental with a $4 cap. The director was told, and credit may be tight for 336 (~$3.8 worst case).
- 16:55 director: agrees; asked the coordinator to get Ben to top up vast credit before Sat night. 336 SEAL-code must list claude_e2e336_twinb.py and claude_twinb_wrap.py, and the twinb addendum must be committed before 336 runs.
- ~17:50 UTC: **333 = registered FAIL** (VERIFY-333.md). All 38 routed turns got the FALLBACK line: Gen333 had thinking on, and the name filter dropped all 11 think-text candidates. The DEV rehearsal had shown 10/10 fallbacks, and I missed it. 13/30 look-alike controls were routed. The fixes are in scripts/claude_cre333b_agent.py:
  - 333b = Gen333b, thinking off. CPU dev: picks 3/3.
  - 333c = is_creative333c, which requires a cue AND a request form AND not recall. My own look-alikes: 0/20 routed vs 13/20 before.
  - PASSMARKS-333b/333c.md are registered. The queue has rent-333bc-creative (run-b, run-c).
  - 330c now joins 333 with 333b+c (main 2e5067dbb). rent-330c-dev2 re-rehearses it; rent-330c-dev ran the older version.
  - LESSON: check every 1B call site for enable_thinking=False. MiniCPM5-1B thinks by default.

Continued in [[month-end-results-log2]].
