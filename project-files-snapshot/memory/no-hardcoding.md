---
name: no-hardcoding
description: Ben 10-07 NO HARD-CODING rule (only tools may run hand code); B3 = all learned, built as group 1 + group 2; plan/marks files and 10-09 audit fixes
metadata:
  type: project
  modified: 2026-10-09T16:54:42.500Z
---

Ben 12:01 PM ET 10-07 (cmsg_01GSLCHTCnZxn7DhV19qcDvM8ENSBVBcxQGJAj6nqY3MXT, thread "No hard-coding + richer input", Opus ultracode): everything the model does must be LEARNED; hand-written code only inside an external tool the model chooses to call (call written as text, reply read back as text). Teaching labels/traces and scoring may be hand-written; if removing a part costs points, fix the learned link, never put the part back.

Shown 10-07: 17 hand parts run when B2 answers (regex+int, value code, span pooling, constants, slot caps, op list, in-forward executor, fixed rounds, place code, word regex, word keys, NUM/WORD/GEN renderers, units-first GEN, 108-char vocab, 208 cap).

Input results (10-07 runs, RESULTS-GAIN.md on claude/custom-reader-talker-4x309r): U0 word pieces instead of letters LOST 3.1/5.4; W1 global reader attention NOT SHOWN; U2 never ran; C0 (no step cap) = new LLM-recipe yardstick, B2-C0 +6.2/+6.9 (claim stands); EGE 6-seed +2.67 over B2 (leak 6.6 vs 3.6). Cipher collapses come from removing the 9-letter window.

10-09 state (FINISHED-MODEL-2026-10-09.md wins over the 10-07 notes): Gemma = main reader (Ben 10-08), window kept on top (Ben 10-09), 2,000-letter inputs, calls any round, ONE learned stop (H1) per answer; question never re-read. B3 built in two groups (big-run PLAN G2): group 1 (any-round calls incl. K1, Gemma+calculator, 2,000 letters, H1; PR #56, not run); group 2 = N1, O1 (+ call writer writes op name as letters), P1, V1, L1, ST1 (being built since 12:15 PM ET 10-09). Per-rung screens and the 3M B3 confirm (PLAN 3c) are superseded by G2 marks; 3c.8 audit (inputs = letter ids + Gemma states only) and 3c.9 caps still define "all learned"; 3a link checks = bisect readouts. Counts now: INVENTORY-B3-2026-10-09.md (stop 0, arith 2, reading 6, writing 4, new kinds 6; pass 0). Group 2's 3M marks sealed in big-run PLAN sec. 5 "G2 step 2b" (12:55 PM ET 10-09), incl. inventory count 0. PENDING: re-run the inventory count once group 2 is built.

10-09 audit fixes (B05-1..19, B18-17..22) applied ~12:45 PM ET to PLAN-AND-MARKS, INVENTORY, INPUT-UNITS, gpt prompt, and the explainer page https://claude.ai/artifact/Y7C596ZUvFJq8TVPbTx9Fn (staircase now D0, T1, group 1, group 2's 7 parts, B3); PR #49 (branch claude/project-thread-tjfi92).

Files: /mnt/project-files/no-hardcoding/; page source in this thread's scratchpad nohc/page/learn-it-all.html (copy in repo design/no-hardcoding/page/).

**Why:** Ben wants a model that does all the work itself, as the path to beating Minecraft like a person.
**How to apply:** never propose a hand-written feature on the model's path; frame new parts as learned or as tools. Related: [[deployed-autonomy-rule]], [[finished-model-source-of-truth]], [[gemma-reader-results]], [[scaling-bar-ben]], [[whole-model-roadmap]].
