# ch08 notes (auto-generated from ch08.json by the lead, 10-09; picture review is separate)

Title: Practice, one small nudge at a time  |  scenes: 13

## SOURCES (distinct src paths)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 table (lines 29-38: reader borrowed and frozen; thinker, stop, talker learned; calculator hand code, allowed as a tool)
- kit/GLOSSARY.md (frozen, hand-written, learned)
- kit/GLOSSARY.md (practice = try, told the right answer, every setting nudged; one nudge = one update)
- architecture/model-deep-dive.html line 156-165 (How it learns: question, model tries, compare to the key, nudge the weights, repeat)
- animations/source-g1-3m-s400.json G-B2 updates 24000
- architecture/EXPERTS-TEST-2026-10-09.md lines 36-38 (24,000 updates of 256 rows)
- whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 166 (pool train file 1,418,702 rows)
- whole-model-roadmap/8A-SPEC-2026-10-07.md line 253 (B1: about 3.9 passes, an estimate before the run)
- architecture/EXPERTS-TEST-2026-10-09.md lines 36-38 (AdamW, lr 1e-3, grad clip 1.0, bf16, 24,000 updates of 256 rows)
- architecture/model-deep-dive.html line 165 (older recipe: AdamW, lr 1e-3 with warm-up then cosine fall to 10%, batch 256, bf16, shuffled order, from random start)
- whole-model-roadmap/8A-SPEC-2026-10-07.md line 93 (as q33: AdamW, bf16, batch 256)
- whole-model-roadmap/8A-10M-RESULT-2026-10-08.md line 5 (60M-piece pool: 38% our questions, 62% web fill-in rows)
- whole-model-roadmap/8A-SPEC-2026-10-07.md lines 71-74 (20M/60M/190M word pieces, GPT-2 count; 38% own text = generator rows plus TEACH; 62% web)
- no-hardcoding/LIMIT-COUNTS-2026-10-07.json train rows 200000
- whole-model-roadmap/whole-model-roadmap-2026-10-06.md lines 250, 265, 393 (TEACH 171,940 kept rows, PR #46; written by the 1.2B teacher; no new teacher rows)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 11 (lines 140-146)
- custom_io/g8a/cloze.py lines 12, 21-22 (prompt <= 280 chars with blank; chunk text itself capped at 279; blanked word 3..12 letters; rows made by a script)
- custom_io/models/ledger.py line 140 and tool.py line 125 (w_noop=0.1)
- architecture/B3-GROUP1-BUILD-2026-10-09.md lines 53-60 (teacher forcing: op loss on the gold call each call round and no-call after the last; answer loss from the last call round on)
- architecture/model-deep-dive.html line 165 (older write-up: losses for operation, pointers, answer, spelling)
- architecture/B3-GROUP1-BUILD-2026-10-09.md lines 49-53, 67-71 (running with no teacher vs teacher forcing; gold calls fed in a free run give the same thinker states)
- architecture/FINISHED-MODEL-2026-10-09.md line 143 (62.5% of the skills rows the 3M models trained on have no worked steps)
- architecture/model-deep-dive.html line 165 (only 11 arithmetic families have teacher steps; older B2)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 lines 79-82 (0 of 200,000 over 8 letters in T1SDR runs; B3 caps_b3 writes up to 35 letters, counts longer ones; any count above 0 fails its sealed mark)
- no-hardcoding/PLAN-AND-MARKS-2026-10-07.md sec. 2 (nothing is cut off; every limit listed with rows touched) and no-hardcoding/LIMIT-COUNTS-2026-10-07.json
- whole-model-roadmap/8A-SPEC-2026-10-07.md line 115 (pooled-5 = 6,040 dev rows), lines 84-90 and A1 lines 179-184 (overlap scan; never trained on the dev splits; 3M runs may start before the protected-panel check)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 12 (web pool gate; hash file waits on a Mac job). DATA-POOL-PLAN sec. 6 and 10 is not in the project snapshot and was not read.
- animations/source-g1-3m-s400.json G-B2 updates_per_s 1.02, train_hours 6.51; G-PT updates_per_s 2.8, train_hours 2.38
- whole-model-roadmap/8A-SPEC-2026-10-07.md lines 250-251 (every arm trains at least 24,000 updates of 256 rows)
- big-run/PLAN.md sec. 6 (lines 274-275: about 23 to 32 days, so 3 to 5 weeks on the PC, suggested; not run)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 13 (line 149: 16 rounds cost 1.2-1.9 points on one B2 probe; open risk for 100M) and line 186 (H1 back-propagates through every round with checkpointing)
- custom_io/models/tool_h1.py lines 22-24 (rounds 9..32 gradient-checkpointed: same values, less memory)
- big-run/PLAN.md sec. 6 line 274 (checkpointing recomputes about a third more)
- no-hardcoding/INPUT-UNITS-2026-10-07.md line 39 (16 rounds cost 1.2-1.9 points, one seed; FINISHED cites line 31)
- architecture/model-deep-dive.html line 165 (from random start; nudge the weights, repeat 24,000 times)
- No source lists real before and after setting values, so none are shown.
- see scenes s02, s03, s05, s06, s09, s10 of this chapter
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 6 (B3 group 1's first run comes after G1)

## SCENE NOTES
- s01: The stop switch (H1) is built but never run; the chip says what the part is meant to be (learned). Statuses per part are shown in earlier chapters.
- s02: The question, the wrong try and the needle angles are all made up to show the idea.
- s03: Computed by us: 24,000 x 256 = 6,144,000; 6,144,000 / 1,418,702 = 4.33. The spec's earlier estimate was about 3.9 passes; we show our own division, labelled. Not 6.1 million different questions.
- s04: Warm-up and the fall to 10% come from the older recipe page, which G1 inherits 'as q33'; the warm-up length is not in the sources so the curve is a picture only.
- s05: Shares are of pieces, not of rows. 200,000 is the skills practice set only. TEACHING_TO_TEST_CONTRACT.md is an older design memo, unrelated to these TEACH rows, and was not used.
- s06: FineWeb-Edu = free human-written web text. The example sentence is made up; real rows come from FineWeb-Edu. The 2,000-letter pool (cloze_long, --cloze-long) is built but never run.
- s07: This is the finished design's loss schedule (B3 group 1): built, never run. The 3M test copy was an older design with its own losses.
- s08: Finished-design behaviour (built, never run). The 62.5% is a share of skills rows and comes from FINISHED; the older page speaks of 11 families.
- s09: Present as a rule plus a check, not a guarantee. 8a's B2 had answers cut to 8 letters by a settings bug (8A-10M-RESULT correction); G1 is the fixed re-run. 6,040 = 1360+1200+1360+800+1320 (LIMIT-COUNTS dev splits).
- s10: Only ours has updates=24000 in the run JSON; the plain model's update count is NOT logged. The spec sets 24,000 as the least for every arm, and 2.8 x 3600 x 2.38 = 23,990 is consistent with it (our inference, not a logged count), so the caption says floor, not "both did". Our division 6.51 / 2.38 = 2.74. Older design (calculator inside, 12 rounds).
- s11: The 'third more' is a suggested plan estimate. The 100M fit in 16 GB with 32 rounds is untested.
- s12: All needle positions are decoration.
- s13: Recap only; every number is shown earlier.
