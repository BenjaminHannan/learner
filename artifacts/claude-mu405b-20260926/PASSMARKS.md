# mu-405b: does the plain 1B use the user's own words when they sit in the user message, and does using them make it make things up about the user?

"Making things up about you" thread. Draft written 2026-09-26 22:07 UTC by date -u; fixed before the run once sealed. DEV data only.
$0: CPU in this container.

## Why
mu-405 (artifacts/claude-mu405-20260926/VERIFY-V405b.md, 885df2bc3) was INCONCLUSIVE: with session 1's
'User said, "..."' block in the SYSTEM message (its arm W, which is how 0.2d's talker builds its W input,
scripts/claude_e2e02d.py:224-228), the plain 1B answered 4 of 60 direct asks about a stored fact (nothing given: 0). y1d
saw the same with lines in the system message (3 of 56); y1f's L1 layout puts the block in the USER message
(scripts/claude_y1f_layout.py:59-63) and bm-398d with that placement answered 137 of 297. Obvious fix first: move the
block. Brain (a guess): what is being said to you now gets attention; a standing instruction in the background does not
steer recall. Only then can this thread's own question be asked: does a talker that really uses the memory make up more
about the user?

## Setup (scripts/claude_mu405b_talk.py, scripts/claude_mu405b_judge.py)
- One new arm, U: the twin's system line only; every session-2 turn's latest user message = claude_y1f_layout.L1_HEAD +
  session 1's 'User said, "..."' lines + a blank line + the user's turn as written; earlier session-2 turns stay in the
  history as plain text. That is ALL the user message contains: the moved block and the user's words. No QA_PROMPT
  (claude_y1f_layout.py:60), no LOCOMO_SYSTEM, no other wording. The block rides on every turn (smalltalk, feelings,
  advice, followup, ask), as 0.2d puts it on every turn (Month-end, 21:55 UTC). So U vs W is placement alone, and
  0.2d's fix can copy U exactly: the same block, moved from system_text into the latest user message. Everything else is mu-405's: the plain MiniCPM5-1B 87179e5c, greedy, 160 new tokens,
  enable_thinking off, the same 60 two-session DEV chats and facts, this container's CPU (fp32, torch 2.14.0+cpu).
- Controls come from mu-405's registered run (run2, same machine, greedy): N (nothing added) and W (the same block in
  the system message), sha256 of talk_N.jsonl 1ed656f1749beeb4eabee778b6e32c213c7d3dfda3de1376cae815573293df76 and of
  talk_W.jsonl 3a6a73409645e29ab9a88e4af7edf2911af56cb372facdc19fb29c3223aa7ce5 (talk_H's sha256 goes in SEAL when H
  ends, before sealing). H (whole chat as real history) is report only. mu-405's K is not used. None of mu-405's replies
  were ever judged: N, W, U and H are all judged fresh in the same packets by the same two blind judges per packet,
  mixed and shuffled, so a drift in the judges cannot favour U.
- Smoke: the 3 smoke chats (mu405-s1..s3) are separate items, never among the 60; the smoke is a format check only
  (rows written, no empty replies, no <think> leftovers) and nothing from it changes a mark.
  Result (22:38 UTC, date -u, CPU alone): 15 of 15 session-2 rows, 0 empty, 0 <think> leftovers, 0 tracebacks; asks
  right 1 of 3 (too few to read anything into).
- $0 counts before the run: every U prompt carries all 3 of its chat's facts (300 of 300); the system line carries none.
- Claims judging: mu-405's text (JUDGE-claims405.md: mu-402's rubric, the earlier session's user messages shown and
  counted as said), one packet per (arm, chat) for arms N, W, U, H (240 packets), arms mixed and shuffled (seeds
  4061/4062/4063), two fresh blind Opus judges per packet, each judge in its own private folder. Blind recount before
  reporting.

## Marks
- VB (validity: the talker uses the memory): U's stored-fact asks right >= N's + 10, of 60 (code: the reply contains
  the asked value). If not, Q3 is INCONCLUSIVE.
- R (placement changes recall; for Month-end's 0.2d talker): PASS when U's asks right >= W's + 10 and, per chat, U
  right where W was wrong more often than the reverse (one-sided sign test p <= 0.05). Proved wrong: U's asks right
  <= W's.
- Q3 (this thread's question): PASS (shown on DEV: using the memory raises made-up claims) when C_U - C_W >= 10
  (C = flags summed over two judges on session 2's 300 replies) and, per chat, U has more flags than W more often than
  fewer (p <= 0.05). Proved wrong: C_U <= C_W. In plain words, a Q3 PASS is BAD news: giving the talker memory it can
  use makes it invent MORE about the user. Q3 proved wrong (C_U <= C_W) is the good outcome: usable memory adds no
  made-up claims. Anything in between (C_U above C_W but short of a PASS) is FAIL, not proved wrong: not shown either
  way.
- Report only: C_U vs C_N and C_U vs C_H with the same sign test; ask right for H; flags by turn kind.

## What each result means
- R PASS: 0.2d's talker should carry the W block in the user message; goes to Month-end with the counts.
- Q3 PASS: a talker that uses its memory makes up more about the user; the fix is then trained (mu-406 plan).
  Q3 proved wrong: the placement fix costs no extra made-up claims on DEV; S1 then rests on the talker alone.

## Predictions (before the run)
- P405b.1: VB and R PASS, 60%. P405b.2: Q3 PASS, 35%.
- Revised before sealing (22:37 UTC, date -u), after mu-405's report-only arm H ended: with both sessions as real
  chat history the plain 1B answered 1 of 60 asks, so the 1B may not recall in plain chat wherever the words sit.
  P405b.1 lowered to 35%; P405b.2 unchanged. The marks do not change.
