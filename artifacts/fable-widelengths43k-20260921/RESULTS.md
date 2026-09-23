# Experiment 43K — results (registered wave, 6 seeds, 2026-09-21). Base ~80 s/seed.

| Seed | K1 fit 4–12 | K2 worst skill at 16 / 20 / 24 / 32 | length 64 (recorded) | K3 flip counter | K4 sleep N=20 |
|---|---|---|---|---|---|
| 4102 | PASS 1.00 | PASS 1.00 / 1.00 / 1.00 / 1.00 | 1.00 | yes | PASS 1.00, long 1.00/1.00 |
| 4103 | PASS 1.00 | PASS 1.00 ×4 | 1.00 | yes | PASS |
| 4104 | PASS 1.00 | PASS 1.00 ×4 | 1.00 | yes | PASS |
| 4111 | FAIL (SWAP 0.10) | FAIL (SWAP 0.00 ×4; other five skills 1.00) | SWAP 0.00 | NO | PASS |
| 4112 | PASS 1.00 | PASS 1.00 ×4 | 1.00 | yes | PASS |
| 4113 | PASS 1.00 | PASS 1.00 ×4 | 1.00 | yes | PASS |

Marks: K1 FAIL (5/6), K2 FAIL (5/6), K3 FAIL (5/6), K4 PASS (6/6).

Diagnosis of seed 4111 (measurement only): the model start is the same as in 43J; none of its 8 counters started on
the "flip" side by more than -0.08 (seed 4102 had four, down to -0.87). Every counter slid to "stay"-type rules, so
SWAP had no odd/even signal. It is a start-up lottery, not a length problem.

What it means: where a flip counter forms, wider practice (4–12) fixes 43J's SWAP misread completely — 5/6 seeds are
perfect on all six skills out to 64 digits with no parity facts given (soft reads; 43I blurred at 64 only for ROTL1's
wrap-around place, which here did not drop below argmax). What it does not mean: not dependable — 1 seed in 6 never
finds odd/even. Toy only; clues, output length and counter size are still hand-chosen.
Licensed follow-up (one change): balanced counter start (half lean "flip", half lean "stay"), fresh seeds added.

## 43K-v2 (balanced counter start) — registered wave, 9 seeds

All nine seeds (4102, 4103, 4104, 4111, 4112, 4113 and fresh 4121, 4122, 4123): every skill 1.00 at every length
4–12, and 1.00 at 16, 20, 24, 32 and 64; flip counters present (forward counters 0 and 1); CARDFOLD from 20 episodes
installed, fresh 1.00, long 1.00/1.00, reload identical, routing ROTL1 -> FOLD -> INC3.
Marks: K1 PASS 9/9, K2 PASS 9/9, K3 PASS 9/9, K4 PASS 9/9. Confirmed on the three fresh seeds.

What it means: the skill bank no longer needs to be TOLD which places are odd. Given a small bank of counters that
includes "change every step" and "stay" types, it learns by itself which skills should use which counter, and the
result holds to 64 digits in 9/9 seeds.
What it does not mean: with the balanced start the flip counters BEGIN about 98% flip, so v2 shows the model keeping
and using an offered odd/even signal, not inventing one. Discovery from a purely random start is the 43J/43K-v1
number: 5 of 6 seeds. Still hand-chosen: four distance clues, output length, 2-state counters, practice lengths 4–12.
Toy only.
