# VERIFY gr-6: DEV-FAIL under the sealed stop rule; the blind panel was not spent (2026-09-27 04:20 UTC)

Owner: Plain-English puzzles thread. Times from `date -u`. Marks: PASSMARKS-gr6.md (dc32468b2). Seals, in the order
the marks fix: layouts and code (0f7679ead), the blind writer's file (6ba05adae), panel, rows and chain (eea8d6e10).

## What ran
- The chain ran once on this container's CPU at $0 (run/RUN-NOTE.md, run/logs/):
  - it started at 01:30:06Z
  - training took 111.8 minutes (1072 rows x 3 epochs; mean loss by epoch 0.1586, 0.0124, 0.0062)
  - the dev step started at 03:22:09Z
  - the chain stopped at 03:57:57Z (STEP stop)
- No registered task ran. artifacts/claude-panel-gr6-20260927 was made and sealed but never read by a model or by
  the owner, so it is still a fresh blind panel.
- The dev numbers come from run/logs/dev.log. The breakdown below, run again after the stop, reproduces them exactly.
  The copy is greedy, so the same adapter gives the same output.

## Dev (the stop rule is on the first row)
| Dev row | Result | Rule |
|---|---|---|
| Held-out squares in training layouts, read exactly | 103 of 123 (14 wrong grids, 6 none) | at least 111: **FAIL** |
| Held-out no-square rows read as a square | 0 of 139 | 0: pass |
| Squares in the 8 dev-only layouts, read exactly (report only) | 51 of 64 (11 wrong, 2 none) | none |
| Format-dev messages (report only) | 30 of 30 | none |
| Dev split by wrapper (report only) | new wrappers 85 of 103, shared 18 of 20 | none |

**gr-6 is a DEV-FAIL.** The marks leave no gr-6 verdict on R1 to R4 or U1 and U2. The proved-wrong comparison (L6
against G5 on U1) was not run. read_latin stays in 358b3's path.

## Where the misses are (post hoc, practice rows only, report only)
Made by scripts/claude_gr6_devdiag.py (diag/devdiag_rows.jsonl, diag/devdiag_counts.txt). It was written after the
dev FAIL, so everything here is a suggested reading, not a registered result.

- **gr-5's own 72 held-out squares, the same rows gr-5's dev read: 63 exact with gr-6's adapter.** gr-5's adapter read
  71 of these 72. Of the 9 misses, 8 are wrong grids and 1 is none. 7 of the 8 wrong grids are the right size with
  cells miscopied, and 6 are at sizes 6 and 7.
- **The 51 held-out squares in the 32 new training layouts: 40 exact.** 6 were wrong and 5 were none. With rows on
  their own lines: 23 of 30. With rows on one line: 17 of 21. With a header line: 13 of 19.
- **The 64 squares in the 8 dev-only layouts: 51 exact.** Of the 11 wrong grids, 10 are the right size. Rows on one
  line: 40 of 48. Rows on their own lines: 11 of 16.

## What this suggests (not tested)
- **Shown on practice rows.** On the same 72 rows, gr-6's adapter reads 8 fewer old-layout squares than gr-5's did (63
  against 71). The added data made the reader worse at the layouts it already knew, and nearly every new miss is a
  cell slip inside a grid of the right size.
- **Suggested.** The training loss at epoch 3 was 0.0062, against gr-5's 0.0003, and it was still falling. So the same
  3-epoch budget spread over 1.45 times as many, more varied rows may leave the copy under-trained. This is the plain
  reading. It is not tested: interference between layouts at rank 16 would look the same, and the recipe was sealed as
  one, so the near misses cannot be told apart from the new layouts.
- **Suggested.** The dev-only layouts reached 51 of 64 (80%), close to the held-out new layouts (40 of 51). So
  practice on the 32 layouts carried over to 8 layouts it never saw about as well as to the 32 themselves.

## Next
Nothing is sealed. The Thread manager gets a plan before anything runs. The gr-6 panel is still unspent and blind, so
it can serve the next reader's test.
