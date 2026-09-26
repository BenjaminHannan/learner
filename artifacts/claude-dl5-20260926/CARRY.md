# dl-5 carry-over row and reply check (report-only; PASSMARKS Addendum 1 and 2)
Run: rent-zdl5c (scripts/claude_dl5_carry.py, unmodified), RTX 5090, ~14 min, ~$0.26 of $0.30; adapters matched their
sidecar sha256. Raw: carry/dl5_carry.json, carry/log.txt (copied from builder-outbox b670825be's content).

## Carry-over: did five grid nights move number puzzles (never practised)?
100 fresh puzzles (seed 3490) x 20 guesses at temperature 1.5, plus greedy:
- base: lucky 66, puzzles reached 34, greedy 3
- S seed 8 adapter: lucky 67, reached 29, greedy 8
- S seed 9 adapter: lucky 53, reached 30, greedy 1
No rise is seen: seed 8 is flat, seed 9 is lower. No placebo adapter exists, so a drop cannot be blamed on the grid
practice itself. Reading: no carry-over from grid nights to number puzzles.

## Reply check: are the lost panel items format or knowledge?
The base answers 0 of 300 panel questions in a "The X of Y is V" sentence. After grid nights, the S adapters answer
299 (seed 8) and 300 (seed 9) of 300 that way, which is the shape of the grid target ("The number in row R, column C
is V", a Claude-written prefix). Every lost item (98 and 61) still names an answer, and the answers are wrong facts,
not cut-off replies: "The capital of Canada is New York.", "The capital of Australia is Sydney", "The day after Monday
is Wednesday". Lost by kind: seed 8 capital 38, bigger 31, order 19, opposite 6, count 4; seed 9 capital 19, order
18, bigger 18, count 4, opposite 2. Only 2 and 4 lost word questions were answered with a number.
Every gained item (18 and 14) is also in the new sentence shape, mostly plurals and opposites, where the full
sentence now contains the right word ("The plural of 'child' is 'children'.").
Reading (suggested): grid nights taught a universal answer template, and under it the model states wrong facts. Gains
are a format effect, losses are real wrong facts. A training target with a fixed sentence frame spreads that frame
to every question, which is one more reason for bare, code-checked targets.
