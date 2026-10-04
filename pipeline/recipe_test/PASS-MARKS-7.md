# Round 7: lift the real core's 49-token query limit (2026-10-04, fast lane). Marks fixed before training

Why: the real core refuses any question over 49 tokens (with EOS): `ordered_begin` in `sol_spatial_poc_ordered_v2.py` raises "query physical cap49 includesEOS". Shown on CPU just now: a 60-token query raises with the cap at 49 and runs once the cap is 160.
Reading of the code: the cap is an interface guard (`QUERY_CAP`, read at call time), not a learned size limit. Position codes are sinusoidal up to 4095 and attention bias is relative with a clip. Nothing sealed on disk is edited: `run_arm.py --long` sets `QUERY_CAP = 160` in the running process; the weights are fresh.

**ONE change (LONG): cap 160 + 30% of training items lengthened with 1-7 neutral filler sentences** (50 sentences written by me, digit-free, no quantity or add/remove words; answer unchanged). 27% of two-step training items end up over 49 tokens (max 149). Otherwise TABV (round-5/6 recipe: copy path, composed wording, extra table variety, contextual reader, 4 loops, 3000 x 16, seeds 0-5).
Control = the six TABV runs of round 6 (`results6/`): same seeds, same frames, same three short eval sets, so nothing is re-run. The control core cannot run the long set at all (refusal shown above), so "now runs" is shown by the demo plus LONG finishing.

## Evals (LONG scores all four)
- Short sets (unchanged, all under 49 tokens): old own-wording 192, Blind-1 192, Blind-2 192.
- **Long set (new):** 192 fresh two-step questions, 55 to 150 tokens, built from the 24 independently written layout families (rounds 5 and 6 blind sets; frames I never trained on, 0 shared sentences/6-grams) with filler sentences from a pool of 60 written by a separate worker (`eval_filler_r7.json`; 59 kept after dropping any that share a 5-gram with my training fillers). 24 families x 4 op pairs x (1 unseen + 1 seen final). The operand triples of all four sets are excluded from training.

## Marks (6 seeds)
1. RUNS: LONG processes all 192 long questions in all 6 seeds with no refusal (the 49-cap core refuses every one).
2. USABLE: long-set chain, mean over seeds >= 50%.
3. NO-DROP: paired gain LONG minus TABV on each of old-all, Blind-1-all, Blind-2-all has mean >= -3 (t = 2.571 interval reported).
**PASS = all three. FAILS = any short-set mean gain < -5, or long chain < 30%. Otherwise partial, no claim.**
Reported with no mark: long chain by length bucket (55-80, 81-110, 111-150), by structure, call 1 / call 2 given call 1.
Gate: train fit (last 192 two-step training items, now including long ones) >= 70%, else UNDERFIT-VOID.
Wrong-if: long chain < 30% means filler practice does not carry to new-author long layouts (suspects: attention dilution over many tokens, 4 loops, practice filler too uniform).
Budget cap ~$3 (expected < $1; 6 runs on six 5090s, one run each). Credit must stay > $1 (shared).
