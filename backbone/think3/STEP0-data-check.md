# Step 0 data check (PR #131 plan), 2026-10-26 ~00:30Z, CPU only

Built with `python3 backbone/build_data.py <dir> --workers 4 --skip-tokens` (3 min, 4 cores). The stories come from
learnlab.village.shards (v1 generator, seed 0). Validation shard 0 has 2,167 questions in 250 visits. 20 random rows are
in `step0_rows.txt`, each with its question, its evidence lines and its answer.

Findings (validation shard 0):
- Every question has `evidence_text_lines` pointing into the shard's .txt, and every one sits before the question line.
- Read by hand, all 20 sampled rows are answerable from their evidence lines plus the question. That includes rule
  lines ("Nuli always follows Nelo", "Lost things are back with their owners every night") and the right distractor-free
  steps for plan, compare and where-before questions. Depth-0 rows have no lines; their answer is "not told".
- The lines are stored in **file order** (ascending line number), not chain order. Example: in "Who is holding the grey
  balloon?" the night rule comes before the event it applies to. A trace that has to follow the chain needs a small
  generator change to keep the order.
- The number of lines often differs from `depth`: depth-1 rows have 1-8 lines, and in-container lists have one line per
  item. So "one latent per line" needs a cap or packing (the counts per (depth, n_lines) are at the top of `step0_rows.txt`).
- Lines are short, about 8-12 words each. A depth-3/4 trace of 3-4 lines is roughly 40-60 tokens, which is the
  short-trace regime where CODI is shown to work.

Verdict: the evidence lines are usable as gold traces. Caveat: they are in file order, and the line count is not the depth.
