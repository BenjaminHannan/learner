# Experiment 43K — pass marks (fixed before any registered run)

One change from 43J's registered arm: base training lengths 4–8 -> 4–12 (even mix; same batch, updates, model, C=4, K=2).
Lengths 9–12 are now practised, so the length test moves to 16, 20, 24, 32, 64. Sleep = 43H unchanged (N=20, lengths 4–8).
Seeds 4102/4103/4104 and 4111/4112/4113, one wave. Still given by hand: four distance clues, output length, counter size.
Disclosed: one full run on throwaway seed 9999 before sealing scored 1.00 at every length up to 64.

- K1 fit: every old skill >= 0.99 exact match at each length 4–12 tested (4,5,6,7,8,9,10,12), all 6 seeds.
- K2 length: every old skill >= 0.90 exact match at 16, 20, 24 AND 32, all 6 seeds.
- K3 parity found: at least one flip counter (both rows >= 0.95 on "change state") in all 6 seeds.
- K4 sleep N=20: CARDFOLD installed AND fresh >= 0.80 AND long (12,16) >= 0.80, all 6 seeds.
- Recorded: length 64 (soft reads are expected to blur there, as in 43I's stress test); per-skill failures per seed.

Reading rule: K1–K3 pass -> with wider practice the design learns odd/even AND length-proof addressing with no parity
facts given. It would still be a toy with hand-chosen clues; "length-proof" is only claimed up to the tested length.
K2 fail -> report skill, length and seed; do not add regularisers.
