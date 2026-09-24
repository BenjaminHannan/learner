# 350: a 3x bigger reasoner (size only)

Sleep research thread, 2026-09-24. Ben (19:17-19:19 UTC): the small reasoner "should become much
bigger", "the reason it fails basic logic is because it is 100000 times stupid than a human", then
"can you do that btw then, the 3 times bigger model?". Ben also OK'd (19:25 UTC, reply to the
coordinator) a 10x model at about $10-20 a run "if it would help"; see the 10x rule below.

## The one change

rsn-296 exactly (varied "sleep school" generator, copy 6,000 + practice 6,000 steps, batches, learning
rate, group-relative reward with 8 tries, fact-check, seeds 1 and 2, eval code), with the plain arm about
3x bigger:
- 296 plain: d=640, 6 layers, 10 heads = 30,938,261 numbers;
- 350 plain: d=1024, 7 layers, 16 heads = 91,588,629 numbers (2.96x).
Runner: scripts/claude_rsn350_run.py (imports 296's runner and adds size "90m"; nothing else changes).

**Twin:** 296's plain seeds 1 and 2, as recounted from files (VERIFY-recount.md; reeval-cpu JSONs on
builder-outbox). Same runner, generator, scorer and panels, so no twin re-run is needed.

**Why only the plain arm:** 296's loop arm never learned to copy (copy loss 1.85 and 1.97, 294's D2
reproduced). Making a broken arm bigger would spend money to reproduce the bug. The loop gets its own
fix (with the thinking stop token Ben asked for) as a separate experiment.

## Panels (TEST-ONLY, category counts only)

- reasonpanel296 v2 (298 items; fresh when 296 ran). Registered panel.
- reasonpanel294 v3 (300 items). Transfer check.
Both panels have been scored before at category level (296 and its recount); no item was ever read by
this design and nothing here was tuned on them. Re-using them keeps the comparison with 296 exact.
Limit: neither panel has chains longer than 3 steps.

296 plain, final checkpoints (checked right):

| category | s1 fresh | s2 fresh |
|---|---|---|
| one/two-step, backwards, yes/no, missing | 150/150 | 150/150 |
| newest correction | 23/28 | 19/28 |
| before/after | 24/30 | 20/30 |
| comparing | 16/30 | 16/30 |
| counting | 12/30 | 12/30 |
| three-step (never practised) | 0/30 | 0/30 |
| **total** | **225/298** | **217/298** |
| transfer (panel294) total | 238/300 | 238/300 |

## Cost

296's plain runs took 38 and 37 min on a 5090 (sharing the box with the loop runs). At ~3x compute the
two 350 runs, 2 at a time, are estimated at ~2-4 h wall, ~$1-2 at ~$0.47/h. Pilot gate and $4 combined
cap as in 296.

## 10x rule (fixed now, before the 3x result)

Go to 10x (~300M, about $10-20 a run, Ben's OK 19:25 UTC) only if Z1 passes on BOTH seeds. Before
launching, check the running rental total with the director; ask Ben before the $30 total cap is passed.

Pass marks: artifacts/claude-rsn350-20260924/PASSMARKS.md.
