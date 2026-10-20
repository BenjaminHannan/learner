# Round G verdict against the pre-set bars (PREREG-G.md + Addenda A-E). DRAFT, coordinator review pending.

Written 2026-10-18 ~09:10Z; G3 confirm section completed 23:15Z. Both confirms are in.
Instrument: 6,800-row DEV (sha 3e3a5edb), house rule harm_measure(5.0, 1.5) plus the "near zero" clause drop <= 1.0 (= C1).
New skill: HO% (held-out layout), bar 36.6 = U 41.6 (unguarded L7-LB at 6-8k) minus SESOI 5. T* = first read step with mean HO >= 36.6.
Raw data: INTERIM-23Z.txt (every reading, with the time it was logged); per-row hits hash-checked where stated.

## Every candidate on both axes
| arm (one change vs L11) | T* | C1 at T* (drop / fired) | past T* | learning | verdict |
|---|---|---|---|---|---|
| G0 = L11 to 16k (reference) | 8k | s93301 FAIL (0.76, seq_next); s31001 pass (0.76) | fails every read 6k-16k (s93301), 10k-16k (s31001) | 43.8 @8k, plateau ~45-55 | FAIL |
| G1 = KL weight 30 | 8k | 0.71 / 0.65, none | s93301 fails 10k, 14k, 16k; s31001 fails 14k, 16k | 37.1 @8k -> 45.6 @16k | **SUCCESS; CONFIRMED on 2 fresh seeds** |
| G2 = parent-fixed K-FAC factors | 10k | cipher_map fires both seeds | - | - | FAIL (hypothesis proved wrong) |
| G3 = guard energy 0.999 | 14k | 0.57 / 0.63, none | C1 holds at every read 6k-16k, both seeds | 22.7 @8k, 42.7 @14k, 46.0 @16k | **SUCCESS; CONFIRMED on 2 fresh seeds** |
| G4 = L14 (hard + KL30) to 16k | 10k | s31001 FAIL (fewshot 5.5) | fewshot fires 10k-16k and grows to 8.0 | delayed, not capped (46.7 @16k on s31001) | FAIL |
| H1 = KL-prioritized replay 0.5 | 8k | FAIL both seeds (seq_next; 1.00 / 0.82) | fails every read 8k-16k, both seeds | not taxed (44.9 @8k; 63.6 / 52.4 late) | FAIL; mechanism check failed (priority went to state_update, not the leaking families) |
E2 guards (already scored in PREREG-G): unguarded L7 FAIL C1 (drop 57); A1F replay+freeze, no mask FAIL C1 (drop 4.5-6.2); L13 shipped FAIL
C1 (fewshot, both seeds); always-on add-on FAIL C1 (drop 88).

## G1 confirm (Addendum D, stop step 8k fixed in advance)
| seed | 6,800 drop @8k | worst family @8k | C1 | HO @8k |
|---|---|---|---|---|
| 93301 | 0.71 | fewshot_number_rule 4.5 | pass | 43.3 |
| 31001 | 0.65 | seq_next 4.0 | pass | 31.0 |
| 31002 (new) | 0.68 | seq_next 4.5 | pass | 46.4 |
| 31003 (new) | 0.78 | seq_next 4.5 | pass | 51.9 |
4-seed mean HO @8k 43.15 >= 36.6 and C1 on both new seeds => CONFIRMED.
s31002's read is the first run's 8k record (scored before a container restart killed it at ~8.7k); the rule for using it was logged at
07:05Z before any s31002 score was seen. The relaunch matched the first run exactly as far as it got (2k harm lines, loss at 2.5k).
New-seed rows hash-checked: 89.94% / 89.84% on 6,800, matching the records.

## G3 confirm (Addendum E, stop step 14k fixed from the original seeds)
| seed | 6,800 drop @14k | fired | C1 | HO @14k | old items lost |
|---|---|---|---|---|---|
| 93301 | 0.57 | none | pass | 42.4 | 75 |
| 31001 | 0.63 | none | pass | 43.1 | 76 |
| 31002 (new) | 0.54 | none | pass | 41.2 | 74 |
| 31003 (new) | 0.54 | none | pass | 41.4 | 75 |
4-seed mean HO @14k 42.02 >= 36.6 and C1 on both new seeds => CONFIRMED. C1 also holds at every read 6k-14k on all four seeds.
Container restarts killed several runs; each new-seed read comes from a from-scratch relaunch (same flags). Determinism checked:
an independent copy of s31003 gave identical records at every step and identical per-item hits at 14k. New-seed rows hash-checked
(90.07% / 90.07%: equal totals by coincidence; 14 items differ between the two runs).

## Which guard ships
**Under the pre-set PREREG-G ship-choice rule ("earliest T*, then lower max drop at T*"), the pick is G1.** That rule stands
(coordinator ruling, Oct 19): the G1-vs-G3 question is a bar change and is Ben's decision, put to him separately. Until he rules,
neither guard is called "the" fix. Both meet SUCCESS and both are CONFIRMED on fresh seeds; their two numbers:

| guard | stop step | old knowledge: 6,800 drop (4 seeds), families | new skill HO (4-seed mean) vs unguarded 41.6 | after the stop step |
|---|---|---|---|---|
| G1 (KL weight 30) | 8k | 0.65-0.78 (mean 0.705), none fired, worst 4.5 | 43.15% | seq_next / fewshot fail on both original seeds 10k-16k |
| G3 (energy 0.999) | 14k | 0.54-0.63 (mean 0.57), none fired, worst reported 4.5 | 42.02% | no family fails at any read to 16k (original seeds) |

Raw per-seed numbers for both are in the G1 / G3 confirm tables above and in raw/ (records, snapshots, hash-checked per-item rows).
For Ben's decision (not applied): clause 1 says "after training on new material ... no question family fails"; G3 meets it at every
reading 6k-14k on all four seeds; G1 meets it only if training stops at 8k. Choosing G3 means overriding the pre-set tiebreak.

## Ship gate (unchanged from the solve doc) and E0
A far success is not yet "ships": the Main brain domain run (DM1/DM3, s200/s201, both DEVs) and the coordinator's code review come first.
E0 (score Main brain's NK-soft10 / NK30 finals on both DEVs) is still not run: it needs /mnt/project-files on the PC, and those
checkpoints are on none of the 123 remote branches (searched Oct 18, 23:50Z). Both are packaged as one PC run sheet:
results/forgetting/e0/PC-PACKET-E0-AND-GATE.md (E0 ~1-2 CPU-h, read-only; then GATE-G3 and GATE-G1 domain runs).
