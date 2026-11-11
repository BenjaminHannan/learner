# D0b: where the text baseline with its calculator loses chain-5 (report only)

No-hard-coding plan, section 3.0. `custom_io/diag_c1_links.py` re-generated the 1,000 chain-5 rows with the calculator on (C1') for
plain_tf_steps seeds 100 and 101 (CPU, fp32). It reproduces the saved scores exactly: 96.3 and 96.5. Each wrong row is labelled by its
first wrong link against the gold steps; all 72 wrong rows (pooled) were also read by eye. Rows and labels: `D0b_c1_links.json`.

| label | link | s100 | s101 | pooled |
|---|---|---|---|---|
| h | trained answer-only (steps + answer over 64 chars) | 30 | 28 | **58** |
| j | wrong name (story_chain3) | 2 | 3 | 5 |
| i | own arithmetic on a step the calculator never fires on | 0 | 1 | 1 |
| f | step format the calculator did not fire on | 3 | 2 | 5 |
| c | wrong operation | 1 | 1 | 2 |
| b | wrong number chosen | 1 | 0 | 1 |
| a, d, e | an operand, a tool result or the answer copied wrong | 0 | 0 | **0** |

- **(h) is 58 of 72 (81%).** All are var_chain rows with 4 or 5 steps, whose training target is the answer alone because steps plus answer
  pass the 64-char cap (`plain_tf_steps.py:15, 21-27`). 56 of the 58 wrote only a number, so the calculator never ran.
- **Call, as sealed (h, i, j left out; 8 rows remain):** copying (a+d+e) 0, choosing (b+c) 3, neither reaches half, so **mixed**. The other
  5 rows are (f): 4 wrote the answer alone on 4-step chains just under the cap (the same habit as h), 1 wrote 'b = 7 * 4 # 28' with no '='.
- **Copying never failed:** 0 of the 72 wrong rows (0 of 2,000 rows) copied an operand, a calculator result or the final answer wrongly.
- The (b) row wrote '17 - 1' for '17 - 11': 1 is a prompt number, so it is (b) by the definition, but it is also one dropped digit from the
  gold operand. The two (c) rows: '7 + 7' for '7 * 7', and '129 + 32' where step '129 - 9' was skipped.
- The (j) rows have every number right ('compare 90 90') and the wrong word ('Wren' for 'same', a name for 'friend').

What it suggests for T1 (suggested, untested): the text baseline's gap to B2's 99.4-99.8 is mostly its own training cap, not copying digits
or choosing numbers. Without (h) it would miss 14 of 2,000 rows (99.3). T1 writes every step of every chain (no 64-char cap; up to 7 calls),
so this gap should not carry over; the risk left is the small choosing set (wrong operation, skipped step, wrong number) and, for
story_chain3, the final word.
