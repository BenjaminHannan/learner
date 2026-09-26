# PASSMARKS k1a and k1b: the creative writer sees the chat; a finished reply is kept whole (Creative answers in chat thread, 2026-09-26)

Fixed before any registered run. Sealed in SEAL.sha256.txt with the code, the judge instructions and the panel's
seal. Registered FAILs stay FAILs.

## Why
0.2c row K1 (artifacts/claude-e2e02c-20260926/VERIFY-02c.md) = FAIL: creative useful 18/50 vs 21 for the plain 1B
(T), bar >= 30/50 and >= T. Counts only (no test item read or quoted): 40 of the 50 idea/uses_facts requests went to
the creative writer (cre333d); X lost only on items whose request came after lead-in turns (useful 4 vs T 9 of 22:
uses_facts 1 vs 3 of 10, routed idea-with-lead-in 2 vs 5 of 9) and was ahead on items without them (14 vs 12 of 28).
On the lead-in items the judge's reasons said off-topic 9 times for X, 3 for T. Code: turn333d
(scripts/claude_cre333d_agent.py) gives the 1B only [system line, current message]; T sees the whole chat.

## The two single changes (each tested against X on its own)
- k1a, scripts/claude_k1a_cre.py: the creative writer also gets this chat's earlier messages (chat338's delivered
  history, last 12, read at turn time), in the form chosen below, and their words join its guard's known words.
  Nothing else changes: routing, system line, notebook facts, 4 samples, guards, trim, fallback, adapter.
- k1b, scripts/claude_k1b_cre.py: a writer sample that ended on its own (end-of-sequence token) is kept whole; only
  a sample the 200-token limit cut off is trimmed back to its last sentence end, as before. Why: trim counts "5." as
  a sentence end, so a finished list whose last item has no full stop loses that item (4 of 40 DEV practice replies
  with the chat ended on a bare list number). Same generate call, same samples; nothing else changes.

## Arms (one rental, one GPU; runner scripts/claude_panel382_run.py unchanged; per-turn seeds identical in all arms)
- X = claude_mu402:build_null02c = 0.2c's build_02c as sealed (cre333d writer), with the Making-things-up thread's
  NullReader (--model NULL) and per-turn seeds, SLEEP02C_ADAPTER = 0.2c's adapter02c.pt (sha256 a33211dc...36f5).
- K = claude_k1a_cre:build_null_k1a = X with the k1a writer. Registered (marks K1a).
- B = claude_k1b_cre:build_null_k1b = X with the k1b writer. Registered (marks K1b).
- KB = claude_k1ab_cre:build_null_k1ab = X with both changes. Report only: what Month-end would ship.
- KB0 = KB without the sleep adapter (base 1B). Report only: does the adapter help or hurt creative replies?
- T = twin b (plain MiniCPM5-1B, whole chat, greedy, thinking off), as in 0.2c.
Disclosed difference from 0.2c: the NullReader saves nothing, so the writer's notebook facts are empty in every
writer arm (0.2c's lis-319 reader saved on 5 of 32 lead turns). This can only make X's uses_facts replies a little
worse than 0.2c's X; it is the same for all writer arms except that K and KB can read the facts in the chat.

## Panel
k1apanel (TEST-ONLY): 60 items written blind by a separate agent from the 382 creative spec, audited blind by a
third agent, held in /mnt/project-files/escrow-k1a/creative; the registered file is items_v2.jsonl, copied unread to
artifacts/claude-k1apanel-20260926/creative/items.jsonl and sealed. Counts (writer's check): 20 idea with 1 lead-in
turn, 20 idea with 0, 20 uses_facts (1 teach turn: 6, 2: 8, 3: 6). Lead items = the 40 with any earlier turn.
The builder of k1a never reads it.

## Judging (artifacts/claude-k1a-20260926/JUDGE-k1a.md)
All six arms' replies to the last request of every item, shuffled together under neutral ids by the runner's
--score step (seed 3822), then cut to one line per distinct reply to each item by claude_k1a_score.py --dedupe
(seed 3823): arms that wrote the same reply to the same item share one verdict, so judge noise can't split them.
Judges 1 and 2 (blind Opus agents, private folders) judge every line; judge 3 decides the lines they split on
(useful, or made-up >= 1). Keys applied by scripts/claude_k1a_score.py. A blind recount (a separate agent re-running
the scorer from the files) before anything is reported.

## Marks for k1a (K vs X; PASS = all three)
| Mark | What | Bar |
|---|---|---|
| K1a.1 | useful on the 40 lead items, K - X; and a one-sided exact sign test on the items where exactly one of K, X is useful | >= +6 and p <= 0.05 |
| K1a.2 | replies with a made-up fact about the user (all 60), K vs X | K <= X + 2 |
| K1a.3 | fallback lines ("I don't have a good idea for that yet...") on the last request, K vs X | K <= X + 2 |

## Marks for k1b (B vs X; PASS = all three)
| Mark | What | Bar |
|---|---|---|
| K1b.1 | last replies ending on a bare list number (code: a last line that is only "5." or "5)"), B vs X | B = 0, or B < X / 4 |
| K1b.2 | useful on all 60, B vs X (B and X share every sample, so they differ only where a reply was kept whole) | B >= X |
| K1b.3 | made-up replies and fallback lines, B vs X | each B <= X + 2 |
k1b claims a fix without a usefulness cost, not a large gain: DEV suggests only a few of 60 replies change, too few
for a sign test to reach p <= 0.05, so the sign test (B-only vs X-only useful) is reported, not required.

## Report only (never part of either verdict)
K - X on the 20 no-lead items (same prompt by construction, so K = X there unless the GPU is not deterministic);
K - T on the lead items; useful per kind; judge 1-2 agreement; KB vs K and B; KB vs KB0 (the adapter); and the
**K1 line on this panel** for every writer arm: useful on all 60 >= T's AND >= 36/60 (K1's 30/50 rate). The K1 line
is the owner problem's bar: k1a and k1b can pass their own marks while K1 stays open.

## Proved wrong
K1a.1 failing means the missing chat is not what costs the writer on lead-in requests (or not enough to matter):
the next suspects are the writer's pick rule (first of 4 samples that passes the guards) and the sleep adapter (see
KB vs KB0). K1b.1 failing means the cut-off items don't come from trim; K1b.2 failing (B < X) means trim was
protecting usefulness (a reply that ended on its own but badly) and the finished-reply rule is wrong.

## Which form of the chat (committed to main in cdd6701ac at 14:45 UTC, before the DEV judges saw the second batch)
Two forms were tried on the 40 DEV practice chats (artifacts/claude-k1a-dev-20260926, readable): W1 = the chat as
chat messages (user and assistant turns), W2 = only the user's earlier words, quoted in the system line. The 333e
E.2 test (09-25) gave a writer the chat as messages and was proved wrong (7 -> 6 of 40): the 1B copied earlier
"Got it." replies. W2 cannot copy an assistant line. Rule, set before W2 was judged: K uses W2 if W2's useful count
on the DEV lead-in chats (mean of two blind judges, judged in the same batch as W1; the committed draft said "20",
a miscount: DEV has 32 lead-in chats and 8 without) is at least W1's minus 1;
otherwise K uses W1.

Result on DEV and the choice (two blind judges, a third on splits; DEV only, readable, no test item seen): on the 32
lead-in chats W1 and W2 were each useful 11 times, so the rule above picks W2. But W2's replies stated a wrong or
made-up fact about the user 8 times against W1's 2 (both judges agreed on all 10): quoted in the system line, the
user's words got misread (numbers changed, the user cast as someone else in their own story). That would likely fail
K1a.2 (made-up K <= X + 2). The rule looked at usefulness only, which was an oversight, so it is overridden in the
open: **K uses W1, the chat as messages** (claude_k1a_cre.install_creative_k1a, unchanged). No W1 reply on DEV copied
an earlier assistant line (the 333e E.2 failure). Limit: under the NullReader the lead turns are answered by the
chat writer, never by the reader's "Got it"-style acknowledgements, so this run cannot show whether the writer
copies those in the full build; the full build's history can hold them. KB uses the same W1 form (claude_k1ab_cre).

## Expected (said before running; DEV practice, no sleep adapter, 40 chats: 32 with a lead-in, 8 without)
- Useful on the lead-in chats: W1 (= K's writer) 10 of 32 in the first batch and 11 of 32 in the second; W0 (= X's
  writer) 2 of 32; plain 1B 9 of 32. Scaled to the 40 lead items: K - X about +8 to +11, so K1a.1 should pass.
- Made-up replies (all 40): W1 2, W0 3, plain 1B 2. K1a.2 should pass.
- Fallbacks: none in any DEV arm. K1a.3 should pass.
- k1b: 3 of 40 W0 replies ended on their own and were changed by trim; kept whole, 1 of the 3 became useful (0 were
  before). Bare list endings: W0 1, W3 (= B's writer) 0. K1b should pass, with a small gain.
- The K1 line (>= 36 of 60 and >= T): not expected. On DEV the writer with the chat is useful 12 of 40 and the plain
  1B 12 of 40, far under 60%. Closing the bar needs the next step (pick the best of the 4 drafts, k1c).
