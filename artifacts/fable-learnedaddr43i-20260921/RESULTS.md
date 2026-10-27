# Experiment 43I — results (2026-09-21): learned addressing + callable skills + router

1,464 trainable numbers. Base 12,000 updates in ~22 s; sleep ~15 s. Seeds 4102/4103/4104 + 4111/4112/4113, one wave.

- L1 fit: all six old skills 1.00 at lengths 4–8 -> PASS 6/6.
- L2 length: all six old skills 1.00 at lengths 9, 10, 12 and 16 -> PASS 6/6.
- L3 sleep from 20 episodes: installed, fresh 1.00 -> PASS 6/6.   L4 (50 episodes): PASS 6/6.
- L5: old skills unchanged, weights-only reload identical -> PASS 12/12.
- Recorded: CARDFOLD at lengths 9–10, 12, 16 = 1.00 in all 12 runs.
- Recorded warning sign: mean correct-digit probability at length 16 is 0.999 for most skills but 0.977 (ROTL1) and 0.970 (FOLD):
  the soft read spreads a little over more places as inputs grow. Answers are still all correct at 16; it should break at some
  much longer length. Not yet measured where.

Caveats that must travel with the result:
- The model starts from all-zero tables, so the six "seeds" differ only in their training data, not in a random start. They are
  less independent than usual; the near-identical numbers reflect that.
- I chose the four distance clues knowing the six skills (the two "double scale" clues exist because FOLD needs halving). The model
  now learns WHICH clue and WHICH distance each skill uses, over all n places, instead of picking 1 of 6 ready-made places —
  less hand-feeding than 43G, not none. Parity facts and output length are still given.
- Digit-shuffling toy. No carrying, no noisy episodes, no skill that is not a chain of known skills, no language, not the transformer.

Allowed sentence: "In the callable-skills design, length-free addressing was LEARNED from four generic distance clues: six skills
trained on 4–8 digits run perfectly at 16, and a new chained skill is learned from 20 raw episodes by training 21 routing numbers."

## Length stress (measurement only; scripts/fable_learnedaddr43i_stress.py, stress.json)
Soft reads, 100 inputs per length, worst old skill / CARDFOLD, seeds 4102 4103 4104 4111 4112 4113:
- 32 digits: 0.98–1.00.  64: 0.77–0.88.  128: 0.50–0.67.  256: 0.36–0.44.
- Only ROTL1 breaks (its wrap-around place: the last answer digit must read place 0, and its margin is shared out over more
  and more competing places). The other five skills are 1.00 at 256 digits in every seed. CARDFOLD uses ROTL1, so it inherits the failure.

One change, no retraining (…_stress_hard.py, stress-hardread.json): at test time each read is hardened to its single best-scoring place.
- All six skills and CARDFOLD = 1.00 at 16, 32, 64, 128 and 256 digits, 6/6 seeds (32x the longest training input).
- Meaning: the learned scores always rank the right place first; the soft mixture was the only thing that failed at long length.
- Not shown: that hard reads are safe during TRAINING or sleep (they remove the gradient); sleep still uses soft reads at lengths 4–8.
