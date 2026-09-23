# Exp 167 PASSMARKS — verb-phrase facts map onto existing relations (sealed BEFORE any registered run)

Ben's ruling (2026-09-22): anything that can be read as a relation should
be. Today loop162b clarifies every verb-phrase turn ("Kwame lives in
Accra." -> "I didn't understand that...", scripts/fable_agent_loop.py:148
FakeEars.hear fallthrough) while the possessive form saves ("Kwame's city
is Accra." -> teach). Base agent: loop162b
(scripts/fable_loop162b_agent.py,
artifacts/fable-plural162b-20260922/loop162b-config.json).

THE ONE CHANGE, behaviour (scripts/fable_fix167_verb.py, Verb167Mixin,
stacked outermost as `Loop167Ears(Verb167Mixin, Plural162bMixin,
TheName162Mixin, OfficeholderGuardMixin, Loop150Ears)` in
scripts/fable_loop167_agent.py; no 162b file edited): the closed table
(fixed in design/v3/30-modes/167-verb-muse.md before any panel read) --
"lives in"->city, "works for"->employer, "was born in"->place_of_birth
(all in the base inventory: FakeEars possessive writes+answers city today,
employer/spouse/place_of_birth in ALLOWED_KEYS;
scripts/fable_fix162_thename.py:79): a claimed turn is rewritten to its
possessive twin ("Kwame lives in Accra." -> "Kwame's city is Accra.";
"Where does Kwame live?" -> "Where is Kwame's city?") and handed to
super().hear(), so writes/answers are the possessive path's own by
construction. Never claimed: "X is married to Y" statements (bench73 owns,
:96), "X was born in the city of Y" (bench73 owns, :114), negations, tense
changes, hedges, hypotheticals, yes/no verb questions, multi-word or
closed-class (150c) subjects, two-sentence turns ("." in value), "Who is X
married to?" (declined: lateral move, needs wife~=spouse; future work).

## Sealed inputs

- T1/T2 probe: artifacts/fable-verb167-20260922/cases167.json (61 rows:
  20 mapped M01-M20 -- 5 lives + 5 works + 5 born verb statements each with
  verb-Q + possessive-Q asks and a possessive-twin triple check vs base, 5
  married statements (base-owned) with possessive-Q asks + twin check;
  18 nowrite N01-N18 -- 6 negations, 6 tense changes, 6 hedges/
  hypotheticals; 20 other O01-O20 flagged identical_to_base; 3 chains
  C1-C3 incl. 2-hop asks ending at verb-taught facts).
- Config: artifacts/fable-verb167-20260922/loop167-config.json.
- Code: scripts/fable_fix167_verb.py, scripts/fable_loop167_agent.py;
  drivers scripts/fable_fix167_probe.py, scripts/fable_fix167_bench.py,
  scripts/fable_fix167_g3.py, scripts/fable_fix167_marksdiff.py.
- G1 reference: BASE agent's frozen rows
  artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl
  (edit200/old/new), read-only.
- G2 reference: base marks162b
  (artifacts/fable-plural162b-20260922/marks162b, all suites completed),
  read-only.
- G3 inputs: sealed cases136.json, fable_redteam143_cases.json,
  sessions152.json, read-only. Loop162b's folder holds no frozen
  sessions/redteam rows, so the base side runs live in
  scripts/fable_fix167_g3.py (162b files never edited).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop167 (scripts/fable_fix167_probe.py): 61/61 OK --
  20/20 mapped (verb teach stores expected triple = possessive-twin triple
  on base; every verb-Q and possessive-Q contains V), 18/18 nowrite (0
  writes + didnt-clarify), 20/20 other (stored+reply byte-identical to
  loop162b), 3/3 chains.
- T2: 0 wrong writes over all 61 rows (no TWIN-DIFF, no WRONG-WRITE).
- G1 bench (scripts/fable_fix167_bench.py, base folder's bench121 driver by
  import): per-item verdict AND reply identical to frozen loop162b rows on
  all 600 items, 0 new wrong, every move listed (prediction: ZERO moves).
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case
  identical to the base marks folder except predicted cases
  (scripts/fable_fix167_marksdiff.py): prediction -- rt110 rows P1 + P3
  move exactly as evidenced below (new log[0] contains "Saved: Mira's city
  is Oslo.", log[2] contains "Mira's city is Oslo."); sleep SKIP identical,
  reason names the new agent file; every other suite byte-identical modulo
  volatile "seconds"; soak/rt110 flakes under load are the known mailbox
  race -> re-run that suite once in the open and report both.
- G3 sessions152 + redteam136/143 (scripts/fable_fix167_g3.py): 0
  per-case verdict moves vs loop162b, 0 new WRONG/WRONG-WRITE, 0 new
  writes, every move predicted (prediction: none).
- G4 each registered run (probe, bench, G3, marks123, diffs) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs)

- Pure-function parse checks: 4 claimed statement shapes twin correctly
  (incl. Actually,-prefix and multi-word values); married statements,
  doesn't/does-not/isn't/wasn't, lived/used-to/will/move-to/worked/
  is-working, I-think/Maybe/Rumor/probably/If/Would, closed-class (Who/She)
  and multi-word subjects, "?"-terminated, born city-of, two-sentence
  turns, "Who is Kip married to?", yes/no verb questions all decline.
- Exact-schema scan (no agent runs): 0 verb-frame hits in 600 bench
  teaches+questions, cases136 (145), rt143 cases, sessions152 turns,
  p2 cases, rt81 rows, p4-innocent-30, q1 turns, loop96-marks turns, soak
  generator shapes. rt110: only P1/P2/P3 "Mira lives in Oslo[. ...]" texts
  hit; P2 (two sentences) vetoed by the "." rule, P4 ("She lives…")
  vetoed by the 150c rule.
- End-to-end on the 4 rt110 pronoun cases (base vs 167, temp dirs):
  P1 turns 0,2 move exactly as predicted (Saved/answer Oslo; triples
  [[Mira city Oslo]]), turn 1 identical; P3 same; P2/P4 byte-identical
  (replies + triples). New P1/P2 replies: "Saved: Mira's city is Oslo.",
  "I didn't understand...", "Mira's city is Oslo.".
- End-to-end verb smoke (temp dirs, dev names only): lives/works/born
  teach + verb-Q + Where/Who possessive-Q all answer; C1-C3 chain asks
  answer (employer-mid 2-hop cannot traverse non-person mids, so C3 ends
  at a verb-taught fact through a person mid -- verified).
- Daemon check (pre-seal): Loop167Daemon stores idle_seconds as given.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code/case/config/driver edits after the seal;
any edit is reported and the affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_probe.py --out artifacts/fable-verb167-20260922/probe167-loop167.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167_agent.py --config artifacts/fable-verb167-20260922/loop167-config.json --out artifacts/fable-verb167-20260922/marks167 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_marksdiff.py
