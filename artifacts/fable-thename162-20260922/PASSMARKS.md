# Exp 162 PASSMARKS — possessive frame for "The"-initial names (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard). Director probe 03:45: "The Hobbit's
author is Tolkien.", "The Beatles' drummer is Ringo Starr.", "The
Guardian's editor is Kath Viner." On loop150/loop137 the office catch-all
`The (.+?) is (.+?)` (scripts/fable_bench73_english_arm.py line 127)
swallows them into a WRONG write ("Hobbit's author", officeholder,
"Tolkien" — "The" dropped); on loop135 (officeholder guard,
scripts/fable_fix135_office.py hear_teach135 at line 175,
OfficeholderGuardMixin.hear at line 205, artifacts/fable-fix135-20260922/)
a refusal. Either way the fact cannot be taught, so chains through
works/bands/papers break.

THE ONE CHANGE (scripts/fable_fix162_thename.py, TheName162Mixin; thin
loop162 = loop150 + 135 mixin + 162 mixin in
scripts/fable_loop162_agent.py with --daemon entry incl. idle_seconds;
loop150/loop135 imported read-only, no file edited): before the office
catch-all, a possessive teach frame "The X's R is V." / "The Xs' R is V."
where R normalises to a key in the loop's own relation tables (union of the
bench73/bench92 cue-table keys + the FakeEars person table, minus the
exp-135 office family; same ALLOWED_KEYS construction as exp 155, 42 keys)
and is not an exp-135 office head -> save (The X, R, V) with "The" kept, via
Bench73Stage._teach_action (structured teach, is_person=True like every
bench value so mid-chain hops stay entity-valued), guarded by the loop121
value screen, the loop102 hearsay-subject check and the 150 subject screen;
loop _act guards (139b value + 150 subject) still apply. All other turns
(non-table relations such as drummer/editor/manager/mood/uncle/captain/
birthplace, office Rs, hedged/two-fact turns) fall through to the base path
untouched. Question side: "The X's R ..." possessive chains (singular 's
and plural s') and "the R of The X ..." (optional trailing possessive
chain) resolve the leading The-name (case of "the" ignored, via the
notebook's own case-insensitive resolve) to the taught entity and return the
equivalent FakeEars ask; unresolvable turns stay on the base path
byte-identical. Office phrases ("The president of Zorvia is Mel Ash", "The
mayor of Leeds is Ann" — no possessive) never match either frame.

## Sealed mechanics (exact)

- Teach (strict full-turn; trailing "." stripped; loop121 trailing-qualifier
  strip applied first; correction prefix stripped, correct-vs-teach decided
  by Bench73Stage._teach_action's existing-row rule): `The <X>('s|s')
  <R> is <V>` with capital "The" (like the base catch-all); plural s'
  requires the stem to end in s. R must match `[A-Za-z][A-Za-z /-]*` AND
  normalise (lower, spaces->underscores) to ALLOWED_KEYS AND not be an
  exp-135 office head. V must pass screen_value_121; name must pass
  subject_is_hearsay_shaped + screen_subject_150.
- Ask (who/what/where + is/are): possessive split on 's/s' links, or the
  of-form `the <R> of <The X...>` (outer R gated by the same relation gate;
  inner chain + outer R appended, <= MAX_HOPS 3 relations). Claims the turn
  only when nb.resolve(name) is OK (exactly one entity); else base.
- is_person=True on all 162 teaches (bench parity: every bench value is
  entity-like; display triples identical; enables the T2 hop).

## Sealed inputs

- T1/T2 probe: artifacts/fable-thename162-20260922/cases162.json (51 rows:
  26 must-write across 8 table relations author/founder/genre/performer/
  manufacturer/headquarters_location/official_language/employer — works,
  bands, newspapers, ships, companies, singular 's + plural s' — each with
  possessive + of-form asks; 12 office phrases frozen to exact loop150x135
  triples+replies incl. the brief's 2 examples and the manager office write;
  11 must-not-write-wrong incl. the brief's weather example + drummer/editor
  (outside the tables) + two-fact/hedged/question shapes; 2 chain rows C1
  3-hop + C2 2-hop through The-names with person-relation continuations, no
  exp-159 hop rule).
- Configs: loop162-config.json, loop150x135-config.json (this folder).
- G1 reference: frozen loop150x135 bench rows
  (fable_bench162_loop150x135_{edit200,old_s2fresh_4hop,new_121_4hop}_rows.jsonl:
  150/50/0, 157/43/0, 136/63/1) via scripts/fable_loop129b_bench.py run_item
  by import. Run BEFORE the seal per the brief.
- G2 reference: sealed loop150 marks123 run
  (artifacts/fable-fix150-20260922/marks150) via scripts/fable_marks123_all.py.
- Bench splits + scorer v2, 123 suites: sealed in their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop162 (scripts/fable_fix162_probe.py): 26 must-write
  -> >= 95 % exact triples (bar: >= 25/26 OK; OK needs the exact triple +
  BOTH asks answering V); 12 office -> 12/12 stored+reply byte-identical to
  frozen; 11 must-not-write-wrong -> 0 wrong writes (didnt-kind clarifies);
  0 wrong writes over all 51 rows.
- T2 chains in the same probe: C1 (The Hobbit author Tolkien, Tolkien mother
  Mabel, Mabel spouse Robert; "Who is The Hobbit's author's mother's
  spouse?" + "Who is the spouse of The Hobbit's author's mother?") and C2
  (plural founder chain + of-form) -> both OK (answers Robert / Mary).
- G1 bench121 new + old fresh split + Fable-Edit per-item verdict AND reply
  identical to the frozen loop150x135 rows except predicted items
  (prediction: ZERO moves on all 600 items), 0 new wrong.
- G2 marks123 suites per-case identical to loop150's marks150 run except
  predicted cases (prediction: ZERO moves on every suite; sleep SKIP verdict
  identical, reason text names the new agent file; soak/rt110 flakes under
  load are a known mailbox race -> re-run that suite once in the open and
  report both).
- G3 each registered run (probe, bench, marks123, marks-diff) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of all 600 bench teach sentences: 0 match the The-name
  teach frame with an allowed relation -> 0 bench teach moves.
- Pure-function scan of 600 bench questions + suite case/report strings
  (redteam98 sealed v1 + results, loop102 reports + p4-innocent-30,
  redteam110 cases, loop117 reports, redteam81): ask-frame fires are
  of-form descriptions only ("the R of the <description>"); no taught
  entity can equal such a description (0 teach-frame fires anywhere), so
  the resolve gate keeps every one on the base path -> 0 ask moves.
- Base calibration on the loop150x135 reference (frozen into cases162.json):
  12 office rows store+reply verbatim (incl. the manager officeholder write
  "Beatles' manager" — identical-by-design, not a 162 write); 11 nowrite
  rows clarify "didn't understand" with no write.
- Reference bench (this folder, pre-seal): edit200 150/50/0, old_s2fresh
  157/43/0, new_121 136/63/1 — reproduces 135's K2 exactly.
- Known limitation (documented, not a move): drummer/editor/manager-class
  relations are outside the loop's tables, so those director-probe facts
  still refuse (drummer/editor) or take the base office path (manager);
  teaching them needs a relation-table change, out of scope for this one
  change.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162_probe.py --out artifacts/fable-thename162-20260922/probe162-loop162.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162_bench.py --variant loop162
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop162_agent.py --config artifacts/fable-thename162-20260922/loop162-config.json --out artifacts/fable-thename162-20260922/marks162 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix162_marksdiff.py
