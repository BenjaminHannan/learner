---
name: reasoning-research-0924
description: Reasoning research 2026-09-24 (workflow + follow-up): ranked next moves, loop-reasoner growth ladder, Ben's 5 loop asks; rsn-350 3x plain FAIL confirms size isn't the bottleneck
metadata:
  type: project
  modified: 2026-09-24T22:50:11.883Z
---
Reasoning research thread (cmsg_01FuvegZXjMmeUzStiEFVnEWQxRUwopSKr6GroxN3JPfaa), delivered 2026-09-24 ~19:55 UTC. Report: reviews/reasoning-research-2026-09-24.md (main 1cad3f721), copy at /mnt/project-files/research-2026-09-24/reasoning-research.md. Nothing run.

- Bottleneck: picking (299b: right sample on 48/60, vote 38) and setup errors. The 30M net has learnability failures (compare = XOR label, at chance; loop copy phase never trained).
- Ranked moves: A learned verifier LoRA picks among the 1B's samples (≤$2.5); B 1B writes notebook programs + exact executor + provenance gate (~$0); C make loop trainable ($0 gate on checkpoints: collapse / ignored state; then per-pass loss or Geiping sandwich norm + 10x lower lr, ~$1); D RFT sleep replay after A; E compare fix (direction curriculum vs binding head, 2x2 diag first).
- Growth ladder for own loop reasoner: 30M fix → hop-tied passes → ~100M → ~300M → retrofit loop inside MiniCPM5-1B (the only affordable route to English).
- Ben's 19:23 asks (adaptive halting, learn rules, real-world envs, MiMo-V2.6 RL, API teacher): halting only after the loop learns (extra passes flat today: loop-s2 916/1200 at 6 and 12); MiMo-V2.6 is real (dynamic sampling, length penalty only among right tries fit $4); API teacher only writes practice data, code re-solves gold; Anthropic/Google/OpenAI terms forbid training competing models, Google API needs age 18+; MIT MiMo weights are the low-risk teacher.
- rsn-350 (sleep thread, 3x plain 91.6M, 296 recipe) = registered FAIL (artifacts/claude-rsn350-20260924/VERIFY.md): fresh 211/209 vs 225/217, three-step 0/30. Size is not the bottleneck now; lr/steps were tuned for 30M.

**Why:** Ben wants the reasoner "much bigger"; evidence says fix trainability first.
**How to apply:** the sleep thread owns loop runs; start from proposal C's $0 gate before any growth. See [[rsn-299-think]], [[brain-emulation-goal]].
