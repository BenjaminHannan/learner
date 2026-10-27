# fd-1 plan (report-only diagnosis, fixed before it runs; Fix-sleep, 2026-09-26)
Question: are the general questions that nights knock out the base's least confident right answers?
Data: dl-4's night-7 lost items (union over S and K, seeds 6 and 7: 29 items); the plain base's per-token
probabilities on its own greedy answers to the same 300 items (scripts/claude_fd1_fragile.py, CPU, $0).
Confidence = the smallest token probability among the first 4 answer tokens.
Prediction fixed now: at least 60% of the lost items fall in the lowest-confidence third of the base-right items
("suggested" if so; chance is 33%). Shown wrong if 40% or fewer do.
What it would change: if lost items are the base's weakest answers, the next forgetting fix protects low-margin
knowledge specifically (for example, the night's harm check and any replay weight the base's unsure answers), and
the harm count needs a noise floor (a placebo night) before a fix can be judged. No marks, nothing trained.
Check first: the base's greedy right/wrong here must agree with dl-4's base_harm_items on nearly all 300 items (same
call, different machine); disagreements are reported.
