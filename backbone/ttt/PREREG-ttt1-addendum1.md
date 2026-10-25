# TTT-1 addendum 1: a graded score for the floor case (written 2026-10-25 ~22:45Z, before the run starts; the sealed PREREG-ttt1.md is unchanged)

Labels: shown / suggested / untested.

## Why
A literature sweep (Haiku, snippets only; backbone/ttt/research-ttt-2026-10-25.md) found that every published TTT gain on ARC used a model that had
first been fine-tuned on ARC-style data (Akyurek et al. 2024: Llama-3 FT-only 5 -> FT+TTT 29 on 80 dev tasks). We found no result for a general
model with no ARC training. Our recipe also uses about 10x fewer training sequences per task (48 vs up to 500). So B, T and C may all solve
0-3 of 100 tasks, and T1 (exact solves) could then be uninformative.

## Added measure (one teacher-forced forward pass per task and arm; no change to training, decoding or T1)
`answer_nll`: the mean per-token loss of the TRUE test output given the prompt, for each arm.
- **T1b pass:** T's answer loss is lower than C's on >= 60% of the complete tasks, AND the exact two-sided sign test gives p < 0.05.
- **Wrong if:** T's loss is lower than C's on <= 50% of the tasks. Then this puzzle's own demos teach no more than another puzzle's demos.
- Reported: mean loss per arm; the same test for T vs B and C vs B.
- T1 still decides "does TTT solve puzzles". T1b only answers "does TTT learn this puzzle's rule at all", which matters for whether to try the heavier recipe.

## Next, only if T1b passes and T1 fails (untested; a later prereg)
Heavier recipe: 2-4 passes, color-permutation augmentation, and voting over the 8 symmetries at inference.
