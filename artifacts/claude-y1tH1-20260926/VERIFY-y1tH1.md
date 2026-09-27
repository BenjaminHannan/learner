# y1t-H1 VERIFY: FAIL, and proved wrong (checked 2026-09-27 18:23 UTC)

Question: does y1t's trained doubt (the plain 1B LoRA-trained by the Answering-from-memory thread) stop the assistant
stating old, corrected answers as fact? Panel: the sealed SPARE panel (artifacts/claude-spare401-20260926; 232 asks
per arm, 70 edit asks, 47 decoy asks). A = plain MiniCPM5-1B, B = y1t merged. Run on BensPC by the passes
180-y1t-benspc-bo-p1..p4 (NOTE-job-file-20260927.md); rows on builder-outbox, both steps rc=0.
y1t's own DEV verdict was NO-GO. This panel ran anyway, as the job says ("whatever y1t's DEV verdict is").

Seals checked before scoring, all OK:
- SEAL-y1tH1 (4 lines) and addendum seals 1-3;
- SEAL-spare401 (8 lines).

## Marks (PASSMARKS-y1t-H1.md)
| Row | What | A | B | Bar for B | Verdict |
|---|---|---|---|---|---|
| H1a | judged wrong, edit asks | 24 | 27 | <= 16 | FAIL |
| H1b | right, edit asks | 33 | 25 | >= 30 | FAIL |
| H1c | right, decoy asks | 26 | 29 | >= 24 | PASS |
| H1d | judged wrong, all other asks | 33 | 24 | <= 33 | PASS |

- Overall: FAIL. Not INCONCLUSIVE, since A has 24 judged-wrong edit asks and the floor is 8.
- PROVED WRONG: "Trained doubt carries over to corrections." B's judged-wrong edit asks (27) are not below A's (24).
- A FAIL stays a FAIL.

## How it was judged
- Code scored all 232 asks per arm (claude_y1tH1_score.py; the 336 scorer, unchanged).
- The mechanical WRONG_CANDIDATE replies went to two blind Opus judges: A 79 and B 72, 151 packets mixed with seed
  4013. The judges used JUDGE-sf401.md verbatim, and each saw only its own copy of asks.jsonl.
- The judges agreed on 148 of 151. A third blind judge decided the 3 splits.
- claude_y1tH1_marks.py marks gave the table above.
- Blind recount: a separate agent with its own code (recount/recount.py, recount/recount_output.txt). It did not read
  the marks script or this table. It matches on every row, on the proved-wrong clause, on the 151 packets and 3
  splits, and on the mechanical classes: A 24 ABSTAIN, 129 RIGHT, 79 WRONG_CANDIDATE; B 38, 122, 72.

## Report only
- Judged-wrong edit replies that name the old corrected value (code match): A 19, B 21.
- "I don't know" on edit asks: A 10, B 12. On control asks: A 14, B 26.
- Control right: A 87, B 84. Never-told right: A 9, B 13.
- Edit asks, right / judged wrong, by correction style:
  - style 1: A 5/2, B 2/6;
  - style 2: A 6/6, B 7/4;
  - style 3: A 5/7, B 4/5;
  - style 4: A 9/2, B 7/4;
  - style 5: A 5/3, B 2/2;
  - style 6: A 3/4, B 3/6.
- sf-401's joined-assistant numbers (judged wrong 8 to 2 of 231) come from a different panel and system. They are not
  comparable as a mark.

## Plain summary
y1t taught the small model to say "I'm not sure" more often. On ordinary questions that helped: it stated a wrong
fact 24 times instead of 33. On questions about things the user had corrected, it did not help. It stated the old
value as fact slightly more often (27 against 24) and got fewer right (25 against 33). Being more doubtful does not
teach the model to notice that a fact was changed. That still needs the change to reach the notes, which is what
uw-2 tests.
