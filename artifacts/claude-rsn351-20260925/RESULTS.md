# rsn-351 results (builder run 2026-09-25, lr 1e-4, size 90m = 91,588,629 numbers)

## Verdict: FAIL

PASS needed Y1 and Y4 on both seeds. Y4 passes everywhere, but **Y1 fails on both
seeds** (fresh panel296 v2 final, checked right: s1 221/298 vs bar 235, s2 218/298
vs bar 227). The slower learning rate did not make the 3x model beat the 30M model.

## Marks (integer counts, checked right unless noted)

| mark | bar (each seed) | s1 | s2 | result |
|---|---|---|---|---|
| Y1 fresh 296 v2 total vs 30M (296: 225, 217) | s1 >= 235, s2 >= 227 | 221 (-14) | 218 (-9) | FAIL both |
| Y2 fresh 296 v2 total vs rsn-350 (350: 211, 209) | s1 >= 221, s2 >= 219 | 221 (+10, exactly at bar) | 218 (+9, 1 short) | PASS s1, FAIL s2 |
| Y3 fresh three-step, never practised | >= 6/30 one seed | 0/30 (296) and 0/15 (294) | 0/30 and 0/15 | FAIL both |
| Y4 invented answers (checked), each panel | <= 2 | 296: 0, 294: 0 | 296: 0, 294: 0 | PASS all 4 cells |

"Proved wrong" clause (Y2 fails on BOTH seeds, within +9 of 350) did NOT trigger:
s1 is exactly +10 over 350 (bar met), s2 is +9 (1 short). So the fast-learning-rate
story is neither confirmed nor cleanly refuted: the slower rate gained +10/+9 over
350 but still sits -4/+1 vs the 30M model.

## Runs

| run | seed | minutes | copy loss first -> last | practice reward first -> last |
|---|---|---|---|---|
| W/plain90-s1 | 1 | 34.6 | 4.0901 -> 0.0064 | 0.6729 -> 0.8422 |
| W/plain90-s2 | 2 | 35.4 | 4.2522 -> 0.0013 | 0.6057 -> 0.8797 |

Both runs 2-at-a-time on one RTX 5090, --workers 8, defaults otherwise.
Practice reward means per 1,000 steps: s1 0.7993, 0.8485, 0.8592, 0.8863, 0.8950,
0.8948; s2 0.7970, 0.8574, 0.8541, 0.8296, 0.8721, 0.8927. Plateau ~0.89
(350's 90M plateaued ~0.83; 30M ended 0.93/0.98).

## Fresh panel296 v2 (298 items), checked-right per category

| category (n) | s1 copy | s1 final | s2 copy | s2 final |
|---|---|---|---|---|
| backwards (30) | 30 | 30 | 30 | 30 |
| before_after (30) | 12 | 22 | 11 | 20 |
| comparing (30) | 0 | 16 | 0 | 16 |
| counting (30) | 0 | 12 | 0 | 11 |
| heldout_three_step (30) | 0 | 0 | 0 | 0 |
| missing_fact (30) | 30 | 30 | 30 | 30 |
| newest_correction (28) | 21 | 21 | 21 | 21 |
| one_step (30) | 30 | 30 | 30 | 30 |
| two_step (30) | 30 | 30 | 30 | 30 |
| yes_no (30) | 30 | 30 | 30 | 30 |
| TOTAL | 183 | 221 | 182 | 218 |

Copy -> final gains: s1 +38, s2 +36 (350 90M: +36/+29; 30M: +58/+36).
Counting learned in practice: s1 0 -> 12/30, s2 0 -> 11/30 (350 90M: 4/30; 30M: 12/30).

## Transfer panel294 v3 (300 items), checked-right per category

| category (n) | s1 copy | s1 final | s2 copy | s2 final |
|---|---|---|---|---|
| backwards (30) | 30 | 30 | 30 | 30 |
| before_after (30) | 11 | 18 | 9 | 18 |
| comparing (30) | 0 | 12 | 0 | 12 |
| counting (30) | 0 | 9 | 0 | 12 |
| heldout_big_notebook (15) | 15 | 15 | 15 | 15 |
| heldout_three_step (15) | 0 | 0 | 0 | 0 |
| missing_fact (30) | 30 | 30 | 30 | 30 |
| newest_correction (30) | 30 | 30 | 30 | 30 |
| one_step (30) | 30 | 30 | 30 | 30 |
| two_step (30) | 30 | 30 | 30 | 30 |
| yes_no (30) | 30 | 30 | 30 | 30 |
| TOTAL | 206 | 234 | 204 | 237 |

(296 transfer: 238/238. 351: 234/237.)

## Raw vs checked totals (every eval, each run once)

| eval | n | raw_right | checked_right | raw_wrong | checked_wrong | raw_idk | checked_idk | raw_invented | checked_invented |
|---|---|---|---|---|---|---|---|---|---|
| s1 296 copy | 298 | 180 | 183 | 110 | 17 | 3 | 98 | 5 | 0 |
| s1 296 final | 298 | 217 | 221 | 74 | 41 | 2 | 36 | 5 | 0 |
| s1 294 copy | 300 | 206 | 206 | 94 | 15 | 0 | 79 | 0 | 0 |
| s1 294 final | 300 | 234 | 234 | 66 | 51 | 0 | 15 | 0 | 0 |
| s2 296 copy | 298 | 179 | 182 | 113 | 20 | 1 | 96 | 5 | 0 |
| s2 296 final | 298 | 213 | 218 | 75 | 45 | 5 | 35 | 5 | 0 |
| s2 294 copy | 300 | 204 | 204 | 96 | 19 | 0 | 77 | 0 | 0 |
| s2 294 final | 300 | 237 | 237 | 63 | 48 | 0 | 15 | 0 | 0 |

checked_invented = checked non-"I don't know" answer where gold is UNKNOWN
(missing_fact category: 30/30 checked right in all 8 evals). Raw invented 5 on
296 panels are all fact-checked to "I don't know" (checked 0).

## Dev check (fresh generated episodes, seed 777, n=1200)

copy: s1 799/1200 (raw and checked), s2 749 raw / 746 checked.
final: s1 937/1200, s2 928 raw / 927 checked.

## Pilots and cost

Single pilot (100 copy + 50 RL steps): 30.6 s wall, min 0.38 (copy ~0.19, RL ~0.19).
Double pilot (seeds 8+9 at once): 35.4 s wall, min 0.47 each. Full-run estimate
2-at-a-time ~42 min wall vs ~68 min one-after-other: ran 2-at-a-time. Actual wall
~35 min. No OOM. Estimate and actual both far under 300 min / $3.40.

GPU money (combined, re-rents included): rental 1 (host docker-proxy failure,
~7 min, never ran) ~$0.06; rental 2 (stuck loading 6+ min) ~$0.07; rental 3
(RTX 5090, 32 vCPU, $0.5511/h, ~62 min creation to destroy) ~$0.57.
Total ~$0.70. Under the $4 cap and the $3.80 stop line.

## Checkpoints (kept, never pushed)

~/premonition-models/rsn351/plain90-s1/copy_only.pt b811b00b38711e3e79006471100dc8c545fa987690e281a35f385f9e60324f8b
~/premonition-models/rsn351/plain90-s1/final.pt 2e5d8765ee453737086505f8cde33f22ca4c7112017444f62945e30b95db3fd8
~/premonition-models/rsn351/plain90-s2/copy_only.pt ea8fba4f8e4bb38f0672f7ddf7df3d79fabb544dc3cd47bedd5eb7677c65494f
~/premonition-models/rsn351/plain90-s2/final.pt 456bac463f77ea81a8f5e5ae28244fcb8a71f241ef84f51ff42ce52e38b113ae
(sha256 identical to artifacts/claude-rsn351-20260925/SEAL-run.sha256.txt.)

## Deviations and misses

1. scratchpad OPUS-RULES.txt path from the brief does not exist (no
   scratchpad/briefs/ dir); followed the rules as stated in the task text.
2. SEAL-run.sha256.txt hashes were computed from the checkpoints BEFORE eval ran,
   but written to the file after eval in wall-clock order. Eval only reads
   checkpoints (sealed runner), bytes unchanged: hashes match the Mac copies.
3. Two dead rentals before the good one (docker-registry proxy failure; image
   stuck loading past 6 min). Both destroyed, counted above. Rentals 1 and 2
   coexisted ~1 min during handover (destroy confirmation lag); no job ever ran
   on more than one instance.
4. Container CPU quota shows nproc=1 (256 processors visible); --workers 8 used
   as registered anyway; timing/throughput as reported.
5. No misses: all 12 eval commands ran exactly once per checkpoint, outputs
   present; seals all-OK; selftest ok.

## What this means / doesn't mean (plain words)

The bigger model trained with a slower learning rate learned counting much better
than the fast-rate big model (12 and 11 out of 30 vs 4), and caught up exactly to
the pass line on one seed. But it still did not beat the smaller 30M model, so
"the learning rate was the whole problem" is not proven: one seed hit the line
exactly, the other missed by one. Something else about size still needs explaining.
Three-step questions nobody ever practised stayed at 0 in all runs, and the model
never made up answers when the fact was missing (0 checked invented answers).
