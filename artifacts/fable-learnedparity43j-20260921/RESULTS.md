# Experiment 43J — results (registered wave, 6 seeds, 2026-09-21)

Seal verified before the wave. Base ~45 s per seed, sleep ~15 s.

| Seed | J1 fit 4–8 | J2 length 12 & 16 | J3 flip counter found | J4 CARDFOLD sleep N=20 |
|---|---|---|---|---|
| 4102 | PASS 1.00 | FAIL — SWAP 0.11 at 12 (also 0.13 at 9); 16 ok | yes (counters 3, 4) | PASS fresh 1.00, long 1.00/1.00 |
| 4103 | PASS 1.00 | FAIL — SWAP 0.11 at 12 (0.06 at 9); 16 ok | yes (0) | PASS 1.00, 1.00/1.00 |
| 4104 | PASS 1.00 | FAIL — SWAP 0.11 at 12 (0.08 at 9); 16 ok | yes (2) | PASS 1.00, 1.00/1.00 |
| 4111 | FAIL — SWAP min 0.10 | FAIL — SWAP 0.00 at 12 and 16 | NO | PASS 1.00, 1.00/1.00 |
| 4112 | PASS 1.00 | FAIL — SWAP 0.06 at 12, 0.00 at 16 | yes (0) | PASS 1.00, 1.00/1.00 |
| 4113 | PASS 1.00 | FAIL — SWAP 0.13 at 12, 0.10 at 16 | yes (0) | PASS 1.00, 1.00/1.00 |

Marks: J1 FAIL (5/6), J2 FAIL (0/6), J3 FAIL (5/6), J4 PASS (6/6).
Every other skill (REV, ROTL1, INC3, FOLD, REV+INC1) scored >= 0.90 at lengths 9, 10, 12 and 16 in all 6 seeds.

What it means: odd/even was discovered by gradient, with no one telling the model, in 5 of 6 seeds, and FOLD (which
needs odd/even) then worked at every tested length. CARDFOLD sleep still installs from 20 episodes in 6/6.
What it does not mean: the skill bank is NOT length-proof without the given parity facts. SWAP misreads one place at
unseen lengths in every seed: its additive clue scores are pinned down only for lengths 4–8 (on seed 9999 the wrong
read was the place with clue d4 = +3 and d1 <= -4, a combination whose suppression in training relied on other clue
values that change at new lengths). Weight decay, a sparsity pull and clue hiding did not fix it (seed 9999 only).
Per the sealed reading rule the next step is a DATA change (wider training lengths), not more regularisers.
Hard-read variant at 12/16: not run (the misread is an argmax error, so hardening cannot fix it).
