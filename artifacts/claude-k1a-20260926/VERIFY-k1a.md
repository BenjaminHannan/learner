# VERIFY k1a and k1b (Creative answers in chat thread, written 2026-09-26 16:17 UTC)

**k1a (the creative writer sees the chat) = PASS. k1b (keep a finished reply whole) = FAIL, on K1b.1 only.**
The K1 line (the owner problem's bar) is still not met: K is useful on 28 of 60 against 36 needed; plain 1B 24.

Run: rent-k1a, one RTX 5090, all six arms 60/60 items, seals, tests and V1 lines as registered, $0.30 of $0.80
(RESULTS-rent.md on builder-outbox). Judging as registered (JUDGE-k1a.md): 360 replies deduplicated to 206 distinct
lines (84 lines shared by two or more arms), judges 1 and 2 on all 206 (agree on useful 201, on made-up 199), judge 3 on
the 12 split lines (judges/). Scored with scripts/claude_k1a_score.py (RESULTS-k1a.json) and recounted blind by a
separate agent with its own script (judges/recount_k1a.py): every count below agrees. Nobody who built k1a read a
panel item or a reply.

| Arm | Useful /60 | Lead /40 | No-lead /20 | Made-up | Fallbacks | Bare list endings |
|---|---|---|---|---|---|---|
| X (0.2c writer) | 15 | 7 | 8 | 5 | 0 | 2 |
| K (k1a) | 28 | 20 | 8 | 5 | 0 | 2 |
| B (k1b) | 15 | 7 | 8 | 5 | 0 | 1 |
| KB (both, report only) | 28 | 20 | 8 | 5 | 0 | 1 |
| KB0 (both, adapter off, report only) | 21 | 10 | 11 | 4 | 0 | 0 |
| T (plain MiniCPM5-1B) | 24 | 17 | 7 | 3 | 0 | 0 |

## k1a marks (K vs X)
- K1a.1 lead items: K 20, X 7, +13; K-only 13, X-only 0, one-sided sign test p = 0.0001. Bar >= +6 and p <= 0.05: PASS.
- K1a.2 made-up replies: K 5, X 5. Bar K <= X + 2: PASS.
- K1a.3 fallbacks: 0 and 0: PASS.
Expected before running (DEV): K - X about +8 to +11 on 40 lead items. Got +13.

## k1b marks (B vs X)
- K1b.1 bare list endings: B 1, X 2. Bar B = 0 or B < X / 4: **FAIL**.
- K1b.2 useful: B 15, X 15 (B changed 4 of 60 replies; none changed a verdict). Bar B >= X: pass.
- K1b.3 made-up 5 vs 5, fallbacks 0 vs 0: pass.
What failed (counts only, no reply read): of X's 2 bare endings, k1b fixed 1. The other is the same text in B and X
(26 words, far under the 200-token limit), so it is not a cut-off sample that trim cut back; inferred: the 1B itself
ended there, which keeping a finished reply whole cannot fix. The proved-wrong clause applies in part: trim made only
some of the cut-off list items. Registered FAIL stays a FAIL. k1b is not needed for anything that follows.

## Report only
- K - X on the 20 no-lead items: 0 (identical prompts and seeds, as designed).
- K - T on the lead items: +3 (20 vs 17). Over all 60: K 28, T 24.
- The sleep adapter helps the creative writer: KB 28 vs KB0 21 (KB-only 11, KB0-only 4).
- K1 line: no arm reaches 36 of 60. K and KB reach T's 24.

## What this means for the build and what is next
k1a is the talker change ADDENDUM-12 names for 0.2d ("k1a for creative"). K1 stays open: even the plain 1B is useful on
only 24 of 60. On DEV practice, at least one of the writer's 4 drafts was useful on 26 of 40 chats while the first was
useful on 12, so the next test (k1c) has the 1B choose among its own drafts by how much each depends on the
conversation, with no hand-written rules (Redirect). It runs on the fresh 100-item k1cpanel against plain MiniCPM5-1B
and Qwen3.5-2B.
