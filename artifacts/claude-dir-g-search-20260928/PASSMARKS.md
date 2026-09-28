# dir-g pass marks: four learned starts, keep the one the net's check head picks (helper G, written 2026-09-28 21:22 UTC, before any script or run)

Fixed now. Nobody changes them after a score is seen. A separate blind recount reads only the raw files and this page.
Labels: SHOWN = counted from code or files. SUGGESTED = fits the counts. UNTESTED = nobody has run it.
Design and reasons: DESIGN.md. Nothing has run; no score of this test exists.

## The single change
Give the loop K = 4 learned start states instead of 1 (the sealed loop starts every puzzle from zeros), train so the four streams differ (only the best stream per item gets the token loss, weight 0.05 on the others), and at test keep the stream whose own halt head is most confident. Nothing else changes: same puzzle stream (the pool H2 and its fallback left, see Entry), loss otherwise, halt rule per stream, architecture width and layers, steps (60,000), batch (256), fixed env 0 (kind not told), the 8 tests, 48 test rounds. No kind label, no solver, no puzzle-specific code at test time.

## Entry (decided by the Director from H2, before G is run)
G is run only if H2's primary result (PASSMARKS of dir-h2) is WRONG-cannot-fit, WRONG-memorised, or PARTIAL. If H2 is PASS-LOOP the number puzzles are solved by the pool alone and G is parked (no run). The Director writes G-BASELINE.md before the G run, naming: the recipe G trains on (H2 pool, or old pool, or H2's any-valid fallback if it was run and read first); B_s = that recipe's held-out numbers4 score (of 300) for each G seed, read from that recipe's own tests.json; F4 (below). These come from other tests, not from any G score.

## Measures (of 300 held-out numbers4 hands, target 24, the sealed 300; per net)
- S_pick: answer of the stream with the highest halt probability at its own stop (sealed stop rule per stream); ties go to the lowest stream index.
- S_rand: answer of a fixed random stream (stream 0 counts; also report the mean over the 4). Reads what the picking adds.
- S_any: any of the 4 streams right at its own stop (oracle, report and read only).
- Also: mean number of distinct final answers among the 4 streams (D), practice exactness of the numbers4 stream (last 3 log lines), sums4, grids5, sums6, grids6, numbers5 (reported).
- F4 (computed in pure python before the run, entered in G-BASELINE.md): expected S_any of 4 independent no-arithmetic guesses (the diagnosis's floor strategies A, B, C, four draws each, exact over number orders). Upper bound 4 x 7.5 = 30.

## Validity (V). Any miss = INCONCLUSIVE
- V0: steps_block_nograd = 0 on every net; V1: poison (kind field swapped) identical on every net.
- V2: K=1 selftest: with K=1 and start zeros the new code gives the same logits, loss and halt loss as the sealed 358u loop on 8 fixed batches (max abs difference <= 1e-5, CPU fp32).
- V3: sealed 358u code, tests and new scripts match their sha256 lines before the run.
- V4 diversity: D >= 2.0 on every net. If D < 2.0 the result is INCONCLUSIVE-COLLAPSED (the mechanism did not run), not a verdict on search.
- V5 gates: sums4 >= 295 and grids5 >= 295 on every net (as the H2 gates). A miss = FAIL-gate: a PASS cannot stand.

## PASS-G (needs V0-V5; loop seeds 13 and 14, primary)
On both seeds: S_pick >= max(30, B_s + 15) AND S_pick >= 2 x S_rand AND S_pick > F4. If F4 > 30 the first bar becomes F4 + 10.
Wording of a pass, fixed: "four learned starts with the net's own pick solved unseen number hands." Never worded "it searches like a person" or "it checks arithmetic": whether the head checks arithmetic or picks by another cue is UNTESTED.
Replication (seeds 15 and 16) only after the primary is recounted; it can confirm or contradict, it cannot rescue a primary non-pass or overturn a primary WRONG.

## The result that would prove it wrong
**WRONG (four tries added nothing)** = V0-V5 met, and on both primary seeds S_any <= B_s + 8. Even an oracle that always picks the right one of four gets no more than 8 above the one-stream net, so the streams are not producing better candidates. Reading: candidates do not differ in a useful way, likely because no net check of arithmetic exists to shape them (cause 2). If practice exactness >= 0.9 on all streams as well: "all four streams memorised".
**Candidates fine, check not** (NOT counted as wrong): S_any >= max(30, B_s + 15, F4 + 10) on both seeds while S_pick fails PASS-G. The net makes good candidates but its halt head cannot pick. Sends the next step to check-head training on wrong-answer corruptions (DESIGN.md section 6), not proposed now.
Anything else (some seed S_pick 9 to 29 above B_s, 1 of 2 seeds passing, arms disagree): PARTIAL, no claim, no second change until the marks are read.

## Prediction (SUGGESTED, not a result)
PASS about 10%. Likeliest: WRONG or PARTIAL, because nothing in the loss teaches arithmetic checking (DIAGNOSIS.md cause 2). A WRONG here still tells us that more tries do not help a net that cannot check.

## Procedure
1. Builder writes the runner and the floor script (new files, prefix claude_dir_g_), runs the pure-python selftest and V2 on CPU; Director seals sha256 of this page and the scripts.
2. Director writes G-BASELINE.md, then releases the queue job (HELD until then).
3. Blind recount step reads only raw files (tests.json, extra.json, train_log.jsonl, poison.json) and this page and writes VERIFY-recount.md.
