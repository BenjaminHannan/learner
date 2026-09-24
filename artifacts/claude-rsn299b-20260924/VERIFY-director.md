# rsn-299b verification by the reasoning thread (2026-09-24)

Verdict: registered FAIL on P299b.1 (+10 of 60 against a bar of +12). P299b.2 and P299b.3 pass. This was rsn-299's one follow-up, so the rsn line stops for September.

Checks:
- Seals: SEAL-code (7 lines) and the panel SEAL are OK on main. The builder ran from git archive faa7ee214 and its seal check matched, done with hashlib because BensPC has no sha256sum.
- Recount: the sealed scorer on the builder's run files gives the same totals as its panel-score.json. P: 28 right / 1 unsure / 29 wrong / 2 none. V: 38 right / 12 unsure / 10 wrong / 0 none. Arithmetic errors: 0 in both arms.
- Vote re-derived: decide() on the stored 5 samples reproduces the chosen reply on 60 of 60 rows. 16 rows had no 3-of-5 majority and were answered "I'm not sure".
- Model: MiniCPM5-1B commit 87179e5c, the same snapshot as rsn-299. Window 09:01-09:13 ET on BensPC.
- The builder's deviations are harmless: it created OUT/ and re-ran P once after a crash that wrote 0 rows, resolved BASE to the local snapshot path, and the rules file was missing.

Extra counts (no mark):
- Sample 0 alone was right on 33 of 60.
- At least one of the 5 samples was right on 48 of 60.
- 11 of the 16 no-majority rows contained a right sample.

What it means: voting makes the 1B much more careful. It had 10 wrong answers instead of 29, and it said "not sure" on 5 of 6 missing-fact questions, where plain said it on 0. But it gets only 10 more right, not 12. The right answer is often among the samples (48 of 60), and the vote can't pick it out.
What it doesn't mean: it is not a panel-independent measure of safety, and 60 items is a small test.
