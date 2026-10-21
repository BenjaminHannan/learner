# Does the model's own add-on switch keep old skills when a new subject looks like old questions?

Opus, 8:30 PM ET 10-10. Marks fixed here before any training, gate or scoring result for these subjects.
Thread "Add-on switch on look-alikes (ultracode)". Builds on domain mode v8 (DESIGN-AND-MARKS addenda A18-A23, PR #58).

## 1. Why

v8 passed on sheet s200, sheet s201 and RPN s200: the model's own switch turned its add-on on for every subject question
and for 1 of 1,360 old questions, with no answer changed (A23). But spreadsheet and RPN prompts look nothing like the old
questions, so telling them apart was easy. This test gives the mode a subject whose questions are worded like two old skill
families, one word apart, with different answers.

## 2. The look-alike subject: `stats` (new tool, same constants file, same mode, nothing else changed)

Plain-code tool `domain/tools/stats.py`. Prompt frame `Numbers: a, b, c. <question>`, exactly the frame of two old families:
`compare_numbers` ("Which is the largest?", "Which is the smallest?", "How many are greater than t?") and `list_stats`
("What is the sum of the numbers?", "What is the largest minus the smallest?", "How many of the numbers are even?",
"What is the second largest number?"). Every working step is a calculator call the model already has (add, sub, mul, div,
max, min), at most 7.

| kind | help example | answer | working | old question it is closest to |
|---|---|---|---|---|
| product | Numbers: 6, 3, 4. What is the product of the numbers? | 72 | mul, mul | sum of the numbers |
| half the sum | Numbers: 12, 4, 8. What is half the sum of the numbers? | 12 | add, add, div 2 | sum of the numbers |
| largest plus smallest | Numbers: 65, 84, 7. What is the largest plus the smallest? | 91 | max, max, min, min, add | largest minus the smallest |
| largest times smallest | Numbers: 9, 4, 7. What is the largest times the smallest? | 36 | max, max, min, min, mul | largest minus the smallest |
| twice the largest | Numbers: 65, 84, 7, 20. What is twice the largest? | 168 | max x3, mul 2 | which is the largest |
| twice the smallest | Numbers: 31, 6, 58. What is twice the smallest? | 12 | min x2, mul 2 | which is the smallest |
| sum minus largest | Numbers: 12, 30, 5. What is the sum minus the largest? | 17 | add, add, max, max, sub | sum of the numbers |

Confirmation subject (only run as section 5 says): `invoice`, worded like old `table_calc` ("Row zipper: qty 6, price 12. ...
What is the total cost of row hammer?"), with new questions (total price over all rows, cost of two rows, largest qty,
smallest price, cost difference of two rows, twice the total qty).

## 3. Panels (ours, sealed, written and hashed before the run; the mode refuses the panel folder)

- `panel/stats.v2.jsonl`: 7 kinds x (60 near + 40 far), seed 91021. Near: the help example's list length, values 1-99,
  the help question. Far: longer lists within 7 calls. Decontaminated like the v2 panels (rows equal to a practice prompt
  are dropped from scoring, A10).
- `panel/lookalike-old.v1.jsonl`: old-skill look-alikes, 100 fresh rows per variant from the curriculum's own generator
  (namespace LA, seed 91031), none equal to any train or DEV prompt: compare_numbers (larger, smaller, count_above,
  largest_of, smallest_of), list_stats (sum, range, count_even, second_largest), table_calc (row_total, column_sum, total).
  Scored like DEV in_dist (custom_io evaluate, accepted answers).

## 4. Marks (stats, seed 200, v8 exactly as in A23: per-tool add-on, own switch, constants file unchanged)

| mark | pass | proved wrong |
|---|---|---|
| LA1 learns the look-alike subject | routed near gain >= +30 (DM1 bar) | < +10 |
| LA2 keeps old skills (DEV in_dist, routed answers) | harm measure passes (in_dist drop <= 1.5, no family drop > 5 with paired 95% interval below 0) | compare_numbers or list_stats fires, or in_dist drop > 1.5 |
| LA3 keeps look-alike old skills (lookalike-old panel, routed answers, harm measure per variant) | pooled drop <= 1.5 and no variant fires (drop > 5, interval below 0) | pooled drop > 3, or a variant drops > 10 with interval below 0 |

Switch holds on look-alikes = LA1, LA2 and LA3 pass. Switch fails = LA2 or LA3 proved wrong. Otherwise fail, not proved wrong.
Ben's hair-miss rule applies (a one-question miss counts as met).

Reported, not gated: the switch's on-rate on each lookalike-old variant, each DEV family and the stats panel (near, far);
the add-on left on for every question (the cost of a switch mistake) on lookalike-old and DEV; which old answers changed.

**LA0, switch-only screen (no model training, reported only).** The switch is a logistic unit on the parent's reader with
the add-on off, so its decisions do not depend on the night training. Before the run: train it exactly as `mode.py` does,
positives = the stats practice prompts the mode's own maker makes over 7 days at even mix (seed 200), negatives = the
seed-200 diary (identical to the v7 runs' diary: same parent, data and seed). Report its on-rates as above.
Prediction, written now: near 100% on the stats panel; low on most old variants, highest on `range` and `sum` (one word
from a stats question). Whether a switch mistake costs anything depends on the add-on, which sees half old questions in
every training batch; only the run can say.

## 5. What happens next (fixed now)

- **Pass on stats:** run `invoice` s200 the same way (LA1-LA3 with table_calc as the look-alike family) to show it is not
  one subject.
- **Fail because the switch turns on for look-alike old questions and the add-on changes their answers:** one change,
  **F1: the switch learns where the add-on is risky, from its own answers.** At the end of the mode the model answers its
  own diary with the add-on on; diary questions where that answer differs from its pre-mode answer (the diary row) are
  risky. The switch trains with the risky diary questions given half of the negative weight (the other negatives the other
  half; positives unchanged). Its own records and own answers only; no panel or DEV row. Re-scored from the same run's log
  and checkpoints (no new training). Marks: LA1-LA3 as above on stats s200, plus A23's bars still met on sheet s200,
  sheet s201 and RPN s200 (re-scored, free), then confirmed on `invoice` s200 (full run).
  Proved wrong for F1: LA3 still proved wrong, or LA1 falls below +30 (the switch gets too shy).
- **If F1 is proved wrong:** F4, the add-on reviews what looks like its subject: the replay half of each night's batch is
  drawn from the diary questions the switch scores highest, so the add-on itself learns to keep those answers. Full re-run,
  same marks.
- **Fail because the switch misses the subject's own questions (LA1 low with the switch off on the stats panel):** F2,
  the switch reads mean and max of the reader's features instead of the mean alone. Re-scored, same marks.

Rules kept: free compute only (cloud CPU); the mode never reads a panel or DEV file; nothing in training is cut short;
every step is the deployed model's own (the tools are outside tools it calls).

## Addendum L1 (Opus, 8:45 PM ET 10-10, before any run or score)

A Haiku helper found that four variants listed in sec. 3 never appear in training or DEV in_dist: the curriculum holds
them out (`larger` and `count_above` of compare_numbers, `sum` of list_stats, and `cost` of table_calc, which sec. 3
wrongly called `total`). So the parent never trained on "What is the sum of the numbers?".
- `panel/lookalike-old.v1.jsonl` (LA3, gated) holds the 8 in-distribution variants, 100 rows each: compare_numbers
  smaller, largest_of, smallest_of; list_stats range, count_even, second_largest; table_calc row_total, column_sum.
  sha256 e1b896640819f3281b41ea64849f1dfff279f28f3c1706bb74cd0cd082e037c9.
- `panel/lookalike-old-heldout.v1.jsonl` holds the 4 held-out variants, 100 rows each, drawn with the curriculum's own
  held-out-variant filter (namespace LV). Scored the same way and **reported only**: it measures questions the parent
  never trained on. sha256 973bcfbd0ca2ec447c135f47d70e05c02c8b0a503ab128dce7c5e105f584a576.
- `panel/stats.v2.jsonl` sha256 bab0000578bc5ef110a8bb2aa66eebab9116b764273cfb24d5682b8d94f5ecc2 (700 rows);
  `panel/invoice.v2.jsonl` sha256 9640d92aa45554dc59d67445fc1a5200c49322fd618e4666519be9e7be9f6b24 (600 rows).
Bars unchanged.

## Addendum L2: result on stats s200 (Opus, 9:45 PM ET 10-10)

Shown, from `runs/stats-s200-v8/analysis/LOOKALIKE_v8.json` and `RESULT.md`. The run took 3 nights (53 minutes) and
stopped on its quiz (2.7 -> 98.4 -> 91.4 -> 98.8). The switch was trained by `mode.py` itself (`gate.pt`, 3,072 practice
prompts against 4,096 diary prompts, training accuracy 99.73%).

| mark | result | verdict |
|---|---|---|
| LA1 learns | near 0.0 -> 99.3 routed (+99.3); every near question switched on, far 87.5% | PASS |
| LA2 DEV old skills, routed | in_dist drop 0.07 (1 of 1,360); list_stats 92.5 -> 90.0 (not fired), nothing fired | PASS |
| LA3 look-alike old skills, routed | pooled drop 0.00; range 81 -> 82, second_largest 80 -> 79, all else unchanged | PASS |

- **The switch is fooled, but being fooled costs nothing here.** It switched the add-on on for 32 of 100 old
  "largest minus the smallest" questions, 10 smallest_of, 7 largest_of, 4 second_largest, and 8 of 1,360 DEV questions
  (all list_stats). Those answers did not change: the add-on trains with half of every batch on old questions, and it
  learned to leave the closest look-alikes alone (range 81 -> 81 even with the add-on left on for everything).
- The add-on left on everywhere still harms other old skills: look-alike panel drop 4.25 (count_even 98 -> 80 fired,
  row_total 22 -> 14, smallest_of 100 -> 95); DEV drop 3.01 (passage_qa, rule_apply, seq_next fired). The switch never
  turns it on there, so the switch is still needed.
- Held-out variants (reported only): the switch turned on for 64 of 100 "What is the sum of the numbers?" questions, a
  question the parent never trained on; routed accuracy rose 1 -> 17. Others unchanged.
- DM5 reads "proved wrong" on its letter (rise over the last night +15.2) only because night 2 dipped and night 3
  recovered; the near score at the stop (99.3) is within 0.3 of the best night.
- Per sec. 5, no fix is due. Next: `invoice` s200, the same way (started 9:41 PM ET).

## Addendum L3: result on invoice s200, the second look-alike subject (Opus, 10:40 PM ET 10-10)

Shown, from `runs/invoice-s200-v8/analysis/LOOKALIKE_v8.json` and `RESULT.md`. 3 nights (51 minutes), stopped on its
quiz (2.0 -> 96.9 -> 96.9 -> 87.1; night 3 fell and the final checkpoint is night 3). Switch from `mode.py` (`gate.pt`,
3,072 against 4,096, training accuracy 99.75%).

| mark | result | verdict |
|---|---|---|
| LA1 learns | near 0.3 -> 62.2 routed (+61.9); switched on for every panel question, near and far | PASS |
| LA2 DEV old skills, routed | in_dist drop 0.00; switched on for 11 of 40 table_calc, 2 arith_bare, 1 verify_claim, none changed | PASS |
| LA3 look-alike old skills, routed | pooled drop 0.12; row_total 22 -> 21 (3 lost, 2 gained), all else unchanged | PASS |

- Same picture as stats: the switch is fooled by the closest old question ("What is the total qty over all rows?", one
  word from the new "total price over all rows?": 36 of 100 switched on; row_total 11 of 100), and the add-on leaves those
  answers alone. Add-on left on for everything: look-alike panel drop 2.12 (none fired), DEV drop 3.31 (fewshot_number_rule,
  passage_qa, rule_apply, seq_next fired), where the switch stays off.
- Held-out variants (reported only): switched on for 15 of 100 "total cost of all rows", no answer changed.
- Aside for the domain-mode owner (not a mark here): DM5 fails on invoice. The near score was best after night 1 (83.1)
  and the mode kept night 3 (62.2), because it stops after its quiz falls and keeps the last night, not its best.

**Verdict over both subjects: the switch holds on look-alikes (LA1-LA3 pass on stats and invoice, seed 200).** Suggested
reason, not tested: two layers cover each other. The switch reliably keeps the add-on off the old skills it would harm
(far from the subject: rule-from-examples, passages), and the add-on, which reviews old questions in every batch, learns
to leave the near look-alikes that the switch lets through unchanged. Untested: other seeds, a look-alike family that
the diary barely covers, and bigger models. Per sec. 5, no fix is due.
