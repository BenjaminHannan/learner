# RESULT gr-9, addendum 1: the L7c control (report only)

- **The control.** L7c is gr-7's reader trained 3 more epochs on gr-6's 1072 rows only, with the same recipe and seed.
  Its mean loss by epoch was 0.0048, 0.0008 and 0.0014.
- **Held-out squares, greedy read.** L7c read 44 of 100 exactly, the same as gr-7's reader (L7, 44). The new reader
  (L9) read 94.
- **What it shows.** L9 minus L7c is 50. On these practice items, the extra epochs alone gave no gain, so the whole
  gain comes from the separator rows.
- **The count of record.** run-r1/logs/count.log gives the same marks and the same DEV-FAIL as count-main.log. The
  owner checked the L7c exact count with a separate short script, and it matches.
- **Predictions.** L7c within 5 of L7: yes (0). L9 minus L7c at least 20: yes (50).
- **Not run.** The post hoc reads of squares and seen with L7 and L7c (posthoc/chain-rows.sh) were stopped before
  they started, when Ben stopped all threads.

Written 2026-09-27T21:09:43Z (date -u).
