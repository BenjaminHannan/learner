# bm-397 AMEND-general: the no-drop check on GSM8K and MMLU (benchmarks thread, 2026-09-26 ~02:10 UTC)

Registered while the LoCoMo trim run (TF) is in progress on CPU here and before any finaliser output exists,
for LoCoMo or for GSM8K/MMLU. PLAN.md is sealed and unchanged; this adds a third mark.

## Why
Ben's goal (01:45 UTC 09-26) counts problem #4 as solved only if the trim step raises LoCoMo F1 by a mark
registered before running, on a slice not tuned on, with no drop on GSM8K or MMLU. PLAN.md covers LoCoMo only.

## The check
scripts/claude_bm397g_general.py applies the sealed finalise() from scripts/claude_bm397_finalize.py, unchanged
(same model, prompt, 32 new tokens, copy-only rule), to the plain 1B's existing bm-390 run2 replies:
- gsm8k_T.jsonl, sha256 29e814f502a0e5045fa0f63e1151240508d01a156f74f6ba482058fdd82e244e (300 rows);
- mmlu_T.jsonl, sha256 ef1b4e6b2666130679cf6ee92e9c937c17168ad2d5a7dbf12d21b35ba2c9fd62 (300 rows).
The question the finaliser sees is the exact user message the plain 1B answered (claude_bm390.general_prompt).
Items: bm-390's gsm8k300.jsonl (df57d09b…b949) and mmlu300.jsonl (e294f5fc…c049), as in its recounts.
Scored with the sealed bm-390 scorer (gsm_pick, mmlu_pick). The script stops if T does not reproduce 191 and 50.

## Marks (fixed now)
- G1: GSM8K TF right ≥ T right (191 of 300).
- G2: MMLU TF right ≥ T right (50 of 300).
- No-drop passes when G1 and G2 both pass.

## What each outcome means for the hand-off
- PASS on PLAN's F1 and F2, and no-drop PASS: the trim step may run on every answer.
- PASS on F1 and F2, but no-drop FAIL: the trim step ships only on the memory path (questions about earlier
  conversation), and never runs on general or math questions. GSM8K/MMLU replies are then untouched by
  construction, and month-end's joined 0.2c test checks that. The general result is reported as "trim everywhere:
  FAIL".
- F1 or F2 FAIL: nothing ships; problem #4 stays open.

## Report only
Lost and gained items per task; final_kept reasons; median words before and after; GSM8K right under a strict pick
("answer is N" only, no fallback to the last number), for T and TF, because an outside review (Ben, 01:54 UTC)
noted the sealed pick can credit placeholder answers.

## Predictions
- G1 passes: 55%.
- G2 passes: 85%.
- GSM8K median words fall from 103 to under 10: 70%.

## Where it runs
CPU here, with the same MiniCPM5-1B snapshot (revision 87179e5c) used for TF, after TF finishes. About 600 calls.
