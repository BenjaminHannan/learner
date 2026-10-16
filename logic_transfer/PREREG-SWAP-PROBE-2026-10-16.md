# Pre-registration: swap-pair binding probe on the R2a replicas and parents ($0, CPU) — 2026-10-16

Written before any probe row is generated or scored. Nothing here changes a sealed mark, re-verdicts R2a / R2a-long, or books a box.

## Why
The sealed hard file has 32 rows; 17 are solved by the "facts differ in not" cue, so the binding test rests on 15 rows (one row = 3.1 points). That cannot tell "slowly learning" from "flat". At 8,000 updates, Unknown ranks second on 77-90% of gold true/false rows as well as on 79% of hard rows, and the top-vs-Unknown margin on hard rows (median 0.86 nats) equals that on gold-true rows (0.83) [shown, `answer_words/*.jsonl`], so the S3 "rank 2" pattern is not specific to split rows.

## Instrument (built after this file)
Swap pairs. Bound member: `A is [pA]X. B is [pB]Y. Is A [q]X?` (true/false). Split member: the same text with X and Y exchanged between the facts (`A is [pA]Y. B is [pB]X.`), same query, same fact order, same option order, len(X) = len(Y): identical bag of characters and words, identical character positions except which property sits in which fact; gold unknown. Strata: equal-not (pA = pB) / differ-not, query polarity, fact order. Word-missing controls (query name or property absent). Labels by the independent checker; no prompt in the rung-6 train file (ignoring option order).

On EQUAL-NOT pairs, any reader that ignores which fact holds which word gives the same answer to both members. So the per-pair binding score `B = logP(unknown | split) - logP(unknown | bound)` (answer-word scorer, nats) is a cue-proof binding readout with paired power.

## Readouts and fixed calls (per checkpoint: 3 parents at update 0, 6 replicas at 8,000)
1. `B_eq`: mean B on equal-not pairs (dev vocabulary), with pair-bootstrap 95% CI.
2. `acc_split_eq`: unknown accuracy on equal-not split members; `u_bound`: unknown rate on bound members.
3. Linear probe (logistic, pair-grouped CV) on the controller readout state for split vs bound on equal-not pairs: AUC; beside it the model's own pointer AUC (logP unknown) on the same rows; controls: shuffled labels (≈0.5) and word-missing vs bound (positive control).
4. Reported, no bar: which fact's polarity the committed answer follows on differ-not split rows (name-fact / property-fact / first / last).

Calls, fixed now:
- **Binding absent at 8,000 (occurrence reader)** if, in at least 5 of 6 replicas, `B_eq` < 0.25 nats AND probe AUC < 0.65. Prediction [suggested]: this holds.
- **Binding present but not read out** if probe AUC >= 0.75 in at least 4 of 6 replicas while the pointer AUC is < 0.65. Prediction: does not hold.
- **Binding partly expressed** if `B_eq` >= 0.5 nats in at least 4 of 6 replicas. Prediction: does not hold.
- Anything else: reported as mixed, no call.
- Parents (update 0) give the floor; a replica-minus-parent rise in `B_eq` is reported per lineage, no bar (two points per lineage cannot fit a slope).

What would prove the instrument broken: the shuffled-label probe AUC outside 0.40-0.60, the word-missing positive control below 0.80, any label disagreement with the checker, or any probe prompt found in the train file.
