# Leap-1 addendum 1 (2026-10-24 ~01:55Z, before any Leap-1 result: the first boxes crashed at a shell bug before running)

One change, adopted from Creative-1's failure (backbone/RESULTS-creative1.md): Qwen "fit" the examples with lookup
tables (`lambda x: 3200 if x == 20 else ...`), the checker accepted them, and sleep amplified the habit.
Leap-1's checker now rejects any program containing if/else, a comparison, or and/or (creative1.NO_BRANCH, the same
rule as PREREG-creative2.md). It applies everywhere programs are judged: first-try scoring, the 16-sample checked
search, exploration and repair, and the vLLM reference. All 600 EVAL gold programs pass it (checked in code).
Pass marks, arms and everything else are unchanged.
