# ch03 notes (auto-generated from ch03.json by the lead, 10-09; picture review is separate)

Title: The reader: giving every letter a meaning  |  scenes: 16

## SOURCES (distinct src paths)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 1 and sec. 2 (Reader row)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Gemma adapter row, line 32)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row, line 31)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row, line 33)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 and sec. 5
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (EGE +2.67, 6 of 6 seeds)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (leak mean 6.59 against a limit of 4.62)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 1
- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 3
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (number finder row, line 89; ledger.py:206)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (place code row; group 2 replaces the count)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 110-112, 18.09 vs 1.40)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 5 (lines 120-122; labelled suggested)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 7 Q2 (lines 173-176; 200 per task, bAbI test split)
- architecture/TOKENS-EXPERIMENT-2026-10-09.md line 26 and line 44 (EGE 6 seeds 75.88-77.19; plain B2 73.00-74.74)
- architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 1 (why, in plain words)
- architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 2 (8,192-token model card)
- architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 2 table, rows 1 and 2 (my count 10-09, Gemma tokenizer.json at 914f7f89)
- architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 8 (no build at 10:15 AM ET; conflict)
- custom-io/g8a/caps_b3.json (max_prompt 2000)
- custom-io/g8a/caps_b3.json (n_num 240)
- custom-io/g8a/caps_g.json (max_prompt 280)
- custom-io/g8a/caps_g.json (n_num 91)
- custom-io/models/eg.py line 6 (text backbone 271,002,624 = 134,217,728 word table + 136,784,896 transformer and its 512 to 768 projection)
- custom-io/models/ledger.py lines 280-294 (read(): eg_proj(ln_eg(H)) passed as extra)
- custom-io/models/ledger.py lines 284-294 (eg_proj applied to Gemma's state)
- custom-io/models/reader.py line 5 and lines 46-63 (two blocks, kernel 5, receptive field plus or minus 4)
- custom-io/models/reader.py lines 1-3 (docstring: E_char + E_pos + E_place) and lines 72-80 (order: char + pos, then place, then extra added)
- custom-io/queue_local/8aTK-pc-3.txt (job file exists; no result file found)
- custom-io/train.py lines 229-230 (tok_think code present)
- custom_io/results/44-egr-s200/EGR_s200/RESULT.json (eg_embed true, reader_layers 0: Gemma plus letters, no window)
- custom_io/results/46-r0ege-s200/R0_s200/RESULT.json (reader_layers 0, no eg_embed: letters alone, no window)
- custom_io/results/RESULTS-EG2.md lines 120-121
- custom_io/results/RESULTS-EG2.md lines 120-121 (in-distribution cipher_map; copies 200 and 201)
- kit GLOSSARY.md (shared translator picture)
- whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 18 (6-seed confirm on q33 data, +2.67, ahead on 6 of 6)

## NUMBERS ON SCREEN (numbers found in each scene text; src list for that scene)
- s01: (none)  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 1 and sec. 2 (Reader row); kit GLOSSARY.md (shared translator picture)
- s02: 12  <- architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 1 (why, in plain words)
- s03: 1, 100, 279, 3, 3.08, 3.1, 4.27, 4.3  <- architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 2 table, rows 1 and 2 (my count 10-09, Gemma tokenizer.json at 914f7f89)
- s04: 256, 69, 768  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row, line 31); architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 1
- s05: 134,217,728, 136,784,896, 271,002,624, 8,192  <- custom-io/models/eg.py line 6 (text backbone 271,002,624 = 134,217,728 word table + 136,784,896 transformer and its 512 to 768 projection); architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Reader row); architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 2 (8,192-token model card)
- s06: 196,864, 256, 393,728, 512, 768  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (Gemma adapter row, line 32); custom-io/models/ledger.py lines 284-294 (eg_proj applied to Gemma's state)
- s07: 1, 2,000, 280, 294, 3, 5, 72, 80  <- custom-io/models/reader.py lines 1-3 (docstring: E_char + E_pos + E_place) and lines 72-80 (order: char + pos, then place, then extra added); custom-io/models/ledger.py lines 280-294 (read(): eg_proj(ln_eg(H)) passed as extra); custom-io/g8a/caps_b3.json (max_prompt 2000)
- s08: 0.7, 1, 2, 2,624,512, 2.6, 256, 4, 512, 656,896  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row, line 33); custom-io/models/reader.py line 5 and lines 46-63 (two blocks, kernel 5, receptive field plus or minus 4)
- s09: 0, 1, 10%, 100, 100%, 12.5, 2, 2.5, 5.0, 95.0, 97.5  <- custom_io/results/RESULTS-EG2.md lines 120-121 (in-distribution cipher_map; copies 200 and 201); custom_io/results/44-egr-s200/EGR_s200/RESULT.json (eg_embed true, reader_layers 0: Gemma plus letters, no window); custom_io/results/46-r0ege-s200/R0_s200/RESULT.json (reader_layers 0, no eg_embed: letters alone, no window)
- s10: 1%, 2,000, 280, 3, 32%, 4,000, 7  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 7 Q2 (lines 173-176; 200 per task, bAbI test split)
- s11: 1, 1,, 16, 2,, 240, 3, 4, 91  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (number finder row, line 89; ledger.py:206); custom-io/g8a/caps_g.json (n_num 91); custom-io/g8a/caps_b3.json (n_num 240)
- s12: 1, 12, 3, 5, 7, 7,  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 5 (lines 120-122; labelled suggested); architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 3
- s13: 100, 116, 118, 2.67, 200, 201, 202, 207, 3, 5, 5,, 6, 6,040, 73.0, 74.7, 75.9, 77.2  <- whole-model-roadmap/8AG-GEMMA-GROWTH-SPEC-2026-10-08.md line 18 (6-seed confirm on q33 data, +2.67, ahead on 6 of 6); architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (EGE +2.67, 6 of 6 seeds); architecture/TOKENS-EXPERIMENT-2026-10-09.md line 26 and line 44 (EGE 6 seeds 75.88-77.19; plain B2 73.00-74.74)
- s14: 1.40, 18.09, 2, 200,, 4.62, 6.59  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 line 31 (leak mean 6.59 against a limit of 4.62); architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 2 (lines 110-112, 18.09 vs 1.40)
- s15: 12, 3, 3.1, 5.4, 8  <- architecture/TOKENS-EXPERIMENT-2026-10-09.md sec. 8 (no build at 10:15 AM ET; conflict); custom-io/train.py lines 229-230 (tok_think code present); custom-io/queue_local/8aTK-pc-3.txt (job file exists; no result file found)
- s16: 100, 2.5, 4, 5.0  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 and sec. 5; custom_io/results/RESULTS-EG2.md lines 120-121

## ILLUSTRATIONS (scenes that say picture-only / made-up in their text)
s01, s02, s11, s15

## OPEN QUESTIONS
- Picture review of the contact sheets: see the lead report. No checker (VERIFIER-GUIDE) run yet.
