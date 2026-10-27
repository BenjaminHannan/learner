# dir-h2 numbers: pass marks (written 2026-09-28T19:13Z, before any script or run; helper H2)

These marks are fixed now. Nobody changes them after a score is seen. A separate step recounts the results from the raw
files (tests.json, extra.json, train_log.jsonl, train_summary.json, poison.json) and this page only.
Labels: SHOWN = counted from code here. SUGGESTED = fits the counts. UNTESTED = nobody has run it.

## The idea being tested (plain words)
The nets learn the 1,062 practice hands of "numbers" (target 24) perfectly, as a lookup table, and get 0 to 3 of 300 on the
300 hands they never saw (12 of 12 nets: 16 of 3,600). Each practice hand is shown about 2,410 times. The idea: stop showing
the same items so often. Give the numbers-4 practice a much bigger pool of different puzzles, and see whether hands the net
has never seen become solvable.

## The single change
Only the pool the 4-number practice draws from. Old pool: the 1,062 practice hands, always target 24. New pool: every 4-number
hand from 1-13 that is not one of the 300 held-out hands, paired with every target from 5 to 40 that the hand can reach
(the same target range the 3-number puzzles already use), with the stored answer from the same solver
(`claude_blurt1.solve`). 300 of those (hand, target) pairs with target not 24 are set aside as a dev check and removed from
practice. Everything else is untouched: tasks, sizes, the 3-number and sum and grid streams, architecture, loss, halt rule,
steps (60,000), batch (256), learning rate, schedule, fixed env 0 (kind not told), the 8 tests, the 48 test rounds and the own
stop rule. Implemented as a new runner (`scripts/claude_dir_h2_run.py`) that imports the sealed 358u code and swaps only
`Source.four`.

Pool counts, SHOWN here in pure python (recounted 2026-09-28, matches the diagnosis: rule.json and answers.json):
- new pool: 37,082 (hand, target) pairs over 1,519 distinct hands; 1,062 of the pairs are the old target-24 practice pairs
  (same hands, same stored answers); minus 300 dev pairs = 36,782 practice pairs.
- draws: numbers4 gets 1/6 of 60,000 steps x 256 = 2.56 M draws, so about 69.6 draws per pair (old: 2,410 per hand). 35 times fewer repeats.
- the 300 held-out hands share no multiset with any pool pair (0 of 300 hands appear, at any target), so they are disjoint by hand
  and therefore by (hand, target).
- Honest limit (SHOWN): the new pool has 1,519 different hands, only 457 more than before. What grows is targets per hand, not
  new hands. A net could still memorise (hand, target) pairs. That is one of the ways the idea can be shown wrong (below).
- Honest limit (SHOWN): target-24 pairs fall from 100% to 1,062 of 36,782 (2.9%) of numbers4 practice.

## Arms and runs
Same size as the rsn-358u race (loop: 2 layers, width 512; plain: 8 layers, width 256; about 6.3 M weights each; same
sizes as the 358u nets), 60,000 steps, batch 256, defaults only.
- Primary: loop seeds 13 and 14, plain seeds 13 and 14 (4 nets). Marks below judge these.
- Replication (only after the primary is scored): loop and plain seeds 15 and 16. Judged by the same marks as their own
  batch; it can confirm or contradict, it cannot rescue a primary FAIL or overturn a primary WRONG.
- Comparison (SHOWN, same recipe, old pool; tests.json of rsn358u and rsn358u2): held-out numbers4 of 300 per net,
  loop 358u 1,1,0,1; plain 358u 1,0,1,3; loop 358u2 2,2,3,1. Twelve nets: range 0 to 3, mean 1.33, spread (sd) about 1.0.
  sums4 and grids5 were 300 of 300 on all 12. Loop sums6 296 to 300 and grids6 287 to 297 (u and u2 together, 8 loop nets).

## Tests and extra measures
- Held-out numbers4: the sealed 300 hands (artifacts/claude-rsn358i-20260926/tests/numbers4.jsonl, sha256 in 358u SEAL-code),
  target 24, right at the net's own stop (loop) or one pass (plain). Checked once per net.
- Gates: sums4, grids5 (practised sizes), and for the loop arm sums6 and grids6 (bigger sizes), from the same sealed tests.
- Practice exactness: numbers4 training exactness (stored-exact), mean of the last 3 log lines of train_log.jsonl.
- P_other: the 300 dev (hand, target not 24) pairs above, right at the net's own stop (any valid answer counts, as in the tests).
  Never trained on. Measured once per net by `claude_dir_h2_run.py extra`.
- P_train24: 300 practice hands at target 24 (fixed sample), right at own stop. Report only.

## Validity (V). Any miss = INCONCLUSIVE, not a pass or a fail
- V0: steps_block_nograd = 0 on every loop net.
- V1: poison check identical (kind field swapped) on every net.
- V2: the run log prints the pool line: 36782 practice pairs, 300 dev pairs, 0 held-out hands in the pool, 0 dev pairs in the pool.
- V3: sealed 358u code and tests match SEAL-code.sha256.txt (20 of 20 lines) before the run; new scripts match the sha256
  listed in the queue job's SEAL step.

## PASS marks (numbers4 held-out of 300)
Threshold **30 of 300 per net.** Why: the twelve old nets sit at 0 to 3 (mean 1.33, spread about 1.0); 30 is 10 times the best
old net and 4 times the best score reachable with no arithmetic at all (search-free floor B = 7.5 of 300, diagnosis section 1).
A net at 30 or more has clearly done something the old ones did not do. Nothing below 30 is called a win.
- **PASS-LOOP** = V0-V3 met, and loop s13 and s14 both have numbers4 >= 30, and loop sums4 >= 295 and grids5 >= 295 and
  sums6 >= 285 and grids6 >= 275 on both seeds.
- **PASS-PLAIN** = V1-V3 met, and plain s13 and s14 both have numbers4 >= 30, and sums4 >= 295 and grids5 >= 295 on both.
- Gate wording: the old nets were 300 of 300 on sums4 and grids5, so 295 allows 5 of 300 of noise; loop sums6 and grids6 allow
  about 12 below the old minimum (296 and 287).
- The idea is SUPPORTED (label: shown for those nets, suggested beyond them) if PASS-LOOP or PASS-PLAIN. Both = the pool fixes it
  for both arms. Only one = it fixes it for that arm only; no claim about the other.
- A pass says the net solves unseen hands at target 24. It does not say it searches, and it says nothing about hands with 5 or 6 numbers
  (numbers5 is reported, not judged).

## The result that would prove the idea wrong
**WRONG (bigger pool did not help)** = V0-V3 met, and every primary net has numbers4 <= 8 of 300 (at the search-free floor,
8 is the smallest whole number above B = 7.5), and this is read as one of:
- memorised again: practice exactness >= 0.9 AND P_other <= 8 of 300 on every net. The nets store the 36,782 pairs the way they
  stored 1,062 hands; new pairs fail like new hands. 69 draws per pair was not enough, or the pool needs new hands, not new targets.
- cannot fit: practice exactness < 0.5 on any net, with numbers4 <= 8. The net cannot even learn the bigger pool, which points to
  cause 2 of the diagnosis (nothing rewards checking arithmetic) rather than repeats.
- too little target 24 (NOT counted as the idea wrong): P_other >= 30 on at least one arm's both seeds while numbers4 <= 8. The net
  generalises to unseen pairs but not to the graded target. It says the pool works and the target mix is the problem; a later
  single change (weight on target 24) is not proposed here.
The example the manager gave: practice exactness 1.0 but held-out still <= 3 of 300 with the big pool. That falls under
"memorised again" and counts as WRONG.

## Everything else
Any result that is neither PASS nor WRONG (numbers4 of 9 to 29 on some net; 30 or more on only one of two seeds; the arms disagree):
PARTIAL. No claim, no second change until the marks are read by the Director. If V0-V3 fail: INCONCLUSIVE.
Prediction (SUGGESTED, not a result): PASS about 20 to 25%. The likeliest results are "memorised again" or "cannot fit". Either one
sends the next step to a training signal that rewards checking (DESIGN.md section 5).

## Procedure
1. Director seals the new scripts (sha256 in the queue job) and runs `python -B scripts/claude_dir_h2_pool.py selftest` (no torch).
2. BensPC runs the queue job (primary 4 nets), then `extra` once per net.
3. A separate blind recount step reads only the raw files and this page and writes VERIFY-recount.md.
