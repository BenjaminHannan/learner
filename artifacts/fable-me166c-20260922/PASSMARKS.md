# Exp 166c PASSMARKS — a name's display takes Title-case only (sealed BEFORE any registered run)

Base agent: loop166 (scripts/fable_loop166_agent.py,
artifacts/fable-me166-20260922/loop166-config.json; RESULTS/PASSMARKS read).
Exp 166 is a registered FAIL on G3 only: sessions152 S4 turn 1's new correct
write (USER, dog, biscuit) from lowercase "biscuit" set the value entity's
display name, so 3 later replies render "biscuit's ..." where loop162b renders
"Biscuit's ..." (verdicts all OK, 0 new WRONG). Exp 166b is a registered FAIL
kept as FAIL: its registered G1 run moved 4 bench teach replies ("judo"
inside "World Judo Championships" upgraded a display); the adjacency guard
was added AFTER the seal and the marks re-ran in the open. Open results were
clean, but a registered FAIL stays FAIL. 166c registers the same feature
cleanly, plus one narrowing the director's 08:27 probe demanded: guarded-166b
renders "Your friend is ANA." after "My friend is ana." + "ANA's city is
Rome." -- an ALL-CAPS shout must never become the display name.

## Step 1 — where loop166/the contract sets and renders an entity's display name

- SETS: `Notebook.new_entity` (scripts/fable_notebook_contract.py:268-277)
  stores `name.strip()` as the ENTITY event name; `_apply`
  (:196-198) sets `entities[entity_id] = name` and files the
  case-insensitive alias (`_norm` lowercases at :116-117). Value entities
  are created with the typed surface in `Listening._person`
  (scripts/fable_listening_m1.py:50-57, called from `_teach` at :115), so
  lowercase "biscuit" stays lowercase; matching stays case-insensitive
  (`resolve` at :235-242).
- RENDERS: `Notebook._show` (:257-258) returns `entities[entity]`;
  `assert_fact` text (:349), `ask` answers/mid-chain-miss subjects
  (:390-420), and `FakeMouth.say` (scripts/fable_agent_loop.py:165-168) all
  copy the stored display verbatim. Loop166's own rewrite
  (scripts/fable_loop166_agent.py:57-77) only maps USER -> your/Your.

## THE ONE CHANGE, behaviour

`Loop166cAgentLoop` (scripts/fable_loop166c_agent.py, mixin subclass of
loop166's loop, same ears `Loop166Ears`, no 166/166b/162b/162/contract file
edited or touched): after each turn, for every entity whose stored display
is all-lowercase, if the turn contains a surface form that (a) differs ONLY
in letter case, (b) is Title-case (first letter uppercase, NOT all letters
uppercase; multi-token names: EVERY token Title-case; a single capital
letter counts), and (c) stands as the whole name (not adjacent, spaces
only, to another capitalised word -- 166b's adjacency guard, copied with
attribution), a per-loop override `{entity_id: Title-case form}` is recorded
and said lines are rewritten with it (word-boundary replace) from that turn
on. No ALIAS/DISPLAY event exists in the contract (ALIAS at :279-286 never
changes the display), so the override lives in the agent layer and the
notebook event log stays append-only. Entity identity, matching and writes
are exactly loop166's: stored triples and fact_writes are byte-identical on
every turn.

## Sealed inputs

- T1: artifacts/fable-me166-20260922/cases166.json (52 rows, read-only,
  reused unchanged).
- T1b: artifacts/fable-me166b-20260922/cases166b.json (30 dialogues,
  read-only, reused unchanged -- never copied or edited).
- T1c: artifacts/fable-me166c-20260922/cases166c.json (24 dialogues, this
  folder, sealed: 8 shout S01-S08 ALL-CAPS incl. the director's ana/ANA
  case, 8 embed E01-E08 lowercase names in capitalised titles/teams/events,
  8 title T01-T08 genuine Title-case first+third person; fictional names
  only; each row has group/cap/low).
- Config: artifacts/fable-me166c-20260922/loop166c-config.json (this folder).
- G1 reference: loop166's FROZEN rows
  artifacts/fable-me166-20260922/fable_bench166_loop166_*_rows.jsonl
  (edit200/old/new splits), read-only. Driver: the same bench121-lineage
  scripts/fable_loop129b_bench.py by import that 166b's G1 used, per-item
  compare.
- G2 reference: loop166's frozen marks166
  (artifacts/fable-me166-20260922/marks166), read-only.
- G3 inputs: sealed sessions152.json/cases136.json/redteam143 cases,
  read-only; loop166's frozen rows
  artifacts/fable-me166-20260922/*-loop166.json + loop162b rows, read-only
  (only the loop166c arm runs live).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop166c vs loop166 (scripts/fable_fix166c_probe.py):
  52/52 rows byte-identical (stored triples AND teach replies AND every ask
  reply), 0 new entities.
- T1b probe (scripts/fable_fix166c_probeB.py): 30/30 OK by the same verdict
  rules as 166b's probeB, AND per-case verdicts identical to loop166b's open
  re-run (artifacts/fable-me166b-20260922/probe166b-B.json).
- T1c new probe (scripts/fable_fix166c_probeC.py): 8/8 shout rows (stored +
  every reply byte-identical to loop166, lowercase display still shows),
  8/8 embed rows (stored + every reply byte-identical to loop166),
  8/8 title rows (stored equal, late replies + asks use `cap`, fix visibly
  fires vs loop166).
- T2: 0 wrong writes, 0 new entities vs loop166 on every T1+T1b+T1c case
  (106 rows).
- G1 bench (scripts/fable_fix166c_bench.py): per-item verdict AND reply
  identical to frozen loop166 rows on all 600 items, 0 new wrong.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case identical
  to frozen marks166 (whole-compare normalised for seconds + agent filename;
  sleep SKIP verdict identical, reason names the new file); soak/rt110 flakes
  under load are the known mailbox race -> re-run once in the open, both
  reported.
- G3 (scripts/fable_fix166c_g3.py): vs loop166 exactly the 3 predicted S4
  reply-case returns, 0 verdict moves, 0 new WRONG, 0 write moves; the 3 are
  byte-identical to loop162b frozen rows; S4/1 keeps loop166's state;
  redteam136 (145) + redteam143 (124) zero moves.
- G4 each registered run < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Predicted moves, in writing, before any registered run

- P166c.1: T1 52/52 byte-identical to loop166 (the 166 probe has no
  lowercase-then-Title-case mention; 0.85).
- P166c.2: T1b 30/30 OK with 0 wrong writes and 0 new entities, verdicts
  per-case identical to loop166b's open re-run (166c's trigger set is a
  subset of guarded-166b's; this probe has no ALL-CAPS surface; 0.80).
- P166c.3: T1c 24/24 OK (8/8 shout + 8/8 embed + 8/8 title) with 0 wrong
  writes and 0 new entities (0.80).
- P166c.4: G1 600/600 verdict+reply identical to loop166 frozen rows, 0 new
  wrong (166b's open re-run moved 0 with a WIDER trigger set; 166c only
  narrows it; 0.75).
- P166c.5: G2 per-case identical to marks166, zero moves everywhere (same
  narrowing argument; sleep reason names the new file; 0.65).
- P166c.6: G3 exactly 3 reply moves vs loop166 -- (S4-pets-identity, 2/3/26)
  return to byte-identical with loop162b (verdict+reply+fact_writes; S4's
  "Biscuit" mentions are genuine Title-case so the fix still fires there);
  S4/1 keeps (OK, "Saved: your dog is biscuit.", 1 write); all other 177
  session turns + redteam136/143 byte-identical; 0 new WRONG/WRONG-WRITE
  (0.75).
- P166c.7: every registered run < 1500 s Mac CPU; daemon idle_seconds OK
  (0.90).
- Anything else, anywhere (any unpredicted verdict/reply/write move, any new
  WRONG, any raw-USER leak): FAIL, recorded as FAIL.

## Pre-seal evidence (dev only, NOT registered runs)

- Helper unit checks (in-memory, no artifacts): "ANA" never qualifies,
  "Pip"/"Biscuit" qualify, "Judo" in "World Judo Championships" and "Hobbit"
  in "The Hobbit" rejected by the guard, "WUG" rejected; multi-token
  "Mary Jane" qualifies, "MARY JANE" does not.
- Director probe replicated live pre-seal in memory: loop166c "My friend is
  ana." + "ANA's city is Rome." -> "Saved: ana's city is Rome." (identical
  to loop166); "My cat is pip." + "Pip's toy is Mouse." -> "Saved: Pip's toy
  is Mouse."; "My dog is Biscuit." + "biscuit's toy is Ball." -> unchanged
  "Biscuit's" (identical to loop166).
- Narrowing argument (no fresh scan needed): every 166c trigger is also a
  guarded-166b trigger, and guarded-166b's open re-run moved 0 bench items,
  0 marks cases (besides the verdict-identical race log line), and exactly
  the 3 S4 returns on G3 -- all of which come from Title-case "Biscuit"
  mentions that 166c keeps.
- Daemon smoke: not yet run (runs only after the seal, inside G1/G3).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_probe.py --out artifacts/fable-me166c-20260922/probe166c-loop166c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_probeB.py --out artifacts/fable-me166c-20260922/probe166c-B.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_probeC.py --out artifacts/fable-me166c-20260922/probe166c-C.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166c_agent.py --config artifacts/fable-me166c-20260922/loop166c-config.json --out artifacts/fable-me166c-20260922/marks166c --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166c_marksdiff.py
