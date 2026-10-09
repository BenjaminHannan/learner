---
name: register-bug-8a-caps
description: Bug found 10-08/09: caps.apply() skipped the lazy ledger import, so 8a B2 and 8a-G EGE ran N_REG=9 / GEN_MAX=8; G1 is the fixed re-run
metadata:
  type: project
  modified: 2026-10-09T14:52:14.570Z
---

Found by Ben's 8b side session (branch claude/nice-lamport-al1gwo), cause confirmed in code (build commit 612f5c5b0 on claude/project-thread-f1to6a): `caps.apply()` skips lazily imported modules, so every 8a B2 run and 8a-G's EGE arm used N_REG=9 / GEN_MAX=8 instead of 36/35, and GEN targets were cut to 8 letters. Fix = overlay `g8b/overlay/custom_io/g8a/caps.py` (sha256 3da2dfbb...). The 8a "B2 does not scale" fail is real for the model that ran, untested for the model specified.

G1 = 8a-G re-run with the fix: seeds 400/401, 3M and 10M, G-B2 vs G-PT, on the PC. Readout GO if gain-difference >= +1.0 on both seeds and G-B2 gains on both; STOP if <= 0 on both. 3M s400: G-B2 73.01 vs G-PT 67.12 (G-B2 3M takes ~6.5 h on the PC, G-PT 2.4 h).

Thinker sizing: one block at width 512 = 4,624,281 params, so 21 blocks = 97.1M (30 blocks = 139M).

**Why:** the diagnose prompts in whole-model-roadmap/reviews/ rest on the unfixed premise.
**How to apply:** judge any size test with the fix; don't cite 8a's fail as evidence against B3's scaling. See [[one-proven-run-rule]].
