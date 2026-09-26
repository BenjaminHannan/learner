# PASSMARKS rt-02e: the chat route skips messages that already state a worked sum (registered 2026-09-26 ~14:25 UTC)

Owner: Plain-English puzzles thread. Written, sealed and committed BEFORE rt-02d's registered run has any result
(rent-rt02d was still waiting for the reader copy; nothing of rt-02d's run, score or panel has been seen). Never edited.

## Why (practice only, not a result)
rt-02d's R3 allows at most 2 route fires on 100 blind lookalike messages. On a practice set that a blind agent wrote
without seeing any code (artifacts/claude-rt02e-20260926/practice/wordings_practice.json: 40 puzzle wordings,
40 lookalikes), rt-02d's parser read 102 of 120 practice puzzles exactly (0 misread, 18 missed) and fired on 3 of the
40 lookalikes. All 3 already state a worked sum: two check questions ("is <sum> equal to <n>?") and one user sharing
a solution they found alone. I read those 3 and designed the filter from them, so the practice numbers below are
biased in the filter's favour; only the blind TEST negatives decide.

## One change
rt-02e = rt-02d with one extra condition on firing: the route fires only if claude_rt02d.parse_puzzle fires AND
claude_rt02e.states_sum(text) is False (the message has no "numbers joined by operators, then = / equals / equal to /
is / makes / gives / gets / comes to and a number"). Parser, solver, tries, seeds, reply wording and arms: unchanged.
Practice (selftest): dev cases 55/55 unchanged; practice puzzles kept 102, lost 0; practice lookalikes fired 3 -> 0;
dl-1's 300 general items fired 0.

## How it is measured (no new run; $0)
On a turn the route does not fire, the reply is the inner build_02c reply, which rt-02d records as B0 for the same
conversation on the same machine. So on rt-02d's own blind panel (artifacts/claude-panel-rt02d-20260926, still never
opened by me), with rt-02d's run files:
  B1e reply = B1's reply where rt-02e fires, else B0's reply; B1off_e likewise from B1off and B0.
  Fires on negatives, general items and chat dev turns = rt-02e's firing rule applied to their text.
Solved = claude_panel382_run.puzzle_solved (rt-02d's registered scorer). Score:
  python -B scripts/claude_rt02e.py score --out artifacts/claude-rt02d-20260926/run --panel-dir
  artifacts/claude-panel-rt02d-20260926 --rt02d-score artifacts/claude-rt02d-20260926/score/rt02d_score.json
  --score artifacts/claude-rt02e-20260926/score
Validity: the replay counts only if rt-02d's dev gate passed and rt-02d's R4 found 0 differing unrouted replies on
both no-harm sets. If not, rt-02e is INVALID (not a FAIL) and needs a live run of build_rt02e.

## Marks
| Row | Test | Bar |
|---|---|---|
| E1 | route fires on rt-02d's 100 blind negatives | <= 2 |
| E2 | chat puzzles solved, B1e | >= 8, and B1e - B0 >= 6, and B1e >= B1 - 2 (the filter costs at most 2 solves) |
| E3 | sleep still reaches chat: B1e - B1off_e | >= 4 |
| E4 | no harm: identity valid (above), rt-02e's fires are a subset of rt-02d's on the panel, and <= 3 of the 300 general items fire | all |
| E5 | honesty: routed replies with an expression that fails the exact checker (rt-02d's R5 count) | 0 |
rt-02e PASSES only if every row passes. A FAIL stays a FAIL. It is scored in every case, whatever rt-02d's verdict.

## Decision rule (fixed now)
- rt-02e PASS and it fires on fewer negatives than rt-02d: rt-02e is the route Month-end joins.
- Otherwise, rt-02d PASS: rt-02d is joined.
- Both FAIL: the failing rows pick the next step (misses -> a learned reader such as door-1; false fires -> a learned
  yes/no "is this a request?" check; B1 - B1off < 4 -> Fix sleep's chat-worded night twins).
Door-1 (Ben's Mac agent) is judged on its own sealed marks; if it passes too, the one with more chat puzzles solved at
<= 2 false fires is joined.

## What would prove it wrong (fixed now)
- E1 > 2: false fires on the blind negatives are not mostly "stated sums"; the filter is the wrong fix.
- B1e < B1 - 2: the filter blocks real puzzle wordings.
