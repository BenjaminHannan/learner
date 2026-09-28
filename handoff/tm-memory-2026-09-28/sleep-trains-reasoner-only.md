---
name: sleep-trains-reasoner-only
description: Ben's decision 09-27 13:28 UTC: sleep/nights train only the reasoner; the talker 1B gets no skill training (talking-only training may still fit); applies across all threads
metadata:
  type: project
  modified: 2026-09-27T13:58:47.386Z
---
Ben, in the Thread manager thread, 2026-09-27:
- 13:25:42 "isn't it supposed to be the reasoner? Why would the talker need to be trained at all? It just talks"
- 13:26:04 "that's like saying google translate every night should train on how well it translated"
- 13:28:08 "yes" (cmsg_01FuvegZXjMmeUzStiEFVnEWF3UMqBUcaQoQMBxSh17FDr), answering the TM's 13:27:32 question "Should the talker stop getting skill training at night, so sleep trains only the reasoner?" (cmsg_01FuvegZXjMmeUzStiEFVnEWJTMMFLrJR1gAnQWKLgUfZh)
- 13:28:18 "can you make sure that happens all around. Am i crazy or is that dumb"

Meaning:
- 0.2d's sleep gate H-B / SLEEP02D moves from a talker adapter (claude_e2e02d.py:25-28, :75, :171-177) to the reasoner's nights, which Sleep research owns (slp-358n line). In force via 0.2d ADDENDUM-46 (371ae4d40), with the citation fixed in ADDENDUM-48 (098c56c56); ADDENDUM-47 lapses the talker sleep-frame line.
- The Z1 talker puzzle nights are out. dl-11's BensPC job (301) is no longer a build candidate.
- The talker gets no skill training: no puzzles, math, facts or reasoning content. Training on how it talks (not inventing facts, saying when it is unsure, reading the reasoner's output, i.e. the owed H1 hand-off) may still fit. The TM is auditing all threads (worker started 13:34).
- bm-398w STOPPED: at 13:57:41 Ben tapped "Stop it" on card cmsg_01FuvegZXjMmeUzStiEFVnEWSS7dEeE7W5AbcUmERsq2Hs (the talker trained to pick the right fact among 20 remembered lines = a skill). Benchmarks was told to hold the training, stop the data run (bm398w-mac-c5), and send a new problem-4 step first. y1t and mu-406 (talking adapters) are still kept.
- NOT decided: a learned switch between separate parts inside the reasoner. That belongs to the open experts card (the TM recommends "Plain network"; 358e4 and 358e6 lost to the dense loop, 240 and 321 vs 470).

**Why:** Ben's design is reader -> reasoner -> talker, where the reasoner is the model and the talker only turns its answer into words.
**How to apply:** reject any plan that trains skills into the talker 1B. Send skill learning to the reasoner. Related: [[ben-yes-needs-his-words]], [[brain-emulation-goal]], [[ben-moe-separate-experts]], [[fix-sleep-0926]].
