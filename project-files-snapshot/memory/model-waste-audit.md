---
name: model-waste-audit
description: Oct 5 audit of what makes the model worse/slower: loud thinker notes (1,300x), fake MoE (1.6M of 9M live), constant lr, tests T1-T5 sent to coordinator
metadata:
  type: project
  modified: 2026-10-05T22:38:57.521Z
---

Thread "model waste audit" (Ben 22:08 UTC 10-05 = 6:08 PM ET, used Hearer/Reader split as the example). Page https://claude.ai/artifact/8Ugiyc1sqL57wNZihHosBo; full ranked list + marks /mnt/project-files/model-audit/AUDIT-ranked-2026-10-05.md (+ probe_prefix_cpu.json, inspect_weights.json; CPU only).

New shown facts (not in blocker logs before):
- LOUD NOTES: main2's 8 exit/front vectors average 964.5 long vs 0.74 per word (1,307x; parent0 391 = 530x). The LM never changes them (cos to input 1.000 all 16 layers), their gradient is 650x weaker than a word's and exactly sideways, answer attention on them 22-42%/layer. Exit weights grow bootstrap->parent0->main2, wd 0. Harm UNTESTED (test T2: RMS-normalise exit, gain 0.74).
- FAKE MOE: main2 routers exactly 0, expert0 == expert1 bit for bit, experts 2-7 never trained (zero router + equal clones = zero router gradient, self-locking). Live distinct core ~1.58M of 9.01M. So Ben's sparse-MoE approval ([[sparse-moe-approved]]) never took effect in the main thinker. Fresh planner cores do train experts.
- Input cap in skills runs is 64 tokens (skills_pretrain_v1.py:117), not 160.
- 4 of 8 thinker heads see only +-1 token (claude_fewex_net.py:23/42/44, grid-puzzle origin).

Tests sent to coordinator 22:40 UTC 10-05 (marks fixed 6:40 PM ET): T1 main-model lr decay (CRDC + --lr-final-mult 0), T2 quiet notes, T3 global heads (after PXH), T4 speed profile + Hearer cache (Sonnet, PC), T5 fold experts (exact).

**Why:** a future thread asking "why is the core so weak / is it really 9M" needs these without re-probing.
**How to apply:** count the thinker as ~1.6M live when comparing sizes; check T1-T5 status in the blocker thread before proposing them again. See [[ultracode-blocker-findings]].
