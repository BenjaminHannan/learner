# PASSMARKS rt-02h: a learned yes/no head decides "is this a sum puzzle?" (registered 2026-09-26 15:45 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u` at writing. These marks are written and committed
BEFORE any head is trained and before any feature is taken from a draft. They are never edited; changes go in a dated
addendum before the registered run.

## Why
rt-02g showed that the plain 1B, when told a message is a sum puzzle, copies the numbers and target almost perfectly
(156 of 159 on practice data). It cannot decide whether a message asks for one: it fired on 15 of 55 lookalikes, against
3 for rt-02d's rules (artifacts/claude-rt02g-20260926/WITHDRAWN-rt02g.md). Ben's goals page puts his design (learned
parts) above a build passing on hand-written rules. rt-02h makes the decision learned.

## One change against rt-02d's reading
rt-02d's rule parser (parse_puzzle) is replaced by these two steps:
1. **Decide (learned).** A logistic-regression head reads the plain 1B's hidden state at the last token of a fixed
   yes/no question about the message (claude_rt02h_probe.ASK; every LoRA scale 0). It is trained only on the 1B's own
   drafts (scripts/claude_rt02h_drafts.py, puzzle seed 4810, first paragraph only), labelled by code from the prompt
   that produced each draft. No Claude-written text is used for training: rt-02d's dev set and the rt-02e practice
   set are report-only. The layer, the L2 weight and the cut are picked by claude_rt02h_probe.fit and nothing else:
   5-fold cross-validation over draft prompts, then the lowest cut at which held-out drafts fire on at most 1% of
   negatives.
2. **Copy (learned, code-checked).** The 1B copies the numbers and target: claude_puzzle_reader.copy_arith, forced
   "numbers:", greedy, LoRA 0. Code accepts the copy only if the numbers plus the target are exactly the message's
   whole numbers.

As in rt-02d, only messages with 4-5 whole numbers reach either step. Solving and replies are rt-02d's (solve_route,
reply_for), unchanged, so these marks are at reading level. The same reading gives the same solver input and the same
seeded tries, and rt-02d's own run measures solving.

## Test data (blind, sealed, never read)
artifacts/claude-panel-rt02g-20260926 (SEAL-panel.sha256.txt, sealed in ba43e88d2): 100 fresh chat puzzles in 10 blind
wordings (34 with 4 numbers) and 100 blind lookalikes. rt-02g was withdrawn before any run, and nothing has read the
panel. Only claude_rt02h.py run/score will read it. It prints counts only.

## Arms (one machine: this container's CPU, fp32; each run launched once)
- H: rt-02h (head decides, 1B copies).
- D: rt-02d's parse_puzzle.
- E: rt-02e's fires (rules minus stated sums).
D and E are code only.

## Marks
| Row | Test | Bar |
|---|---|---|
| H1 | puzzles read exactly (numbers and target), H | >= 85 of 100 AND >= D - 2 |
| H2 | lookalikes fired, H | <= 2 of 100 |
| H3 | puzzles fired with a reading that is not the true puzzle, H | <= 2 |
| H4 | dl-1's 300 general items that reach the head (code check) | 0 |

A message is fired when the head says yes AND code accepts the 1B's copy. rt-02h PASSES only if every row passes. A
FAIL stays a FAIL.

Report only:
- D's and E's reads and fires.
- Per-wording reads.
- The head's score distribution.
- Wall time per message.

## Decision rule (fixed now)
If rt-02h passes and fires on no more lookalikes than E, the learned reading replaces the rule reading in the chat
route, joined by Month-end as its own single change. If it fails, the rule route stays (rt-02d, or rt-02e by its own
decision rule).

## What would prove it wrong (fixed now)
- H reads fewer than D - 2 puzzles exactly: the learned decider rejects real requests that the rules take.
- H fires on more than 2 lookalikes: training on the 1B's own drafts did not teach it what a request is.

## Limits, stated before the run
- The run uses fp32 CPU features. The build runs the 1B in bf16 on a GPU, where hidden states differ slightly. A bf16
  check of the same head on dev data is owed before any join.
- The panel is one blind writer's 10 wordings and 100 lookalikes, so it says little about wordings far from these.
