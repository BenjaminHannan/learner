# Exp 166b PASSMARKS — a name's display keeps its capital letter (sealed BEFORE any registered run)

Base agent: loop166 (scripts/fable_loop166_agent.py,
artifacts/fable-me166-20260922/loop166-config.json; RESULTS/PASSMARKS read).
Exp 166 is a registered FAIL on G3 only: sessions152 S4 turn 1's new correct
write (USER, dog, biscuit) from lowercase "biscuit" set the value entity's
display name, so 3 later replies render "biscuit's ..." where loop162b renders
"Biscuit's ..." (verdicts all OK, 0 new WRONG).

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

`Loop166bAgentLoop` (scripts/fable_loop166b_agent.py, subclass of loop166's
loop, same ears `Loop166Ears`, no 166/162b/162/contract file edited or
touched): after each turn, for every entity whose stored display is
all-lowercase, if the turn contains a surface form differing ONLY in letter
case whose first letter is uppercase, a per-loop override
`{entity_id: capitalised form}` is recorded and said lines are rewritten
with it (word-boundary replace) from that turn on. No ALIAS/DISPLAY event
exists in the contract (ALIAS at :279-286 never changes the display), so the
override lives in the agent layer and the notebook event log stays
append-only. Entity identity, matching and writes are exactly loop166's:
stored triples and fact_writes are byte-identical on every turn.

## Sealed inputs

- T1: artifacts/fable-me166-20260922/cases166.json (52 rows, read-only,
  reused unchanged).
- T1b: artifacts/fable-me166b-20260922/cases166b.json (30 dialogues,
  fictional names only: 12 lower-then-cap C01-C12 first+third person,
  8 cap-then-lower L01-L08, 10 other O01-O10; each row has group/cap).
- Config: artifacts/fable-me166b-20260922/loop166b-config.json (this folder).
- G1 reference: loop166's FROZEN rows
  artifacts/fable-me166-20260922/fable_bench166_loop166_*_rows.jsonl
  (edit200/old/new splits), read-only. Driver: base folder's bench121-lineage
  scripts/fable_loop129b_bench.py by import, per-item compare.
- G2 reference: loop166's frozen marks166
  (artifacts/fable-me166-20260922/marks166), read-only.
- G3 inputs: sealed sessions152.json/cases136.json/redteam143 cases,
  read-only; loop166's frozen rows
  artifacts/fable-me166-20260922/*-loop166.json + loop162b rows, read-only
  (only the loop166b arm runs live).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop166b vs loop166 (scripts/fable_fix166b_probe.py):
  52/52 rows byte-identical (stored triples AND teach replies AND every ask
  reply), 0 new entities.
- T1b new probe (scripts/fable_fix166b_probeB.py): 12/12 C rows (stored
  equal, late replies + asks use `cap`, fix visibly fires vs loop166);
  8/8 L rows byte-identical to loop166 (display stays capitalised);
  10/10 O rows byte-identical to loop166.
- T2: 0 wrong writes, 0 new entities vs loop166 on every T1+T1b case
  (82 rows).
- G1 bench (scripts/fable_fix166b_bench.py): per-item verdict AND reply
  identical to frozen loop166 rows on all 600 items, 0 new wrong.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case identical
  to frozen marks166 (whole-compare normalised for seconds + agent filename;
  sleep SKIP verdict identical, reason names the new file); soak/rt110 flakes
  under load are the known mailbox race -> re-run once in the open, both
  reported.
- G3 (scripts/fable_fix166b_g3.py): vs loop166 exactly the 3 predicted S4
  reply-case returns, 0 verdict moves, 0 new WRONG, 0 write moves; the 3 are
  byte-identical to loop162b frozen rows; S4/1 keeps loop166's state;
  redteam136 (145) + redteam143 (124) zero moves.
- G4 each registered run < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Predicted moves, in writing, before any registered run

- P166b.1: T1 52/52 byte-identical to loop166 (the 166 probe has no
  lowercase-then-capitalised mention; 0.85).
- P166b.2: T1b 30/30 OK (12/12 C + 8/8 L + 10/10 O) with 0 wrong writes and
  0 new entities (0.80).
- P166b.3: G1 600/600 verdict+reply identical to loop166 frozen rows, 0 new
  wrong (entity-level scan of all bench teaches+questions through base
  loop166: 0 triggers; 0.75).
- P166b.4: G2 per-case identical to marks166, zero moves everywhere (same
  scan over rt81 SEQS, p3-L2 turns, rt110 multi-turn cases, p2 steps: 0
  triggers; sleep reason names the new file; 0.65).
- P166b.5: G3 exactly 3 reply moves vs loop166 -- (S4-pets-identity, 2/3/26)
  return to byte-identical with loop162b (verdict+reply+fact_writes); S4/1
  keeps (OK, "Saved: your dog is biscuit.", 1 write); all other 177 session
  turns + redteam136/143 byte-identical; 0 new WRONG/WRONG-WRITE (0.75).
- P166b.6: every registered run < 1500 s Mac CPU; daemon idle_seconds OK
  (0.90).
- Anything else, anywhere (any unpredicted verdict/reply/write move, any new
  WRONG, any raw-USER leak): FAIL, recorded as FAIL.

## Pre-seal evidence (dev only, NOT registered runs)

- Director probe replicated live pre-seal: loop166 "My dog is biscuit." then
  "Biscuit's toy is Ball." -> "Saved: biscuit's toy is Ball."; loop166b ->
  "Saved: Biscuit's toy is Ball." with stored triples byte-identical.
- Entity-level scan (base loop166 driven over every bench teach+question,
  rt81 SEQS, p3-L2 turns, rt110 multi-turn cases, p2 steps, all sessions152):
  the fix triggers in exactly one place -- S4's biscuit entity (turns 2+).
  Third-person value slots store literals (no entity), so only subject and
  me-path value slots can carry lowercase displays.
- Dev trials of both probes to scratch (NOT artifacts): T1 52/52, T1b 30/30
  OK (two T1b case bugs found and fixed pre-seal: third-person value slots
  are literals; 1-hop OK answers echo question case -- cases rewritten to
  subject slots + mid-chain-miss asks). The registered probes run after the
  seal.
- Daemon smoke (scratch dir): Loop166bDaemon stores idle_seconds as given.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_probe.py --out artifacts/fable-me166b-20260922/probe166b-loop166b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_probeB.py --out artifacts/fable-me166b-20260922/probe166b-B.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166b_agent.py --config artifacts/fable-me166b-20260922/loop166b-config.json --out artifacts/fable-me166b-20260922/marks166b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166b_marksdiff.py
