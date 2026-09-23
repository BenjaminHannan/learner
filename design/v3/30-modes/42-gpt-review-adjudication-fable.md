# GPT outside review (2026-09-21) — adjudication against our numbers

GPT saw 43A/43C/43B. It did NOT see 43D (relative attention), 43E (rank-4 confirmed) or 43F.

## Accepted
- Main diagnosis: the wall is the hypothesis class (length-dependent addressing; skills not callable/reusable), not the sleep optimiser. Matches 43A/C/D and the fully-trained-INC3 probe.
- "43B does not show randpos hurt sample efficiency" — correct; four things changed at once. 43E (registered base, clean) is the clean comparison.
- Gradient "energy kept" is not step size under Adam — correct; dropped as evidence.
- H2's impossible floor, integer noise counts (7/8/9 noisy rows in training, not a fixed number) — correct; print integers from now on.
- 3,040 = 8 block LayerNorms (2,560) + final LayerNorm (320) + one embedding row (160) — consistent with GPT's guess.
- Finite short examples cannot pin down the algorithm; the system must supply an inductive bias. The question is WHICH bias.
- Robust mixture likelihood for noisy episodes; CV-selected checkpoint with an exact-match floor — adopted for the router.

## Checked
- Prediction-position off-by-one (43C): real but a CONSTANT shift (query sits one place before the digit it predicts), except at "=" whose number depends on n. Does not explain 43C's failure at places 2–11. 43D's indices make the shift constant everywhere, including "=".
- Randpos prefix positions are sampled once per example and kept during greedy decoding — OK.

## Tested (43G/43H, artifacts/fable-transport43g-20260921/)
- v1 exactly as specified: FAIL to fit in 2/3 seeds (saturated soft choice). GPT's 0.85 forecast did not survive its own init.
- v2 (one change, cosine-bounded scores): everything passes 6/6 seeds incl. 3 fresh. Lengths 12/16 = 1.00; CARDFOLD from 20 episodes = 1.00 fresh and long; 21 trained numbers; ~15 s sleep.

## Not accepted as the architecture (Ben's call)
- The six readable places are exactly the answer key for our six skills; the model chooses among 6 options per (skill, parity). Length generalisation is then true by construction. It is a CONTROL / upper bound, not "a model that learns".
- "Stop optimiser work on the existing representation": partly overtaken — 43E's rank-limited update is a confirmed gain on that representation (but still nowhere near 20-episode learning, pending 43F).
- The trained router is, in effect, a soft 3-step program over named skills. It is found by gradient arithmetic (nothing proposes it), so it fits the letter of "automatic and mathematical"; whether it fits the spirit is Ben's ruling.

## What carries forward
1. Skills must be CALLABLE modules on a shared tape, and a new skill = a small router over frozen skills (+ new primitive capacity when routing cannot fit). This is where the 20-episode result came from.
2. Addressing must be length-free. Next rung: keep (1), but replace the six given places with LEARNED relative addressing (43D's start/end-difference bias, plus a learned halving/parity feature), and measure how much of 1.00 survives.
3. Carry/arithmetic needs recurrent scratch state; the linear tape cannot do it. Separate later experiment.
