# ch05 notes (auto-generated from ch05.json by the lead, 10-09; picture review is separate)

Title: Asking the calculator for help  |  scenes: 15

## SOURCES (distinct src paths)
- GLOSSARY.md (call writer and calculator pictures)
- GLOSSARY.md (pooled-5: 6,040 kept-aside questions; chain-5: 1,000 multi-step questions)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row), sec. 5 item 6 (Gemma and calculator never run together), sec. 3 (any-round built, untested)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: leak mark cleared 8:21 AM ET 10-09)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: size 0)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (call writer row)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row) and sec. 5 item 5 (replies read by the letter window only)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (parts table) and sec. 4 (rules dated 10-07)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-62)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-65) and sec. 7 Q1 (answered 9:30 AM ET 10-09)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (21 slots, last digit first) and step 4 (add 7 3 = 10)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (lines 46-50): worked Tom example and copy rule
- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 steps 2-4 (lines 46-53): worked Tom example
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code only as a tool)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code table: op word, number finder, span copy rules, last letter first; group 2 row)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (last letter first row)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (span copy row): 98% of written operands and 91.5% of answers on every T1SDR seed
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (swap holds on 5 of 6 copies; checkpoint lost)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1: chain-5 99.6-99.8, mean 99.72; B2 99.4-99.7
- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (6 copies; mark 5 on 5)
- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 201): mark 5 values for seeds 200-204; seed 205 unscored
- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 202): donor 5.59/5.15/5.59/5.07/5.00/5.59; B2 3.09-3.75; loops:0 on s201 12.94 vs B2 10.81
- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 203): owner cleared mark 4, 8:21 AM ET 10-09
- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (lines 198-205): pooled-5 +0.62, CI -0.23 to +1.46; 6 of 6 copies within 1.0; tool off 0.0
- custom_io/g8a/configs.py:95 (B3_G1 gap_p=0.25)
- custom_io/models/b3.py:26 (TAPE_MIN = 16)
- custom_io/models/b3.py:6-10 (any_round, gap_p, think-only rounds 0-2)
- custom_io/models/ledger.py:206 (number finder regex)
- custom_io/models/progparse.py:12 (NOOP plus 8 operations)
- custom_io/models/progparse.py:12 and :23-33 (ex: exact semantics; DIV only when exact)
- custom_io/models/progparse.py:23-33 (ex)
- custom_io/models/tool.py:15 (op head on control token 0; NOOP = no call)
- custom_io/models/tool.py:155-170, 368-374 (reply read as a short string; thinker keeps its vectors)
- custom_io/models/tool.py:188, 191-197, 222-247 (last letter first; span copy rules)
- custom_io/models/tool.py:222-247 (span copy: one letter left until the learned stop head says stop)
- custom_io/models/tool.py:338, 350 (call timing; no call after round 8 in the tested code)
- custom_io/models/tool.py:84 (CELLS = 21, with its comment: longest int64 string 20 characters, then end mark)
- custom_io/models/tool.py:95-103 (calc)
- custom_io/models/tool.py:95-103 (calc: '?' when it cannot run)
- example results computed by hand from those lines, with made-up numbers 12 and 5

## NUMBERS ON SCREEN (numbers found in each scene text; src list for that scene)
- s01: 7  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (parts table) and sec. 4 (rules dated 10-07)
- s02: 12, 5, 7  <- GLOSSARY.md (call writer and calculator pictures); architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code only as a tool)
- s03: 0, 8  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (call writer row); custom_io/models/tool.py:15 (op head on control token 0; NOOP = no call); custom_io/models/progparse.py:12 (NOOP plus 8 operations)
- s04: 0, 1, 1,, 12, 17, 2, 5, 60, 7  <- custom_io/models/progparse.py:12 and :23-33 (ex: exact semantics; DIV only when exact); custom_io/models/tool.py:95-103 (calc: '?' when it cannot run); example results computed by hand from those lines, with made-up numbers 12 and 5
- s05: 1, 12, 2, 3, 4, 91.5%, 98%  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (lines 46-50): worked Tom example and copy rule; architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (span copy row): 98% of written operands and 91.5% of answers on every T1SDR seed; custom_io/models/tool.py:222-247 (span copy: one letter left until the learned stop head says stop)
- s06: 0, 1, 10, 11, 15, 20, 21, 3, 64, 7  <- custom_io/models/tool.py:84 (CELLS = 21, with its comment: longest int64 string 20 characters, then end mark); architecture/FINISHED-MODEL-2026-10-09.md sec. 3 step 2 (21 slots, last digit first) and step 4 (add 7 3 = 10); architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (last letter first row)
- s07: 0, 12, 5, 7  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: size 0); custom_io/models/tool.py:95-103 (calc); custom_io/models/progparse.py:23-33 (ex)
- s08: 10, 12, 2, 3, 3,, 5, 5,, 7, 7,  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 steps 2-4 (lines 46-53): worked Tom example; architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (letter window row) and sec. 5 item 5 (replies read by the letter window only); custom_io/models/tool.py:155-170, 368-374 (reply read as a short string; thinker keeps its vectors)
- s09: 1,, 2,, 3, 32, 4, 5, 6, 7, 8, 8,, 9  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-62); custom_io/models/tool.py:338, 350 (call timing; no call after round 8 in the tested code)
- s10: 0,, 1, 16, 2, 32, 4  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 3 (lines 60-65) and sec. 7 Q1 (answered 9:30 AM ET 10-09); custom_io/models/b3.py:6-10 (any_round, gap_p, think-only rounds 0-2); custom_io/models/b3.py:26 (TAPE_MIN = 16)
- s11: 108, 12, 2, 4, 5, 8, 8,  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (hand code table: op word, number finder, span copy rules, last letter first; group 2 row); custom_io/models/ledger.py:206 (number finder regex); custom_io/models/tool.py:188, 191-197, 222-247 (last letter first; span copy rules)
- s12: 0.0, 0.23, 0.62, 1,000, 1.0, 1.46, 13, 3, 5, 5,, 6, 6,040, 99.4, 99.6, 99.7, 99.72, 99.8  <- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (lines 198-205): pooled-5 +0.62, CI -0.23 to +1.46; 6 of 6 copies within 1.0; tool off 0.0; architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1: chain-5 99.6-99.8, mean 99.72; B2 99.4-99.7; GLOSSARY.md (pooled-5: 6,040 kept-aside questions; chain-5: 1,000 multi-step questions)
- s13: 1, 12, 200, 205, 5, 6, 99, 99%, 99.28, 99.87  <- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 201): mark 5 values for seeds 200-204; seed 205 unscored; architecture/FINISHED-MODEL-2026-10-09.md sec. 5 item 1 (swap holds on 5 of 6 copies; checkpoint lost)
- s14: 0,, 10.81, 100, 12.94, 200, 201, 205, 3.09, 3.75, 4, 5, 5.00, 5.07, 5.59, 9  <- architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 202): donor 5.59/5.15/5.59/5.07/5.00/5.59; B2 3.09-3.75; loops:0 on s201 12.94 vs B2 10.81; architecture/MARKS-D0-T1-2026-10-07.md Record 13 (line 203): owner cleared mark 4, 8:21 AM ET 10-09; architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row: leak mark cleared 8:21 AM ET 10-09)
- s15: 3  <- architecture/FINISHED-MODEL-2026-10-09.md sec. 2 (calculator row), sec. 5 item 6 (Gemma and calculator never run together), sec. 3 (any-round built, untested); architecture/MARKS-D0-T1-2026-10-07.md Record 13 (6 copies; mark 5 on 5)

## ILLUSTRATIONS (scenes that say picture-only / made-up in their text)
s03, s04, s10

## OPEN QUESTIONS
- Picture review of the contact sheets: see the lead report. No checker (VERIFIER-GUIDE) run yet.
