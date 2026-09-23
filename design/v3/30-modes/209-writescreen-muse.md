# 209 — Write screen on loop138i (Muse)

## Problem

Director-verified bad saves on loop138i, all in how a heard turn becomes
a declared fact/relation:

1. `"Anwar's dog is named Pip."` stores `dog = "named Pip"` — the
   filler verb sticks to the value.
2. `"My birthday is in March."` stores the birthday as an ENTITY (a
   person-like row "in March"), after which `"When is my birthday?"`
   answers about age — Me166 forces every "My R is V" value to
   entity-valued (`scripts/fable_fix166_me.py:209`), and nothing
   re-checks date relations.
3. Relation names built from clause words get declared as new notebook
   relations (e.g. `Nadia's friend who lives in Oslo is Elsa` declares
   `friend_who_lives_in_oslo`) — FakeEars joins the whole possessive
   remainder with underscores (`scripts/fable_agent_loop.py:151`).

## Where facts and relations are declared (MRO trace)

`Loop209Ears(WriteScreen209EarsMixin, Loop138iEars)` → … → FakeEars
shapes; `Loop209AgentLoop(WriteScreen209LoopMixin, Loop138iAgentLoop)`.
Every teach flows: `Ears.hear` → action `(name, relation, value,
is_person)` → `AgentLoop._act` (`fable_agent_loop.py:344`) builds the
structured line `teach NAME REL ->/=> VALUE` → `Listening._teach`
(`fable_listening_m1.py:106`) → `Notebook.new_entity` for `->` values,
`declare_relation`, `assert_fact` (`fable_notebook_contract.py`). The
screen sits at the two narrowest additive choke points: outermost
`hear` (sees every action the 138i chain returns) and an `_act`
backstop (covers `Multival154eMixin._act_multi_teach138i`, which
re-enters `_act` below the ears). 138i itself is never edited.

## The change

- (a) Strip leading `named`/`called` from teach/correct values
  (repeatedly, so hear + `_act` are idempotent; later-in-phrase kept).
- (b) Date-type relation keys (contains `birthday`/`anniversar`, or
  `birth` + `date`/`day`, or `birthdate`/`dob`) with `in|on` +
  month/weekday/digit-date values flip to literals with the preposition
  stripped. Person relations never match, so `Kim's sister is April`
  and `May's city is Paris` stay entities.
- (c) Relation keys containing whole-token clause words (`but`, `now`,
  `that`, `which`, `who`, `because`, `then`, bigram `used to`) refuse
  the whole turn: 0 writes + the base's `SPLIT_MSG`. Only the key is
  screened, so `hobby is that she paints` still saves; token matching
  (not substring) keeps `thenar` saving.

## Alternatives

Screening inside `Listening` was rejected (shared module, not additive).
Learning the distinction was rejected (one explicit rule beats a
fitted gate for a closed, director-specified list).

## Marks

W1: 32 bad-save cases, exact stored facts. W2: 33 near-misses,
byte-identical reply + stored. W3: rt136/rt143/sessions152 + marks123 +
bench-v3, 0 moves vs 138i, 0 new wrong. Full evidence in
`artifacts/fable-writescreen209-20260922/RESULTS.md`.
