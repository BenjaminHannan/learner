# 154 — Yes/no questions (Muse)

Director probe on loop150: after "Ann's mother is Rita.", both "Is Rita
Ann's mother?" and "Is Bob Tom's boss?" get "I didn't understand that".
One new stage answers them, changing nothing else.

## Step 1 — the code responsible (found before sealing, read-only)

The loop decides question-vs-statement by surface shape, and "Is ...?"
matches neither branch:

- `scripts/fable_agent_loop.py:94` — `_QUESTION` only matches
  `who|what|where + is|are`. An "Is ...?" turn never becomes an ask here.
- `scripts/fable_agent_loop.py:135-148` — the `_STATEMENT` teach regex
  cannot match a leading-"Is" turn with no second copula, so `FakeEars`
  falls to line 148: `I didn't understand that. Could you say it another
  way?`.
- `scripts/fable_loop90_agent.py:135-151` (`Bench73Stage.hear`) —
  `compose_question` has no "Is" frame and no teach template matches, so it
  returns None on these turns.
- `scripts/fable_loop90_agent.py:291-292` (`ChainEars.hear` total miss) —
  re-emits the same "I didn't understand that..." clarify. THIS is the miss
  the stage keys on (substring `didn't understand that`).
- Value rendering the comparison reuses: `scripts/fable_agent_loop.py:166`
  (`FakeMouth`: `{owner} is {answer}.`), `scripts/fable_notebook_contract.
  py:420` (`ask` OK detail carries `answer`), normalisation
  `scripts/fable_fix129_punct.py:119` (`strip_sentence_punct`).

## The rule

When — and only when — the unchanged forward path returns that single
didn't-understand clarify, a turn shaped `Is V X's R?` / `Is V the R of
X?` / `Is X's R V?` / `Is X's R1's R2 V?` is rewritten to the wh-question
the loop already answers (`Who is X's R?` / `Who is X's R1's R2?`, "What"
for non-person last hops), run through the UNCHANGED forward path (same
ears hear, same `_act`/`_ask`), and the answered value is compared with V
(exact after the loop's own normalisation: whitespace collapse plus the
129 strip on both sides, relation keys via `FakeEars._relation`):

- same value → `Yes — Ann's mother is Rita.`
- different value, last hop single-valued per the sealed table →
  `No — Ann's mother is Rita.`
- different value, multi-valued last hop (friend, child, sibling, sister,
  brother, notable_work, ...) → `I only know that Ann's friend is Bob.`
  (never `No`)
- forward path abstains (any non-OK: MISSING_FACT, UNKNOWN_ENTITY,
  AMBIGUOUS, BROKEN_CHAIN) → its own honest reply, never `No`.

Sealed single-valued table (`SINGLE_VALUED_154` in
`scripts/fable_fix154_yesno.py`, one reason each): mother, father (one
slot each; corrections supersede); capital (one per country); place_of_
birth, date_of_birth (born once); city (one current city); spouse, wife,
husband (one active); boss, teacher (one current). Everything else is
multi-valued.

The stage never writes: the wh run executes only ask/clarify (any
write-shaped wh action aborts to the base clarify), and the final record
is a mouth-verbatim clarify. Non-shapes (`Is Bob a doctor?`) pass through
untouched. Parser limits (sealed): the turn must start with "Is" and end
with "?"; `X`/`V` are single tokens in the possessive shapes; the
`the R of` shape needs an `R` without "of" (relations like place of birth
use the possessive shape instead); two-hop only in the `Is X's R1's R2 V?`
order; ambiguous double splits stay clarify.

## Where it sits

`YesNo154Mixin` (`scripts/fable_fix154_yesno.py`) is loop-level and
cooperative: `_listening_tick` peeks at the inbox head through the
unchanged ears hear and diverts only on miss + parse; all else delegates
byte-identical to `super()`. `scripts/fable_loop154_agent.py` stacks it as
`Loop154AgentLoop(YesNo154Mixin, Loop150AgentLoop)` with an unchanged
`Loop150Ears` subclass, plus the usual daemon (`idle_seconds`), config,
and `--once` entries — the 140/150 file pattern. No existing file edited.

## Results (registered: Y1/Y2/G1/G3/G4 PASS, G2 FAIL on the letter)

Y1 49/49 (21 Yes incl. 4 two-hop, 12 No, 8 only-know, 8 unknown non-No),
0 wrong, 0 question writes. Y2 0 writes / 54. G1 600/600 bench rows
identical to loop150. G3 0 reply moves, 0 new WRONG/writes vs T-T. G4
5.1/92.0/181.1/6.7 s. G2: all suites per-case identical except 3
Is-turns with unknown answers (rt81 D_q_vs_s-04, l5z1 turns 49/58)
relaying the mandated honest reply — 0 writes, 0 new BUG/WRONG; the
zero-move forecast missed that the sealed suites contain Is-turns.
Post-seal edit: restored a dropped `idle_seconds` line in the daemon
`__init__` (subprocess boots crashed; in-process runs unaffected), all
marks re-run in the open. See
artifacts/fable-yesno154-20260922/RESULTS.md.

## What it means

"Is ...?" turns the loop never understood now answer Yes / No
(single-valued only) / "I only know that ..." / the honest abstain, with
zero writes and zero movement on benches, sessions, and non-yes/no suites.

## What it does not mean

It does not teach new facts or relations: single-chain cued Is-questions
are still answered directly by the old N-hop composer, and ambiguous
shapes still clarify.
