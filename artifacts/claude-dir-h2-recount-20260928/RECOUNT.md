# Blind recount of dir-h2-a (numbers puzzles, wide practice pool)
Counted 2026-09-28 by the recount thread. Inputs: only the raw files in `artifacts/claude-dir-h2-numbers-20260928/runs/<net>/` on origin/builder-outbox (tests.json, extra.json, poison.json, train_log.jsonl, train_summary.json, <net>.log) and RUN-NOTE.md, plus PASSMARKS.md and ADDENDUM-1.md on main. No Director board, roadmap or other judgement was read. Labels: SHOWN = counted from those files.

## VERDICT: WRONG-cannot-fit  (SHOWN, if V3 holds; see V3)
Test G entry rule that applies: **WRONG-cannot-fit** (PASSMARKS "cannot fit": practice exactness < 0.5 on any net, with numbers4 <= 8 on every net). G runs.

## Counts (x of 300 unless noted)
| net | numbers4 | numbers5 (report) | sums4 | grids5 | sums6 | grids6 | practice exactness (numbers4, mean of last 3 log lines) | P_other | P_train24 |
|---|---|---|---|---|---|---|---|---|---|
| loop s13 | 4 | 1 | 300 | 300 | 294 | 283 | 0.3817 (0.369, 0.376, 0.400) | 7 | 117 |
| loop s14 | 4 | 0 | 300 | 300 | 295 | 287 | 0.5610 (0.580, 0.581, 0.522) | 10 | 174 |
| plain s13 | 6 | 0 | 300 | 298 | (178) | (234) | 1.0000 | 7 | 300 |
| plain s14 | 4 | 0 | 300 | 287 | (137) | (226) | 1.0000 | 10 | 300 |
Numbers in brackets are not judged for plain. "right" in tests.json / extra.json is the score at the net's own stop (loop) or one pass (plain).

## Validity
- V0 (steps_block_nograd = 0 on every loop net): 2 of 2 loop nets are 0. MET.
- V1 (poison identical on every net): 4 of 4 `V1_identical: true`. MET.
- V2 (pool line 36782 / 300 / 0 / 0): 4 of 4 logs print "h2 pool: 36782 practice pairs over 1519 hands, 300 dev pairs, 0 held-out hands in the pool, 0 dev pairs in the pool". MET. All 4 nets also have 120 log lines ending at step 60000.
- V3 (seals match): **cannot be recounted from the raw files.** RUN-NOTE.md reports the 20 of 20 check of the 358u SEAL-code file (after a re-fetch of two files) but does not state a check of SEAL-h2.sha256.txt or of the new scripts' sha256. Treated as NOT SHOWN here. If the Director's own seal check of SEAL-h2 and SEAL-run holds, the verdict stands; if V3 fails the result is INCONCLUSIVE.

## Applying the marks
1. PASS-LOOP / PASS-PLAIN need numbers4 >= 30 per net. Best net is 6 of 300. Not met (0 of 4 nets at 30).
2. WRONG needs every primary net numbers4 <= 8: 4, 4, 6, 4. Met (4 of 4).
3. Branches:
   - memorised again (exactness >= 0.9 AND P_other <= 8 on every net): loop exactness 0.38 and 0.56 (0 of 2 loop nets at 0.9); P_other 7, 10, 7, 10 (2 of 4 nets at <= 8). NOT met.
   - **cannot fit (exactness < 0.5 on any net): loop s13 is 0.3817. MET (1 of 4 nets).** loop s14 is 0.561, which is in neither branch alone; "any net" is enough.
   - too little target 24 (P_other >= 30 on both seeds of an arm): P_other max is 10. NOT met.
4. ADDENDUM-1 floor: P_other is 7, 10, 7, 10 of 300, all at or below the no-search floor F = 12.00 (and B = 12.00). 4 of 4 nets sit inside the "9 to 29 is noise band" or below it; none beats a net that copies one fixed skeleton without checking arithmetic. Nothing here supports a net that generalises to new targets.

## Side observations (SHOWN counts, not part of the marks)
- Plain nets memorised the pool: practice exactness 1.0 on 2 of 2, P_train24 300 of 300, but held-out numbers4 6 and 4 and P_other 7 and 10.
- Loop nets did not fit the pool: numbers4 practice exactness 0.38 and 0.56 (old recipe was perfect on its 1,062 hands). Loop P_train24 117 and 174 of 300.
- Nothing else got worse: sums4 and grids5 are 300, 300 (loop) and sums4 300, 300, grids5 298, 287 (plain); loop sums6 294, 295 and grids6 283, 287. Loop grids6 283 is 4 below the 287 old minimum and above the PASS gate 275 (gates only matter for a PASS).

## How to redo it
`python3 recount.py <path to runs/>` (this folder) reads only the five raw files per net and the net's log, prints every number above and writes recount.json. Practice exactness = mean of `exact_by_kind.numbers4` in the last 3 lines of train_log.jsonl. Tests are `tests.numbers4.right` etc. in tests.json; P_other and P_train24 are `P_other.right`, `P_train24.right` in extra.json.
