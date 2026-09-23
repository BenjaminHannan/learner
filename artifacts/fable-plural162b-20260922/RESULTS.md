# Exp 162b RESULTS (plain words for Ben) — SCORE: PASS

The idea: last time, names like "The Beatles" could never be taught because
a spelling rule ate the final "s" ("Beatles'" was read as "Beatle" plus a
dangling mark, then rejected). This run adds exactly that missing "s" back,
so plural names save and answer questions. Singular names ("The Hobbit")
take the old code path literally, so they cannot change.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 plural (24, 8 relations, Who+What+of-form asks) | 24/24 exact | 24/24 PASS (2.0 s) |
| T1 162 must-write rerun (26) | >= 25/26 OK | 26/26 PASS |
| T1 identical to loop162 (12 office + 11 nowrite) | 23/23 | 23/23 PASS |
| T1 chains C1/C2/C3 (C2+C3 through plurals) | all OK | 3/3 PASS |
| T2 wrong writes (76 rows) | 0 | 0 PASS |
| G1 bench 600/600 vs frozen loop162 rows | 0 moves, 0 new wrong | 0 moves PASS (22.6 s) |
| G2 marks123 per-case vs marks162 / marks150 | 0 moves except predicted | 0 semantic moves PASS (183.4 s) |
| G3 redteam136 (145) + redteam143 (124) + sessions152 (180 turns) | 0 moves, 0 new wrong | 0 moves PASS (14.3 s) |
| G4 every run < 1500 s Mac CPU | < 1500 s | max 183.4 s PASS |

Suite detail: p2 FAIL identical to base (2 OK->BUG / 4 still-BUG, 0 moves);
q1 F5+M5 FAIL identical (seconds only differ); rt81 61/0/13 identical
(0 moves); q4 leaks identical to marks150; bench tables identical (seconds
only differ); p3 l1-l6 all PASS (seconds only differ); rt110 62 cases 0
verdict moves, still-bug same 6, 0 harness errors (2 log-status cosmetic
diffs, replies identical); sleep SKIP both (reason names the new agent file
only); soak registered wrong=0 clean (base 162 had wrong=1, the known
empty-mailbox race -- clean here, so no open re-run needed).

## What it means

Plural "The"-names now teach, answer both question forms, and chain through
2 hops, with zero movement anywhere else: 600/600 bench, every marks123
suite verdict-identical, 449 G3 turns move-free.

## What it does not mean

It does not mean drummer/editor-class relations work -- those are outside
the loop's tables by design and still refuse; "The Beatles' manager" still
takes the old office path on purpose.

## Deviations (one, reported)

- Post-seal edit to my own G3 driver only
  (scripts/fable_fix162b_g3.py: create scratch subdirs; it crashed at
  startup with FileNotFoundError before producing anything). Sealed files
  byte-identical since the seal (`shasum -c` passes); G3 re-ran after the
  fix as the registered run. No sealed case/config/mark change.
- G3 base side runs live in the same script (loop162's folder holds no
  frozen sessions/redteam rows; 162 files never edited).
- marks123 ran with --workers 2 (gentler under load 66); daemon suites
  p3/rt110/q4 now complete thanks to the disclosed one-line
  `idle_seconds` harness fix.

## Questions for Ben

None.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_probe.py --out artifacts/fable-plural162b-20260922/probe162b-loop162b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop162b_agent.py --config artifacts/fable-plural162b-20260922/loop162b-config.json --out artifacts/fable-plural162b-20260922/marks162b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_marksdiff.py
