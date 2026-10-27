# Experiment 43I — pass marks (fixed before any registered run; smoke = throwaway seed 9999 only)

One change from 43G-v2: the six hand-given places are replaced by a LEARNED score over all n places, using four clipped
length-proof distance clues (see script header). Still given: two parity facts, wired-in output length.
Seeds: 4102/4103/4104 and 4111/4112/4113 in one wave. Registered base data, 12,000 updates. Sleep = 43H unchanged.

- L1 fit: every old skill >= 0.99 exact match at each length 4–8, all 6 seeds.
- L2 length: every old skill >= 0.90 exact match at length 12 AND 16, all 6 seeds.
- L3 sleep N=20: installed by the fixed gate AND fresh >= 0.80, all 6 seeds.   L4: same at N=50.
- L5: old skills unchanged and weights-only reload identical in every installed run.
- Recorded: CARDFOLD at lengths 9–10, 12, 16; per-skill accuracy at every length; correct-digit probability.

Reading rule: L1+L2 pass -> length-free addressing can be LEARNED in this design, not only given. L1 pass + L2 fail ->
report which skills and which lengths break (soft-read dilution vs wrong place) before changing anything.
Any pass is still a digit-shuffling toy with parity facts given; no claim about carry, noise, language or the transformer.
