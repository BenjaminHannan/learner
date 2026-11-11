# bridgelab pre-registration (written before any run; do not edit pass marks)

Question: which bridge design lets information that is private to one module reach the other, per item?

## Task (card experiment only; nothing here is about the village model)
- A ("reader", d=64): 4 entities (names from 40 train name tokens), values 0..15, query `? name` -> v (A alone knows v).
- B ("calculator", d=96): `[mul, a, add, b]`, f(x) = (a*x + b) mod 17 (B alone knows f).
- Both heads must output f(v) (17 classes). Chance = 1/17 = 5.9%.
  - "A->B direction" = B's head accuracy (needs v from A). "B->A direction" = A's head accuracy (needs f from B).
- Design note (before running): a is drawn from 1..16, not 0..16. With a=0, f(v)=b is known to B alone, which would leak ~6% of items.
- Marginally, f(v) is uniform given only A's input or only B's input, so neither side can beat chance alone.
- Both modules: pre-LN transformer, 4 heads, R=4 registers, block looped 2x with shared weights; exchange between loop 1 and loop 2.
- Arms: none, ema_const, pooled, xattn, slots. 3 seeds (0,1,2). Loss = CE_A + CE_B.
- Test sets: 5000 fixed items (train names) and 5000 fixed items using 8 held-out names (generalisation check; reported, not part of pass marks).
- Ablations at eval: real, off, shuffle (derangement of messages within batch), mean (batch-mean message), probe (linear, frozen model).
- Probe targets: A->B message -> v (16-way). B->A message -> a and b (two linear probes); probe score = mean of the two accuracies.
  Probes are fit on 20000 fresh train-distribution items and scored on the 5000 test items.

## Pass marks (per arm, per direction; mean over 3 seeds)
An arm "carries question-specific information" in a direction iff ALL hold:
1. real accuracy >= 90%
2. shuffle accuracy <= 16%
3. mean-message accuracy <= 16%
4. probe score >= 80%

## Proved wrong (task/analysis invalid) if any:
- ema_const real accuracy > 20% in either direction (task leaks), or
- none real accuracy > 20% in either direction (task leaks), or
- an arm has real >= 90% but shuffle >= 50% (accuracy is not coming via the message).

## Notes
- ema_const: shuffle is a no-op by construction (every item gets the same vector), reported anyway.
- Labels used in reports: shown (measured here), suggested (inferred), untested.

## Amendments
Made BEFORE the sweep whose results are reported, after four rounds of 1-core feasibility debugging (no result tables were produced; pass marks below
the "Pass marks" heading are UNCHANGED). Reason for all of them: the original arithmetic task, f(x)=(a*x+b) mod 17, was a parity-like problem (every marginal
is uniform, so there is no first-order gradient to cross the zero-initialised bridge) and stayed at chance for thousands of steps in every arm (shown, 4 debug
runs, <=4000 steps; including a=1 only and with local auxiliary losses). The compute available (4 shared cores, other jobs running) rules out training for much longer.

1. Task replaced by a symmetric two-way lookup (still split-information, still needs both directions):
   - A sees 4 (name, value 0..7) pairs, a query `? name` (-> private v) and its own private table sigma (permutation of 0..7, 8 tokens).
   - B sees its private table pi (permutation of 0..7, 8 tokens) and a private key u (0..7).
   - head B must output pi[v] (A->B direction); head A must output sigma[u] (B->A direction).
   - Each answer is uniform given only the receiver's own input, so chance = 1/8 = 12.5% (not 1/17). The numeric pass marks are kept as written
     (shuffle / mean-msg <= 16% is stricter than chance+10 = 22.5%). Under shuffle a perfect channel scores ~12.5% (the other item's key matches 1 time in 8).
   - Probes: A->B message -> v (8-way), B->A message -> u (8-way); probe score = that accuracy (no a/b any more).
   - Held-out names: A's query names. B->A never touches names, so this check mainly tests A's name matching; reported, not part of pass marks.
2. Training curriculum (all arms identically): tables start as the identity and are scrambled by up to 0..10 random swaps, with the allowed
   swap count growing linearly over the first 60% of steps; the last 40% of steps use uniformly random permutations. All evaluation uses uniformly random tables.
   Information still has to cross in every curriculum stage (identity tables still need v / u from the other module); the curriculum only creates a first-order signal.
3. Run settings: batch 64, 8000 steps, AdamW lr 1e-3 cosine, MLP ratio 2, 2 layers, 4 heads, R=4, 2 loops. No auxiliary losses (loss = CE_A + CE_B).
4. Reporting: A->B accuracy is head B, B->A accuracy is head A.
