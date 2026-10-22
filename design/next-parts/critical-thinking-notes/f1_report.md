# F1 report: error shape (128 saved answers, study only)

Nothing here is a score or a pass mark. The answer key is consumed. This only steers design.

## 1. What was measured

We took the 128 saved answers (16 questions x 8 checkpoints). For every wrong final answer we asked: is it a number the model saw in training? How far is it from the right number? Does it depend on carry or borrow? Does it vary by seed, reader or learning rate? We re-computed the main numbers from the saved trace and the answer key. They match f1_results.json.

## 2. Key numbers (all shown, computed here)

| Measure | Result |
|---|---|
| Wrong finals | 113 of 128 (15 correct) |
| Wrong finals equal to some training answer | 113 of 113 (100%) |
| Distinct final answers emitted vs distinct right answers | 24 vs 13 |
| Training answers the model can pick from | 27 (it used 24 of them) |
| Right answers that are NOT a training answer | 64 of 128 rows, all 64 wrong |
| Numeric distance, all 113 wrong finals | median 20, within 5: 18% |
| Numeric distance, 71 correct-call-wrong-final rows | median 14, within 5: 27%, within 10: 44% |
| Same 71 rows vs shuffled answers (null) | mean gap 14.6 vs 23.5 (chance); closer than chance |
| Wrong rate, carry | 38 of 40 |
| Wrong rate, no carry | 20 of 24 |
| Wrong rate, borrow | 13 of 16 |
| Wrong rate, no borrow | 42 of 48 |
| Seed 0 / seed 1 | 54 of 64 / 59 of 64 |
| Static / contextual reader | 58 of 64 / 55 of 64 |
| Control / low LR | 57 of 64 / 56 of 64 |
| Checkpoints with a repeated top answer (4+ of 16) | 4 of 8 (answer 42 shows up 19 times overall) |

Carry and borrow make no real difference. Seed, reader and learning rate make little difference. Low LR gave the same answers as control on 50 of 64 rows.

## 3. Which reading applies

**Pre-committed reading (the text in the design doc: near-misses plus a length effect point to a squeeze; copy above 25% or collapse point to memorising; scattered errors point to a skill gap).**
- Shown: copy-from-train is 100%, far above 25%. By that rule it is "memorising".
- Shown: near-misses are above chance (49% vs 31% expected). A length effect cannot be tested, because every answer has two digits. So "squeeze" cannot fire under its own rule.
- Caution (suggested): the 25% rule is weak here. The model can only output 27 training numbers, so 100% copy is almost forced. The uniform baseline is already about 30%.

**Adjusted reading (v5-check item 10: numeric distance and carry/borrow instead of length and edit distance).**
- Shown: wrong answers are closer to the truth than chance, but only 18% land within 5. They are not tight near-misses.
- Shown: carry and borrow do not matter. This is not the pattern of an arithmetic skill gap.
- Suggested: the model picks from a small shelf of familiar numbers, leaning toward the right size. That fits "mixed": a closed answer vocabulary (memorising flavour) plus a rough size signal (squeeze flavour).
- Untested: whether the answer is limited by the output side (a pipe problem) or by what the model learned. These data cannot separate the two.

Label summary: shown = the table. Suggested = "small shelf plus rough size". Untested = the cause.

## 4. What it means for the next step

This leans toward C3 (data change) over C1 (pipe test). The big fact is that 64 right answers are not in the training answer set, and the model got 0 of them. A data change that widens the answer set can test that directly. It also fits the 71 rows where the call was right but the final was wrong. C1 is not ruled out, though. Because the calculator value is right on those rows, a pipe test could show whether the number gets lost on the way out. Neither is proven. Pick one change at a time, fix the pass marks first, and use fresh questions, not these 16.
