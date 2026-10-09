---
name: critical-thinking-reasoner-design
description: Reasoner design thread (10-03): PR #23, plan order F0-F4 -> C1 pipe test -> C2-C5 -> scaling; (role, modality) contract; peeking at 128 outputs allowed
metadata:
  type: project
  modified: 2026-10-03T13:44:11.268Z
---

Thread cmsg_01GSLCHTCnZxn7DhV19qcDvM7sjidCKE5Mf6Gn4MzvBzfm, PR #23 (design/next-parts/critical-thinking-reasoner-design.md + explainer, page https://claude.ai/artifact/2oMLbW6LeYG4Nz78MCUuRe).

- Shown in code: reader uses static LM word vectors per token (no context); output averages all question positions through 32 wide into 8 prefix vectors; v6 trains 4 fixed rounds but inference runs up to 48.
- Plan: free checks F0-F4, then C1 round-trip pipe test, C2 answer registers (only if C1 fails), C3 never-repeating data, C4 random-depth rounds, C5 ordered notebook few-shot, then S scaling test reusing the fair-scaling ladder (PR #18: D=256/384/512, 3 seeds).
- Interface contract: tokens [B,N,256] + (role, modality) id pair + coords + valid mask, agreed with vision PR #22; audio follows it.
- Defaults (coordinator, 13:26 UTC, under autonomy): talker stays 32 wide unless C1 fails. Reader choice belongs to the English pilot (v5; no default here).
- Ben 13:29 UTC replied "yes", read as permission to mine the 128 saved (consumed) panel outputs for design steering only, never as a score. Interpretation was stated back to him in-thread; correct this if he says otherwise.

- 13:44 UTC: PR #23 moved to the Opus thread "Critical-thinking reasoner (Opus)" (cmsg_01GSLCHTCnZxn7DhV19qcDvMSugd3UZRB74iBqU3Xc79Cn). Raw notes (online shape search, v5 cross-check with 18 edits, partial F1 analysis) are in design/next-parts/critical-thinking-notes/ on the PR branch; its README lists what is partial.

**Why:** Ben wants max critical thinking per parameter; stage one is proof of concept; north star is Minecraft by screen/keyboard/mouse.
**How to apply:** follow the plan order; one change at a time with sealed pass marks. See [[sparse-moe-approved]], [[talker-decodes-final-state]].
Contract v1 (13:55 UTC 10-03, PR #23 §6, from audio PR #25 j3): coords [B,N,3] + coord_valid per axis with per-axis neutral bias; row/col bias only within same (role, modality); time = seconds before now (<=0) in signed log buckets 0/50/100/200/400/800ms/1.6s/older; registers+actions at t=0. Relayed to vision/audio via coordinator.
Opus thread results (10-03): ranked shortlist design/next-parts/critical-thinking-shape-shortlist.md (1 think-before-calling, 2 state lanes/Hyperloop, 3 damped round step, 4 Canon). F1 shown: all 113 wrong finals are training answers; 0/64 rows with unseen answer right (memorising), so data change precedes shape changes. Pipeline code shows op chosen before any core advance (127/128 call at loop 0). Doc aligned with v5 (18 edits).
18:00 UTC 10-03 (vast PR #29, reimplementation): copy-result-to-talker path held 12 runs (unseen 81-100%); think-before-calling no gain over 6 seeds (demoted). Rule adopted in PR #23: assistant-format rows need >=6 paired seeds (baseline noise: new-wording call 81.6 +/- 11.9 SD, overall 90.8 +/- 5.9).
18:35 UTC 10-03: recipe = copy route + varied wording (180 frames): new-wording call 98.1%, overall 99.0%. Shape ideas to be judged on two-step chained problems next.
