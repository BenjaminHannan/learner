---
name: gpt-scouts-20260921
description: 2026-09-21 two GPT xhigh literature scouts — counters/length (negative eigenvalues, entmax reads, LSD-first addition) and ears (role head, min-confidence abstention, renaming); bridge recipe that works
metadata:
  type: reference
---

Saved in design/v3/30-modes/45-gpt-scout-length-counters.md and 46-gpt-scout-ears.md (citations unverified). Top leads: (1) parity counters — "negative eigenvalues" line of work (arXiv 2411.12537) says make a flip-capable transition family easy to reach; matches our 43K seed-4111 diagnosis; (2) train with entmax sparse reads instead of test-time argmax; (3) next carry task = least-significant-digit-first addition, train 4–12, test to 128; (4) ears: explicit FORWARD/REVERSE role head that must agree with pointers, frame confidence = minimum over heads, calibrated WRITE/ASK threshold, entity-renaming consistency training; eval data WebRED / WikiFact (CC BY 4.0).

**Bridge recipe that works:** serial only; NO --allowedTools flag (it caused 502s); --max-turns 40 for web research (4 is too few). See [[subagents-gpt-xhigh]].
