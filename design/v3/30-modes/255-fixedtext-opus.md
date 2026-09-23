# Exp 255: fixed-reply text pass (design note)

## What was tried

A single outermost text mixin (`scripts/claude_fix255_text.py`, agent
`scripts/claude_loop255_agent.py`) on the 138m head. It rewrites a reply line
only when the WHOLE line fully matches one of 60 fixed templates (T01–T60):
an honest two-sentence decline ("I don't know that. I may have misread …"),
"USER" → "your", no capitalised mode names, one grammatical greeting that
names Premonition once, proper sentences for dashes/placeholders/fragments,
words for small counts, and Oxford-comma removal. No routing, reading, writing
or new decisions change. Details: `artifacts/claude-fixedtext255-20260922/`.

## What happened

Registered FAIL on M4. The decline template T02_Q2 ("I don't know that. …")
fires on misread questions, including ones whose answer is already stored
(user's name; Tomas's boss), the assistant's own name, or a teach request. The
director ruled those 8 probes (A06, B04, B05, B20, D02, D03, D04, D08) worse on
meaning. Everything else passed: M2 (162 reply-only moves, 0 verdict changes),
M5, M6 (17 predicted moves), M7 (+0.019 ms), M3 runner (153 changed turns, all
explained, 0 store changes; judging not run). M1 graded by the director
separately.

## Lesson for the next try

A fixed decline sentence cannot start with "I don't know that." unless the
"that" is actually unknown. The misread-question case needs wording that stays
true when the fact is stored — e.g. lead with the misread ("I may have misread
your question …") and keep the not-knowing part conditional — or the decline
must check whether the asked-for fact is stored before choosing its sentence
(which would make it routing, not pure text).
