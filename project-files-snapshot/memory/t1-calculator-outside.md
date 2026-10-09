---
name: t1-calculator-outside
description: T1 calculator-outside state: T1SDR 6-seed confirm PASS (Ben cleared mark 4 donor leak 10-09); s205 checkpoint lost; H1R folded into B3 3M
metadata:
  type: project
  modified: 2026-10-09T17:20:12.350Z
---

Ben (10-07): the calculator must be an outside tool the talker calls; if it only works inside, fix the link, never move it back in. Sealed marks: /mnt/project-files/architecture/MARKS-D0-T1-2026-10-07.md. Owner: custom reader/talker thread, branch claude/custom-reader-talker-4x309r; full history in custom_io/PASS-MARKS.md addenda 17 and 22.

- Fix chain (MARKS Amendments 3-8): T1 -> T1S span copy -> T1SI entry index -> T1SD distance-from-end -> T1SDR = T1SD + ans_drill 0.25 (code f6d724cffc, model 'tool', 3,314,132 params). T1SDR screen passed on Ben's hair-miss rule (Amendment 10).
- 6-seed confirm read 10-08 (54a12b0d0, custom_io/results/RESULTS-T1SDR.md; judge analyze_t1s --arm T1SDR --opswap results/opswap-rescore/*.json --opswap-dev sk200k_big): marks 1-3 and 6 pass (pooled-5 +0.62 vs B2, CI -0.23..+1.46). Mark 5 swap (Amendment 12: lower of the unambiguous and own-pointer readings) is 99.28-99.87 on s200-204. Mark 4 donor is 5.0-5.6 vs a flat 5 (B2 3.1-3.8). BEN CLEARED mark 4 at 8:21 AM ET 10-09 (decision card), so T1SDR confirm = PASS (17a356e62).
- s205's mark 5 can never be scored: its checkpoint was lost when both stopped Vast boxes were deleted at 10:38 AM ET 10-09 (the Vast instance list was empty at 10:50 AM ET). Only parts 000-002 are in cio-1007/parts, and they don't load. Ben 10-09: no Vast at all.
- Checkpoints: cio-1007 holds the T1-line seeds 200-201, T1SDR s200/s201/s204 and B2 at claude/b2-confirm-checkpoints. The PC copies of T1SDR s202/s203 stay on BensPC (work/results/80b...).
- H1R (H1 on T1SDR) stopped before any results; folded into B3 3M by the big-run replan. See [[h1-learned-rounds]].
- Audit 10-09 (36 findings): disclosures in custom_io/PASS-MARKS.md addendum 23 (GEN 8-letter cut never fired in T1SDR training, 0/200,000; 6,433 calculator rows lost programs; d clipped at 39). FINISHED fixes and the H1 'settled' label fix (B13-2, real, also in B3) handed to owners via coordinator: /mnt/project-files/custom-io/audit-2026-10-09/.
- K1 rung (no-hardcoding 5b8ab3fbc7): lift T1's 7-call limit to 16; it waits on the big-run plan.

**Why:** Ben's rule that the chain must work with the calculator outside.
**How to apply:** T1SDR (f6d724cffc) is the confirmed outside-calculator design; new T1-line runs only through the big-run plan. Related: [[gemma-reader-results]], [[no-hardcoding]], [[one-proven-run-rule]].
