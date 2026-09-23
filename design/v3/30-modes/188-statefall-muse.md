# 188 — statefall: a statement-shaped fallback on loop138g (design)

One new file (`scripts/fable_loop188_agent.py`) subclasses the frozen
loop138g stack. The ONE change is an outermost reply-text swap; every rule
body is imported read-only; no existing file is edited. Drivers are
`scripts/fable_fix188_f1.py`, `scripts/fable_fix188_suites.py`,
`scripts/fable_fix188_compareg2.py` (plus stock `fable_marks123_all.py`).

## The problem

Director probe 09:40 on loop138g: five plain statements ("The city of
Kim's boss is Oslo.", "Word is Kim's boss is Lee.", "Kwame was born in
Paris.", "My name is Dawn and I live in Leeds.", "My sister lives in
Nairobi.") all get the generic QUESTION fallback ("I do not know that
from what you taught me. I have no record of it, so I will not guess…"),
which answers a question nobody asked. These turns parse to nothing the
base understands, so the notebook path misses and the frozen router
declines, and the decline text is question-shaped.

## The one change

`Loop188AgentLoop.turn()` runs the unchanged 138g path, then swaps the
reply text ONLY when both hold: (a) the base reply equals the generic
question fallback byte-for-byte, (b) the turn is statement-shaped under a
closed stdlib test — no "?" anywhere, first alphabetic word not a
question word (who/what/where/when/why/which/whom/whose/how), not an
auxiliary (is/are/was/…/must/ought/need/dare), not a
command/pretend/greeting opener
(tell/show/…/pretend/imagine/suppose/…/hello/hi/hey/please/thanks).
The replacement is one sealed sentence: "I couldn't save that as a
fact. I don't know that shape yet. Could you say it another way, like
"Kim's boss is Lee.""

Three properties by construction: (1) the notebook is never touched in
the swap, so events.jsonl stays byte-identical and hearsay keeps 0
writes; (2) anything the base already handles — teaches, pretend, hypo,
greetings, confirmations, hearsay clarifies, split-clarifies, grounded
self replies — has a different reply, so it can never change; (3) real
questions keep the question fallback (they contain "?" or open with a
question word/auxiliary).

## Why the fallback keeps abstain markers

The frozen suites encode an abstain contract mechanically: sessions152
`is_clarify`, bench121 `ABSTAIN_PHRASES`, rt81's wanted-marker check all
look for shared bits ("don't know", "another way"). Pilots showed the
bare paraphrase trips 2 sessions OK→WRONG and 3 rt81 OK→UNCLEAR verdicts.
Keeping those two markers while dropping the question-answering head
("I do not know that from what you taught me…") returns every suite to
verdict-identical, leaving only reply-only moves. This is the sealed
trade-off, stated openly: the fix changes the claim the reply makes,
not its abstain status.

## Composition

Ears, _act, reasoner, notebook, sleep, daemon: 138g unchanged
(Loop138gEars reused; Loop188Daemon = Loop138gDaemon shape with
build_agent188 inside, idle_seconds parameter kept). The in-memory self
log's served-reply field is updated to the served text, mirroring how the
base overwrites it on routed answers; no disk events change.

## Known edges

- "and"-compounds ("Kim's boss is Lee and her city is Oslo.") get the
  split-clarify, not the question fallback, so they keep it (not
  statement-fallback cases).
- "I heard…"/"Rumour has it…" keep HEARSAY_MSG (never equal the
  question fallback); "Word is…" shapes get the statement fallback.
  Both write nothing.
- rt136 C124/C127/C129/C142 and sessions S2n8/S3n6/S4n1/S6n14 move
  reply-only with verdict+writes kept; marks123 moves 15 reply-only
  cases (rt81 5, rt110 10 log lines). All enumerated in PASSMARKS.
