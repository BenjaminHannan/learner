# rt-02g WITHDRAWN before its registered run (2026-09-26 ~15:35 UTC)

Owner: Plain-English puzzles thread. rt-02g was never run on its blind panel. No rental was rented and nothing was spent.
The $0.40 goes back to this thread's $2. The blind panel artifacts/claude-panel-rt02g-20260926 has not been read by any
model, script or person since it was sealed (ba43e88d2). It stays sealed and unread; a later learned reader may use it
if that experiment names it in its own marks before it runs.

## Why: practice data shows the plain 1B cannot tell a puzzle request from a message that only contains numbers
Before sealing the code I ran the reader on dev and practice data only. These were rt-02d's 40 dev puzzles and 15 dev
lookalikes, plus the blind agent's practice set in artifacts/claude-rt02e-20260926/practice: 40 wordings × 3 puzzles and 40
lookalikes. Everything ran on CPU in this container (fp32). The files are in dev/.

Registered prompt (greedy, exactly as in scripts/claude_rt02g.py):

| | 1B reader | rt-02d rules |
|---|---|---|
| puzzles read exactly, dev | 39 of 40 | 40 of 40 |
| puzzles read exactly, practice | 112 of 120 | 102 of 120 |
| lookalikes fired, dev | 4 of 15 | 0 of 15 |
| lookalikes fired, practice | 11 of 40 | 3 of 40 |

The mark G2 allows at most 2 fires in 100 lookalikes. The reader fired on 15 of 55, and 0 of its readings were the
wrong puzzle.

## What else I tried (dev + practice only, split fixed before looking)
The tune half was dev plus the odd-numbered practice wordings and lookalikes. The check half was the even-numbered ones.
Each variant got a confidence cut: the 1B's score for starting its answer with "numbers" (or "yes") minus its score for
"none" (or "no"). The variants were:
- V0: the registered prompt.
- V1: a stricter instruction listing what is not a puzzle, with 12 examples.
- V2: a plain yes/no question using V1's examples, with V1 doing the reading.

Totals below are the tune and check halves added together. There are 159 puzzles and 48 lookalikes with 4-5 numbers
(the other 7 never reach the 1B). The full sweep is in dev/sweep.txt.

| setting | puzzles read exactly | lookalikes fired |
|---|---|---|
| rules (rt-02d) | 142 of 160 | 3 of 55 |
| V0, no cut | 153 of 159 | 19 of 48 |
| V0, cut 2.0 | 142 of 159 | 5 of 48 |
| V0, cut 3.0 | 112 of 159 | 2 of 48 |
| V1, cut 4.0 | 142 of 159 | 6 of 48 |
| V2, cut 0.5 | 153 of 159 | 5 of 48 |
| V2, cut 1.0 | 121 of 159 | 2 of 48 |

No setting keeps at least 85% of puzzles read (G1) while firing on 2 or fewer of the 48 lookalikes (the blind panel's
G2 bar is 2 per 100, and at least 60 of those 100 have 4-5 numbers). The scores also change steeply around every cut, so
a cut set on CPU fp32 would be fragile on a bf16 GPU. Running the registered test would spend $0.40 on a FAIL I can
already predict, so I stopped before sealing the code.

## What it shows (dev and practice only)
- Shown on practice data: when the 1B is told a message is a puzzle, it copies out the numbers and target almost
  perfectly. With V1 forced to read, it got 156 of 159 exactly, and none of its readings was the wrong puzzle. That
  includes whole wording families the rules miss, such as "Target: 24 / Numbers: ...", "evaluates to 6" and "24 from 4,
  7, 7 and 8?".
- Shown on practice data: few-shot, the plain 1B cannot decide whether a message is asking for a puzzle. It answers
  "yes, a puzzle" to lists of ages, codes, seat numbers and schedules that carry one extra number.
- Shown on practice data: a hybrid (the 1B reads whenever rt-02d's operator-or-list-and-question cue fires) reads 153 of
  160 but fires on 15 of 55 (13 with rt-02e's stated-sum skip). rt-02d's target-word rule is what screens out
  lookalikes.
- Untested: whether a small trained yes/no head on the 1B's inner state can make the decision. It would be trained on
  the 1B's own drafts labelled by code, never Claude-written text.

## Record corrections
- PASSMARKS-rt02g.md's header says "registered ~14:50 UTC". The commit (ba43e88d2) is at 14:29 UTC, and the commit is
  the record.
- scripts/claude_rt02g.py is committed as it stood at withdrawal (selftest 11/11), with no code seal.
  scripts/claude_rt02g_margins.py and scripts/claude_rt02g_sweep.py made the tables above.

## Consequence
The rule route stays the candidate for 0.2d's puzzle slot: rt-02d, or rt-02e by its own sealed decision rule.
