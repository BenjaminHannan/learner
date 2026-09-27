# PASSMARKS gr-7: gr-6's reader trained for 3 more epochs (registered 2026-09-27 04:22 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. These marks were written before any gr-7 code,
training or run. They are never edited; changes go in a dated addendum before the registered run. The plan went to the
Thread manager at 04:20 UTC. The review (04:20 UTC) passed it as one change with five changes, all written in below:
the exact recipe, loss in the test, a grey zone, the disclosure about the dev rows, and the breakdown kept out of the
marks.

## Why
gr-6 (VERIFY-gr6, 1b519a88c) was a DEV-FAIL: 103 of 123 held-out squares exact, against the 111 its rule needed.
- Its training loss at epoch 3 was 0.0062 and still falling. gr-5's was 0.0003.
- Suggested only, from a post-hoc breakdown on practice rows (scripts/claude_gr6_devdiag.py):
  - on gr-5's own 72 held-out squares, gr-6's adapter read 63, where gr-5's adapter read 71
  - nearly every new miss was a cell slip inside a grid of the right size
- The breakdown's 63 is not a mark (review point 5). The test below re-measures the same 72 rows after epoch 6, and
  its bar of 69 comes from gr-5's 71, not from the 63.

The plain reading is that the same 3-epoch budget, spread over 1.45 times as many and more varied rows, left the copy
under-trained. Interference between layouts, or too little capacity at rank 16, would look the same. The plain fix,
tried first under Ben's 19:20 rule, is to train longer.

## Brain first
Practice on a wider set of variants takes longer to settle than practice on a few. People who learn many layouts at
once make more small slips at first, and the slips fall away with more practice. That holds only if the skill is
under-practised and not crowded out. This test tells those two apart.

## One change from gr-6: 3 more epochs, continuing from gr-6's adapter
- **The starting point.** gr-6's adapter (sha256 54feb2fd..., kept off git in
  /mnt/project-files/plain-english-puzzles/gr6_adapter.pt) is loaded into the same 1B.
- **The recipe.** It trains for 3 more epochs on gr-6's exact training rows (artifacts/claude-gr6-20260927/train/
  rows.jsonl, split "train", 1072 rows). The rest is gr-5's recipe, unchanged:
  - AdamW, batch 8, loss on the answer only, rank 16
  - learning rate a constant 2e-4, the same as epochs 1 to 3. gr-5 and gr-6 used no warmup and no schedule, so none
    restarts: this is a continuation of that constant rate.
- **What is new.** Two things, and both are written here:
  - AdamW's moment estimates start fresh, because gr-6 did not save them.
  - The shuffle and dropout seed is 5070, not 4990, so the order differs from epochs 1 to 3.
- **What "6 in total" means.** 6 passes over the rows at the same constant rate.
- **What is unchanged.** The prompt, grammar, greedy decode, rows, dev split and panel are all gr-6's.

## Disclosure (review point 4)
The 123 held-out dev squares have now been copied row by row twice, by gr-6's dev step and by the post-hoc breakdown,
and the owner has read their per-row results (source, layout, size, exact, wrong or none; never the message text). The
stop rule still stands, but a dev pass is weaker evidence than before. The unread gr-6 panel is the real test.

## Dev and loss (fixed now, in this order)
The training log prints the mean loss for epochs 4, 5 and 6. Dev reads the 30 format-dev messages, the 123 held-out
squares (split into gr-5's 72 and the 51 in new layouts), the 139 held-out no-square rows, and the 64 squares in
dev-only layouts. That is one pass, and the chain script prints every count.
1. **PROVED WRONG (the under-training reading).** gr-5's 72 held-out squares are 66 or fewer exact after epoch 6. The
   loss then says which reading holds:
   - Epoch-6 loss at or below 0.001: more training fit the rows but the slips stayed, which reads as interference
     or capacity.
   - Epoch-6 loss above 0.001: the optimiser is still slow, and the cause stays open.
2. **INCONCLUSIVE (review point 3).** The 72 give 67 or 68, or the dev reads 105 to 110 of the 123. No panel is spent,
   and no gr-8 is chosen from this result.
3. **DEV-FAIL.** Any held-out no-square row is read as a square, or the dev reads 104 or fewer of the 123 while the 72
   give 69 or more. The old layouts would then have recovered but the new ones not.
4. **DEV PASS.** The 72 give 69 or more, the dev reads at least 111 of the 123, and no held-out no-square row is read as
   a square. Only then is the gr-6 panel spent.

## Predictions (fixed now)
- Epoch-6 mean loss is at or below 0.001.
- gr-5's 72 held-out squares give at least 69 exact. The dev reads at least 111 of 123, so the result is DEV PASS.

## If the dev passes: the registered test
The still-unread gr-6 panel (artifacts/claude-panel-gr6-20260927, sealed in eea8d6e10) is spent once under gr-6's
sealed marks, with L7 (this adapter) in L6's place. Everything else in PASSMARKS-gr6 is unchanged:
- the arms: L7, G5 (gr-5's adapter, same prompt and grammar) and C (read_latin)
- the bars R1 to R4, U1 and U2
- the report-only lines: the 8 lookalikes that hold a square, and U1 split by whether the cell separator was seen in
  training (51 and 9 squares)
- the one proved-wrong result for the recipe: L7's U1 is not above G5's on the same panel
- the readings fixed in advance

A FAIL stays a FAIL.

## Where it runs
- **Compute.** This container's CPU, $0, under ADDENDUM-gr5-3's rules: a cap of 6 hours from the first STEP line,
  then PARTIAL. A reclaim means a restart from the start under the same seals, noted in RUN-NOTE.
- **Estimated time.** About 2 hours of training, 25 minutes of dev and 45 minutes of runs.
- **What stays off git.** The adapter.
