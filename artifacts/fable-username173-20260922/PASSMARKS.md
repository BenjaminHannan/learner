# Exp 173 PASSMARKS — the agent learns the user's own name (sealed BEFORE any registered run)

Ben's ruling: "me" is the single user (loop166's USER entity). Base agent:
loop166 (scripts/fable_loop166_agent.py,
artifacts/fable-me166-20260922/loop166-config.json; its RESULTS.md,
PASSMARKS.md and design doc 166 were read first).

## Step 1 — what the base does with name turns today (file:line)

End to end, loop166 replies `I didn't understand that. Could you say it
another way?` and stores nothing for every director-probe turn (verified
live pre-seal): `My name is Sam.` / `I'm Dara.` / `Hi, I am Nell.` /
`Call me Dee.` / `What is my name?` / `What's my name?` / `Who am I?`.
`Who is Nell's sister?` (after `My sister is Ida.`) replies the honest
unknown `I don't know anyone called Nell.`

Mechanism: relation `name` is vetoed out of the me166 frames because
`is_office_head("name")` is True (scripts/fable_fix135_office.py:158-172;
`name` sits in the table-derived OFFICE_SINGLE_TITLES set), so
`canonical_relation("name")` returns None
(scripts/fable_fix166_me.py:83-106) and both `parse_me_teach` (:118-147)
and `parse_me_ask` (:150-173) refuse. The turn then falls through the whole
162b stack to `FakeEars`' final clarify
(scripts/fable_agent_loop.py:148). `Who am I?` / `Do you know my name?`
match no frame anywhere and clarify identically.

USER is created in `Bench73Stage._teach_action`
(scripts/fable_loop90_agent.py:153-170), which builds the teach/correct
action; the write goes through the listening doorway (`AgentLoop._act` ->
`_write`, scripts/fable_agent_loop.py:335-380) into the notebook, which
mints `E00xx` ids with the taught display name (`USER_KEY = "USER"`,
scripts/fable_fix166_me.py:49). Replies render without the raw key in
`rewrite_me166_reply` (scripts/fable_loop166_agent.py:57-77), applied to
parser-claimed turns in `Loop166AgentLoop._listening_tick` (:83-98).

The existing change-prompt path is the notebook's functional-relation
CONFLICT: `I have {subject}'s {relation} as {old}. Do you want me to
change it to {new}?` (scripts/fable_notebook_contract.py:79); `yes`
supersedes (`Saved: ...`), `no` keeps (`Okay, I left it as it was.`,
scripts/fable_listening_m1.py:154-163). The existing honest don't-know
forms are `I don't know anyone called {name}.` (:81, unknown entity) and
`I don't know {subject}'s {relation}.` (:82, known entity, unknown fact;
the me166 post-pass appends ` yet.` for first-person asks, e.g. F10
`I don't know your father yet.`).

## THE ONE CHANGE, behaviour

`Name173Mixin` (scripts/fable_fix173_username.py), stacked outermost as
`Loop173Ears(Name173Mixin, Loop166Ears)` in scripts/fable_loop173_agent.py
(no 166/162b file edited or touched):

- Statement `My name is X` / `I'm X` / `I am X` / `Call me X` /
  `You can call me X` (optional `Hi,/Hello,/Hey,` greeting with or without
  comma; optional trailing `.`/`!`/nothing; `?` stays a non-statement) with
  X = 1-3 tokens -> stores literal `(USER, name, X)` through 166's own
  gates (121 value, 102 hearsay, 150 subject screens) with `act="teach"`
  forced and `is_person=False` (a name statement creates no non-USER
  entity). Name-shaped = capitalised as typed (`My name is`/`Call me`
  capitalise a lowercase token silently; `I'm`/`I am` never accept a
  lowercase token) AND each token's lowercase form is absent from
  /usr/share/dict/words or a genuine given name (scripts GIVENS list holds
  real given names only). So `I'm Tired` / `I am Happy` (ordinary words)
  never name; `i'm tired`, `I am from Oslo`, `I am Kim's sister`,
  `Call me later`, `My name is not important` fall through to the loop166
  path byte-identically (loop166 clarifies all of them with 0 writes).
- Question `What is my name?` / `What's my name?` / `Who am I?` /
  `Do you know my name?` / `what is my name` -> ask `(USER, [name])` ->
  `Your name is X.` when set; `I don't know your name yet.` when unset
  (the me166 first-person unknown form, instantiated for `name`; when truly
  nothing was ever taught the miss arrives as UNKNOWN_ENTITY and
  `rewrite_name173_reply` in scripts/fable_loop173_agent.py maps that one
  line to the same sentence -- never the raw key).
- Second, different name: taught with `act="teach"`, so the functional
  `name` relation CONFLICTs and the turn takes the existing change-prompt
  path (`I have your name as Sam. Do you want me to change it to Max?`;
  `yes` -> `Saved: your name is Max.`, `no` -> `Okay, I left it as it
  was.`). Never a silent replace (unlike 166's `_teach_action`, which
  auto-upgrades to `correct`). Same-name reteach hits DUPLICATE_OK
  (`I already have that.`). A correction lead (`Actually, my name is
  Max.`) is stripped and treated as a plain name statement, so it also
  takes the change-prompt path. The completing `yes`/`no` turn is
  rewritten when a USER-name confirm is pending (its `Saved: ...` reply
  would otherwise leak the raw key); all other `yes`/`no` turns are
  untouched.
- After naming, third-person turns whose possessive head equals the stored
  name (`Nell's sister is Ida.`, `Who is Nell's sister?`,
  `Where is Max's mother's city?`) are re-dispatched with the head
  rewritten to `my`, storing/answering the SAME USER facts (relation
  teaches mirror `my`: silent supersede via `_teach_action`, exactly like
  F12). `Is X <Owner>'s <R>?` with X the stored name looks up
  (`<Owner>`, `<R>`) and compares to X: `Yes, X is <Owner>'s <R>.` /
  `No, <Owner>'s <R> is <V>.` / the reasoner's own untouched record when
  the lookup misses (existing unknown wordings preserved).
- All rendering reuses loop166's `rewrite_me166_reply` verbatim
  (`USER's` -> `your`, capitalise, ` yet.` rule) plus the one
  UNKNOWN_ENTITY line above. The mixin only claims name-statement /
  name-question turns (which loop166 always refuses) and stored-name-headed
  turns (impossible before a name is set -- and no suite input sets one);
  everything else is the loop166 code literally, byte-identical by
  construction.

## Sealed inputs

- T1: 166's sealed probe reused UNCHANGED:
  artifacts/fable-me166-20260922/cases166.json (52 rows).
- T1b: NEW probe artifacts/fable-username173-20260922/cases173.json
  (45 dialogues, fictional names only: 13 statement S01-S13, 11 look-alike
  L01-L11, 4 rename R1-R4, 7 third-person P1-P7, 5 unset U1-U5, 5 other
  O01-O05; each row runs on a FRESH loop, steps in order).
- Config: artifacts/fable-username173-20260922/loop173-config.json.
- G1 reference: BASE agent's frozen rows
  artifacts/fable-me166-20260922/fable_bench166_loop166_*_rows.jsonl
  (edit200/new/old splits), read-only.
- G2 reference: base marks166
  (artifacts/fable-me166-20260922/marks166, read-only). Bench splits +
  scorer v2 + 123 suites sealed in their own exps, read-only.
- G3 reference: loop166's own frozen rows
  artifacts/fable-me166-20260922/redteam136-loop166.json,
  redteam143-loop166.json, sessions152-loop166.json, read-only; only the
  NEW agent runs live. G3 inputs: sealed cases136.json,
  fable_redteam143_cases.json, sessions152.json, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop173 AND loop166 (scripts/fable_fix173_probe.py
  --which t1): 52/52 rows stored+teach-replies+ask-replies byte-identical
  to loop166. Prediction: 52/52 OK, ZERO moves.
- T1b probe (scripts/fable_fix173_probe.py --which t1b): S 13/13 name set
  + `What is my name?` answers; L 11/11 zero writes + byte-identical;
  R 4/4 change-prompt with yes-replaces/no-keeps + final answer; P 7/7
  USER-fact resolution incl. Is-yes/no/unknown; U 5/5
  `I don't know your name yet.` + 0 writes; O 5/5 byte-identical.
  Prediction: 45/45 OK.
- T2: 0 wrong writes over all 97 rows; S/U/L/R rows hold entities <=
  {USER} (0 new non-USER entities from name statements).
- G1 bench (scripts/fable_fix173_bench.py, base folder's bench121-lineage
  driver by import): per-item verdict AND reply AND teach-replies identical
  to the frozen loop166 rows on all 600 items, 0 new wrong. Prediction:
  ZERO moves.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case
  identical to base marks166 on every suite incl. p3/l2-cases.jsonl;
  whole-file equality after the disclosed scrub (drop timing keys
  seconds/wall_seconds/elapsed/duration/timings anywhere; rewrite the two
  agent paths, two config names, two artifact dirs, loop173/loop166 tokens
  to fixed tokens -- cosmetics only: suite summaries + sleep SKIP reason
  naming the new agent file). Prediction: 0 case-moves, 0 whole-diffs
  after scrub. Soak/rt110 flakes under load are the known mailbox race ->
  re-run that suite once in the open and report both.
- G3 (scripts/fable_fix173_g3.py): 0 verdict moves, 0 reply moves,
  0 new WRONG/WRONG-WRITE, 0 write moves vs loop166's frozen rows on
  redteam136 (145) + redteam143 (124) + sessions152 (180 turns).
  Prediction: ZERO moves.
- G4 each registered run (probe t1/t1b, bench, G3, marks123, diffs)
  < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds.
- Anything else, anywhere (any unpredicted verdict/reply/write move, any
  new WRONG, any raw-USER leak): FAIL, recorded as FAIL.

## Pre-seal evidence (dev only, NOT registered runs)

- Pure-function scan (scripts/fable_fix173_scan.py) of 2885 sealed input
  turns (G1 bench teaches+questions, marks-bench, cases136, redteam143,
  sessions152, p2 CASES strings, p4-30, rt110 cases, rt81 SEQS turns, q1
  fixed turns): 0 name-statement fires, 0 name-question fires, 0 raw-USER
  tokens. Hence no suite run can set a name, so every name-dependent frame
  (x-head, namecheck) is dead in all regressions: zero moves predicted.
- Dev trial of both probes to scratch (NOT artifacts): T1b 45/45 OK, T1
  52/52 byte-identical. The registered probes run after the seal.
- Reverse check on loop166 live: all 7 director-probe name turns clarify
  with 0 writes; `Who is Nell's sister?` -> the quoted unknown form.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_probe.py --which t1 --out artifacts/fable-username173-20260922/probe173-t1.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_probe.py --which t1b --out artifacts/fable-username173-20260922/probe173-t1b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop173_agent.py --config artifacts/fable-username173-20260922/loop173-config.json --out artifacts/fable-username173-20260922/marks173 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173_marksdiff.py
