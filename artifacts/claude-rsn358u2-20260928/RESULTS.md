# rsn-358u2 results (stand-in for the sleep research thread, 2026-09-28T01:32:34Z)

**Verdict: NOT ACCEPTED.** A1 is met, and A2 is met on sums8 but missed on grids7. By PLAN.md, slp-358n3 does not run on these
nets. It has not run.

Run: one vast RTX 5090 (instance 53067079, host 406325, 16 cores, $0.469/h), torch 2.11.0+cu128, 358u's SEAL-code 20 of 20 and
its selftest and check-mask passed on the rental. The 4 loop runs (seeds 13-16) trained at once, 60,000 steps each, about 60 min
each. Records were copied from builder-outbox (rent358u2-2-collect): 38 of 38 small files match the rental's manifest.

## Weights: on the Mac, verified
Each final.pt came back one file at a time and matches both the rental's manifest and SEAL-run: 4 of 4, in
~/premonition-models/rsn358u2/loop-s13..16/final.pt. The instance was destroyed only after that check, and was confirmed gone.
Rental cost: **$0.52** by the guard's count (1 host, 66.6 min).

## Acceptance mark (PLAN.md, fixed before training)
| mark | result |
|---|---|
| A1 (358u's V0) | steps_block_nograd = 0 on 4 of 4 nets: **met** |
| A2 sums8 | mean 260.25 (265, 250, 266, 260); 358u 274.25; band [259.25, 289.25]; difference −14.00: **met** |
| A2 grids7 | mean 208.50 (206, 257, 195, 176); 358u 184.00; band [169.00, 199.00]; difference +24.50: **missed** |

## Report only
- V1 poison: predictions identical with the kind field swapped, 4 of 4 nets.
- Loop means, re-run vs 358u (of 300): sums4 300.00 vs 300.00; sums6 297.75 vs 298.25; sums10 222.00 vs 238.00; sums12 169.00 vs
  191.75; grids5 300.00 vs 300.00; grids6 292.75 vs 291.00; numbers4 2.00 vs 0.75; numbers5 0.50 vs 0.50.
- The practised and 6-size tests match within 2 points. The bigger sizes do not: the re-run is lower on long sums (−14 to −23) and
  higher on grids7 (+24.50; seed 14 went from 187 to 257).
- Suggested, not tested: the same code and seeds give nets that differ by this much at the bigger sizes, because GPU training is
  not bit-identical and here 4 runs shared the card instead of 8. So a ±15 band on a 4-seed mean was tighter than the run-to-run
  spread at those sizes.
- Kit note: the start script's launch ssh (inherited from the 358u kit) stayed open until drive.sh ended, so the Mac guard only
  started after training (01:24 UTC). Its money and time stops were not active during the 65 min of training. It cost nothing
  extra here. The n3 kits launch with `{ ... & }` and do not have this problem.

## What this means
- The re-run nets are verified and kept on the Mac, but they are not accepted as n3's base. The kit handoff/kit/sleep358n3r is on
  main unused: it refuses to rent without artifacts/claude-slp358n3-20260927/ADDENDUM-1.md, which was not written.
- Instance 52964920 (358u's original nets) still exists, **stopped**, with a small storage charge. It was not destroyed. The third
  restart (rent358u-4c-recopy) started it and ssh answered within about 1 min, but every copy came back empty in the same second.
  That job ran each copy under `timeout`, and the Mac has no `timeout` command (other Mac jobs printed "command not found:
  timeout"). So the originals are most likely still on its disk (suggested, not checked).
- Held, not released: handoff/held/rent358u-4d-recopy.md, which is 4c without `timeout`. If Ben releases it and it prints
  RECOPIED-DESTROYED, slp-358n3 can run exactly as sealed, with no addendum.
