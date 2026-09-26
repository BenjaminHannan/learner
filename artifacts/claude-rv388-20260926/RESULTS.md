# rv-388 results (thought-memory thread; written 2026-09-26 17:33 UTC by date -u)

Raw output: run/ (both seeds on CPU here, 2 torch threads, started 15:07 and 16:09 UTC). Marks: PASSMARKS.md, sealed at
53d7a6489. The seal re-checks OK on all 5 lines, and no sealed file changed after it. Counted from the per-hand rows;
the log summary lines agree. Blind recount: VERIFY-recount.md.

## Verdict: NO CLEAR RESULT (neither PASS nor PROVED WRONG)

| hands solved of 80 | END | JUDGE | PLACEBO | ORACLE (report only) |
|---|---|---|---|---|
| seed 388101 | 34 | 42 | 37 | 80 |
| seed 388202 | 28 | 35 | 33 | 80 |

- PASS needs JUDGE >= END + 6 AND JUDGE >= PLACEBO + 6 in both seeds. JUDGE - END = +8 and +7 (holds); JUDGE - PLACEBO
  = +5 and +2 (fails in both). Not PASS.
- PROVED WRONG needs JUDGE <= END in both seeds (no: +8, +7), OR JUDGE - PLACEBO summed over both seeds <= 0 (no: +7).
  Not PROVED WRONG.
- Plain words: going back when Creative's learned judge says "this can't reach 24 any more" solved 7 or 8 more hands
  than going back only at a wrong final answer. But setting aside the same share of states at random solved 3 or 5
  more on its own. So most of the gain comes from pruning at all, and what the judge knows added only 5 and 2 hands,
  under the bar of 6.

## Report only
- Flags on states that could still reach 24 ("live"; exact check), 3-number + 2-number:
  - JUDGE: 4 + 1 = 5 live of 451 flags (seed 388101); 14 + 0 = 14 live of 510 flags (seed 388202).
  - PLACEBO: 13 + 21 = 34 live of 685 flags; 7 + 21 = 28 live of 682 flags.
  - Overall the judge sets aside fewer live states than random pruning (5 vs 34, 14 vs 28). It almost never sets aside
    a live 2-number state (1 and 0, against 21 and 21). On 3-number states, where feas-24b was known to be weak
    (Creative's note), it set aside more live ones than the placebo in seed 388202 (14 vs 7).
  - The placebo flagged 1.3 to 1.5 times as many states as JUDGE, although its cut was set to flag the same share of
    practice states. Suggested cause (blind recount): the cut was set on END's practice states, not on the states each
    arm reaches itself.
- Hands one arm solved and the other did not: JUDGE vs PLACEBO 13 vs 8 and 11 vs 9; JUDGE vs END 14 vs 6 and 13 vs 6;
  PLACEBO vs END 11 vs 8 and 11 vs 6. On a sign test over both seeds (blind recount), JUDGE vs END gives p about 0.02,
  and JUDGE vs PLACEBO gives p about 0.35. So the judge's edge over random pruning is within chance. Suggested.
- JUDGE entered slightly more states that were in the judge's own training rows (5.4% and 4.1%, against END's 2.8%).
  Whether any of its edge comes from those states is untested.
- Steps used (budget 160 per hand): END 9,739 and 10,341; JUDGE 8,501 and 9,181; PLACEBO 9,115 and 9,738; ORACLE 1,044
  and 1,200.
- Share of entered states that were in the judge's training rows: END 35/1,249 and 37/1,303; JUDGE 49/914 and 40/981;
  PLACEBO 36/1,030 and 38/1,083; ORACLE 52/97 and 51/105.
- Judge cost: the log's "calls" counters are cumulative unique states across the arms of one run, not per arm. JUDGE's
  arm, which ran right after END (which needs none), needed judge features for 781 and 919 new states.
- ORACLE (exact reachability as the flag) solved all 80 hands in both seeds. The 1B proposer is not the limit. A judge
  that knows which states are dead would make search almost free.

## Predictions
- P388.1 (JUDGE beats END by 6 or more in both seeds): RIGHT (+8, +7).
- P388.2 (JUDGE does NOT beat PLACEBO by 6 in at least one seed, so no PASS): RIGHT (+5, +2).
- P388.3 (ORACLE solves at least 75 of 80 in both seeds): RIGHT (80, 80).

## What it means, and what is next
- Going back with a learned judge helps a little. The judge does carry real knowledge: it sets aside far fewer live
  states than random pruning. But in these hands the proposer walks into dead states so often that pruning anything
  already pays, and the judge's extra knowledge adds under 6 hands per seed. The gap to ORACLE (80) is what a better
  judge could still win.
- This was search around the 1B, a test that was running before Ben's 16:04 redirect. Its verdict stands, and no follow-up on
  the 1B is planned here. The part that carries over to the learned reasoner is the idea that going back should be
  triggered by a learned "this can't work" signal. rv-391 (artifacts/claude-rv391-20260926/NOTE-dev-plan.md) looks
  for that signal inside the loop net itself.
