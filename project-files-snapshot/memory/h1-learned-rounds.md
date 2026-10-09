---
name: h1-learned-rounds
description: H1 (model decides its own thinking rounds, required for B3): H1R on T1SDR built, reviewed, stopped; folded into B3 3M (big-run replan 10-09)
metadata:
  type: project
  modified: 2026-10-09T14:51:07.853Z
---

H1 = T1 + a 257-param stop head (model 'tool_h1', 3,277,650 params; sealed spec /mnt/project-files/architecture/redesign-ideas-2026-10-07.md sec. 8b; PASS-MARKS.md addendum 21). Built 10-07 ~3:30 PM ET by the custom reader/talker thread on branch claude/custom-reader-talker-4x309r.

- Turn = one question; rounds = T1's controller iterations (calls at rounds 1-7 as T1, rounds 8-32 think only). Stop after first round with sigmoid >= 0.5, cap 32. Training: K from {4,8,16,32} per batch, runs max(K, longest program + 1) rounds; ~1.9x T1 step cost, activations ~1.0x T1 (checkpointed).
- loops:8 (stop ignored) reproduces T1 exactly (tests: custom_io/tests/test_tool_h1.py). Tool.run got an `each` hook + `think()`; T1 is bit-identical to before.
- Queue custom_io/queue_local/49-pc-h1-screen.txt (45-48 = 8a). Run ONLY after q40 T1 screen lands and is not PROVED WRONG. Judge: `python -m custom_io.analyze_h1 --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-vast-t1 custom_io/results/49-pc-h1-screen`.
- Label: {"label":"settled"} sealed by the architecture thread (sec. 8c, PASS-MARKS add. 21 amendment 1, 0a7937f7c); queue 49 uses it.
- WAITING (5:10 PM ET 10-07): T1 screen NOT SHOWN (see [[t1-calculator-outside]]); spec 8b says H1 waits. Asked the coordinator whether H1 runs on T1 as is or waits for the fixed T1. On Vast it would run like custom_io/queue/t1a (pin 0a7937f7c or later).
- 10-08: H1R (H1 on T1SDR, 26875d754, tool_h1 3,314,389 params, PASS-MARKS add. 21 amend. 2, H-e resealed <= T1SDR+1.0) staged as queue_local/85-pc-h1r-screen.txt; judge analyze_h1 --base T1SDR. HELD 3:27 PM ET 10-08 (Ben: big money only on one run that demonstrably works, no more little tests); queue 85 stopped before results. Big-run thread (cmsg_01GSLCHTCnZxn7DhV19qcDvMCgCBY1xaDubyZbDbdwEHRK, 3:37 PM ET): keep queue 85 stopped until gate G1's first seed reads GO. Big-run replan 10-09 (no Vast): H1R stays stopped and is folded into B3 3M (no separate H1R screen).

**Why:** Ben's rule 0 (2:45 PM ET 10-07): the deployed model decides how long to think, so H1 is required for B3.
**How to apply:** run queue 49 only when the architecture thread clears it; judge with analyze_h1. Related: [[t1-calculator-outside]], [[no-hardcoding]], [[deployed-autonomy-rule]].
