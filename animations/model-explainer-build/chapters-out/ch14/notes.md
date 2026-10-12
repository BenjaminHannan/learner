# ch14 notes (auto-generated from ch14.json by the lead, 10-09; picture review is separate)

Title: What is proven, what is not, what comes next  |  scenes: 12

## SOURCES (distinct src paths)
- architecture/FINISHED-MODEL-2026-10-09.md:29-38 (parts table: reader row 31, thinker 34, calculator 37, stop 36, talker 38)
- big-run/PLAN.md:80 (the learned stop has never run)
- architecture/FINISHED-MODEL-2026-10-09.md:32-33 (adapter 196,864 / 393,728; window ~0.7M / ~2.6M; kept), 177-178 (cipher_map 100% to 2.5-10%), 130-131 (size counts borrowed and adapter and window)
- architecture/FINISHED-MODEL-2026-10-09.md:136-139 (experts), 155-157 (tokens), 85-86 (group 2 build started 12:15 PM ET), 160-162 (sleep and domain mode not in run-1)
- domain-mode/DESIGN-AND-MARKS-2026-10-09.md:171 (DM-S v1 proved wrong on seed 200)
- sources/pr-53-consolidation-sleep.md:2,8
- whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md:187-189 (G-B2 73.01 = 4,410/6,040, thinker-off 0.66; G-PT 67.12 = 4,054/6,040; one rung of one seed)
- architecture/FINISHED-MODEL-2026-10-09.md:109-110
- big-run/PLAN.md:223 (G1's 3M lead for G-B2 over G-PT was +5.9 on one seed); architecture/FINISHED-MODEL-2026-10-09.md:125-126 (G1 tests the calculator-inside, 12-round model)
- architecture/FINISHED-MODEL-2026-10-09.md:106-108 (T1SDR matched B2 over 6 seeds: pooled-5 +0.62, CI -0.23 to +1.46; calculator off scores 0.0; mark 5 holds on 5 of 6 seeds, seed 205 unscored, checkpoint lost)
- architecture/FINISHED-MODEL-2026-10-09.md:42-57 (the sub 12 5 = 7 example)
- sources/pr-53-consolidation-sleep.md:2,8,9 (76.1% = 78.3, 77.9, 71.3, 75.8, 76.4, 77.0; 256 updates against 558-610)
- sources/pr-53-consolidation-sleep.md:27 (71.3 is the research loop's stored number, not a paired baseline; one training run per parent)
- sources/pr-53-consolidation-sleep.md:7,12,16,22,24 (sleep minus replay-only -1.58 [-1.79, -1.37]; replay-only control +2.11; harm vs original model fails on all six parents; stop rule never ended a night early)
- progress-board/data.json key blockers[0] (earlier fast-sleep: seq_next 85 -> 30; claim of no harm withdrawn; lower learning rate removes the loss on both parents)
- big-run/PLAN.md:80 (SC proved wrong on harm 12:14 PM ET, SCL passed on two parents 1:18 PM ET)
- architecture/FINISHED-MODEL-2026-10-09.md:123-124 (outside calculator and Gemma never run together; first run B3 group 1 at 3M seed 400 after G1)
- big-run/PLAN.md:114-116 (B2 +0.49 from 3M to 10M, plain step model +3.77; B2 ran with 9 letter slots instead of 36)
- architecture/FINISHED-MODEL-2026-10-09.md:38 (English talker unbuilt), 167 (games paused); big-run/PLAN.md:77,33 (SmolLM2-360M race, planned)
- architecture/FINISHED-MODEL-2026-10-09.md:31 (mean 6.59 against limit 4.62, plain B2 3.62 + 1.0), 111-112 (separate seed-200 in-distribution run, addendum 14: EGE 18.09 against 1.40 for plain B2 / B2V; not one of the six confirm copies)
- architecture/FINISHED-MODEL-2026-10-09.md:149-150 (16 rounds cost 1.2-1.9 points on one B2 probe), 66-69 (stop may fire early, suggested), 147-148 (web pool gate)
- architecture/FINISHED-MODEL-2026-10-09.md:84-86 (stop 0, arithmetic 2, reading 6, writing 4, new kinds 6; pass mark 0 each)
- no-hardcoding/INVENTORY-B3-2026-10-09.md:11-17 (summary; X1 is counted under both arithmetic and writing)
- big-run/PLAN.md:38-39 (G1 then the post-G1 chain: GX stage 1, fit check, g2c3, B3 group 1 at 3M seed 400), 42-47 (10M, 30M, Oct 31 readout), 51 (the 90% bar)
- architecture/FINISHED-MODEL-2026-10-09.md:24-25 (no rentals; the owner: demonstrable results first)
- big-run/PLAN.md:62 (the SCORECARD section; the brief's 'PLAN sec. 5' is really the G1 gate at line 195)
- big-run/PLAN.md:204 (G1 readout: GO if difference >= +1.0 on both seeds, STOP if <= 0 on both), 39 (STOP: replan, no B3 on this thinker)
- big-run/PLAN.md:223 (B3-1: pass at least +3.0 over g2c3; below +1.0 no seed 401, bisect)
- domain-mode/DESIGN-AND-MARKS-2026-10-09.md:88 (DM1 pass +30, proved wrong < +10 on seed 200), 171 (v1: DM1 -0.48, proved wrong)
- big-run/PLAN.md:136 (teacher data as a booster: PROVED WRONG, new kinds +0.78, needed +15)
- kit/GLOSSARY.md (the five parts and the one analogy)
- big-run/PLAN.md:112-113 (bottom line 1: nothing is ready to buy), 80 ('Today: 0 of 9 fully green'), 87 (realistic read at Oct 31: 5 or 6)

## SCENE NOTES
- s01: Reader +2.67, 6 of 6 seeds, but the 6-seed confirm missed its zero-round leak mark (6.59 vs 4.62), FINISHED:31. Calculator column covers the call writer (tested in T1SDR, 6 seeds) and the any-round change (B3 group 1, built, never run, FINISHED:62-64). Talker: FINISHED:38 says 'today a small stand-in; the English talker is unbuilt'; the brief's 'stand-in works' is not a stated test result, so the chip only says 'stand-in only'.
- s02: Group 2: the dossier said 'code built, no run'; FINISHED:85-86 and PLAN:41 say its BUILD STARTED Oct 9 (code only), so the chip says 'being built, no run'. Domain mode: the brief says 'untested' and FINISHED:160-162 says 'later, planned', but the DM design file records a v1 run that failed its mark on seed 200; the chip says v1 failed. Plug and window sizes (393,728 and about 2.6M at width 512) are left out to save words; the window figure cites RESULTS-EG2, which is not in the project snapshot.
- s03: Same numbers as ch04 s14, ch06 s03, ch09 s04. 73.01 belongs to the older design with the calculator inside and 12 fixed rounds (the Gemma-fronted G-B2 arm, 3M, seed 400); the finished design has not produced a number yet. The +5.9 gap is quoted from PLAN:223, not computed here (73.01 - 67.12 = 5.89).
- s04: The slip 'sub 12 5' and reply '7' are the project's made-up example (Tom's apples), a picture, not a result. The number-line is drawn to scale for the three numbers only. Chain-5 99.6-99.8 (FINISHED:106) is left out to save words; ch05 s12 already shows it. Brief says 'matched'; the source says matched with +0.62 and a range that includes 0, so the caption says so.
- s05: Dots A-F are the six parents s200-s205 in order. 'The test kept aside' is the C2 holdout, first try. 76.1 is the source's own mean (the six values average to 76.1). PR #53 is open, not merged. This is NOT the 30M forecast of 76.1 in scale.json (a different number).
- s06: Conflict on harm: PR #53 marks 'no harm' as pass (against the pre-sleep model) but says the check against raw B2 still fails on all six parents; the progress board withdraws the earlier 'no harm' claim for the 71.3 fast-sleep win. The 85 to 30 drop belongs to that earlier, different sleep, not to the 76.1 recipe, and the caption says so. The +0.52 and +2.11 are in_dist changes in points; -1.58 is quoted from the PR, not subtracted here.
- s07: The pieces sliding together is a picture of the plan, not a measurement. FINISHED:128-129 quotes a different pair of earlier 10M-ladder gains (+0.03 and +0.28 vs plain +3.08 and +4.25); both say the register bug means they do not count either way. The caption uses PLAN:114-116, the 'only result on size'. The progress board also says 'mark 1 fails'.
- s08: Leak mark A (reader, missed, not cleared) is a different test from leak mark B (calculator, limit 5, cleared by the project owner Oct 9; ch05 s14). This scene is about A only. The bars are the six-copy confirm (FINISHED:31, addendum 15); the 18.09 / 1.40 line is a separate seed-200 in-distribution run against plain B2 (B2V), PASS-MARKS addendum 14 (FINISHED:111-112), so it is labelled as its own run and not as one of the six. 'Out of 100' follows the leak being a share of questions.
- s09: No total is shown: X1 (operand span copy) is listed under part 2 and part 4, so adding gives a double count. 'New kinds' counts apply to training only (part 8b).
- s10: G1: as of Oct 9 its 3M seed 401 is finishing and the 10M arms follow (PLAN:38). The seed-401 files in the snapshot belong to earlier 8a runs, not G1. The 90% bar is the plan author's reading of a relayed rule (PLAN:51). Every date is 'planned'; the Nov to Dec range for the 100M run (PLAN:44-47) is left out as an estimate.
- s11: B3-1's failure branch is 'find which new part broke it' (bisect), not 'the idea is dead'; the zone says 'find the cause'. The gauges are drawn evenly and not to scale. The DM1 marker (-0.48) is the only measured point; the other two gates have no result yet.
- s12: Both numbers are the plan's own judgment, labelled as such on screen. No ch00 chapter file exists in the worktree; the five-part sentences follow the glossary.
