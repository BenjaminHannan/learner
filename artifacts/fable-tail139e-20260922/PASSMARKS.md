# Exp 139e PASSMARKS — relation-gated unknown-tail clarify (loop139c + one rule), sealed before run

Agent: `scripts/fable_loop139e_agent.py` (Loop139eEars / Loop139eAgentLoop /
Loop139eMouth / Loop139eDaemon, build_agent139e, DEFAULT_CONFIG139E), mixin
subclass of loop139c; no loop139c/139d file edited (139d/139c code reused
by import only).
Change module: `scripts/fable_fix139e_tail.py` (closed LISTED_RELATIONS +
check_value + guard_action(s) + RelationGatedTailMixin; trigger/reply and
connectors imported read-only from `scripts/fable_fix139d_tail.py`, 139c
strip from `scripts/fable_fix139c_tail.py`).
Drivers: `scripts/fable_fix139e_cases.py` (writes cases139e.json),
`scripts/fable_fix139e_probe.py` (T1/T2),
`scripts/fable_fix139e_bench.py` (G1, imports
fable_loop138b_bench121.py + fable_bench121_run.py),
`scripts/fable_marks123_all.py` (G2, existing file, new args only),
`scripts/fable_fix139e_g3.py` (G3),
`scripts/fable_fix139e_compareg2.py` (G2 semantic compare vs marks139c),
`scripts/fable_fix139e_scan.py` (pre-seal static scan, not a mark).
Config: `artifacts/fable-tail139e-20260922/loop139e-config.json`.
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, the case file, and the scripts above.
Ledger P139e.1–P139e.6 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL.
No code edit after the seal except as reported in RESULTS.md (affected
marks re-run in the open).

## Step 1 (file:line, read before building)

- 139c's strip: `scripts/fable_fix139c_tail.py:46` (strip_chat_tail),
  applied in `scripts/fable_loop139c_agent.py:66` (ears hear) and `:82`
  (loop _act, before super()._act()).
- Value extraction: `scripts/fable_agent_loop.py:136` (FakeEars possessive
  path raw value span; loop138b wraps it with the exp-140 cleaner).
- 139b value guard: `scripts/fable_fix139b_valueguard.py:99`
  (`screen_value_139b`), per-action at `:118`/`:131`.
- 139d trigger+reply: `scripts/fable_fix139d_tail.py`
  (unknown_tail_split, clarify_text, CONNECTORS — imported read-only).
- 139d FAIL: `artifacts/fable-tail139d-20260922/RESULTS.md`
  (G1 20 new wrong on "Gaelic football" / "American football" /
  "Wa language"); design `design/v3/30-modes/139d-tail-muse.md`.

## THE ONE CHANGE (vs 139d; everything else byte-identical to loop139c)

The same 139d trigger and exact reply, but ONLY when the teach/correct
action's relation is in LISTED_RELATIONS (fixed in
`scripts/fable_fix139e_tail.py` before any panel read and in
`design/v3/30-modes/139e-tail-muse.md`): person-valued mother, father,
sister, brother, sibling, spouse, husband, wife, boss, friend, teacher,
coach, pet, dog; place-valued city, town, hometown/home_town, country,
birthplace/place_of_birth, school. NOT listed: sport, language, genre,
occupation, food, drink, color, instrument, every other relation.
Missing/empty relation never fires. "maybe"/"probably" never reach any
guard (base ears split-clarify first; locked as O19/O20); lowercase-start
values keep loop139c's exact behaviour (locked as O21).

## Pre-seal scan (scripts/fable_fix139e_scan.py; declarative templates included)

- bench121 all 800 taught triples (possessive + bench73 declarative):
  5375 triples, 0 gated hits. 139d's killers miss by relation:
  "Gaelic football"/"American football" are sport (unlisted),
  "Wa language" is language (unlisted) — the guard cannot fire there.
- marks-bench edit200 (575) + s2fresh (1600 triples): 0 hits.
- G3 turns: rt143 0, sessions152 0; rt136 3 static hits.
- marks123 chat suites: p4-innocent 0; p2-redteam98 1, rt110 3, rt81 1,
  p3-loop96 1 static hits; suite sources 0. Soak: single-token values,
  cannot trigger by shape.
- All 9 static hits verified end-to-end (fresh loop139e vs loop139c,
  pre-seal, not a registered run): every one is byte-identical stored +
  reply in both arms — base hearsay veto ("Bob, Ann said",
  "Ann, reportedly", "according to the web"), multi-fact split
  ("Lisbon and Mira's pet is a cat", ";" variant), or question path
  ("Also, how many facts do you know?") fires before any tail guard.
  Predicted moves from these: NONE.

## Marks

- T1 (sealed probe `cases139e.json`, 65 cases: 27 unknown-tail on listed
  relations covering honestly/tbh/fr/ngl/lowkey/obviously/basically/idk
  and more incl. 5 corrections + a stacked-tail run -> exact clarify
  reply, 0 writes; 17 same-shape incl. the three 139d killers "Gaelic
  football" / "American football" / "Wa language" plus "Pad thai"
  (now stores: food unlisted), "Bass guitar", "Hip hop", lowercase
  values, connector-ending names; 21 other teaches/questions incl.
  O19/O20/O21 base-identity locks, byte-identical stored + replies to
  loop139c). Bar: every case OK.
- T2: 0 wrong writes over all 65 cases; 27/27 tailu exact.
- G1 bench (4 splits vs sealed `fable_bench121_loop139c_*_rows.jsonl`):
  0 new wrong; predicted moves: NONE (pre-seal scan: 0 gated hits in
  all 5375 taught triples). Any move or new wrong = FAIL.
- G2 marks123 (`--out artifacts/fable-tail139e-20260922/marks139e`):
  per-case semantic (verdict+reply) identical to `marks139c` on every
  suite; predicted moves: NONE (all 9 static chat-suite hits verified
  byte-identical end-to-end pre-seal; only volatile-metadata / cosmetic
  diffs may appear: timings, tmp paths, statuses, p3
  replied_before_kill counts, sleep SKIP reason naming the new file).
  Any semantic per-case move = FAIL. rt110/soak harness-error flake
  under load is the known mailbox race: re-run once in the open,
  report both.
- G3 redteam136 + redteam143 + sessions152 (vs `redteam136-loop139c.json`,
  `redteam143-loop139c.json`, `sessions152-loop139c.json`): 0 new
  WRONG/WRONG-WRITE; predicted moves: NONE (rt143/sessions 0 static
  hits; all 3 rt136 static hits verified byte-identical end-to-end
  pre-seal). Any new wrong/write = FAIL.
- G4: each registered run < 25 min Mac CPU wall-clock; daemon wrappers
  take idle_seconds (default 30.0; regression drivers use 3600.0).

## Predictions (ledger P139e.1–P139e.6, falsified = FAIL)

- P139e.1: T1 65/65 OK. Falsified by any non-OK case.
- P139e.2: T2 0 wrong writes, 27/27 tailu exact. Falsified by any
  WRONG-WRITE or any inexact tailu case.
- P139e.3: G1 0 new wrong, 0 moves on all 4 splits. Falsified by any
  move or new wrong.
- P139e.4: G2 per-case semantic identical to marks139c on every suite.
  Falsified by any semantic per-case move.
- P139e.5: G3 0 new WRONG/WRONG-WRITE, 0 moves on all three suites.
  Falsified by any move, new WRONG, or new write.
- P139e.6: every registered run < 1500 s wall-clock. Falsified by any
  run >= 1500 s.
