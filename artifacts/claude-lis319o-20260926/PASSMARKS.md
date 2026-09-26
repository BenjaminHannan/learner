# lis-319o: the compiler accepts an owner named earlier in the chat (one change, no retraining)

Thread "Fix: reading facts from chat" (problem #1, saves too few). Written 2026-09-26 15:54 UTC, before the test panel exists.

## Why
lis-319k's diagnosis (artifacts/claude-lis319k-20260926/VERIFY.md): of 60 corrections, 16 (lis-319) / 14 (lis-319f) that
the reader did read were thrown out by claude_lis300_compiler.check_fact as owner_not_span, because the owner was named in an
earlier turn and the check only looks in this turn and the previous assistant reply. The reader is shown 6 earlier turns,
so the notebook can point at where the owner was written.
Dev (lis-319 dev reads, 1311 rows; claude_lis319o_owner.py dev): 60 owner_not_span facts, 51 pass the new check,
18 of them saved at 0.995 of which 17 match the gold frame exactly. Dev bank (69 teach/correct turns): saved 34 -> 36.

## The one change
scripts/claude_lis319o_owner.py: when check_fact says owner_not_span and the owner occurs as whole words (exact case) in the
row's history (earlier user turns and replies, as given to the reader), the fact goes on to the usual value and
owner-equals-value checks. Nothing else changes: reader, prompt, bar (0.995), all other checks.

## Test
A fresh TEST-ONLY panel, readpanel319o, written after this file by a separate agent, focused on turns whose owner is named
only earlier (new facts and corrections), plus lookalike turns that mention earlier-named people without a savable fact
about them (questions, plans, doubt, other people's claims, and ambiguous "she"/"he" when two people could be meant).
Blind second labeller + adjudicator as readpanel319k. Read ONCE by lis-319f (sha 970ef0ac...4f9b) on the Mac.
OLD = that read with the current compiler (claude_lis319k_score.py final); NEW = the same read with the change
(claude_lis319o_owner.py final). NEW's saves are a superset of OLD's; pairs from claude_lis319o_owner.py pairs cover both.
Two blind Opus judges (JUDGE_SAME.md), one-to-one whole-claim credit.

## Marks (NEW vs OLD, T 0.995)
| Mark | Bar |
|---|---|
| O1 | saved_right_full: NEW >= OLD + 8 |
| O2 | saved_wrong_full: NEW <= OLD + 2 |
| O3 | lookalike_saves: NEW <= OLD + 1 |
PASS = O1 and O2 and O3. Proved wrong: the O1 gain <= 2.
INCONCLUSIVE if the panel has fewer than 40 current facts with needs_history, or the read covers fewer than 230 rows.
Report only: correction_right, stale_saves, OLD vs NEW.
If it passes, the rule is not shipped by hand: the owner-in-history case becomes the compiler's documented contract for
the next retrained reader, and training rows are checked against it.
