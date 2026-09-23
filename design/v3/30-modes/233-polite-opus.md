# 233 — Polite negative questions (Opus)

## Problem
On loop223, "Can't you tell me where Kim lives?", "Don't you know who
Kim's boss is?" and "Won't you tell me Kim's city?" are stopped by the
exp-148 question screen (it sees "n't") and get the negation clarify
("I didn't understand that. I only know current facts and I can't do
'not' ..."), even when the fact is stored. These are ordinary polite
requests, not negated questions.

## The one change
`scripts/claude_loop233_agent.py` subclasses loop223 (no earlier file
edited). `Loop233AgentLoop.turn` looks at the incoming turn before
anything else runs. If the turn

1. ends in "?",
2. starts with a polite negative frame addressed to the assistant —
   Can't / Cannot / Couldn't / Won't / Wouldn't / Don't **you**, or
   **Do you not**, optionally "please"/"just", then **tell me / know /
   remind me / say** — and
3. the rest parses into a plain question the base already reads, and
4. that plain question has no negation word (sealed 148 list plus
   cannot / no / nothing / nowhere / neither / nor; taught names exempt),

then the plain question is handed to the unchanged loop223 `turn()`
instead of the original text. Otherwise the original text goes through
unchanged, so true negations ("Where doesn't Kim live?") and negated
statements are byte-identical to loop223.

Rewrites (embedded clause → plain question):

| embedded | plain |
|---|---|
| where Kim lives | Where does Kim live? |
| who Kim's boss is | Who is Kim's boss? |
| which city Kim lives in | Which city does Kim live in? |
| where Kim was born | Where was Kim born? |
| who is Kim's boss (already direct) | Who is Kim's boss? |
| Kim's city (bare noun phrase) | What is Kim's city? |
| if Kim lives in Oslo | Does Kim live in Oslo? |

## Why this shape
- Rewriting at turn entry means the plain question takes exactly the
  path it would take if typed: same screen, same reasoner, same mouth,
  same no-write question path. Nothing downstream needs to know.
- The negation guard runs on the *rewritten* question, so "Can't you
  tell me where Kim doesn't live?" keeps today's clarify.
- Content that does not parse is left alone (today's reply), never
  guessed at.

## Limits (known before registration)
- Two-hop "where Kim's boss lives" rewrites to "Where does Kim's boss
  live?", which the base itself does not read; the reply is the base's
  honest abstain (dev case D21, the one dev miss).
- Only the listed frames and verbs; "Can you not tell me ...", "Don't
  you remember ..." are not covered.
- The parser is word-pattern based: subjects must start with a capital
  letter or I/you/my/your/we/they/our/their.
