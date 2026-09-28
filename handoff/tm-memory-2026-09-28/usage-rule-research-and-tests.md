---
name: usage-rule-research-and-tests
description: Ben 14:34-14:35 UTC 09-27: threads spend usage only on research, building/launching tests and reading results; TM keeps hourly review rounds
metadata:
  type: feedback
  modified: 2026-09-27T14:35:22.685Z
---
Ben, Thread manager thread, 2026-09-27:
- 14:30:29 "stop all the threads ... From now on, you should give me a prompt to give individual chats to execute". The coordinator stopped 15 threads at ~14:32.
- 14:33:49 "actually wait sotp" (cmsg_01FuvegZXjMmeUzStiEFVnEW2pbACvW6Sz1WBqeNMbfdvy).
- 14:34:08 "I want you to make sure that threads are using their usage most efficiently. THey should only do research and launching tests" (cmsg_01FuvegZXjMmeUzStiEFVnEWGmoXrrZm8peiTSSuHxEF9H).
- 14:34:35 "basically I feel like you haven't achieved enough from the amount of usage you've had".
The TM read this as "threads resume, only research and tests" (cmsg_01FuvegZXjMmeUzStiEFVnEWNUyKWoiWaK6e7e353jGvVZ). The prompts-for-chats mode was dropped by the 14:34 message. If Ben asks for prompts again, write them.

The rule sent to every thread via the coordinator (14:35):
1. Spend usage only on research (papers, code, results -> next test), building and launching tests, and reading a finished result and sending its verdict.
2. No polling: one check at a job's expected end, then at most one every 2 h. No wording-only addenda, no re-checking other threads' work, ledger/board only one line per result. Message the TM only with a verdict, a launched test or a blocker, in 8 lines or fewer. Workers only when needed. Drop drafts that won't launch soon.
3. The test rules stay: seal first, one change, data rules, money rules.
4. Nothing to launch or read -> no_reply_needed at once.

TM's own role: at 14:35 the TM told Ben it would drop per-plan reviews and check every 3 h, but Ben answered at 14:35:44 "you should still do hourly review rounds, but just have everyone else minimize usage" (cmsg_01FuvegZXjMmeUzStiEFVnEWK7T7ULcym64TNhwrGGHkzt). So the TM round (trig_01Vbo7VMT1XNHmGrXyRF1fDg) stays hourly at :11 with full reviews, plus a check that threads keep to the rule. TM messages to threads stay short so they cost little to read.

**Why:** Ben judged that too little came out per unit of usage; most of it went on process.
**How to apply:** the minimize-usage rule applies to everyone except the TM's hourly review rounds. Related: [[web-fetch-allowed]], [[vast-standing-order]].
