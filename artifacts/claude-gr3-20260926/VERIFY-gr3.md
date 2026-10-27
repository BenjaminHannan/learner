# VERIFY gr-3: registered FAIL (R1, R2, R3); gr-3U FAIL (U1, U2) (2026-09-26 20:20 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. Marks: PASSMARKS-gr3.md (203d3f04b) and
ADDENDUM-gr3-1.md (044e9adfe). Code, the glance head and the 1B table drafts were sealed in ab6b72d94 before the run.
Each task was launched once on this container's CPU at $0 (run/, logs/run.log, score/gr3_score.json; ee2d35577). A
separate blind agent recounted everything from the run files and the panel with its own code, without importing
claude_gr3.py, and printed integers only. The recount agrees on every count, every arm, the size breakdown and every mark, and the
run files' ids match the panel's exactly.

## Result (L = gr-3: the glance, then gr-2's search at the size it names)
| Row | Test | Bar | L | Pass |
|---|---|---|---|---|
| R1 | squares read exactly | >= 97 of 100 | 92 | no |
| R2 | lookalikes read as a square where the truth is none (56) | <= 1 | 2 | no |
| R3 | squares read as a different grid | <= 1 | 6 | no |
| R4 | general items read as a square | 0 of 300 | 0 | yes |
| U1 | unseen-format squares read exactly | >= 48 of 60 | 30 | no |
| U2 | unseen-format squares read as a different grid | <= 2 | 17 | no |

**gr-3 registered FAIL. gr-3U registered FAIL.** The code stand-in read_latin stays in 358b3's path.

## Report only (every arm on this fresh panel)
| Arm | Squares exact / wrong / none | Unseen exact / wrong / none | False lookalikes | General |
|---|---|---|---|---|
| L (gr-3) | 92 / 6 / 2 | 30 / 17 / 13 | 2 | 0 |
| G2 (gr-2's search over every size) | 99 / 1 / 0 | 47 / 10 / 3 | 4 | 0 |
| P (gr-1's per-token reading) | 84 / 0 / 16 | 16 / 0 / 44 | 0 | 0 |
| C (read_latin, code) | 100 / 0 / 0 | 6 / 0 / 54 | no comparison | 0 |

- C is no comparison on R1 and R2 (ADDENDUM-gr3-1): the truth of each lookalike is what read_latin reads, and the maker
  checks that read_latin reads every inserted square. 4 of the 60 lookalikes hold a square by that definition.
- The glance named the right size for 93 of 100 squares and 33 of 60 unseen-format squares, and said none for 50 of
  the 56 lookalikes whose truth is none.
- L's exact reads by size: 18 of 25 at size 4, 25, 24 and 25 at sizes 5 to 7. In unseen formats: 3 of 15 at size 4,
  13, 6 and 8 at sizes 5 to 7.
- 3 unseen messages have two cells in one token, which no token-level reader can read.
- Median time per general item: 1353 ms.

## What this shows
- Shown: the learned glance made gr-2 worse, not better, on squares. It fixed half of gr-2's false squares (2 vs 4 on
  this panel), but it named a wrong size for 7 of 100 squares, and L missed 8 squares: 6 read as a wrong grid and 2 as
  none. 5 of the 6 wrong grids were read at a smaller size and 1 at the right size. The cross-validation warning in
  DEV-REPORT-gr3 (a wrong size for 40 of 360 practice squares) came true.
- Shown: on this fresh panel gr-2's search alone reached R1 (99) and R3 (1) but failed R2 (4 false squares), as it
  did on its own panel (3).
- Suggested, not tested: choosing the size, learned or searched, is where these token-tag readers break. Here 5 of
  L's 6 wrong grids came out smaller, and on gr-2's panel every wrong read was a smaller size (NOTE 4fba03a3c).
- Suggested, not tested: size 4 is the weak spot (18 of 25). A mean over the message's hidden states may not separate
  a 4 x 4 block from a 3 x 3 or 5 x 5 one well, because the square is a small part of the message.
- The ruled-out reading: "a whole-message glance is enough to say the size" (proved wrong by R1 and R3).

## Next
gr-5 (registered 3634a4195, addendum dcb37487e, queued on BensPC as 250-gr5-benspc) is the plain, well-known fix
that Ben's 19:20 rule asks for. The reader 1B is fine-tuned to copy the square or say none, and it is tested on a
fresh blind panel against the same bars. No further token-tag variant is planned before gr-5's result.
