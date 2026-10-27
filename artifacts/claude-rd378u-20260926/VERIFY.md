# rd-378u = PASS (blind recount by the Trustworthy notes thread, 2026-09-26 17:30 UTC)

Source: origin/builder-outbox runs/rent-rd378u (rc=0) and artifacts/claude-rd378u-20260926/ (copied here; sha256
notes_confirm.json 106168ba..., ranked_turns.jsonl 785c9c9a..., both equal to the rental's copy-back hashes).
Recount from notes_confirm.json alone (not from RESULTS.md), categories 1-4, 772 questions on LoCoMo conversations 5-9
(PRACTICE, "after using LoCoMo for development"; no text read or printed):

| Mark | Bar | A (heard only, store v3) | B (store v4 + rd-378 notes) | Verdict |
|---|---|---|---|---|
| U1 | B any@10 >= A + 5 points | 489/772 (63.3%) | 585/772 (75.8%), +12.4 | PASS |
| U2 | no category > 3 points below A | cat 1 85/140, 2 109/164, 3 18/45, 4 277/423 | +7.9, +10.4, +22.2, +13.7 | PASS |
Proved-wrong clause (B <= A + 1): not triggered. Lines shown @10: 7,720 in both arms; 6,297 of B's reached through a note.
Notes 2,866 over 3,122 turns (0.92 per turn), 16 unparsed turns (0.5%). ranked_turns.jsonl: 1,544 rows (772 x 2 arms).
Writer: merged sha256 dbcc8db5... rebuilt on the rental (match). Cost ~$0.39 (0.773 h x $0.5037/h).

## What it means
Shown: on five chats no notes decision had used, the rd-378 writer's notes, searched as pointers to the raw lines
through store v4's defaults, put an evidence line in the top 10 for 96 more of 772 questions, at the same number of
lines shown. This confirms rd-378L's gain (+11.5 on conversations 0-4) on unseen chats.

## What happens next (PASSMARKS "PASS", as changed by the 16:53 ruling)
- Store v4 (scripts/claude_ep382_store_v4.py, code only) is offered to Month-end for 0.2d's recall.
- The rd-378 writer itself stays out of every build: it learned from Opus-written notes (Ben's 16:39 "Use GLM" rule;
  Thread manager ruling 16:53). Its figure here, R = 585/772, is the bar the Claude-free writer must reach within 2
  points (rd-378g G2: >= 73.8%), and G1 needs >= A + 5 points (>= 68.3%) on the same questions.
