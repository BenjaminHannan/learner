# PR #53 body (copied from GitHub, open, 10-09): Consolidation sleep
Title: Consolidation sleep: fresh dreams reach 76.1% C2 holdout in 256 updates, no harm vs the pre-sleep model (transfer not shown)

Ask (Ben, 10-08): design and test a sleep that (a) absorbs the day's finds in very few updates, (b) loses no old skills, (c) ideally improves old skills through transfer. The model must run its sleep itself, and every pass mark was fixed before its run.

## Verdict (six parents s200-s205; marks in creative/results/fastsleep/consol/MARKS.md)
| mark | result | verdict |
| 1. C2 holdout first try, six-parent mean >= 71.3% | 76.1% (78.3, 77.9, 71.3, 75.8, 76.4, 77.0) | pass |
| 2. <= 256 updates and <= half the research-loop sleep's | every night ran 256 updates; the research loop needs 558-610 by its formula | pass |
| 3. no harm vs the pre-sleep model (harm_measure) | in_dist +0.12 to +0.82; no family fires on any parent | pass |
| 4. old skills up, pooled interval above 0 | +0.52 [0.31, 0.74] | pass |
| "through transfer" (sleep minus replay-only control > 0) | -1.58 [-1.79, -1.37] | not shown |

## The recipe
The model runs its own night: its own tries at a temperature it picks, plus chain search. It then sleeps 256 updates of 1,024 rows:
- half fresh dreams: the executor writes a new prompt from a found program every time, so no day row is read twice;
- half fresh skills rows.
Every 32 updates the model checks its fit rate on 128 held practice questions, and it keeps its best checkpoint.

## What else was found
- Fresh dreams vs re-read rows (Screen A, 2 parents, DEV): at equal updates, fresh dreams beat the research loop's re-read rows by +7.4 [3.5, 11.3] and +5.5 [0.8, 10.2]. A1 ("fresh dreams cut harm") could not be tested, because re-read rows did no harm at 128 updates either.
- Old skills improve from plain practice: a replay-only control with the same skills rows raises in_dist by +2.11 [1.88, 2.32]. So the sleep's +0.52 is not shown to come from the new skill.
- The rule-from-examples damage comes from the parent build (report only, against the raw B2): B2 -> N costs 2.3 in_dist points, mostly on fewshot_number_rule, seq_next and rule_apply. The sleep wins back about 0.5 of that; the control wins back most of it. harm_measure against B2 still fails for the sleep on all six parents.
- Not tested: "the model decides when to stop". The stop rule never ended a night early. Only its "keep the best checkpoint" part acted.

## Caveats
- Not a paired comparison: 71.3% is the research loop's stored number on its own (near-copy) parents. PC job 1 would give the paired baseline and the research-loop sleep's real harm.
- One training run per parent.
- Compute: everything ran on the cloud CPU. No money was spent.

Files: creative/results/fastsleep/consol/ (README.md, MARKS.md, ...); code creative/consol.py. Next steps are parked per Ben: one big proven run comes first, and the PC is busy until late Saturday.
Checks: an independent Opus judge confirmed each mark; a Haiku workflow re-derived 289 numbers from the raw files, all table values matched.
