# rv-391 dev plan: a go-back trigger that fires (thought-memory thread; written 2026-09-26 16:38 UTC by date -u, before any measurement)

Why: rv-387 (artifacts/claude-rv387-20260926/RESULTS.md) never went back. Its trigger was "the stop head q fell after a
guess", and q rises after anything is written on the page.

Brain first (Ben, 16:05 UTC): people go back when something clashes, not when they feel less sure. In the brain, a
frontal region (the anterior cingulate cortex) responds to conflict between competing answers and to errors, and that
response triggers a change of strategy. This is textbook-level, and mapping it onto this net is a guess. So the
candidate triggers are conflict signals the net produces itself (scripts/claude_rv391_dev.py lists them). A rule-based
clash count is measured for comparison only. Under Ben's 16:04 redirect it cannot be the trigger.

## Step 1: measure, unregistered, on practice grids only
- Nets: 358i's four loop nets (the Mac copy), each sha256 checked against 358i's SEAL-run.sha256.txt.
- Grids: rv-390's practice sets p-grids7 and p-grids6 (seeds 39114 and 39113). No test grid of rv-387, rv-390 or 358i
  is touched.
- Search: rv-387's GUESS for 96 rounds on each unfinished practice grid. Each guess is labelled right or wrong from the
  practice grid's own solution.
- Output: artifacts/claude-rv391-20260926/dev/measure-s<seed>.json, with the AUC of each signal for wrong vs right
  guesses, over all guesses and over first guesses only, plus the per-guess rows.

## How the trigger is chosen (fixed now, before any number exists)
- Candidates: dq, d_mean_ent, d_max_ent, flips, p_written. clash_rule_based is not a candidate.
- The trigger is the candidate with the highest mean AUC over the four nets on p-grids7 (all guesses), if that mean
  is at least 0.65 and it is above 0.5 in all four nets.
- Its cut is the value, pooled over the four nets on p-grids7, that flags at most 20% of right guesses. The share of
  wrong guesses flagged at that cut is reported.
- p-grids6 is the check: the same signal and cut must flag more wrong than right guesses there, or the choice is
  reported as not holding up. rv-391 then uses the fallback below.
- Fallback (also the plan if no candidate reaches 0.65): the time slice from NOTE-rehearsal-2 in rv-387. Go back when
  the checker has not accepted the grid W = 16 rounds after a guess. It needs no signal. On the tiny rehearsal net it
  added nothing (27 vs 28 of 60), so it is the weaker bet.

## Step 2 (after step 1): register rv-391
One change from rv-390's GUESS worker: going back with the chosen trigger. It restores the snapshot and writes the next
candidate, as rv-387's BACK does. Fresh 7x7 test grids with a new seed; 4 nets; 480 rounds, like the between-messages
worker. Marks and predictions are fixed and sealed before any run. This note is a plan, not marks.
