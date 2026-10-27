# Experiment 45 — pass marks (fixed before any registered run)

One change from Experiment 44's sleep: loss -log p  ->  -log(0.9 p + 0.1/N)  (fixed 10% "teacher is wrong" allowance;
used for training and for the gate's checkpoint choice). Gate, thresholds, start, optimiser unchanged.
Design reviewed by GPT xhigh (reply saved as gpt-design-review.md). Paired arms plain / robust: same base, same 20
episodes, same wrong answers. Wrong answers out of 20: exactly 0, 2, 4, 6, 20. Three words. Seeds 4102–4106 (4105 and
4106 are new; bases are retrained by the unchanged Experiment 44 code). 15 word-seed cells per condition.
Disclosed: one run on throwaway seed 9999: robust installed 3/3 at 0 wrong, 2/3 at 2 wrong (maternal_grandmother
rejected, cross-validated match 0.40), 0/3 at 4, 6, 20. Plain installed 3/3 at 0 wrong and nothing else.

"Wrong install" = installed AND fresh-village accuracy < 0.99.

- N1 safety: zero wrong installs over all 150 runs (both arms, all conditions). One = FAIL of the whole experiment.
- N2 clean: robust installs 15/15 at 0 wrong, each fresh accuracy 1.000.
- N3 noisy teacher: robust installs >= 12/15 at 2 wrong (each with fresh accuracy >= 0.99); plain is expected ~0/15.
- N4 nonsense: robust installs 0/15 at 20 wrong.
- Recorded only: 4 and 6 wrong (the unchanged 0.90 agreement gate makes installs there structurally unlikely).

Reading rule: N1+N2+N4 pass and N3 fails -> the loss is not enough; per GPT's review the next control is scoring all
729 hard chains with the same likelihood, to separate "optimiser stuck" from "not enough signal". Toy only.
