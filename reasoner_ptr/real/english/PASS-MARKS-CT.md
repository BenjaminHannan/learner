# Copy talker vs LM talker: pass marks (fixed 2026-10-04 before any training run)

Ask: Ben approved the 18-run deciding test (timeline, 19:13 UTC 10-04 = 3:13 PM ET, "thr run has my ok"). It is the top pick in
`/mnt/project-files/reader-talker-compare/armB-report.md`: replace the second LM pass (the talker) with a small
copy-and-gate head, so the answer has to come out of the core. Fast lane: 6 paired seeds, cap about $2.

## Runs: seeds 0-5, three arms per seed, every other setting identical
All three arms use the round-6 "six" settings: `--gen 8000 --kinds 6 --block-r6`, 2000 updates of 16 rows,
`--extra-eval NEW-KINDS-R5.json --extra-eval2 NEW-KINDS2-R6.json`.
- **allptr** is the control, rerun on the same seeds. The LM talker gets the prefix, the pointers and all the prompt words.
- **copytalk** is the one change. It drops the second LM pass entirely. A head on the core's final token states makes
  the answer from three parts:
  - a start/end span pointer over the prompt;
  - a closed answer list: yes, no, and the training answers that cannot be copied from their own prompt;
  - a gate that chooses between the span and the list.
- **copytalk_nocore** is a diagnostic. It uses the same head directly on the reader output, with the core skipped.

## Judged (paired by seed, exact accuracy as scored by the runner)
- **Unseen kinds** means NEW-KINDS-R5 and NEW-KINDS2-R6 pooled (384 questions per seed).

**A. Talker swap: copytalk minus allptr**
- **PASS:** all of these hold:
  - the mean gap on unseen kinds is at least -5.0 points;
  - the mean gap on GEN-HELDOUT-R4 is at least -5.0 points;
  - at least 5 of 6 seeds are within 8 points on unseen kinds;
  - the talk stage is at least 5x faster per question (`talk_ms_per_q`, same GPU type, same fp32 runner, eval batch 32).
- **FAILS (proves the top pick wrong):** either of these:
  - the mean gap on unseen kinds is below -10.0;
  - copytalk falls below the bare 8-shot LM on either unseen set (lm_fewshot: 67.7% on NEW-KINDS-R5, 77.6% on NEW-KINDS2-R6).
- **In between:** partial, no claim.

**B. The core does real work: copytalk minus copytalk_nocore on unseen kinds**
- **REAL:** the mean is at least +10.0 points and the 95% t-interval lower bound is above 0 (df 5, t = 2.571).
- **NOT SHOWN:** a mean below +3.0. Then the reader alone does the work, and that becomes the headline.
- **In between:** partial.

## Read, not judged
- **Accuracy by answer type:** yes/no, one-word copyable, multi-word copyable, and not copyable from the prompt.
  copytalk can get a non-copyable answer right only if it is in its closed list. This is the known loss of the design.
- FRESH-EN-R3.
- Whole-question inference time (`infer_ms_per_q`).
- Trainable parameter counts.
- **allptr shuffled-core lesion on unseen kinds:** the core states come from another question of the same length.
  This is the fairer version of the zero-pool lesion.

## Rules
Never score on GOLD-PRIVATE or reserved/blind panels. The eval files are the ones rounds 4-6 already used. These marks
are committed and pushed before the first box is rented.
