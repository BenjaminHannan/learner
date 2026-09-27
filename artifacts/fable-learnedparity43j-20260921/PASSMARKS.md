# Experiment 43J — pass marks (fixed before any registered run)

One change from 43I: the two hand-given parity facts are removed. In their place: 4 forward + 4 backward learned
2-state counters (random start), shared by all skills; score tables are indexed by counter state and added up.
Still given: four distance clues, wired-in output length, the counter size (2 states).
Registered arm: plain (FABLE43J_C=4, K=2, DROP=0). Seeds 4102/4103/4104 and 4111/4112/4113, one wave. 12,000 updates.
Sleep = 43H unchanged, N=20 only.

Exploration disclosed (throwaway seed 9999 only, no registered seed touched): product-of-two-counters (K=2, K=4) failed
length 9+; 1 vs 4 additive counters -> 4 chosen; weight decay 0.1/0.3/1.0, sparsity pull 1e-4/1e-3/1e-2 and clue
hiding 0.1/0.25 were tried to fix a SWAP misread at lengths 9 and 12 and NONE helped; none is in the registered arm.
On seed 9999 the registered arm scored 1.00 on 5 of 6 skills at every length and SWAP failed at lengths 9 and 12.
My prediction is therefore that J2 FAILS on SWAP.

- J1 fit: every old skill >= 0.99 exact match at each length 4–8, all 6 seeds.
- J2 length: every old skill >= 0.90 exact match at length 12 AND 16, all 6 seeds.
- J3 parity found: in every seed at least one counter is a flip (both rows of its step rule put >= 0.95 on "change state").
- J4 sleep N=20: CARDFOLD installed by the fixed gate AND fresh >= 0.80 AND long (12,16) >= 0.80, all 6 seeds.
- Recorded: per-skill accuracy at every length; which skills fail J2 per seed; hard-read variant (FABLE43J_HARD=1) at 12/16.

Reading rule: J3 pass = odd/even can be DISCOVERED by gradient in this design. J2 fail on SWAP only = the counters work
but the additive clue scores are under-determined by lengths 4–8 (next step would be wider training lengths, a data
change, not more regularisers). Toy only; no claim about language, carry, noise or the transformer.
