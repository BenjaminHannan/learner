# Test G result, primary seeds 13 and 14 (marks judge by the G builder thread; NOT yet blind-recounted)

Judged 2026-09-29 09:25 UTC (`date -u`) from `runs/g-s13/` and `runs/g-s14/` (tests.json, poison.json, train_log.jsonl, train_summary.json, `runs/RUN-NOTE.md`) against `artifacts/claude-dir-g-search-20260928/PASSMARKS.md`, ADDENDUM-1.md and G-BASELINE.md (B_13 = B_14 = 4, F4 = 19.219). Labels: SHOWN = counted from those files.

## Verdict: CANDIDATES FINE, CHECK NOT (PASSMARKS: "not counted as wrong"). Not a pass. Not proved wrong.  (SHOWN, subject to the blind recount)
Next step the marks name: check-head training on wrong-answer corruptions (DESIGN.md section 6). Not started; needs the Director.

## Counts, held-out numbers4 (x of 300)
| net | S_pick | S_rand (stream 0) | S_rand (mean of 4) | S_any (oracle) | D | one stream, any of 48 rounds | any stream, any round |
|---|---:|---:|---:|---:|---:|---:|---:|
| g-s13 | 30 | 19 | 16.25 | 42 | 3.177 | 37 | 90 |
| g-s14 | 24 | 13 | 13.0 | 33 | 2.897 | 35 | 94 |
Reference: one-stream loop on the same pool B = 4, 4 (RECOUNT.md); F4 = 19.219.
Per-stream right at own stop: s13 [19, 15, 14, 17], s14 [13, 11, 14, 14]. Pick histogram (which stream was picked): s13 [109, 54, 47, 90], s14 [110, 65, 77, 48].

## Validity
V0 steps_block_nograd = 0 on both (MET). V1 poison identical on both (MET). V2 K=1 selftest passed, max abs diff 4.8e-07 (RUN-NOTE, MET). V3 seals 20 of 20, 3 of 3, 5 of 5 (RUN-NOTE, MET). V4 D >= 2.0: 3.177 and 2.897 (MET). V5 sums4 300 and 300, grids5 300 and 300 (MET; both >= 295).

## Applying the marks
- PASS-G needs, on both seeds, S_pick >= 30 AND S_pick >= 2 x S_rand AND S_pick > F4. s13: 30 >= 30 met; 30 >= 2 x 19 = 38 **not met** (also not against the mean, 2 x 16.25 = 32.5). s14: 24 >= 30 **not met**; 24 >= 26 not met. Result: PASS-G not met (0 of 2 seeds).
- WRONG needs S_any <= B_s + 8 = 12 on both: 42 and 33. Not met.
- "Candidates fine, check not" needs S_any >= max(30, B_s + 15, F4 + 10) = 30 on both, while S_pick fails PASS-G: 42 and 33 >= 30 on both seeds, S_pick fails PASS-G. **Met.**

## Reading (SHOWN counts; the reasons are SUGGESTED or UNTESTED as labelled)
- Every single stream is much better than the H2 one-stream loop: 11 to 19 of 300 at the own stop against 4 (SHOWN). The change that did it (four starts plus winner-take-all) is one bundle; which part matters is UNTESTED.
- The pick adds something over a random stream: S_pick 30 vs mean 16.25 (s13) and 24 vs 13 (s14), +13 and +11 (SHOWN). Whether the halt head checks arithmetic or uses another cue is UNTESTED (the marks forbid the wording "checks arithmetic").
- Both S_any values (42, 33) are above F4 = 19.2 by 23 and 14 (SHOWN), so the candidates beat four blind guesses; still below the "any of 48 rounds" controls: one stream alone reaches 37 and 35 if an oracle may choose the round (SHOWN, `right_at_any_round_stream0`). So the oracle over four streams at the stop (42, 33) is no higher than one stream's any-round oracle (37, 35): +5 on s13, -2 on s14; most of the "candidate" gain comes from streams being better and from the answer changing over rounds. Any stream at any round: 90 and 94 of 300, a third of hands; the stopping and picking do not find those (SHOWN counts, reason UNTESTED).
- Training fit is low: numbers4 practice exactness (mean of last 3 log lines, per stream) s13 [0.268, 0.187, 0.225, 0.238], s14 [0.308, 0.257, 0.271, 0.239]; best-of-four in training 0.734 and 0.790. Not memorised ("all four >= 0.9" no).
- Not part of the marks: numbers5 0 of 300 on both seeds (SHOWN). sums6 297 and 295, grids6 273 and 293 (report only).

## Cannot say
Why the head does not pick better, and whether check-head training would; whether a second seed pair replicates (dir-g-b held, needs a blind recount of this first). This is one design at one size.
