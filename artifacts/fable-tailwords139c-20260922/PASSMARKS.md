# Exp 139c PASSMARKS — trailing chat words (loop138b + one strip), sealed before run

Agent: `scripts/fable_loop139c_agent.py` (Loop139cEars / Loop139cAgentLoop /
Loop139cMouth / Loop139cDaemon, build_agent139c, DEFAULT_CONFIG139C), mixin
subclass of loop138b; no loop138b file edited.
Change module: `scripts/fable_fix139c_tail.py` (closed lowercase list +
strip_chat_tail + sanitize_action(s) + ChatTailMixin).
Drivers: `scripts/fable_fix139c_cases.py` (writes cases139c.json),
`scripts/fable_fix139c_probe.py` (T1/T2),
`scripts/fable_fix139c_bench.py` (G1, imports
fable_loop138b_bench121.py + fable_bench121_run.py),
`scripts/fable_marks123_all.py` (G2, existing file, new args only),
`scripts/fable_fix139c_g3.py` (G3).
Config: `artifacts/fable-tailwords139c-20260922/loop139c-config.json`.
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, the case file, and the five scripts above.
Ledger P139c.1–P139c.6 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL.
No code edit after the seal except as reported in RESULTS.md (affected
marks re-run in the open).

## Step 1 (file:line, read before building)

- Value extraction: `scripts/fable_agent_loop.py:136` (FakeEars possessive
  path raw value span; loop138b wraps it with the exp-140 cleaner).
- 139b value guard: `scripts/fable_fix139b_valueguard.py:99`
  (`screen_value_139b`), per-action at `:118`/`:131`.

## THE ONE CHANGE (vs loop138b)

Before the save path, strip from the END of teach/correct values the
closed lowercase list (fixed in fable_fix139c_tail.py): too, as well,
also, actually, though, tho, lol, lmao, haha, btw, again, now, anyway,
then, instead, rn, right, ok, okay, i guess — each only when lowercase,
optionally followed by punctuation/emoji, only when >= 1 value word
remains. Capitalised tails never strip. Stripped now/instead/actually
go through the existing correction prompt with the clean value.

## Marks

- T1 (sealed probe `cases139c.json`, 61 cases: 31 tail covering every
  list word x >= 1 across 8 relations incl. single teaches, corrections
  with yes, questions/2-hop afterwards; 15 Title-case names/titles
  ending in a list word; 15 other teaches/questions): tail cases store
  the exact clean value (correction prompts carry the clean value,
  never the dirty tail); title/other cases byte-identical stored +
  replies to loop138b. Bar: every case OK.
- T2: 0 wrong writes over all 61 cases; >= 95 % of tail cases exact
  (>= 30/31).
- G1 bench (4 splits vs sealed `fable_bench121_loop138b_*_rows.jsonl`):
  0 new wrong; predicted moves: NONE (all per-item verdicts and replies
  identical). Any move or new wrong = FAIL.
- G2 marks123 (`--out artifacts/fable-tailwords139c-20260922/marks139c`):
  every suite per-case identical to `marks138b`. Any unpredicted
  per-case move = FAIL.
- G3 redteam136 + redteam143 + sessions152 (vs `redteam136-loop138b.json`,
  `redteam143-loop138b.json`, `sessions152-loop138b.json`): 0 new
  WRONG/WRONG-WRITE; predicted moves: NONE. Any new wrong/write = FAIL.
- G4: each registered run < 25 min Mac CPU wall-clock; daemon wrappers
  take idle_seconds (default 30.0; regression drivers use 3600.0).

## Predictions (ledger P139c.1–P139c.6, falsified = FAIL)

- P139c.1: T1 61/61 OK. Falsified by any non-OK case.
- P139c.2: T2 0 wrong writes, 31/31 tail exact. Falsified by any
  WRONG-WRITE or any inexact tail case.
- P139c.3: G1 0 new wrong, 0 moves on all 4 splits. Falsified by any
  move or new wrong.
- P139c.4: G2 per-case identical to marks138b on every suite.
  Falsified by any per-case move.
- P139c.5: G3 0 new WRONG/WRONG-WRITE, 0 moves on all three suites.
  Falsified by any move, new WRONG, or new write.
- P139c.6: every registered run < 1500 s wall-clock. Falsified by any
  run >= 1500 s.
