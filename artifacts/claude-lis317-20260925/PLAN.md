# lis-317: what does the reader read in chatty DEV turns, before any gate? (REPORT ONLY)

Thread "Fix: reading facts from chat" (cmsg_01FuvegZXjMmeUzStiEFVnEWFFJdDCbBKsf18JUgMQeEYH), 2026-09-25 00:50 UTC.
Ben, 00:31 UTC 09-25: fix the known issues; reading facts from chat is the main blocker (336: saved 182/318 = 57%,
answerable asks right 42/193 = 22%, VERIFY-336.md).

## Why
From the rent-330-dev run (DEV only, arm 330a_chat, builder-outbox artifacts/claude-e2e330-dev-20260924/run), counted
on CPU with the teach-turn reply for each of the 131 DEV facts:
| outcome | facts |
|---|---:|
| saved | 49 |
| held as unsure, reply "Okay." (lis-314 pending) | 35 |
| a confirm question instead (many garbled: pronoun owners, odd relations) | 28 (+1 saved under another owner) |
| "whose is it?" question | 8 |
| other facts in the same turn saved, this one missed | 10 |
Asks whose facts were all saved: right value named on 3 of 15 (excluding never-told and partial).
lis-301 on its own panel: 97.9% recall with no gate, 35.2% at T 0.995 (the gate is min token probability).
So the question is: on chatty multi-fact turns, is the reading wrong, or is the gate throwing good reads away?

## What runs (no training, no agent, no TEST-ONLY data)
scripts/claude_lis317_sample.py on the lis-301 reader, for the 194 e2e DEV turns (rows_e2edev.jsonl, prev_reply = the
reply 330a_chat gave before that turn) and the 959 lis-301 dev rows: greedy read (as live), greedy token probabilities,
and K = 8 samples at temperature 1.0 (agreement check). Scored by scripts/claude_lis317_score.py.

## Decision rule (fixed before the GPU run)
R0 = DEV gold teach/correct facts (131) that appear in the greedy read with mode ASSERT/CORRECT, owner + value matching.
- R0 >= 105/131 (80%): the reader reads chat; the lead fix is the gate (a better "am I right?" signal than min token prob).
- R0 < 79/131 (60%): the reader misreads chat; the lead fix is retraining the reader on chatty turns.
- In between: both; the gate first (it needs no training).
Report only. Whatever it shows, the fix is a new numbered experiment with its own sealed marks.

## Addendum 01:20 UTC: the compiler's own ceiling (CPU, shown)
scripts/claude_lis317_ceiling.py -> ceiling_e2edev.txt. With a PERFECT reader (owner and value copied as typed,
bank relation mapped generously to the 153-name table) and no confidence gate, the live structural checks
(claude_lis300_compiler.check_fact) can write 103 of 131 DEV facts (79%). Blocked: 15 relations with no table name
(species 6, breed 2, interest 2, studies 2, major, subject, unit), 6 owners not in the turn (pronoun or nickname
pointing back to an earlier turn: the reader only sees the assistant's last reply, not earlier user turns), 6 values
not typed word for word ("i drive a tram" -> tram driver, "keep bees" -> beekeeping), 1 "me" fact with no I/my.
So no gate fix alone can reach 336's 85% bar on this kind of chat; the hand-written checks cap it first.
