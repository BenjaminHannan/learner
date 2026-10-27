# Experiment 43E-confirm — pass marks (fixed before the new bases exist)

Same script (hash in SEAL.sha256.txt, unchanged), same setting, FRESH seeds 4111 / 4112 / 4113
with new bases trained by the registered recipe (fable_cardfold_sleep.py --stage base, 12,000 updates).

V0: base old-skills >= 0.95, else the seed is invalid and reported, not counted; fewer than 3 valid seeds = VOID.
K1 (identical to E3): fresh(rank4, match pick) >= fresh(plain, match pick) + 0.10 in >= 2/3 seeds,
    and never lower by more than 0.02 in any seed.
K2: same comparison at the final update (3,000), same thresholds — so the result does not depend on the selector.
K3: old-skills at the pick >= base - 0.02 in all 6 runs.

K1 and K2 and K3 pass -> allowed sentence: "On the CardFold toy, limiting sleep's weight change to rank 4
improved new-skill accuracy on unseen inputs from 80 episodes, in 6/6 seeds." Rank-4 then joins Sleep-vNext
as a candidate and is next tested at 20 and 50 episodes and against other ranks.
Any fail -> no claim; 43E's E3 is recorded as unconfirmed.
