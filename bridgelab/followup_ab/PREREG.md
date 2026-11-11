# followup_ab pre-registration (written BEFORE any run in this folder)

Question: the look-up-then-send direction (A->B) of the card game stays at ~41% with the best per-item arm (pooled). What is the bottleneck: training length, timing, how the sender reads, or whether A computes v at all?
Card experiments only (nothing about the village model). Task, curriculum, optimiser, batch 64, lr 1e-3, widths, 2 layers, R=4 are exactly bridgelab's (see bridgelab/PREREG.md amendments). Loss = CE_A + CE_B.
Labels: shown / suggested / untested.

## Baseline (the one every change is compared with)
`base`: arm pooled, 8000 steps, 2 loops, exchange after loop 1, sender = register 0, no aux loss. Re-run with this folder's code (fa.py) so it also carries the new diagnostics. Seeds 0 and 1 (earlier bridgelab pooled runs: B 41%, probe 0.41).

## Pass mark (per variant; mean over seeds 0,1; fixed now)
PASS = B-head real >= 90% AND B-head shuffle <= 16% AND probe(v) on the A->B message >= 80%.
A variant that does not meet all three FAILS. "Improves" is reported separately (>= +10 points B-head real over base) but is not a pass.
B->A must stay >= 99% (sanity; a variant that breaks it is flagged).

## One change at a time (each differs from base in exactly the stated thing)
H1 `steps3x`: 24000 steps (curriculum fraction scaled with steps). Hypothesis: just undertrained.
   Wrong-if: B real mean < 60% at 24000 steps (i.e. < +19 points), or the learning curve (logged every 1000 steps) is flat over the last 12000 steps (< 3 points).
H2 `timing`: 3 loops, exchange after loop 2 (A gets two loops to finish the look-up before it sends; B gets loop 3 to use it). Hypothesis: A needs more depth/time before the exchange.
   Wrong-if: B real mean < 60%.
H3 `fullread`: sender attends over A's WHOLE sequence (one learned query, 4 heads, + register rows) instead of reading register 0 only; same zero-init projection and receiver. Hypothesis: the bridge cannot reach the lookup result because it is not in register 0.
   Wrong-if: B real mean < 60%.
H4 (diagnostic, not a fix) `auxv`: base plus an auxiliary local loss on A (linear head on A's register 0 at send time predicts v, weight 1). Uses an extra label, so it is NOT a legal pass; it tells compute vs transmit.
   Reading: if aux makes B >= 90% and probe(v) >= 80%, the bridge/receiver can carry v and the bottleneck is A computing v under only the B-via-bridge gradient (shown). If aux gets A's local v high but B stays low, the bottleneck is transmission/receipt (shown).
   Wrong-if (of "A does not compute v"): the baseline's linear probe of v on A's states at send time (reg 0, and all 4 registers concatenated) is >= 80%. Then the compute is fine and the bottleneck is transmit.
D1 (diagnostic, free, on base) probe v from A's states at send time: reg0, all registers; compared with the message probe (0.41 in bridgelab).

## Verdict rules (fixed now)
- compute: base state probe(v) <= 55% AND auxv local-v probe >= 80% AND auxv B >= 90%.
- transmit: base state probe(v) >= 80% while message probe/B stay ~41%.
- training length: steps3x passes.  timing: timing passes (or improves while steps3x does not).  sender reading: fullread passes.
- If nothing passes: report which improved, and say untested for the rest. If time allows, one combo (best change + auxv-free best other) is run and labelled exploratory.

## Compute / run notes
Seeds 0,1. Runs may be on a rented GPU or CPU; hardware does not change the maths. Test sets: bridgelab's fixed 5000-item train-name set. Probes: linear, fit on 20000 fresh items, score on the 5000.

## Amendment 1 (before any real run; added after a 200-step smoke test)
In the smoke test every linear probe of v (message, reg0, all registers, sequence mean) already read ~0.40 at 200 steps. Likely reason (untested until run): v is always one of the 4 values present, so a bag-of-values feature predicts v ~40% with no look-up at all. A control probe `bag` (counts of the 8 value tokens in A's input) is added to every run. Reading rule: a probe of v only counts as evidence that A looked something up if it beats `bag`. Pass marks unchanged.
