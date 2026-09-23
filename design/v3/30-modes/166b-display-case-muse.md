# 166b — display case: a name keeps its capital letter (Muse)

Ben in one line: if you teach the assistant a name in small letters and later
write it with a capital, it now answers with the capital from then on.

## The bug (exp 166's registered G3 FAIL)

"My dog is biscuit." teaches a real fact, but the dog's display name is stored
exactly as typed: `biscuit`. Three later replies then say "biscuit's ..." where
they used to say "Biscuit's ...". Same answers, same facts, just an ugly small
letter. Cause, with file:line:

- The notebook files every name under a lowercased key but keeps the typed
  form as the display (`scripts/fable_notebook_contract.py:116-117`,
  `:196-198`). Values from "my ..." teaches are stored with the typed surface
  (`scripts/fable_listening_m1.py:50-57`, `:115`).
- Every reply copies the stored display word for word: `Notebook._show`
  (`:257-258`), fact/answer texts (`:349`, `:390-420`), and the mouth
  (`scripts/fable_agent_loop.py:165-168`). Nothing ever re-capitalises.

## The fix (one change, agent layer only)

`Loop166bAgentLoop` (`scripts/fable_loop166b_agent.py`, a subclass of loop166's
loop with the same ears) watches each turn: when an entity whose display is
all small letters (say `biscuit`) is mentioned with the same letters but a
capital first letter (`Biscuit`), it remembers `{entity: Biscuit}` for that
conversation and rewrites later replies with it. The notebook log is
append-only and has no rename event (ALIAS never changes the display), so the
memory lives in the agent, not the notebook — the stored facts never change.

Rules that keep it safe:

- Only small-letter displays can gain a capital; `Wug` never changes, however
  you write it later. Only same-letters-different-case counts (`Biscuit` yes,
  `Biscuits` no). Matching, entity ids, and all writes are loop166's exactly.
- Third-person value slots ("Tom's pet is nib") store plain words, not name
  pages, so there is nothing to fix there — only subject slots and "my ..."
  value slots carry displays.

## Proof plan (predictions P166b.1-6 in PASSMARKS.md, sealed first)

- T1: 166's 52-case probe unchanged → byte-identical to loop166 (no trigger
  in it). T1b: a new 30-dialogue probe (12 small-then-capital incl. "My dog
  is quib." → "What is Quib's toy?" giving "I don't know Quib's toy."; 8
  capital-then-small staying put; 10 others identical).
- G1 bench 600/600, G2 all marks123 suites: zero moves vs loop166's frozen
  rows (an entity-level scan of every suite input fires in exactly one place:
  S4's biscuit, which is not in any bench/marks suite).
- G3: exactly the 3 S4 replies return to loop162b's "Biscuit's ..."; S4's new
  correct write stays; redteams silent. G4: every run < 25 min on the Mac.

## What it does not do

It does not guess full names from nicknames, touch the notebook log, or change
any answer — only the capital letter in how a name is shown.
