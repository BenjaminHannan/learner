# 166 — First-person ("my") user entity (Muse)

## Step 1: what the base does with "My mom is Rita." (file:line first)

End to end, loop162b replies `I didn't understand that. Could you say it
another way?` and stores nothing. The deepest template layer,
`FakeEars.hear` (scripts/fable_agent_loop.py:112-148), splits teach
subjects on the possessive in `_chain` (:101-102): `My mom` has no `'s`, so
it yields one part and can never reach the teach action at :145-147; `Who
is my mom?` likewise never reaches the ask action at :128-129. No 162b
stack layer claims `my`-headed turns either -- the 162/162b frames require
`The`-initial subjects (scripts/fable_fix162_thename.py:88,
scripts/fable_fix162b_plural.py:44-85). Entities are created in
`Bench73Stage._teach_action` (scripts/fable_loop90_agent.py:153-170); the
write flows through the listening doorway (`AgentLoop._act` -> `_write`,
scripts/fable_agent_loop.py:335-380) into the notebook.

## The one change (behaviour)

`Me166Mixin` (scripts/fable_fix166_me.py), stacked outermost as
`Loop166Ears(Me166Mixin, Plural162bMixin, TheName162Mixin,
OfficeholderGuardMixin, Loop150Ears)` in scripts/fable_loop166_agent.py:

- teach `My <R> is <V>.` (single relation; Actually-/No- corrections;
  same qualifier strip as base) saves `(USER, key, V)` through 162's own
  gates (relation-shape + office-head veto, 121 value, 102 hearsay, 150
  subject, `Bench73Stage._teach_action`, `is_person=True` so values stay
  entity-valued for hops). `USER` is the one reserved key, fixed in the mixin.
- ask `Who/What/Where is|are my <chain>?` (up to 3 links; mom/mum/mummy/
  mommy->mother, dad/daddy/papa/pop->father) runs the normal hop path with
  name=USER, so `Where is my mom's city?` chains with no hop rule.
- `Loop166AgentLoop._listening_tick` rewrites said lines only for
  parser-claimed turns: `Saved: your mother is Rita.` / `Your mother is
  Rita.` / unknown `I don't know your mother yet.` Mid-chain misses keep
  base wording (`I don't know Rita's city.`). The raw key never renders.

Only `my`-headed turns are claimed (loop162b refuses every one: verified 0
base writes over the 25 probe rows). Second-person turns, bare/third-person
turns, office heads (`My manager is Tom.`), chained teaches (`My mom's
city is X`), and multi-word relations fall through to the loop162b code
literally -- byte-identical by construction, not by testing.

## Why this shape

- Outermost-only-claims-what-base-refuses keeps the blast radius at the
  first-person frame: the pre-seal scan of 2885 sealed turns finds exactly
  3 fires (`my dog is biscuit` in sessions152; `What is my mother?` / `My
  city is Lisbon.` in rt81 O_user, also inside p3 L2) -- each predicted in
  PASSMARKS with its exact new verdict/reply/write.
- Reusing `Bench73Stage._teach_action` (which already decides teach vs
  correct by existing row) gives `Actually, my mom is Zara.` corrections
  with no new rule; taught facts still supersede only by correction, never
  by inference.
- Reply rewrite at `_listening_tick` (not in the ears or mouth) covers all
  transports at once -- direct `turn()`, mailbox daemon, soak subprocess --
  with one gate (parser-claimed), so unclaimed turns return super()'s event
  untouched.

## Limits (claims never exceed evidence)

- Sealed suites pin the OLD refusal in rt81 O_user and p3 L2: those move by
  design (2 per-case moves + L2 pass flip), predicted exactly, nothing else.
- One sessions152 turn (`my dog is biscuit`, S4-pets-identity/1) moves from
  UNHELPFUL to OK -- the session designer had marked it `expect: teach`.
- A literal user input of `USER's mother is ...` (probe control O13) still
  writes entity USER on the base path; the key then appears raw, exactly as
  on the base -- out of scope, documented.
- Multi-word relations (`best friend`) and office heads stay on the base
  path; `What is my name?`-class turns map to USER when storable.

## Reproduce

Sealed config + 52-case probe in artifacts/fable-me166-20260922/;
`scripts/fable_fix166_probe.py`, `scripts/fable_fix166_bench.py` (vs the
base folder's frozen loop162b rows), `scripts/fable_fix166_g3.py`,
`scripts/fable_marks123_all.py --agent scripts/fable_loop166_agent.py
--config …/loop166-config.json --workers 2`,
`scripts/fable_fix166_marksdiff.py` (vs marks162b, vs marks150 for
p3/rt110/q4, with predicted-move triage).
