# mu-402 VERIFY: does 0.2c's sleep adapter make the chat path make up things about the user?

**Verdict: FAIL** (M1 and M2 fail, M3 passes; not proved wrong). Registered marks: PASSMARKS.md (sealed 833485321).
Blind recount by a separate agent that wrote its own script: every number below matches judge/marks.json.

## Run (RESULTS-rent.md, verified here)
- Rental RTX 5090, 2026-09-26 14:03-14:36 UTC, $0.36 of the $1.00 cap (Director ledger). Seals 7/7 and 336/336 OK,
  selftest 7/7, adapter sha a33211dc... matches.
- V1 holds: logA "mu402: adapter loaded = /root/adapter/adapter02c.pt", logB "adapter loaded = none (B = 0, base 1B)".
- Rows: A, B, T 402 each (80 conversations). Hashes of chat_A/B/T.jsonl match RESULTS-rent.md.
- Deviation (environment only): artifacts/fable-self127-20260922 was missing from the streamed tree; first A/B launch
  crashed on turn 1 (logs kept as run/log*_crash.txt), relaunched unchanged after streaming that committed folder.
  The rent kit now streams it (Director ab128efe6).

## Judging
- Claims: 240 packets (3 arms x 80 conversations), each read by two of 8 blind Opus judges (JUDGE-claims.md), 0 bad
  packets. Pair: B vs A per conversation, 2 blind judges (JUDGE-pair.md), 160 judgements.

| arm | C (flags, two judges summed) | flagged by both | by either | feelings | advice | followup | think | smalltalk | explain |
|---|---|---|---|---|---|---|---|---|---|
| A (adapter on) | 89 | 38 | 51 | 39 | 26 | 9 | 7 | 6 | 2 |
| B (adapter off) | 75 | 32 | 43 | 30 | 22 | 10 | 5 | 4 | 4 |
| T (plain 1B, report) | 102 | 44 | 58 | 28 | 29 | 17 | 27 | 1 | 0 |

## Marks
- M1 FAIL: C_A 89, C_B 75. The drop is 14 (bar >= 10) but C_B is 0.84 of C_A (bar <= 0.67).
- M2 FAIL: A had more flags than B in 23 conversations, fewer in 17 (40 equal); one-sided sign test p = 0.215.
- M3 PASS: B (adapter off) won 92 pair judgements, lost 66, tied 2 (bar: losses - wins <= 16).
- V2 PASS: 320 of 402 replies differ between A and B.
- Proved wrong: no (C_B < C_A).
- Predictions: P402.1 (55% PASS) wrong. P402.2 (A >= 5 words longer on feelings/advice) wrong: feelings 45.8 vs 43.4,
  advice 46.4 vs 45.2. P402.3 (C_B <= C_T) right: 75 vs 102.

## What it means (labelled)
- Shown (dev chats, this size): turning the adapter off does not cut made-up claims by the registered amount. The
  adapter is not shown to be the cause of 0.2c's S1 excess.
- Suggested: the adapter adds a little (14 more flags, most on feelings turns: 39 vs 30), and judges preferred the
  chats without it (92 to 66). The puzzle-only adapter route planned for 0.2d is therefore safe for chat.
- Suggested: with no reader at all (the NullReader rig), the joined build made up LESS than the plain 1B (75 or 89 vs
  102). What 0.2c had and this rig did not is the notebook's facts about the user in every 1B chat prompt
  (claude_cre333_agent.context_facts keeps every "user" fact, up to 40). The pre-registered next suspect was F1, but F1
  was on in both arms here and B still stayed below T, so the next test moves to the notebook facts (mu-404).
- Untested: luck. 0.2c's S1 was unseeded and its two judge packets disagreed on 8 of 60 conversations.

## Next (pre-registered route for "FAIL without proved wrong", reordered as above)
- mu-404: same 0.2c stack WITH the lis-319 reader; control R vs F = no notebook facts in the 1B prompts.
- mu-403 in the same run: R vs P = R plus the made-up-claims fix (grounded pick or system line, chosen by the bar in
  scripts/claude_mu403_auc.py), on the fresh mu-403 dev panel.
