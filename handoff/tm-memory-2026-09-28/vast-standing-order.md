---
name: vast-standing-order
description: Ben 14:05 UTC 09-27: "just use vast until I tell you not to" + "use cheap gpus, whatever gives most tflops/$/hr" - PC-waiting GPU jobs go to vast, no plan pages, from the $30 pool
metadata:
  type: project
  modified: 2026-09-27T14:07:00.317Z
---
Ben, in the Thread manager thread, 2026-09-27 (read first-hand):
- 14:05:17 "just use vast until I tell you not to" (cmsg_01FuvegZXjMmeUzStiEFVnEWAJNujr4X4uoDahik97VR46)
- 14:05:27 "use cheap gpus, whatever gives most tflops/$/hr" (cmsg_01FuvegZXjMmeUzStiEFVnEWAyqaysTANyG6bThwNZoPu2)
Context: BensPC unreachable since 12:30 UTC; the TM had told him every GPU job there was waiting.

The TM's stated reading (cmsg_01FuvegZXjMmeUzStiEFVnEWXH6HPT9BEuxETixkqzqPaN, sent 14:06:16). Ben CONFIRMED it with "yes" at 14:06:43 (cmsg_01FuvegZXjMmeUzStiEFVnEWJhrvkg8ijL5XQwW6MGfd7g):
- GPU jobs waiting on BensPC go to vast until he says stop. No plan pages for them. This replaces the 12:49 "this time" $5 waiver.
- Ceiling: the rest of the $30 pool (about $29 before 358u, from the Director's 13:09:39 credit read), at most $4 per job. Never ask for a top-up.
- Talker skill jobs marked DO NOT RUN stay out. Reasoner jobs first. Spend and pool left are reported to Ben every hourly round.
- Kits choose the best TFLOPS per $/h, but must check GPU RAM for everything they put on one card and scale TIME_CAP to the card's speed. The 358u kit pins a 5090, saves final.pt only at the end, and has a 4.5 h cap, so a slower card could lose every run.

**Why:** Ben wants GPU work moving while his PC is down, at the lowest cost per unit of compute.
**How to apply:** relay each release to the Director with the two message ids above. The TM checks each new or changed kit before release. If Ben corrects the reading, update this file. Supersedes the plan-page rule in [[thread-manager-spending]] and [[plan-before-spend]] for PC-waiting jobs only. Related: [[ben-plain-yes-is-enough]].
