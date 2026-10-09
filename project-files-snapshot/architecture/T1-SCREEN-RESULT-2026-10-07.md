# T1 screen result (calculator outside the model), 2026-10-07 about 5:10 PM ET

Written by the custom reader/talker thread. Judge: `python -m custom_io.analyze_t1 --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-vast-t1`
(commit c155aa1e0, files custom_io/results/RESULTS-T1.md and T1-ANALYSIS.json). T1 ran on two rented RTX 5090s from the queue 40 recipe at
code 2b1cbd4d7 (the PC chain's commit), seeds 200 and 201. q33's B2 ran on BensPC. Same data file (train sha256 010af671...).

## Verdict: NOT SHOWN at the screen (no 6-seed run; per spec section 8b, H1 waits)

| mark | seed 200 | seed 201 | result |
|---|---|---|---|
| S1 pooled-5 T1 - B2 >= -2.0 | +1.72 | -0.31 | pass |
| S2 chain-5 >= 95 | 99.7 | 99.9 | pass |
| S3 write_copy exact copy >= 99 (operand / answer) | 29.3 / 42.1 | 30.9 / 42.4 | FAIL |

Also measured (not screen marks): tool off (noexec program set) 0.29 / 0.53; opswap swap_match 95.9 / 96.5; call accuracy free run
98.3 / 98.6; loops:0 in_dist 9.41 / 5.00 (B2 0.00 / 10.81); donor in_dist 4.85 / 4.78.

## Where S3 breaks (shown): copying works for the number lengths seen in training, and fails beyond them

write_copy replaces every calculator result with a random 1-9 digit string and checks that the model copies it exactly into the next call
(operand) or the answer. Exact copy by length of the string (seed 200; seed 201 is the same within a few points):

| digits | 1 | 2 | 3 | 4 | 5 | 6-9 |
|---|---|---|---|---|---|---|
| operand copy | 86% | 93% | 85% | 14% | 1% | 0% |
| answer copy | 96% | 98% | 98% | 59% | 1% | 0% |

Lengths of the numbers T1 is trained to write (40,000-row train sample, 13,874 program rows): call results 1 digit 16.6%, 2 digits 61.8%,
3 digits 20.6%, 4 digits 0.8%, 5 digits 0.2%, never 6 or more. Operands: 1-3 digits 99.6%. So the miss lines up with the training lengths.

## Reading (suggested, not tested)

The outside calculator itself is fine (tool off drops to ~0, so the model really uses it, and in-distribution parity holds). The link that
breaks is the call writer's copy: each operand cell j copies by its place-from-the-right row j, and rows 4 and up were almost never trained,
so a cell for place 4+ does not find the matching character. Inside B2 this never showed, because B2's executor held exact values of any
length and its NUM mode printed them with str(). Per Ben's rule (fix the link, never move it back in), the next step is one change to the
writer's copy link, with the screen re-run.

Candidate single changes (for the architecture thread to pick and seal):
1. Span copy: the writer points at a whole number in the context (a prompt number or an entry's result, like the WORD pointer) and its
   characters are copied as a block; per-cell writing stays for numbers it composes itself. Length-general by construction.
2. Relative-place copy: each cell attends by its offset from the chosen number's last digit, so place rows are not needed past the length.
3. Longer numbers in training (a data change: only Ben approves).
Untested which one fixes it. A cheap check that separates "place rows untrained" from "copy attention is length-bound": fine-tune the
T1 checkpoints briefly on rows whose results are 4-9 digits and re-run write_copy (diagnostic only, not a candidate).

Checkpoints: /mnt/project-files/checkpoints/cio-1007/40b-t1-s20{0,1}/T1_s20{0,1}/checkpoint.pt (being copied off the boxes).
