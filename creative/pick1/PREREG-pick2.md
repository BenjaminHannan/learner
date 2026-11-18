# Pick-2: does a better-informed or thinking self-judge clear the bar Pick-1 just missed?

Fixed 2026-10-26 ~08:55Z, after Pick-1 (INCONCLUSIVE: SELF 34.4% vs RAND 19.7%, AUROC 0.692) and before any Pick-2
judging. Same 192 pools x 12 transcripts (Guess-1, K2-3.7B), same success labels, same pickers and metrics as Pick-1.
Because the data are reused, every variant and mark is fixed here and nothing is tuned afterwards.

## New judge variants (K2-3.7B, temperature 0)
- FULL: Pick-1's SELF prompt, but tool results truncated at 1,500 chars instead of 300 (Haiku often refused to score
  because results were cut). Score = P(yes) as in Pick-1.
- THINK: K2 thinking on at reasoning_effort "low" (template's <ifm|think_faster> path), max 768 new tokens, same
  question with 1,500-char results; the reply must end with "Answer: yes" or "Answer: no" and "Confidence: N" (0-10).
  Score = N/10 if yes, (10-N)/10 * -1 if no... simplified: score = N if yes else -N; unparsable = 0.
- FULL+THINK ensemble is NOT added (no post-hoc combos).

## Pass marks (all pools)
- Q1: max(FULL, THINK) pick rate >= RAND + 15 points (the Pick-1 P1 mark).
- Q2: the same variant's AUROC >= 0.70 (the Pick-1 P3 mark).
- Q3: the same variant >= Pick-1 SELF + 3 points (it must actually be better, not just over the line).
PASS = Q1-Q3 for at least one variant (report which). PROVED WRONG for this route: both variants <= SELF + 1 point;
then the small judge is at its limit and better picking needs a check that runs (sandbox replay / end-state probes).

## Cost
~4,600 K2 calls (2,304 short, 2,304 up to 768 tokens) on one GPU, ~20-40 min. No API spend.
