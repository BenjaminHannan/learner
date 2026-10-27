# Exp 139d PASSMARKS — unknown chat-tail clarify (loop139c + one rule), sealed before run

Agent: `scripts/fable_loop139d_agent.py` (Loop139dEars / Loop139dAgentLoop /
Loop139dMouth / Loop139dDaemon, build_agent139d, DEFAULT_CONFIG139D), mixin
subclass of loop139c; no loop139c file edited.
Change module: `scripts/fable_fix139d_tail.py` (closed connector list +
unknown_tail_split + check_value + guard_action(s) + UnknownTailMixin).
Drivers: `scripts/fable_fix139d_cases.py` (writes cases139d.json),
`scripts/fable_fix139d_probe.py` (T1/T2),
`scripts/fable_fix139d_bench.py` (G1, imports
fable_loop138b_bench121.py + fable_bench121_run.py),
`scripts/fable_marks123_all.py` (G2, existing file, new args only),
`scripts/fable_fix139d_g3.py` (G3),
`scripts/fable_fix139d_compareg2.py` (G2 semantic compare vs marks139c),
`scripts/fable_fix139d_scan.py` (pre-seal static scan, not a mark).
Config: `artifacts/fable-tail139d-20260922/loop139d-config.json`.
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, the case file, and the scripts above.
Ledger P139d.1–P139d.6 appended pre-run.

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

## THE ONE CHANGE (vs loop139c)

After 139c's strip, if a teach/correct value's FIRST word starts with A-Z
and its trailing RUN of words is all all-lowercase letters ([a-z]+), none
a name connector, the turn does not write and replies exactly:
`Did you mean "<clean>"? Please say it again without the extra words.`
Connector list (fixed in fable_fix139d_tail.py): of, the, and, de, da,
del, della, di, du, des, van, von, der, den, la, le, les, y, e, al, el,
bin, ibn, upon, on, in, at, for, a, an, to, with. Lowercase-start values
and all-Capitalised / connector-ending names pass through byte-identical.
Honest edge: real tail-shaped values (e.g. "Pad thai") are questioned.

## Marks

- T1 (sealed probe `cases139d.json`, 62 cases: 28 unknown-tail covering
  22 distinct non-139c-list tails x 8 relations incl. 5 corrections + the
  Pad-thai honest edge -> exact clarify reply, 0 writes; 16 same-shape
  connector/lowercase/Title values + 18 other teaches/questions
  byte-identical stored + replies to loop139c). Bar: every case OK.
- T2: 0 wrong writes over all 62 cases; 28/28 tailu exact.
- G1 bench (4 splits vs sealed `fable_bench121_loop139c_*_rows.jsonl`):
  0 new wrong; predicted moves: NONE (pre-seal scan of all 800 bench
  item turns: 0 trigger-shaped teach spans). Any move or new wrong = FAIL.
- G2 marks123 (`--out artifacts/fable-tail139d-20260922/marks139d`):
  per-case semantic (verdict+reply) identical to `marks139c`; predicted
  moves: NONE (scripted closed-form teaches; only volatile-metadata /
  cosmetic diffs may appear: timings, tmp paths, statuses, p3
  replied_before_kill counts, sleep SKIP reason naming the new file).
  Any semantic per-case move = FAIL.
- G3 redteam136 + redteam143 + sessions152 (vs `redteam136-loop139c.json`,
  `redteam143-loop139c.json`, `sessions152-loop139c.json`): 0 new
  WRONG/WRONG-WRITE; predicted moves: NONE (pre-seal scan of all actual
  G3 turns: 0 trigger-shaped teach spans). Any new wrong/write = FAIL.
- G4: each registered run < 25 min Mac CPU wall-clock; daemon wrappers
  take idle_seconds (default 30.0; regression drivers use 3600.0).

## Predictions (ledger P139d.1–P139d.6, falsified = FAIL)

- P139d.1: T1 62/62 OK. Falsified by any non-OK case.
- P139d.2: T2 0 wrong writes, 28/28 tailu exact. Falsified by any
  WRONG-WRITE or any inexact tailu case.
- P139d.3: G1 0 new wrong, 0 moves on all 4 splits. Falsified by any
  move or new wrong.
- P139d.4: G2 per-case semantic identical to marks139c on every suite.
  Falsified by any semantic per-case move.
- P139d.5: G3 0 new WRONG/WRONG-WRITE, 0 moves on all three suites.
  Falsified by any move, new WRONG, or new write.
- P139d.6: every registered run < 1500 s wall-clock. Falsified by any
  run >= 1500 s.
