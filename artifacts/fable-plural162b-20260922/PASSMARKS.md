# Exp 162b PASSMARKS — plural "The Xs'" possessives save (sealed BEFORE any registered run)

Follow-up to the registered FAIL of exp 162
(artifacts/fable-thename162-20260922/RESULTS.md, diagnosis note 1): the teach
regex `The\s+(.+?)('s|s')\s+…` consumes the stem-final "s" into the `s'`
branch, so "The Beatles'" parses as stem "Beatle" + `s'`; the stem guard
(`endswith("s")`) then rejects every plural and the turn falls to the base
refusal. Base agent: loop162 (scripts/fable_loop162_agent.py,
artifacts/fable-thename162-20260922/loop162-config.json).

THE ONE CHANGE, behaviour (scripts/fable_fix162b_plural.py,
Plural162bMixin, stacked outermost as
`Loop162bEars(Plural162Mixin, TheName162Mixin, OfficeholderGuardMixin,
Loop150Ears)` in scripts/fable_loop162b_agent.py; no 162 file edited, no 162
file touched at all): plural possessives "The Xs' R is V." save subject
"The Xs" (name = stem + "s") through 162's own gates (relation-key gate,
loop121 value screen, loop102 hearsay check, 150 subject screen,
Bench73Stage._teach_action, is_person=True). The mixin only claims turns
whose marker is the plural `s'` branch; every other turn -- all singular
`'s`, office phrases, asks -- takes the loop162 code path literally, so
singular behaviour is byte-identical by construction. Ask side is 162's
unchanged code (plural chains + of-form already resolve once the entity is
taught). Allowed second change, HARNESS ONLY (disclosed): 162's
`_DaemonBase.__init__` copy dropped the `self.idle_seconds =
float(idle_seconds)` line its loop150 template has, so `run()` raises
AttributeError; `_DaemonBase162b` re-adds that one line after delegating to
162's own `__init__`. No teach/ask code touched.

## Sealed inputs

- T1/T2 probe: artifacts/fable-plural162b-20260922/cases162b.json (76 rows:
  24 NEW plural P01-P24 across 8 table relations author/founder/genre/
  performer/manufacturer/headquarters_location/official_language/employer x
  3 plural names, each teach + Who-ask + What-ask + of-form ask; 162's 26
  must-write W01-W26 + 2 chains C1-C2 copied VERBATIM; 12 office O01-O12 +
  11 must-not-write N01-N11 copied verbatim and flagged identical_to_base;
  1 NEW 2-hop plural chain C3 through a plural with both ask forms).
- Config: artifacts/fable-plural162b-20260922/loop162b-config.json (this folder).
- G1 reference: BASE agent's frozen rows
  artifacts/fable-thename162-20260922/fable_bench162_loop162_*_rows.jsonl
  (edit200/new/old splits), read-only.
- G2 reference: base marks162
  (artifacts/fable-thename162-20260922/marks162) for suites 162 completed;
  sealed marks150 (artifacts/fable-fix150-20260922/marks150) for p3/rt110/q4
  which 162 could not run. Bench splits + scorer v2 + 123 suites sealed in
  their own exps, read-only.
- G3 inputs: sealed cases136.json, fable_redteam143_cases.json,
  sessions152.json, read-only. Loop162's folder holds no frozen
  sessions/redteam rows, so the base side runs live in
  scripts/fable_fix162b_g3.py (162 files never edited).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop162b (scripts/fable_fix162b_probe.py): 24 plural ->
  24/24 exact triples + all 3 asks answering V; 162's 26 must-write rerun ->
  >= 25/26 OK; 23 identical_to_base rows (12 office + 11 nowrite) -> 23/23
  stored+reply byte-identical to loop162; chains C1/C2/C3 -> all OK.
- T2: 0 wrong writes over all 76 rows.
- G1 bench (scripts/fable_fix162b_bench.py, reuse of the base folder's
  bench121 driver by import): per-item verdict AND reply identical to the
  frozen loop162 rows on all 600 items except predicted items (prediction:
  ZERO moves), 0 new wrong, every move (none predicted) listed.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case identical
  to the base marks folder except predicted cases (prediction: ZERO moves on
  every suite; sleep SKIP verdict identical, reason text names the new agent
  file; soak/rt110 flakes under load are the known mailbox race -> re-run
  that suite once in the open and report both).
- G3 sessions152 + redteam136/143 (scripts/fable_fix162b_g3.py, base-folder
  patterns): 0 per-case verdict moves vs loop162, 0 new WRONG/WRONG-WRITE,
  0 new writes, every move predicted (none).
- G4 each registered run (probe, bench, G3, marks123, diffs) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Plural parse check: "The Beatles'/Rolling Stones'/Times'/Supremes'" all
  parse to the full "The Xs" name; loop162's parse returns None on all four.
- Disjointness audit over all 51 162 turns + 76 new turns: the 162b plural
  frame claims NOTHING loop162 claims, except the ss-stem edge ("The Class'"
  -> base saves truncated "The Clas", 162b saves "The Class"); no such input
  exists in any probe/bench/suite file, so singular byte-identity holds over
  every sealed input.
- Pure-function scan: 0 plural-teach fires in 600 bench teaches, 0 ask-frame
  fires in bench questions, 0 plural fires in cases136.json,
  fable_redteam143_cases.json, sessions152.json, p4-innocent-30,
  fable_redteam110_cases.json, fable_redteam81_results.json.
- Daemon check: Loop162bDaemon stores idle_seconds=45.0 as given;
  Loop162Daemon has the attribute MISSING (confirms the 162 bug).
- Known limitation (unchanged from 162): drummer/editor-class relations stay
  outside the tables and refuse; "The Beatles' manager" stays on the base
  officeholder path (verified identical_to_base O12).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_probe.py --out artifacts/fable-plural162b-20260922/probe162b-loop162b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop162b_agent.py --config artifacts/fable-plural162b-20260922/loop162b-config.json --out artifacts/fable-plural162b-20260922/marks162b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162b_marksdiff.py
