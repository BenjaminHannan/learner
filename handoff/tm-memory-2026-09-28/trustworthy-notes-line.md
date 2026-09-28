---
name: trustworthy-notes-line
description: Trustworthy notes (problem 2) 09-27 22:43 UTC: rd-378g Claude-free writer G PASS G1-G5 (9d7a51c0f); G 49.2% vs R 50.9% unsupported; next = G into build notes slot; then rd-378k
metadata:
  type: project
  modified: 2026-09-27T22:44:00.000Z
---
Thread root cmsg_01FuvegZXjMmeUzStiEFVnEWC34DYnYJykVs4PVeJrQHpM (session cse_01RNDQzoVcF2DgnSFDfkye9f). Problem 2: notes the build writes can't be trusted.

- Shown: notes searched as POINTERS to raw lines help recall. rd-378L PASS (LoCoMo 0-4 any@10 496 -> 583/759, 274fae558); rd-378u PASS on 5-9 via store v4 (489 -> 585/772, f4edf55ac). Store v4 = scripts/claude_ep382_store_v4.py (answers read raw lines only).
- bm-398n (15d492d52): answers from turns+notes 269 vs 252/759, p 0.19 = FAIL not proved wrong.
- rd-378 writer (sha dbcc8db5) learned from Opus notes: out of every build (Ben 16:39, TM 16:53). Its 585/772 is the bar.
- Plan: rd-378g (854f21660 + addenda A, B 3d27fbc23) = writer retrained from plain 1B on GLM chats+notes with GLM grades (G1 >= heard+5, G2 >= 585-2). Then rd-378k (3316b3ba2 + addenda) = cut-only step on the GLM writer's drafts, blind panel notepanel378k (deab5fa31).
- GLM grader v2/v3 gates (gate3, gate3oc, gate3low) all NO VERDICT, never read (J ab315dfe6).
- 09-27 03:47 Ben: "just have luna rewrite all the training data". SEALED e10b39b4b: rd-378k PASSMARKS-K (grader = Luna) and rd-378g ADDENDUM-I (Luna writes 21 batches).
- 09-27 07:30 writer pilots; trap: match processes by executable, not by prompt text (000-rescue3 c0a338df0).
- 09-27 10:00 gate3luna FAIL, PROVED WRONG (38ad6d0a3): agree 78.4% (bar 85), Luna too strict; no Luna grade trains. ADDENDUM-K SEALED 01d3582ee: keep-all + G5 paired blind judges on 43 dialogs, G share <= R + 5. Kits: handoff/kit/rd378gv (vast).
- 09-27 20:03 RESULT (71d3e8c10 RESULTS.md + vast/): one RTX 5090, $0.87, all steps rc=0. any@10 G 577, A 489, R 585 of 772: G1 +11.40, G2 -1.04, G3 all cats above A, G4 0.16% unparsed = G1-G4 PASS. G5 NOT scored: vast/g5/notes_G.jsonl + notes_R.jsonl (504 lines each, R arrived so no 57% fallback) wait for g5 make, two fresh blind judges (items.jsonl + JUDGE_NOTES.md only, never map.json), g5 score. Overall PASS needs G5. Ben stopped all threads 19:57; resume only on his word.
- 09-27 22:41 G5 PASS (Ben's cloud chat, 9d7a51c0f RESULTS-G5.md; TM verified vs recount.txt): key unsupported G 153/311 49.2%, R 203/399 50.9%; bootstrap G-R -7.6..+4.0 (43 dialogs, report only); G 0.73 notes/turn vs R 0.93. rd-378g PASS G1-G5. PASS = 'no less true than rd-378 writer', never 'trustworthy'. Next (fixed by ADDENDUM-K): G offered for the build's notes slot as search aid only, disclosed shares; rd-378k may use A = G but still needs a passing grader. TM asked Ben 22:43 whether to write the build-slot prompt.
Related: [[listener-line]], [[notebook-line]], [[benchmarks-line]].
