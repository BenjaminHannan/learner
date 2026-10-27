---
name: talker-swap-lfm
description: Ben 19:27 UTC 09-27 chose "Swap to LFM": the 0.2d talker becomes LFM2.5-1.2B (was plain MiniCPM5-1B); evidence c1-dl
metadata:
  type: project
  modified: 2026-09-27T19:28:11.123Z
---
**Decision.** Ben tapped "Swap to LFM" at 19:27:28 UTC on 09-27, on the TM decision card cmsg_01FuvegZXjMmeUzStiEFVnEW6CLKBsytdgAep4Pm1h5rMn ("Swap the talker from MiniCPM5-1B to LFM2.5-1.2B?"). That is his goals:96 architecture yes, for the talker only. The reader, the reasoner and sleep are unchanged.

**Evidence (TM-verified).** c1-dl: artifacts/claude-c1dl-20260927/RESULTS.md at 3b5717258. DEV practice chats, 60, one judge model. Talker path build_talker02d plus the W block, on LFM.
- vs plain LFM: 22-34-4 (-12, PASS exactly at the bar)
- vs MiniCPM: 57-3
- vs Qwen3.5-2B: 33-26-1
- Made-up user details: DL 5 vs Q 30, DL 4 vs T 17
- y1u: plain LFM 35 right / 18 wrong / 1 of 10 "don't know" on y1t DEV (MiniCPM 26/24/2)

**Follow-ons sent 19:28:**
- Month-end: additive 0.2d addendum (TALKER02D = LFM, same path).
- Biggest model inside is now 1.2B (goals:86-87).
- MiniCPM-only adapters (mu-406, y1t DOUBT02D) don't load. Making things up: test on LFM or stand down. Answering from memory: y1t-doubt-on-LFM is the build candidate. Wrong-as-fact: stand down unless it has a new LFM test.
- Benchmarks: "build beats plain LFM" is now the key same-size row.

**How to apply:** treat LFM2.5-1.2B as the talker from now on. The talker still gets no skill training ([[sleep-trains-reasoner-only]]). The final check is still the sealed chat panel.
