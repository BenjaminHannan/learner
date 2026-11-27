# T1SDR opswap (confirm mark 5) miss breakdown, seeds 200 and 201

Read only, CPU fp32, the T1SDR_s200/s201 checkpoints (queue 70), the big dev build's chain-5 rows; `python3 -m custom_io.diag_swap_misses`
(custom_io/diag_swap_misses.py), full lists in SWAP-MISSES-T1SDR.json. The text-match reading reproduces the runs' own opswap figures exactly.

| seed | affected | text-match reading (as extra_evals) | own-pointer reading (as B2's opswap) |
|---|---|---|---|
| 200 | 829 | 97.47 (21 miss) | 99.88 (1 miss) |
| 201 | 829 | 97.23 (23 miss) | 99.28 (6 miss) |

- Every text-match miss is an operand, never the program or the answer: a later call's operand that the scorer expects to be an earlier
  (swapped) result is written as something else (21/21, 23/23). Families: state_update 12/13, chain_ops 5/5, var_chain 4/5.
- In 20 of 21 (s200) and 18 of 23 (s201) the written operand is a number from the question that equals that earlier call's intact result.
  The model copied the question's number; with the calculator intact the two strings are the same, so the text-match scorer
  (`Tool.sources`: "the latest earlier result with that text wins") credits the earlier result and expects the swapped value.
- Negative values are not the link: 6 of 21 / 5 of 23 misses have a negative value in the swapped replay, the rest none.
- Why the model copies the question's number: the teacher program (`progparse.row_targets`) attributes a value that equals a question number
  to the question's slot. In training, 33,633 of 138,106 call results (24%) equal a question number, and 0 of 42,818 result-sourced operands
  have a question number's text: whenever they coincide, the target source is the question. B2 learns the same targets; its opswap replays
  B2's own pointers, so it is not counted against B2 (99.88 every seed).
- Own-pointer reading: each span-copied operand's source is the string the span pointer copied from (a question number, or entry k),
  cells-path operands keep the text match; then the same replay and swapped run. This is B2's definition applied to T1SDR.
