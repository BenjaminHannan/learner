# lis-319c: lower the save bar from 0.995 to 0.98 (one change on top of lis-319)

Thread "Fix: reading facts from chat". Written 2026-09-26 00:25 UTC, before readpanel319c was written, sealed or run.
Why: on lis-319's practice dev (1,311 messages, 1,053 facts) bar 0.98 saves 771 facts vs 611 at 0.995 with the same
3 wrong messages (recounted, artifacts/claude-lis319-20260925/VERIFY.md). The 0.98 was picked by looking at that dev
set, so it must pass a fresh sealed test. Ben's decision card (00:20 UTC) recommends this test.

## The one change
The save bar on the lis-319 reader's min-token confidence: A = 0.995 (live), B = 0.98. Same reader (lis-319 merged,
sha256 e688e1b2...6a76), same reads (the panel is read ONCE; both arms score those same reads), same compiler,
same per-fact release (claude_lis318_score via claude_lis319_score.py).

## Registered test
artifacts/claude-readpanel319c-20260926 (TEST-ONLY; 30 dialogs x 8 user turns; everyday chat with long multi-fact
messages, back-references and no-save turns; written blind by a separate agent, blind second labeller, sealed before
any run). History built by scripts/claude_lis319_rows.py.

## Marks (fixed now)
| Mark | Bar |
|---|---|
| S1 more saved: B saved_right | >= A's + 25 |
| S2 no less safe: B wrong_turns | <= A's + 1 AND <= 3 of 240 |
| S3 no invention: B nofact_rows_with_save | <= 1 |
PASS = all three. Proved wrong: B wrong_turns >= A's + 3 (0.98 lets in real errors that practice data hid).
Report only: held_right both arms, per-kind counts, median ms.
