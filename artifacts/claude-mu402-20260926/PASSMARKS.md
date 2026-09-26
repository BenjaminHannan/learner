# mu-402: does 0.2c's sleep adapter make chat replies make up things about the user? (marks fixed before any run)

"Making things up about you" thread, 2026-09-26. Owner of 0.2c's rows S1 (made-up facts about the user) and H3
("I don't know" when never told). Code: scripts/claude_mu402.py (arms), scripts/claude_mu402_judge.py (packets,
counts, marks). Dev panel: artifacts/claude-mu402-20260926/devchat (readable DEV data, written blind by a separate
agent from 382-panels-spec with teach/ask turns removed).

## Why
0.2c row S1 failed: X made up more about the user than the plain twin (26 vs 16; VERIFY-02c.md). A blind auditor
(counts only; chatpanel02c stays unread by builders) found that the extra claims in X are all in ordinary 1B-written
chat replies, not in the notebook's template lines: 17 non-template claims for X vs 7 for G in the same judged
chats, the template ones byte-identical in both. Most are the reply assuming a feeling or situation the user never
described (feelings and advice turns); a few misread who did what or the user's numbers. Between X and G, the only
thing that changes those 1B calls is the sleep adapter (LoRA r16 on q/k/v/o, trained by three copy-practice nights,
loaded into the one shared 1B). X's feelings and advice replies are also longer, even on a chat's first turn
(51 vs 38 words on feelings). Suggested, not shown: 0.2c's chat sampling was not seeded, so part of 17 vs 7 may be
luck.

## The one change
- **A (control)** = 0.2c's X chat path: claude_e2e02c:build_02c with SLEEP02C_ADAPTER = 0.2c's adapter
  (adapter02c.pt, sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5, sidecar base
  1080632832:b40d4053c0ec2b83, checked on load by claude_sleep02c).
- **B (under test)** = the same build without SLEEP02C_ADAPTER: the LoRA is installed with B = 0, so it adds exactly
  zero and the 1B is the base model.
Everything else is the same code, panel, settings and seeds. Both arms use claude_mu402:build_null02c: a NullReader
(every turn reads as the reader's own chat frame, {"act": "CHAT", "facts": [], "ask": null}) put into
claude_lis319_arms' reader cache, so the rental needs no 2 GB reader; and before every turn torch and random are
seeded from (turn number in the conversation, user text), so A and B draw from the same seed on the same turn.
- **T (report only)** = the plain twin (claude_twinb_wrap, --arm twin, greedy), the S1 comparison arm.

What this does and does not test: the dev panel has no teach or ask turns, the notebook stays empty, and every reply
comes from the 1B layers (creative 333d, think 299b, chat 338b) exactly as in X. It tests the 1B chat path, where the
auditor put every extra claim. It does not test the reader, the notebook, or memory answers.

## Panel and run
artifacts/claude-mu402-20260926/devchat/items.jsonl: 80 conversations of 4-7 turns (smalltalk ~10%, advice ~25%,
explain ~15%, feelings ~25%, followup ~15%, think ~10%), fictional names A-M. Sealed with the code
(SEAL.sha256.txt) before the run. Runner: scripts/claude_panel382_run.py --panel chat, unchanged; A, B and T once
each on one rented GPU (same machine for all three).

## Judging (blind; judges see packets only, never code, arm names or keys)
- Claims: every (arm, conversation) transcript is one packet with a neutral id; arms mixed and shuffled (seeds 4021
  and 4022); each packet is judged by two different Opus judges (two passes over 8 batches of 60) with
  JUDGE-claims.md: for every assistant reply, 1 if it makes something up about the user, else 0.
  C(arm) = flagged replies summed over the two judges.
- Chat quality: B vs A per conversation, order shuffled per conversation, two Opus pair judges (seeds 4023, 4024)
  with JUDGE-pair.md: "1", "2" or "tie".
- Keys are applied by script (scripts/claude_mu402_judge.py count). A blind recount by a separate agent checks every
  number before any report.

## Marks (coded in claude_mu402_judge.py; B is the arm under test)
| Mark | What | Bar |
|---|---|---|
| M1 | fewer made-up claims without the adapter | C(A) - C(B) >= 10 AND C(B) <= 0.67 x C(A) |
| M2 | not luck: conversations where A has more flagged replies than B vs fewer (two judges summed) | one-sided exact sign test p <= 0.05 |
| M3 | chat no worse without the adapter: pair judgments (2 x 80) | B's losses - B's wins <= 16 |
| V1 | validity: arm A's log line says the adapter loaded (its path); arm B's says none | both as stated, else the run is VOID |
| V2 | validity: the adapter changes the chat path at all: replies that differ between A and B | >= half of A's replies (report; below half means the adapter barely touches chat) |
**PASS** = M1, M2 and M3, with V1 holding. A FAIL stays a FAIL.
**Proved wrong** (the adapter is not the cause): C(B) >= C(A).

Report only: C(T); replies flagged by both judges and by either judge, per arm; flags by turn kind; mean words per
reply by kind; judge agreement; minutes and dollars.

## Predictions
- P402.1 (55%): PASS.
- P402.2 (70%): A's mean words per reply on feelings and advice turns are at least 5 above B's.
- P402.3 (50%): C(B) <= C(T).

## What each outcome leads to
Agreed 13:20 UTC: Month-end plans 0.2d with the adapter on only for the puzzle route (switched per call by
Benchmarks' bm-398i bypass), and chat and creative on the plain 1B. Arm B is exactly what that route gives chat, so
mu-402 is the check that puzzle-only is safe and better for chat: B makes up less (M1, M2) and chats no worse (M3).
Fix sleep will use this probe as a second harm check on its nights and send any future saved adapter (same format)
through it as its own run.
- PASS: shown on dev chats that 0.2c's sleep adapter makes the chat path make up more about the user. Evidence goes
  to Month-end (owner of the router: adapter on for puzzle/think turns only, with Benchmarks' bm-398i switch) and to
  Fix sleep (night recipe: the KL anchor of dl-4, and this probe as a harm check on future adapters). S1 is then
  rechecked in the next joined build's own registered run, never by rerunning chatpanel02c.
- FAIL on M1 or M2 without "proved wrong": the adapter is not shown to be the cause at this size; next suspects in
  order: 0.2c's delivered history (F1) in the chat prompt, facts the lis-319 reader saved into the chat prompt, luck.
- Proved wrong: look elsewhere, starting with F1.
- M3 failing alone: the adapter helps chat quality even while it adds claims; the fix then belongs in the night
  recipe (Fix sleep), not in turning the adapter off.

## Budget
One rental from Ben's $2 for this thread (09-26 12:59 UTC), through the Director: RTX 5090 (else 4090), cap $1.00
for this task. Judges and recount: Opus agents in the thread, $0.
