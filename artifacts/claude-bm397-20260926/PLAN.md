# bm-397 PLAN: a copy-only answer finaliser on the plain 1B's existing LoCoMo replies (benchmarks thread, 2026-09-26 ~02:00 UTC)

This is change 1 of GPT-6 Pro's reply to reviews/gpt6pro-benchmark-gap-2026-09-26.md. It is registered before any
finaliser output exists. Every number is "after using LoCoMo for development". The instruction below was written
once, without seeing any output. No second version will be tried on LoCoMo: any later version must be built on
non-LoCoMo material.

## Why
bm-396 measured the gap on existing replies:
- If the plain 1B's whole-chat replies (T, 27.50) were each cut to their best run of words, the gold-guided bound is
  48.30. Qwen3.5-2B is at 47.87, with its own bound at 54.15.
- T's replies contain every gold word in 402 cases; Qwen's do in 469.
- The open question: can a real shortener, which cannot see the gold, recover part of that without changing
  meaning?

## The one change
scripts/claude_bm397_finalize.py. The frozen plain MiniCPM5-1B (revision 87179e5c, greedy, thinking off, at most 32
new tokens) sees the question and one existing reply (the draft), and nothing else: no gold, no chat, no evidence.
- System: "You shorten answers. You never add information."
- User: the question, the draft, then: "Write the shortest answer to the question that uses only words from the
  draft answer. Keep every name, date, number and list item the question needs. If the draft does not answer the
  question, says it does not know, or gives more than one possible answer, write the draft unchanged."
Code enforces copy-only. The draft is kept unchanged when it abstains (the scorer's abstain rule), when the output
is empty, or when the output uses any word more often than the draft does. Categories 1-4 only; category 5 is
untouched.

Arms (drafts are existing files, sha256 in bm-391's baselines.sha256.txt and bm-395's run/):
- TF = finaliser on T (bm-390 run2/locomo_T.jsonl).
- E20F = finaliser on E20 (bm-395 run/locomo_E20.jsonl). Report only.

## Marks (fixed now)
- F1 (gain): TF − T ≥ +5.0 F1 on categories 1-4 (the sealed bm-390 scorer's per-question F1). The 95% interval
  from the conversation-level bootstrap (scripts/claude_bm396_audit.py cluster_boot, seed 396, 10k) must be above 0.
- F2 (faithful): a blind semantic audit of the rows TF changed.
  - Sample: 300 question ids, drawn with random.Random(397).sample from the sorted ids whose final_kept is
    "changed" (all of them if fewer than 300).
  - For each sampled question, the draft and the final reply are each judged by a different blind judge, who sees
    the question, the gold answer and one reply, and never learns which kind it is.
  - Labels: A = right and complete (extra words are fine); B = contains the right answer and also an incompatible
    alternative; C = partly right; D = wrong; E = says it doesn't know.
  - Counts: lost = draft A becoming C, D or E; picked = draft B becoming A (choosing between guesses).
  - F2 passes when lost ≤ 3 and picked ≤ 3.
  - A second judge relabels 60 of the items (the first 60 of the sample, both kinds), and the agreement is reported.
- PASS = F1 and F2. A pass is reported as a formatting improvement (the same facts, written as asked), not better
  memory or better answering.

## Proved wrong
TF − T ≤ +1.0. Then cutting the 1B's own drafts recovers little, and the gap is content. The next dollar goes to
evidence-conditioned training (GPT's change 4), not to more shortening.

## Report only
- E20F − E20 (same bootstrap).
- Counts per final_kept reason.
- Median scored words before and after.
- bm-396's bound columns for TF and E20F.
- The semantic label table for drafts and finals.

## Predictions
- P1 (70%): TF − T is between +2 and +12 F1 (my point guess +6).
- P2 (50%): F1 passes.
- P3 (70%): F2 passes.
- P4 (60%): at least 15% of attempted rows are kept as not_copy (the 1B paraphrases).
- P5 (70%): E20F − E20 is smaller than TF − T.

## Where it runs
With the plain MiniCPM5-1B on a GPU, roughly 3,080 short greedy calls. Wherever the Director has room: as a
fourth lane in rent-bm391, or as a small shared BensPC job. Scoring, the bootstrap and the audit happen afterwards
on CPU. Blind judges are separate agents that return labels only.
