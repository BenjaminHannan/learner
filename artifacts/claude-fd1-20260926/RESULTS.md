# fd-1 results: are the items nights knock out the base's shakiest right answers? (Fix sleep, report-only)

Run: scripts/claude_fd1_fragile.py on CPU, plain MiniCPM5-1B (rev 87179e5c, thinking off), finished 2026-09-26 16:00 UTC.
Raw: cpu/fd1_rows.jsonl (300 rows), cpu/fd1_summary.json. Plan fixed before the run: PLAN.md (0ecbfb843).

## Check first
The base's right/wrong here agrees with dl-4's base_harm_items on 298 of 300 items. The 2 disagreements are "bigger"
items (198, 214) right here and wrong in dl-4's GPU run; neither is a lost item.

## The fixed prediction
Lost items = union of dl-4's night-7 lost items over S and K, seeds 6 and 7: 29 items. Base-right items: 200, sorted by
confidence (smallest token probability among the first 4 answer tokens); lowest third = 66 items.
- Lost items in the lowest-confidence third: **17 of 29 (58.6%)**. Chance would be about 33%.
- Bar fixed in PLAN.md: 60% or more = suggested; 40% or less = shown wrong.
- **Verdict: in between. The fixed bar is missed by one item (18 of 29 would be 62%), and the idea is not shown wrong.**

## Report only (read after the verdict; descriptions, not tests)
- By third of confidence: lowest 17 lost, middle 9, highest 3.
- Median confidence: lost items 0.55, kept items 0.75.
- Lost items by kind: capital 19, order 5, opposite 2, count 2, bigger 1. The base gets 58 capitals right; 19 of those
  58 (a third) were lost in at least one of dl-4's four night-7 models.
- Within capitals only: 17 of the 19 lost capitals are in the less confident half of the base's right capitals (2 in
  the more confident half). Outside capitals the pattern is weak: 4, 5 and 1 of 10 lost items by third.

## What this means (suggested, not shown)
The forgetting is mostly the base's shaky capital-city knowledge being knocked over. The base's confidence predicts
which capitals fall well, and other kinds only weakly. A fix therefore has to protect thin-margin facts, and it has to
do so without the harm panel: facts the nights never rehearse are the case that matters in real use.

## Limits
One base run on CPU; the lost set comes from four night-7 models of one experiment (dl-4). The within-capital split
was not in the plan. No adapter was loaded and nothing was trained.
