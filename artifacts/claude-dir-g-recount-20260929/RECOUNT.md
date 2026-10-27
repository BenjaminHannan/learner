# Blind recount of test G (2026-09-29)

Inputs used before writing this table: runs/g-s13 and g-s14 (tests.json, train_summary.json, poison.json, train_log.jsonl), PASSMARKS.md, ADDENDUM-1.md, G-BASELINE.md. RESULT.md was NOT opened until this table was written. No GPU, no spend. Counts are held-out numbers4 hands, "x of 300".

## Counts (SHOWN, read from tests.json `numbers4`)
| | seed 13 | seed 14 |
|---|---|---|
| S_pick | 30 of 300 | 24 of 300 |
| S_rand (stream 0) | 19 of 300 | 13 of 300 |
| S_rand mean over 4 streams | 16.25 (right_by_stream 19,15,14,17) | 13.0 (13,11,14,14) |
| S_any (4 streams, at own stop) | 42 of 300 | 33 of 300 |
| D (mean distinct answers) | 3.177 | 2.897 |
| stream 0 alone, oracle over any of 48 rounds | 37 of 300 | 35 of 300 |
| any round, any stream (reading-only oracle) | 90 of 300 | 94 of 300 |
B_s = 4 and 4 (from G-BASELINE.md, not recounted here); F4 = 19.219 (G-BASELINE.md).

## Validity
- V0 steps_block_nograd = 0 on both (train_summary, 60000 steps seen). MET.
- V1 poison identical on both (sums, grids, numbers each 100 of 100). MET.
- V2 (K=1 selftest): not recountable from raw run files; only ADDENDUM-1 reports it (diff 4.8e-07 vs bar 1e-5). Taken from that file, not recounted.
- V3 sha256: `sha256sum -c` passes for SEAL-g (PASSMARKS, ADDENDUM-1, both scripts, G-BASELINE) and SEAL-results (tests, summaries, poison, logs, RUN-NOTE, RESULT.md), all OK. MET. (This only shows files unchanged since sealing.)
- V4 D >= 2.0: 3.177 and 2.897. MET.
- V5 sums4 and grids5 >= 295: 300/300 and 300/300 on both. MET.
- Extra: all 10 tests have n = 300 on both nets. Practice numbers4 exactness per stream, mean of last 3 log lines: s13 0.268, 0.187, 0.225, 0.238; s14 0.308, 0.257, 0.271, 0.239. All far below 0.9, so "all four streams memorised" does NOT apply.
- Other tests, S_pick: sums6 297 / 295, grids6 273 / 293, numbers5 0 / 0.

## Verdicts by the sealed rules
- PASS-G: FAILS. Bar is S_pick >= 30 AND S_pick >= 2 x S_rand AND > F4 on both seeds. Seed 13: 30 >= 30 yes, but 2 x 19 = 38 (2 x 16.25 = 32.5 on the mean) so 30 fails it. Seed 14: 24 < 30 fails. Both fail on the 2 x S_rand clause; seed 14 also on the 30 clause.
- WRONG: FAILS. It needs S_any <= 12 on both; S_any is 42 and 33.
- Candidates fine, check not: MET numerically. Needs S_any >= max(30, 19, 29.2) = 30 on both (42 and 33 pass) while S_pick fails PASS-G (it does).
- The sealed catch-all "PARTIAL, no claim" is not the verdict, since the "candidates fine" clause is satisfied.

## Reading caveat: is S_any over 4 streams better than one stream with an oracle over 48 rounds?
- Seed 13: 42 vs 37 (5 more). Seed 14: 33 vs 35 (2 FEWER).
- So four streams with an oracle is not clearly better than one stream with an oracle over its own 48 rounds: one seed slightly, one seed worse. The claim "the four starts produce better candidates" is not supported by this comparison; the "any-round" oracle is a different kind of oracle (it picks the round, not just the stream) but it is already 37 and 35 without any extra start vectors.
- Per-stream right counts (13 to 19) sit near the H2 plain nets (6, 4) and F4 blind-guess level (19.2), and S_pick is at or below stream 0 plus a few (30 vs 19, 24 vs 13). The pick beats a random stream by 11 in both seeds, so the halt head adds something, but S_any - S_rand is 23 and 20.
- Caveat on the comparison: S_any is judged at each stream's stop, the 37/35 at any of 48 rounds; the two are not the same rule. Not recomputed for single-stream at its stop from raw files.

## Comparison with RESULT.md (opened only after the tables above were written)
- MATCH: every count (S_pick 30/24, S_rand0 19/13, S_rand mean 16.25/13.0, S_any 42/33, D 3.177/2.897, 37/35, 90/94), V0, V1, V4, V5, the three verdict lines, the per-stream and practice exactness numbers, and the S_any-vs-one-stream reading (+5 and -2).
- No mismatch in counts or verdicts.
- Differences in how checked: RESULT.md takes V2 and V3 from RUN-NOTE; here V3 was rerun with `sha256sum -c` (all OK) and V2 is only taken from ADDENDUM-1. RESULT.md's "best-of-four in training 0.734 and 0.790" was not recounted here.
- Wording note: the sealed rules make "candidates fine, check not" true on the numbers. It is not proof the candidates are good: S_any is not clearly above one stream's own any-round oracle (37, 35), so a "the four starts help" claim is not supported by that comparison.
