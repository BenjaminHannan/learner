# Exp 166 PASSMARKS — first-person ("my") user entity (sealed BEFORE any registered run)

Ben's ruling (2026-09-22): "me"/"my"/"I" is the user, and there is exactly
one user. Base agent: loop162b (scripts/fable_loop162b_agent.py,
artifacts/fable-plural162b-20260922/loop162b-config.json).

## Step 1 — what the base does with "My mom is Rita." today (file:line)

End to end, loop162b replies `I didn't understand that. Could you say it
another way?` and stores nothing (verified live pre-seal). Mechanism: the
first-person possessive matches no frame in the stack. The deepest template
layer, `FakeEars.hear` (scripts/fable_agent_loop.py:112-148), splits teach
subjects on the possessive in `_chain` (:101-102); `My mom` has no `'s`, so
it yields 1 part and can never reach the teach action at :145-147. The
question side is the same: `_chain("my mother")` is 1 part, so
`Who is my mom?` can never reach the ask action at :128-129. No layer of
the 162b stack (plural162b / thename162 / office135 / loop150 chain) claims
`my`-headed turns either -- the 162/162b frames require `The`-initial
subjects (scripts/fable_fix162_thename.py:88, scripts/fable_fix162b_plural.py:44-85).

Entities are created in `Bench73Stage._teach_action`
(scripts/fable_loop90_agent.py:153-170), which builds the
teach/correct action; the write itself goes through the listening doorway
(`AgentLoop._act` -> `_write`, scripts/fable_agent_loop.py:335-380) into
the notebook, which mints `E00xx` ids with the taught display name.

## THE ONE CHANGE, behaviour

`Me166Mixin` (scripts/fable_fix166_me.py), stacked outermost as
`Loop166Ears(Me166Mixin, Plural162bMixin, TheName162Mixin,
OfficeholderGuardMixin, Loop150Ears)` in scripts/fable_loop166_agent.py
(no 162b/162 file edited or touched):

- teach `My <R> is <V>.` (single relation, optional Actually-/No- correction
  prefix, same trailing-qualifier strip as the base) -> saves
  `(USER, <canonical key>, V)` via 162's own gates (T162 relation-shape gate
  + exp-135 office-head veto, loop121 value screen, loop102 hearsay check,
  150 subject screen, `Bench73Stage._teach_action` with `is_person=True` so
  values stay entity-valued and mid-chain hops work). `USER_KEY = "USER"`,
  fixed in scripts/fable_fix166_me.py, is the one reserved entity.
- ask `Who/What/Where is|are my <chain>?` (1-3 possessive links, relation
  synonyms mom/mum/mummy/mommy->mother, dad/daddy/papa/pop->father) ->
  normal hop path with name=USER.
- replies render without the raw key (`Loop166AgentLoop._listening_tick`
  post-pass, same file, only for parser-claimed turns): `Saved: your mother
  is Rita.` / `Your mother is Rita.` / `Your mother's city is Lisbon.` /
  unknown `I don't know your mother yet.` (mid-chain miss keeps the base
  wording, e.g. `I don't know Rita's city.` -- no key to leak).

The mixin only claims `my`-headed turns (second-person `your...`, bare and
third-person turns, office heads e.g. `My manager is Tom.`, chained teaches
e.g. `My mom's city is X`, and multi-word relations never match); all of
those take the loop162b code path literally, byte-identical by
construction. `What is my name?`-class turns whose relation is storable are
first-person and map to USER by the same rule (documented, not probed).

## Sealed inputs

- T1/T2 probe: artifacts/fable-me166-20260922/cases166.json (52 rows: 25
  first-person F01-F25 across 8 relations mother/father/sister/brother/
  friend/city/husband/wife incl. mom/mum/mummy/daddy synonyms, 3 two-hop
  rows, 3 correction rows, duplicate, 2 unknowns, mid-chain miss;
  10 agent-itself A01-A10; 17 other O01-O17; A+O flagged identical_to_base).
- Config: artifacts/fable-me166-20260922/loop166-config.json (this folder).
- G1 reference: BASE agent's frozen rows
  artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl
  (edit200/new/old splits), read-only.
- G2 reference: base marks162b
  (artifacts/fable-plural162b-20260922/marks162b) for completed suites;
  sealed marks150 (artifacts/fable-fix150-20260922/marks150) for p3/rt110/q4
  (same fallback 162b's brief allows). Bench splits + scorer v2 + 123 suites
  sealed in their own exps, read-only.
- G3 inputs: sealed cases136.json, fable_redteam143_cases.json,
  sessions152.json, read-only. Loop162b's folder holds no frozen
  sessions/redteam rows, so the base side runs live in
  scripts/fable_fix166_g3.py (162b files never edited).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop166 (scripts/fable_fix166_probe.py): 25/25
  first-person rows OK (stored triples exact incl. (USER,...) rows,
  teach replies Saved/already, every ask want-substring hit); 27/27
  identical_to_base rows stored+teach-reply+every-ask-reply byte-identical
  to loop162b; raw USER key in no reply except the literal-USER control O13
  (identical to base by construction).
- T2: 0 wrong writes over all 52 rows (no WRONG-WRITE verdict).
- G1 bench (scripts/fable_fix166_bench.py, base folder's bench121-lineage
  driver by import): per-item verdict AND reply identical to the frozen
  loop162b rows on all 600 items, 0 new wrong. Prediction: ZERO moves.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case
  identical to the base marks folders EXCEPT the 3 predicted cases below;
  sleep SKIP verdict identical, reason text names the new agent file;
  soak/rt110 flakes under load are the known mailbox race -> re-run that
  suite once in the open and report both.
- G3 (scripts/fable_fix166_g3.py, base-folder patterns): EXCEPT the 1
  predicted turn below, 0 per-case verdict moves vs loop162b, 0 new
  WRONG/WRONG-WRITE, 0 new writes.
- G4 each registered run (probe, bench, G3, marks123, diffs) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Predicted moves, in writing, before any registered run (all by design)

- P166-G3: exactly ONE sessions152 turn moves: (S4-pets-identity, n=1)
  `my dog is biscuit`: base UNHELPFUL + clarify + 0 writes -> loop166 OK +
  `Saved: your dog is biscuit.` + 1 write (USER, dog, biscuit). All other
  179 turns byte-identical (verdict+reply+fact_writes). redteam136 (145) +
  redteam143 (124): zero moves.
- P166-G2a: exactly TWO rt81 per-case moves, both O_user by design:
  O_user-02 `What is my mother?` UNCLEAR -> UNCLEAR, reply becomes
  `I don't know your mother yet.` (facts_delta 0, no new entity);
  O_user-03 `My city is Lisbon.` UNCLEAR -> BUG(question wrote), reply
  becomes `Saved: your city is Lisbon.` (facts_delta 1, +entity USER).
  Other 72/74 identical.
- P166-G2b: p3 L2 (same 74 SEQS vs loop90): changed_vs_loop90 becomes the 6
  pre-existing ids + O_user-02 + O_user-03; wrong_writes becomes exactly
  [O_user-03]; L2 pass True -> False. L1/L3/L4/L5z1/L5z2/L6 identical to
  marks150. (p3-report.json whole-compare triaged via p3/l2-cases.jsonl in
  scripts/fable_fix166_marksdiff.py.)
- Anything else, anywhere (any unpredicted verdict/reply/write move, any
  new WRONG, any raw-USER leak outside O13): FAIL, recorded as FAIL.

## Pre-seal evidence (dev only, NOT registered runs)

- Pure-function scan (scripts/fable_fix166_scan.py) of 2885 sealed input
  turns (G1 bench 600 teaches+questions, marks-bench 400, cases136,
  redteam143, sessions152, p2 CASES steps, p4-30, rt110 cases, rt81 SEQS
  turns, q1 fixed turns, loop96-marks strings): the me parser fires on
  exactly 3 -- `my dog is biscuit` (s152), `What is my mother?` + `My city
  is Lisbon.` (rt81 O_user, also inside p3 L2). Zero raw-USER tokens in any
  suite input. Soak turns are all `SoakPxxx's city...` (read in code).
- Reverse check: base loop162b over all 25 F-group turns stores NOTHING
  (0 writes) -- the me frames claim only turns the base refuses.
- Dev trial of the sealed probe to scratch (/tmp/me166_trial.json, NOT an
  artifact): 52/52 OK (25/25 first-person, 27/27 identical). The registered
  probe runs after the seal.
- Daemon smoke (scratch dir): Loop166Daemon stores idle_seconds=45.0 as
  given; mailbox turn `My mom is Rita.` -> `Saved: your mother is Rita.`,
  triple (USER, mother, Rita).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_probe.py --out artifacts/fable-me166-20260922/probe166-loop166.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166_agent.py --config artifacts/fable-me166-20260922/loop166-config.json --out artifacts/fable-me166-20260922/marks166 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_marksdiff.py
