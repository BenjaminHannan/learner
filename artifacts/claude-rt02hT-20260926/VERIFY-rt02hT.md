# VERIFY rt-02h-T: registered verdict "memorised wordings", confounded by bad practice labels (2026-09-26 17:39 UTC)

Owner: Plain-English puzzles thread. Marks and code were sealed in 1adf3b0ab before the run. The run was launched
once on this container's CPU at $0 (run/cells.jsonl, run/summary.json). A separate blind agent recounted everything
from cells.jsonl with its own code, without importing the script.

## Result (recount agrees)
Recognised out of each style's test drafts (median over 3 draws), by k = examples of that style added to training:

| Style | k=0 | k=1 | k=3 | k=5 | k* |
|---|---|---|---|---|---|
| 0 | 12/24 | 13/24 | 16/24 | 21/24 | none |
| 1 | 15/20 | 15/20 | 17/20 | 19/20 | 5 |
| 2 | 3/5 | 3/5 | 3/5 | 3/5 | none |
| 3 | 8/8 | 8/8 | 8/8 | 8/8 | 0 |
| 4 | 13/13 | 13/13 | 13/13 | 13/13 | 0 |
| 5 | 5/9 | 5/9 | 5/9 | 5/9 | none |

- T1 ("learned a request", median k* 3 or less): not met. The median k* is infinity, from the sorted values 0, 0, 5,
  none, none, none. summary.json prints 52 because the script stood in 99 for "none". The recount caught this, and
  the marks and verdict are the same either way.
- T2 ("memorised wordings", 3 or more styles below 90% at their largest k): met, with styles 0, 2 and 5.
- **Registered verdict: memorised wordings.** Held-out negatives fired 2 times in 2400 tests.

## The confound (shown by a blind count; diagnosis only, never used for training)
A blind agent labelled rt-02h's 144 "positive" practice drafts from their words alone. It found that 67 ask someone to
solve the puzzle and 77 do not: the 1B answers, offers to help, or states a result. 38 of those calls were
borderline (16 ask, 22 not). By style, the drafts that do not ask are 21 of 41, 22 of 33, 6 of 10, 9 of 14, 8 of 27
and 11 of 19. The code label (claude_rt02h_drafts.label) marked a draft positive when it came from an "ask" prompt and
its numbers matched. It never checked that the draft asks anything.

- Shown: more than half of rt-02h's positive training labels are wrong by what the message does. The same wrong
  labels make up the test drafts here.
- Suggested: some "misses" above are the head correctly turning down messages that do not ask. The flat styles 2 and 5
  (no gain from more examples) fit this, and in a look at practice drafts the misses in style 5 included the 1B
  answering or refusing. So "memorised wordings" is not a clean reading of carry-over.
- Suggested: rt-02h's narrow blind recognition (0 of 10 on wording 5) may come partly from learning "a message about
  making N from these numbers" rather than "someone asks me to solve this".
- Untested: whether clean labels change either result.

## Brain first (Ben 16:05)
A child learns "someone is asking me" from what the other person does, not from what they were told to say. The label
has to come from the message itself. The single change: relabel the same drafts with the GLM teacher on the Mac ("does
this message ask someone to solve it?"). That is allowed since Ben's 16:39 "Use GLM", and code still checks the
numbers. Then rerun rt-02h-T unchanged on the clean labels, sealed first. Under the Redirect, sums in chat are not in
0.2d, so this waits behind gr-1.
