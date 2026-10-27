---
name: listener-line
description: Listener thread ("lis-", exps 300-319): our own MiniCPM5-1B LoRA reader emitting typed frames; state as of 2026-09-24 11:40 UTC
metadata:
  type: project
  modified: 2026-09-24T01:53:21.214Z
---
Thread cmsg_01FuvegZXjMmeUzStiEFVnEWAqu8KBs8RUqYCP4Ni32DFW, started 2026-09-23. Ben picked MiniCPM5-1B (not 27B, not the small own ear). 11:24 ruling: save only taught facts for now; at scale-up the reasoner may write confident facts. 17:55: never offer Ben try pages until it speaks fluent conversational English.

**Results**
- lis-300 and lis-301 = registered FAIL on recall (301: panel 35.2% at T 0.995, 0/240 wrong turns, median 1523 ms). No dev T below 0.995 reaches 0 wrong turns.

**lis-302/313-316 (09-24):** per-fact commit 534/771; confirm-at-use 743/771; Ben approved confirm wording "I think you told me X, is that right?"; stack built (claude_lis_stack.py), handed to month-end.

**SCOPE CAP (Ben 10:51 UTC 09-24, via coordinator):** people-facts are "0.01% of the important things". Finish and verify lis-313/314/315/316, hand them to the month-end session, then start NOTHING new on people-fact reading (no lis-317) unless the month-end session asks.
- e2e DEV bank (report): facts saved C 49/131, S/G 34/131; confirms C 75, S 33.

**Rules**
- From lis-302 on, training tasks copy OUT/adapter/ to ~/premonition-models/lis3NN-adapter/ (shared-base mouth).
- 292t needs Mac-only self122_head.pt; cloud smoke stubs route122.

**READING FIX THREAD (Ben 00:31 UTC 09-25, thread cmsg_01FuvegZXjMmeUzStiEFVnEWFFJdDCbBKsf18JUgMQeEYH) supersedes the scope cap for general chat reading.**
- DEV loss count (rent-330-dev arm 330a_chat): 131 facts, 49 saved, 35 held silently ("Okay."), 28 confirm Qs (garbled pronoun owners), 8 whose Qs, 10 missed in multi-fact turns. Asks with all facts saved: right 3/15.
- lis-317-diag queued on main c7122d36a (rent, $1.50): greedy + 8 samples of the lis-301 reader on 194 DEV turns + 959 lis dev rows. Decision rule in artifacts/claude-lis317-20260925/PLAN.md: R0 >=80% -> fix the gate; <60% -> retrain reader on chatty turns.
- 09:50 UTC 09-25: lis-318 = REGISTERED FAIL (artifacts/claude-lis318-20260925/RESULTS.md, main 4bb1668ee): panel R0 B 237 vs A 239/255, saved 132 vs 111, 0 wrong. Panel was already easy for the old reader; loss is the gate + fact shape (DEV: invented 52->18, reading unchanged 88 vs 89). rent try died on empty vast.ai credit. lis-319 queued on BensPC (main 91459c8b5); history data 1,417/1,500 agreed via scripts/claude_lis319_agree.py (plain checker saves 0 back-ref facts; lis-319b fixes that).
- 19:30 UTC 09-25 DIRECTION (Ben: relations ~1% of the work): line moves to plain-sentence memory notes found by meaning (370 road map 'Direction change', main a7862522b); rd-371 general verifier + lis-319 stay (queued BensPC). Overlap partners: Fix sleep, Month-end (0.2 store), Benchmarks, Sleep research.
- 20:30 UTC 09-25: lis-319 (reader sees 6 earlier turns) = REGISTERED PASS, verified (VERIFY.md main 69bce2363): back-refs 93/98 vs 1/98, wrong turns 1/240 vs 11, dev 577 vs 553. Merged sha e688e1b2 at BensPC lis319/work/run/merged + Mac lis319-merged. Gate still holds back 132/197; rd-371 tests that. rd-378 note writer queued BensPC 006c.
- 20:50 UTC: rd-371 checker = REGISTERED FAIL (saved 15 vs 106; VERIFY.md main 3ee53ee7d). Causes: my T rule fell back to the grid max (0.9999) not 0.995; checker trained only on short turns (<=450 chars). One follow-up: checker on long sources + plain sentences, after rd-378.
- 01:30 UTC 09-26: rd-378 note writer = REGISTERED FAIL (main 10f87a9b1): finding test at ceiling (within-dialog search, 150/150 heard-only: my flaw); blind judge 113/360 notes unsupported. Notes = search aids only. Ben picked save bar down (00:19): lis-319c 0.98 vs 0.995 on sealed readpanel319c (239 rows, 424 facts) queued BensPC 006e. GPT save-gate prompt: reviews/gpt6pro-save-gate-2026-09-26.md (unanswered).
- 02:30 UTC 09-26 on: see [[listener-line-overnight]].
