# English fresh eval draft v2 vs TRAIN v3: answer overlap check (2026-10-03)

Read-only check. Files:
- Eval: artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/FRESH-EVAL-DRAFT-v2/eval_items.json (48 passages, 102 grading rows = 96 QA + 6 paraphrase)
- TRAIN: .../ENGLISH-PARAPHRASE-RECONSTRUCTION-CPU-FEASIBILITY-v1/CONFIRMED-TRAIN-CONTENT-v3/english_training_candidates_v3.json (24 examples)
- Script: scratchpad overlap.py (normalise: lowercase, apostrophes, trim punctuation; whole-word match)

## (a) Numeric answers
- Answers with a digit, number word, ordinal, month or weekday: 0 of 96 (canonical and accepted lists both checked).
- 11 regex hits were all the pronoun "one" ("the pine one", "the hooded one"); not numbers.
- Number words occur in eval passages/questions only as context ("Two kettles", "Of the two ropes", "What did X do first?"), never as an answer. TRAIN text contains "two", "first" and digits 0-4 (where not inspected).
- Shown: no eval item rewards producing a number.

## (b) General answer overlap
- 23 of 96 canonical answers are in the TRAIN answer set; all 23 are "yes"/"no" (these are exactly the 23 yes_no items).
- Short-answer items: 0 of 73 have any accepted answer that is a TRAIN answer, or that appears anywhere in TRAIN text.
- Overlapping IDs: CD-F1-Q2, CD-F2-Q1, CD-F3-Q2, CD-M1-Q2, CD-M2-Q2, CD-M3-Q2, CD-M4-Q2, NG-F1-Q1, NG-F2-Q2, NG-F3-Q2, NG-F4-Q2, NG-M1-Q1, NG-M2-Q2, NG-M3-Q2, NG-M4-Q2, EO-F2-Q1, EO-F3-Q1, EO-F4-Q2, EO-M1-Q1, EO-M2-Q2, EO-M3-Q2, EO-M4-Q2, DR-M3-Q2.

## Recommendation
Drop or replace nothing for numeric memorisation. Flag the 23 yes/no items: a yes/no prior from TRAIN can score at about chance level, so report them apart and compare with a constant-answer baseline. ROOT-DECISIONS item 10 already says this.
Not checked: draft v3, the paraphrase items, and the full pilot schedule's train stream.
