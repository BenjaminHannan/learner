# Sleep-B addendum 20: addendum 15's long nights (R8, V8) move to LFM3-1.7B (written 2026-10-28 ~00:20Z, before any R8 or V8 run)

Labels: shown / suggested / untested. Week-2 world, seed 1. Not the village model, not the card experiments.

## Why
- Addendum 15 (sealed) tests Ben's long nights on K2: R8 (2x longer nights, same cards) vs V8 (2x longer nights, varied cards and weird
  dreams). Since 2026-10-27 19:45Z the small tier is LFM3-1.7B (Ben: "we use LFM3 now instead of K2"), so a K2 answer no longer
  decides the recipe that ships.
- **Shown (Ben's PC, 2026-10-27, `results_pc/run4`):** K2 is too slow for long nights on this card. Addendum 17's fifth try (K2, B's
  recipe at 4x, 14 GiB cap, `--gen-bs 16` after running out of memory at 24) took 826 s for night 1 and 5265 s for night 2. That is
  3.6-3.8x the RTX 5090's 227 / 1379 s. Its projector stopped it after night 2, because seven nights would have ended 2 h past its 10 h
  budget. At 8x, R8 and V8 on K2 would need about 20-25 h each (suggested), so both would stop at their 16 h budgets with no result.
- Addendum 17 is not tried again: its gate change is part of addendum 19's arm on LFM3.

## What changes from addendum 15 (nothing else does)
- **Model:** LiquidAI/LFM3-1.7B at revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd, bf16, code f35dd7e840 or later (addendum 19's port).
- **Base recipe (the rule, fixed now):**
  - If addendum 19's arm (l3_g570_w) passes its no-harm marks and P1, the base is its flags: `--rem-chain-mode q_think --rem-dirs both
    --rem-tries 2 --rem-steps-mult 2 --gate-arc-n 570 --rem-writer base --rem-pairs distinct --rem-parse first_q
    --rem-verify-tokens 96`. The no-harm marks are ARC-Easy >= pre - 5, diary >= base_diary - 5 and changed-new >= 53.3; P1 is
    recall C2+C4 >= 88.5.
  - Otherwise the base is the recipe's defaults.
  - As in addendum 15: `--arc-base --tok-budget 256 --reword data/week2_reworded.json`, no `--think-eval`.
- **The 4x reference** is addendum 19's run when it is the base. When the defaults are the base, there is no LFM3 4x reference: L1 is
  not judged, and V1 and V2 are judged as written.
- **Arms:** R8 = base + `--budget-scale 8 --text-scale 4`; V8 = base + `--budget-scale 8 --dream-vary mix` (addendum 15's definitions).
  D8 and V8p stay unscheduled, as in addendum 15.
- **Generation batch:** both arms at `--gen-bs 24`. If R8 runs out of memory, both arms use 16.
- **No-harm recall mark:** recall C2+C4 >= the 4x reference's - 3 (addendum 15's 93.5 was K2's level); >= 88.5 when there is no
  reference. The other no-harm marks are addendum 15's: ARC >= pre - 5, diary >= base - 5, changed-new >= the reference's - 10.
- **V1, V2 and L1** are addendum 15's marks unchanged, on LFM3.
- **Addendum 19's K2 fallback is dropped** (a compute-order change; no mark changes). If addendum 19's pre-check finds the LFM3 port
  broken, the slot is passed on instead of running addendum 18 or arm A on K2, because K2 cannot finish a week within budget on this
  card (shown above). R8 and V8 are then skipped, and their turns are passed on.

## Compute and PC order
Ben's PC, in this thread's slots, which are unchanged:
- R8 after looping P2a and the 4-bit thread's G run: flag `think2-p1/SEG3-DONE`, which G writes;
- V8 after looping P2b: flag `handoff/GO-SLEEP-V8`.
Each arm stops itself if its log is silent for 90 min, or if, once night 2 or later ends, the projected end passes 16 h. Expectation (not a
mark): 8-12 h each. Chain script: `pc/sleepb_pc11.sh` (pc10 with R8 and V8 on LFM3 and no K2 fallback). It replaces pc10 while pc10 is only waiting;
mock-tested on three paths (addendum 19 passes, fails, port broken).
