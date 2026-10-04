# Fix screen v1: result

Boxes 54198527 (W, L, O) and 54198737 (P), RTX 5090, 2026-10-04 20:24-21:32 UTC. Both copy-backs sha256-checked before destroy.
Scored at update 6,000 against the paired diagnosis F1-F3 runs at update 6,000 (same seeds, rows and order).

| arm | change | fit gain per seed (1,2,3) | mean fit gain | held-out gain mean | verdict |
|---|---|---|---|---|---|
| W | reader 32 -> 256 | -0.9, +2.2, -0.6 | +0.2 | +1.1 | NO EFFECT |
| L | 8 rounds | -2.5, -0.3, +2.2 | -0.2 | +0.8 | NO EFFECT |
| O | lr 3e-4 | -4.0, +1.2, -0.9 | -1.2 | +2.8 | NO EFFECT |
| P | allptr pointer exit | -3.4, -2.5, -1.6 | -2.5 | +0.4 | NO EFFECT |

## Shown
- No single change moves fit; every arm ends near 47-50% fit on its own 2,000 practice rows.
- With 8 rounds instead of 4, main2's answers at update 0 are identical to the 4-round answers (121/320 fit, 89/320 held-out, same per family), although the 8-round runs took longer (36.9 vs 31.6 min in the same wave). Doubling the core's thinking changes nothing the LM says.
- P starts lower (fit 21-25%, its new pointer is untrained) and climbs to 47%, the same ceiling.

## Suggested (not tested)
The ceiling is the same no matter what changes on the core side (reader width, rounds, lr, core size in PR #18). That points downstream: the exit. The core reaches the frozen LM only as 8 soft vectors made by a 32-wide StatePrefix (rank 32 of 2,048) and averaged over positions, next to the raw prompt words, which the LM can use alone. Together with the helpers' finding (a shuffled core state leaves new-kind answers unchanged), the LM seems to answer mostly from the prompt words, with the core's 8 vectors carrying little it can use.
Next single change: widen the StatePrefix hidden from 32 to 256 (function-preserving), with the same screen and marks.
