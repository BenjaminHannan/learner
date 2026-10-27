# 153 — Reverse questions on taught facts (Muse)

Reversal ("Tom's boss is Bob." -> "Whose boss is Bob?" -> "Tom") is a
benchmark target: plain transformers fail 'A is B -> B is A'. Our notebook
stores triples, so reverse lookup can be exact.

## The problem

Director probe on loop150 and loop149-qrewrite: after "Tom's boss is Bob."
every reverse question gets "I didn't understand that": "Whose boss is
Bob?", "Who is Bob the boss of?", "Bob is the boss of whom?", "Who is Rita
the mother of?", "Kelm is the capital of what?".

## Code responsible (read before sealing; nothing edited)

- `scripts/fable_loop90_agent.py:291-292` — `ChainEars.hear` total miss:
  both stages (bench73, fake) abstain and the chain returns the single
  clarify "I didn't understand that. Could you say it another way?".
- `scripts/fable_agent_loop.py:148` — `FakeEars.hear` fallthrough: a
  reverse question matches no `_QUESTION`/`_STATEMENT` template (e.g.
  "Whose ..." matches neither), so the fake stage abstains and the chain
  above fires.
- `scripts/fable_bench73_english_arm.py:246-336` — `compose_question`:
  handles bench-relation questions plus the narrow `REV_OF_NOUNS` /
  `REV_BY_VERBS` reversal shapes only; M1-relation reverse frames
  (boss/mother/capital) return None, so the N-hop/2-hop router in
  `scripts/fable_loop113b_agent.py:77-102` also yields None and the turn
  falls back to the exact loop102 chain, which misses the same way.
- Relation table reused: `FakeEars._relation`
  (`scripts/fable_agent_loop.py:150-152`, lowercase + underscores).
- Triple store reused: `notebook_triples`
  (`scripts/fable_loop90_agent.py:101-114`: source == taught AND active
  only — corrected-away, forgotten, refused/hearsay rows are already
  excluded there).

## The one change

`scripts/fable_fix153_reverse.py` (`Reverse153Mixin`), stacked onto loop150
by `scripts/fable_loop153_agent.py` (`Loop153Ears`, ears subclass only, in
the style of `scripts/fable_loop140_agent.py`). On ears `hear()`:

1. Run the base (loop150) hear first.
2. If it did NOT return exactly the loop's own miss clarify, return it
   byte-identical (forward path understood -> reverse stage never runs).
3. Else try the four closed reverse frames (sealed in PASSMARKS.md):
   `Whose R is V?` / `Who|What is V the R of?` / `V is the R of whom|what?`
   / `Which|What X has V as its R?`. No match -> base clarify unchanged.
4. Map R with `FakeEars._relation`, collect every subject S with a live
   taught (S, R, V) triple in teach order, reply "Bob is the boss of Tom."
   (several: "... of Tom and Sue."; none: "I don't know anyone whose boss
   is Bob." -- never invents).

No `_act` override: the stage emits clarify actions only, which the loop's
`_act` passes through without writing (`scripts/fable_agent_loop.py:337-339`),
so a reverse question never writes. Relation/value spans are single noun
phrases (no `'s`/`of`/relative cues), so multi-hop reverse ("Whose mother's
boss is Bob?") matches no frame and keeps the base clarify: out of scope,
never answered wrong.

## What it means / does not mean

- Means: one-hop reverse questions over live taught facts answer exactly.
- Does not mean: the agent understands paraphrase or multi-hop reversal;
  anything outside the four frames still clarifies.
