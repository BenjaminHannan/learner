# 137b — discourse words glued onto multi-word names (design)

Exp 137's upgrade accepts any 2–4 Title-case tokens as one possessive
subject (`scripts/fable_fix137_names.py:123-127`, called from
`scripts/fable_loop138b_agent.py:142-169`). Phones capitalise the first
word, so "Suppose Tom's boss is Ann." teaches subject "Suppose Tom" and
"Hi. Tom's boss is Ann." teaches "Hi. Tom" — verified live on loop137
itself and on loop138b (redteam136 C089/C122, sealed WRONG-WRITE).

## The one change

`Loop137bEars` subclasses loop138b's ears (`scripts/fable_loop137b_agent.py`,
new files only, no loop138b file edited) and replaces just the 137
upgrade step. A 137-parsed subject or value name is rejected when (a) it
contains a sentence break (". ", "! ", "? ") that is not an abbreviation
period (a single-capital initial "A. " or St./Mr./Mrs./Ms./Dr. never
counts, per exp-129, so "A. A. Milne" stays one name), or (b) its first
token is in a closed 24-word discourse list (suppose, imagine, say, hi,
hey, hello, okay, ok, so, well, oh, btw, also, and, but, actually,
basically, anyway, please, remember, note, fyi, listen, look — fixed
before any panel read, in `scripts/fable_fix137b_discourse.py`).

A rejected subject re-parses the message minus its leading token through
the unchanged loop138b pipeline ("Suppose Tom's boss is Ann." →
"Tom's boss is Ann."); a rejected value drops its first token and is
re-screened ("Mary Ann's boss is Oh Bob." → "Oh Bob" → "Bob").
Phone-fronted questions ("So what is Tom's boss?") strip the same way.
The stripped result is used only when it yields a non-clarify action;
otherwise the base refusal stands.

## Deliberate scope edges

- Statements outside 137's rule are untouched: "Imagine the capital of
  Peru is Lima." stays a no-write OK (sealed C090), "Actually, ..." of-
  forms and "Actually, Rao's city is Denver." (base teaches Rao clean)
  are byte-identical.
- Values containing a sentence break keep the base refusal (loop138b
  already refuses "Mary Ann's boss is Bob. Call me." with 0 writes;
  truncating to the head would newly teach).
- A real title starting with a listed word in 137 position strips like
  discourse ("Hey Jude's director ..." → Jude). No sealed suite contains
  such a case (scanned: bench 800 inputs, redteam136/143, sessions152,
  marks123 sources); the T1 title probes sit in base-path positions and
  stay identical. This is the one known ambiguity of the rule, listed
  with live-measured outcomes in RESULTS.md.

## What it means / does not mean

It means discourse-fronted teaches and questions land on the bare twin
exactly (same reply, same write), junk subjects ("Suppose Tom", "Hi.
Tom", "Also Wren") disappear, and every other turn is bit-identical to
loop138b. It does not mean hypotheticals are understood ("Suppose ..."
still teaches the rest as fact), titles in 137 position survive, or
lowercase phone sludge ("btw marta's ...") parses — those clarify with 0
writes exactly as before.
