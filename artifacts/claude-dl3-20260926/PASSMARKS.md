# dl-3: does replaying the base's own general answers each night stop the slow forgetting dl-2 showed?
(Fix-sleep thread. Registered when this file is committed, before the run.)

## Why
- dl-2 was a registered PASS (artifacts/claude-dl2-20260926/VERIFY.md). A week of copy-practice nights raised right
  guesses on fresh puzzles from 64 to 237 and 249.
- But on dl-1's 300-item general panel the nights LOST items the base got right:
  - 5-7 after night 1;
  - 26 of 200 after night 7, on both seeds.
- Net harm stayed ≤ 0 only because format gains covered those losses, and the wrong-answer placebo also got the gains.
- An outside review Ben posted (01:54 UTC 09-26, section 11) says to measure forgetting as old right answers lost,
  apart from gains.
- Ben's bar is that nights almost never make the model worse. His 00:03 UTC note asks for replay mixed with old.

Code: scripts/claude_dl3_replay.py (the docstring is the method). It reuses claude_dl1_nights unchanged. The model is
plain MiniCPM5-1B, thinking off, no download.

## ONE change from dl-2's S arm: replay
Each night also practises as many REPLAY pairs as it has puzzle examples. A replay pair is a general question plus
an answer, both made once before night 1:
- The question was written by the BASE 1B: 1,500 samples at T 1.0, alternating two fixed asking prompts (a curious
  student's question; a search-engine question), deduplicated. A question is dropped if it:
  - has no question mark;
  - contains a digit;
  - contains any word tied to the harm panel's topics.
- The answer is the BASE 1B's own greedy answer, first 96 tokens. A cut answer is trained without an end-of-reply
  token, so it never teaches stopping mid-sentence.
- No pair is Claude-written, and none comes from the harm panel.

Puzzle and replay pairs are shuffled together through dl-2's loop: 3 epochs, lr 2e-4, batch 8, answer-only loss.
- S = dl-2's night, unchanged.
- A = S + replay.

Setup:
- Seeds 4 and 5, 7 nights each.
- Day: 150 fresh puzzles, greedy + 30 guesses, exact checker.
- TEST: new seed 3790, 100 fresh puzzles × 20 guesses.
- HARM: the same 300 items.
  - "lost" = right at base and wrong after the night.
  - "gained" = the reverse.

## Marks (on A; S is the reference)
- **F1 forgetting cut:** A's night-7 lost ≤ 0.5 × S's night-7 lost (sums over seeds), and each A seed is below each
  S seed.
- **F2 low forgetting every night:** at most 1 of A's 14 nights has lost > 10 (5% of the base's 200 right).
- **F3 still learns:** A's night-7 lucky ≥ 2 × L0 on each seed, and A's gain over L0 ≥ 0.8 × S's gain (sums over
  seeds).
- **F4 nights rarely hurt the day's work:** at most 1 of A's 14 nights has TEST lucky more than 15% below the night
  before. Night 1 is compared with L0.
- **F5 variety kept:** A's night-7 puzzles reached ≥ base, on each seed.

Verdict:
- PASS = F1-F5.
- INCONCLUSIVE if L0 < 10, if S's night-7 lost sum < 20 (nothing to cut), or if the replay pool has < 100 pairs.
- Proved wrong: A's night-7 lost ≥ S's on both seeds.

Reported, not marked:
- gained, net harm, greedy solves and KL per night;
- lost and gained against the NIGHT BEFORE (per-item panel scores are saved every night);
- A nights with lost > 5 (2.5%, the outside review's bar);
- the replay pool size and 10 sample pairs;
- lost by panel kind.

## Changes made after Ben's second outside review (02:11 UTC), before registration
- F2 was lost > 15; it is now > 10.
- F3's second half was "A sum ≥ 0.85 × S sum"; it is now a gain-based 80%.
- Lost-vs-previous-night and the 2.5% line were added as report-only.
- The review suggested replaying older PUZZLE practice at 25% with total steps fixed. Not taken, for two reasons:
  - What was forgotten is general answering, not puzzles.
  - Fixing total steps would practise each new win fewer times. That is a second change.
  The 25% share with fixed steps is a follow-up if A passes.

## Limits stated before the run
- One kind of work (number puzzles).
- The panel is short general questions, not full conversation.
- Replay adds training steps as well as old answers. A cut in losses shows the replay night forgets less, not which
  part of it did.
- 14 nights per arm cannot show "1 in a billion".
