# 152 — Realistic-user session red team (Muse, 2026-09-22)

The owner chats with the agent on his phone tomorrow. I played a
high-school student across 6 sessions x 30 turns on both best sides
(T-Q = loop149 qrewrite, T-T = loop139b), fresh daemon per session,
mailbox, one file per turn. I found bugs only; I fixed nothing and
edited no existing file.

## What breaks (novel; known K144/K146/K147/K148/K150/K151 kept to one
instance each and excluded from the count)

1. **Small talk is dead.** hi, lol, thanks, ok cool, k bye (46/360 turns)
all get "I didn't understand that. Could you say it another way?"
No write happens (safe), but turn 1 of any human chat is already stuck.
Cause: `scripts/fable_loop90_agent.py:291` — no chain stage matches, so
the fallthrough clarify fires.
2. **No self.** "who are you" / "what can you do" (10 turns) get the same
clarify. Same cause; needs a no-write identity card.
3. **No pronouns, no synonyms.** "where does she live?", "what about his
mom?" (10 turns) clarify; "mom" never maps to "mother". Cause:
`scripts/fable_agent_loop.py:94` (`_QUESTION`, possessive-split only) and
`:153` (literal relation mapping).
4. **Filler words kill teaches.** "btw marta's brother is kai",
"also ...", "oh and ..." are refused ("btw marta" fails the one-word-name
check, `:141`), and the next 5 asks go honestly-but-stuck MISSING — 16
stuck turns from 3 prefixes. Strip fillers before `:96` statement parse.
5. **Only canonical questions parse.** "what's tess's city?", "tell me
tess's city" refused with the fact sitting in the notebook (`:94` allows
only who/what/where + is/are).
6. **Bare corrections ignored.** "no wait, it's Denver" needs an
Actually-/no,-prefix (`:95`); the canonical "Actually, ..." works.
7. **"???" leaks.** "Who is Rosa's mother's city???" answers "I don't know
Vera's city??." — one-mark strip (`:94`) keeps "??" inside the relation.
8. **"my X is Y" rejected.** "my dog is biscuit" needs possessive shape
(`:96`, `:143`); a phone user teaches family exactly like this.
9. **One WRONG answer.** "Who is Ana's pet's color?" says "not someone I can
look up" although Biscuit's color is taught: first hop "pet" stores a
literal (not in PERSON_RELATIONS, `:91`), so the notebook hop loop hits
BROKEN_CHAIN (`scripts/fable_notebook_contract.py:405`). Only class that
answers wrong instead of abstaining; rare shape, highest severity.

Replies were byte-identical on T-Q and T-T for all 360 turns (shared ears
path), so every class above hits both sides.

## What still works (evidence, not vibes)

0 wrong writes in 360 turns, including 28 small-talk/self turns. Lowercase
teaches/asks, emoji values, canonical teaches, 1-/2-hop asks, immediate and
~10-turn-later re-asks, "Actually,..." corrections, honest MISSING_FACT on
untaught facts/entities, and idempotent "I already have that." all OK.

## Files

Sessions: `scripts/fable_session152_sessions.py` (sealed pre-run).
Runner/judge: `scripts/fable_session152_run.py`.
Artifact: `artifacts/fable-session152-20260922/` (PASSMARKS.md,
SEAL.sha256.txt, sessions152.json, turns152-*.json, TURNS.md, RESULTS.md).
Ledger: P152.1 (6 predicted new classes; 9 found -> TRUE), outcome appended.

## Deviations

One judge correction, documented in RESULTS.md: S5-T16 (both targets)
mechanical UNHELPFUL -> OK (idempotent re-teach correctly acked). No plan
deviations; no non-owned file touched; 3.0 s wall-clock.
