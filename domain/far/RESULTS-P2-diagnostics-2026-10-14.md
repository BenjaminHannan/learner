# P2 zero-GPU far diagnostics: results (Wed Oct 14, 2026, 2:42 AM ET). Marks: MARKS-P2-diagnostics-2026-10-14.md

Thread "Far transfer (ultracode)". Scoring of saved step-4000 checkpoints on probe rows only (F4-two and F5-far, 420 rows each), free CPU,
nothing trained, no sealed row read. Script `domain/far/p2_diag.py` (collect, tf, report); raw per-row files and the full tables are in
`/mnt/project-files/far-transfer/learn/P2-diagnostics/`. Labels: **shown** = measured, **suggested** = reasoned, **untested** = never run.
The marks file was written 2:27 AM ET, before the scoring started at 2:29 AM ET; its only later edit is the time stamp on line 1.

**Seed rule.** Every run below is ONE training run, so every headline is UNPOWERED (screening at best); 420-row bootstrap intervals are in the full tables
and are not a seed spread. Nothing here is a best-of-anything. Quarantined and left out: all join-last figures (L10, L12). L9 (whole-formula joins) is not join-last.
**Check on the scoring itself (shown):** the whole-question hit counts re-derived here equal the runs' own `scores.jsonl` and the A1 files on all 9 checkpoints (F4: 3, 192, 13, 18, 118, 118, 137, 71, 60 of 420).

## Answers

1. **Is the 4% an eval artifact? No (shown).** Re-marking every answer with the format fixed (spaces, signs, leading zeros, `.0`, commas) changes nothing: W_norm - W = 0.0
   on all 18 run x cell pairs. The tool's 7-call cap is never exceeded (F4 and F5 working has 3-7 calls). Every answer the mark counted right is right; on the L8 baselines all
   13 (LB) and 17 of 18 (LA64) right F4 answers used fewer calls than the tool's working (a MIN or MAX call skipped, the right cell written straight into the next call; the 18th uses the same calls in another order),
   which is a valid solution, not luck.
2. **Piece accuracy inside the join (the "one number"). Pieces lose about half of what they have alone; the combine step is also weak on the baselines (shown).**
   Baselines L8-LB / L8-LA64, F4-two: first piece K alone 81 / 72% (by value), inside the join 43 / 44%; second piece J alone 89 / 77%, inside the join 35 / 39%; both pieces' values inside the
   join 12 / 13%; when both are there the answer is right 23 / 29%; with the tool's own working on the tape (no history of its own mistakes) the join call is right only 11 / 9%. Strict
   call-by-call the K ratio is 0.31 / 0.36; by value it is 0.52 / 0.62 (the truth sits between: calls undercount shortcuts, value overcounts coincidences).
   After join practice (L9, L7, L11) K keeps 0.78-0.96 of its alone rate inside the join and J 0.65-0.75, and the join call given the tool's working is right 64-84%. Reading (suggested): the 4%
   is a real low rate with two parts, pieces damaged by the second piece beside them and a join call never practised; join practice repairs both on near joins (L1/L5/L6/L9 agree).
3. **10% dissolution rule: does not fire on the literal reading (shown).** The roadmap does not define "corrected join baseline"; three readings were fixed in the marks.
   D1 (same protocol, scorer corrected = W_norm, baselines): F4-two 0.7 (parent) / 3.1 / 4.3 (L8), F5-far 0.0 / 1.2 / 0.5: all under 10, so no. D2 (outside splitter T: the model's own piece
   answers and own join): F4-two 40.2 / 44.8, F5-far 9.0 / 11.9 (L8): over 10 on F4 and on one far arm, but that is a different protocol (a splitter, dropped 10-12), so reported and not applied.
   D3 (mean ladder credit, partial credit not a pass rate): F4-two 12.1 / 11.8, F5-far 6.3 / 4.3 (L8). **So the far programme is not dissolved by this test; if Ben meant D2, say so and it is
   a one-line change.** T is not a clean splitter score for the join-trained runs (L7, L11, L13, L14 answer `=151+92` with a grid number, e.g. a min call giving 59, so T is 0.5-1.7), as A1 found for L7.
4. **Merged error taxonomy (shown).** Of the failed whole rows the first wrong call is at round 0 in: F4-two 68 / 72% (L8 baselines), 60 / 63% (L13 / L14), 47% (L11), 45% (L9); F5-far 65-86% (baselines 76 / 82%).
   This reproduces Ben's number from the per-item files exactly (HO: L13 226 of 361 = 62.6%, L14 245 of 379 = 64.6%). What the round-0 error is (L13 / L14 HO): the wrong grid number
   in the first call 88 / 87% (55 / 58% a cell the formula names, the wrong one; 33 / 29% a cell the formula does not name), wrong op 8 / 7%, a later step done first with this one skipped
   4 / 4%, **order swapped 0 / 0%**. So "first-step routing" means picking the wrong cells for the first call, not picking the wrong piece to start with (Q4b: swapped order is 0-2% of round-0
   errors on every cell, so the old A1 "first error in K" counts are not inflated by J-first ordering). Single formulas fail the same way: on F0-near 99% of first wrong calls are a wrong
   grid number (L13 168 failures, L14 192; the rest are extra calls). Suggested: the round-0 weakness is the model's reading of which cells a formula names, and a join only shows it twice.
   Per-round accuracy with the tool's working on the tape (shown): on near joins round 0 and 1 are the hardest and later rounds improve (L9-LB 66, 64, 69, 75, 79, 87%; L13 49, 49, 57, 61, 70%), which
   supports first-step over mid-chain collapse there; on far rows accuracy falls with depth (L9-LB 36, 39, 29, 22, 16, 13, 0%) while round 0 is already low (13-36%), so far has both. The L8 baselines'
   first errors are 10-29% "skipped a MIN/MAX call", the shortcut of answer 1.

## Marks (fixed 2:27 AM ET) against the results

| Question | Reading |
|---|---|
| Q1 artifact | **No** (W_norm - W = 0.0 everywhere; mark: no if < 1) |
| Q2 combining alone is the failure | **Not met** (K in join is 0.31 / 0.36 of K alone, mark needs >= 0.8); join call with the tool's working is only 9-11% on the baselines, so the combine step is weak too |
| Q2b in-join piece loss | **Yes by calls** (0.31 / 0.36 F4, 0.28 / 0.20 far, mark < 0.5); **no by value** (0.52 / 0.62 F4; far 0.68 / 0.88, probably coincidences). Reported both; no single verdict claimed |
| Q3 10% rule | **Does not fire on D1**; fires on D2 (F4, one far arm), flagged and not applied |
| Q4 round 0 is the main first error | **Yes** on the baselines (F4 68 / 72%, F5 76 / 82%) |
| Q4b round-0 errors are ordering | **No** (order swapped 0-2%; skipped step 10-29% on the L8 baselines, 2-8% on guarded runs) |

## Headline tables (% of 420 rows; full tables in P2-diagnostics/report.md)

Columns: W whole right; K / J alone = the piece asked by itself (by value); K / J inside = the piece's value among the numbers the whole-question calls touch; both inside = both values; right if both = answer right given both;
first / join call = the call is right with the tool's own working on the tape; T = outside splitter (not comparable for join-trained runs).

### F4-two (420 rows each)

| run | whole right W | W after format fix | K alone | K inside join | J alone | J inside join | both inside join | answer right if both inside | first call (tool history) | join call (tool history) | T splitter (own pieces, own join) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| parent | 0.7 | 0.7 | 2.6 | 5.2 | 5.5 | 8.8 | 1.0 | 25.0 | 0.5 | 0.0 | 0.0 |
| L8-LB | 3.1 | 3.1 | 81.4 | 42.6 | 88.8 | 34.8 | 12.4 | 23.1 | 32.4 | 10.7 | 40.2 |
| L8-LA64 | 4.3 | 4.3 | 71.9 | 44.3 | 77.4 | 38.8 | 13.3 | 28.6 | 29.5 | 8.8 | 44.8 |
| L9-LB | 28.1 | 28.1 | 79.3 | 69.0 | 83.1 | 53.8 | 39.0 | 70.1 | 66.4 | 80.5 | 33.6 |
| L9-LA64 | 28.1 | 28.1 | 68.1 | 65.7 | 72.1 | 58.1 | 38.1 | 69.4 | 66.2 | 84.3 | 38.3 |
| L7-LB | 45.7 | 45.7 | 97.4 | 90.2 | 99.0 | 74.3 | 68.3 | 61.7 | 91.0 | 63.6 | 1.7 |
| L11-LBsoft | 32.6 | 32.6 | 80.2 | 72.1 | 81.0 | 56.9 | 43.8 | 72.8 | 67.1 | 73.6 | 0.7 |
| L13-LBsoft10 | 16.9 | 16.9 | 66.0 | 56.0 | 63.3 | 44.8 | 24.3 | 65.7 | 49.0 | 74.3 | 0.5 |
| L14-LBnk30 | 14.3 | 14.3 | 60.5 | 53.6 | 56.9 | 42.1 | 22.4 | 59.6 | 44.5 | 68.3 | 0.7 |

### F5-far (420 rows each)

| run | whole right W | W after format fix | K alone | K inside join | J alone | J inside join | both inside join | answer right if both inside | first call (tool history) | join call (tool history) | T splitter (own pieces, own join) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| parent | 0.0 | 0.0 | 2.9 | 1.4 | 4.3 | 4.0 | 0.0 | - | 0.0 | 0.0 | 0.0 |
| L8-LB | 1.2 | 1.2 | 36.7 | 25.0 | 62.1 | 24.0 | 5.2 | 22.7 | 24.0 | 7.1 | 9.0 |
| L8-LA64 | 0.5 | 0.5 | 26.0 | 22.9 | 50.7 | 28.1 | 4.5 | 10.5 | 18.3 | 7.1 | 11.9 |
| L9-LB | 1.4 | 1.4 | 28.1 | 25.2 | 51.2 | 21.4 | 4.8 | 30.0 | 35.5 | 19.8 | 3.8 |
| L9-LA64 | 1.7 | 1.7 | 24.0 | 21.4 | 36.2 | 28.6 | 4.8 | 25.0 | 28.1 | 33.3 | 3.8 |
| L7-LB | 1.9 | 1.9 | 16.9 | 22.1 | 29.8 | 28.6 | 6.4 | 29.6 | 26.4 | 15.0 | 0.0 |
| L11-LBsoft | 0.7 | 0.7 | 18.6 | 20.0 | 28.6 | 22.9 | 3.3 | 21.4 | 26.2 | 11.2 | 0.5 |
| L13-LBsoft10 | 0.0 | 0.0 | 15.5 | 20.2 | 21.4 | 22.6 | 3.3 | 0.0 | 17.4 | 10.2 | 0.0 |
| L14-LBnk30 | 0.2 | 0.2 | 14.5 | 18.3 | 21.0 | 23.3 | 3.3 | 0.0 | 13.6 | 8.8 | 0.0 |

## Guards and piece tokens (P1 lookups, shown from files)

- **Were the guards on in the headline far runs? Mostly no.** The far figures (F5) of my runs come from L2, L4, L8, L9 (and L12, quarantined): none of their scores.jsonl rows has a guard field, so no K-FAC mask and no KL replay. LB = every weight, LA64 = rank-64 add-on on a frozen base
  (a structural guard only). The K-FAC guard was on only in the join tests L7-LBG (hard mask, no KL), L11 (soft 1, 10x KL), L13 (soft 10, 10x KL), L14 (hard, 30x KL), recorded in each scores.jsonl; F5 was not among the cells those runs scored; scored now on the kept checkpoints it is
  0.7 / 0.0 / 0.2 (L11 / L13 / L14). Domain mode's own far runs (DM2; v7, v9, v10) used the per-tool low-rank add-on (rank 8; v10 rank 64) on a frozen base, replay share 0.5 and a 3-point undo rule, with no K-FAC and no KL
  (`domain/constants*.json`, `domain/mode.py`). Main brain's K-FAC + KL arms scored DM2 far at +2.14, -0.71, -0.36, +1.07 (its "fails as always"). So far has failed with and without the K-FAC guard.
- **Does the model emit piece results as tokens? No (shown, `custom_io/models/tool.py` docstring and `run`, lines 340-364).** The model writes only the call text (`add 12 5`: the op, then each operand as digit cells or as a span copied
  from the prompt or the tape). The calculator outside the model computes the result and appends the entry `add 12 5 = 17` to the tape, which the reader reads from the next round on. The model never writes a result itself; it
  copies it into a later call or into the final answer. A piece's value therefore exists only as a calculator-written tape entry, and a join needs a correct copy of it into an operand.

## What this does and does not settle

Shown: the 4% is not a scoring artifact; pieces lose accuracy beside a second piece; the join call is weak on the baselines and strong after join practice; the first call's cell reading is the main first error, equally on single formulas.
Suggested: far is limited by first-call cell reading on big grids and by long chains, not by the join. Untested: whether a change that fixes first-call cell reading on single far formulas lifts far joins; the ladder and taxonomy are for the saved
single runs only, so none of this is a seed-powered verdict.
