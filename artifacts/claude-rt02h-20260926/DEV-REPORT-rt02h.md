# rt-02h dev report (2026-09-26 16:48 UTC, before the registered run; report only, nothing here changed the head)

Training data: artifacts/claude-rt02h-20260926/train/drafts_1b.jsonl. It holds 720 drafts that the 1B itself wrote
(LoRA 0, 180 prompts x 4, puzzle seed 4810), cut to their first paragraph and labelled by code. 337 were kept: 144 puzzle
requests, 127 everyday messages and 66 shared solutions, sum checks or plain sums, all with 4-5 whole numbers. No
Claude-written text and no panel was used for training.

Fit (scripts/claude_rt02h_probe.py fit, fixed by PASSMARKS): 5-fold cross-validation over draft prompts picked
layer 18 and L2 0.001. Cross-validated recall is 0.944 at a cut (1.855) where held-out drafts fire on at most 1% of
negatives. The head is artifacts/claude-rt02h-20260926/head.pt.

Report on rt-02d's dev set and the rt-02e practice set. Both were written by Claude agents, so they are never training
data. Neither was used to pick anything. Copies come from rt-02g's V1 forced reading (dev/margins_V1.jsonl).

| set | head + checked copy | rt-02d rules |
|---|---|---|
| dev puzzles read exactly | 38 of 40 | 40 of 40 |
| practice puzzles read exactly | 112 of 120 | 102 of 120 |
| dev lookalikes fired | 0 of 15 | 0 of 15 |
| practice lookalikes fired | 2 of 40 | 3 of 40 |

On the lookalikes, the head said yes to 5 of 48. The exact-number check on the 1B's copy then turned down 3 of those, so
2 fired. Of the 10 missed puzzles, 6 scored below the cut: 3 in one practice wording family ("Quick math puzzle for
you: ..."), 2 dev teacher-style requests and 1 "Numbers: ... Target: ... Go." item. In the other 4, the check turned
down the 1B's copy. What the blind panel is expected to show: reads near 90%, and lookalike fires
near the H2 bar of at most 2 in 100.
