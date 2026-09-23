# Exp 155 PASSMARKS — inverted-frame teach stage (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard). Director probe on loop150: "Rita is
Ann's mother." and "Rita is the mother of Ann." -> "I didn't understand
that" (no write); "The mother of Ann is Rita." -> a WRONG write ("mother of
Ann", officeholder, "Rita"). Exp 135's officeholder guard
(scripts/fable_loop135_agent.py, artifacts/fable-fix135-20260922/) turns
that wrong write into a refusal; 135 is not in loop150 yet (it arrives
through integration).

THE ONE CHANGE (scripts/fable_fix155_inverted.py, InvertedFrame155Mixin;
thin loop155 = loop150 + mixin in scripts/fable_loop155_agent.py with
--daemon entry incl. idle_seconds; loop150/loop135 imported read-only, no
file edited): an inverted-frame teach stage, ONLY for relation cues in the
loop's own relation tables (never the officeholder catch-all):
"V is X's R." / "V is the R of X." / "The R of X is V." -> save (X, R, V)
through the same guards, audit trail and replies as the canonical
"X's R is V.". Second config stacks the same mixin on loop150 + the 135
mixin to show they coexist (Loop155x135Ears).

## Sealed mechanics (exact)

- Frames (strict full-turn match; whitespace-collapsed; one trailing "."
  stripped; questions ending "?" and who/what/where-led turns never match):
  F1 `V is X's R`, F2 `V is the R of X`, F3 `The R of X is V`
  (correction lead "Actually, "/"No, " preserved onto the canonical twin).
- Relation gate: R must match `[A-Za-z][A-Za-z /-]*` AND normalise
  (lower, spaces->underscores) to a key in ALLOWED_KEYS AND must not be an
  exp-135 office head. ALLOWED_KEYS (42 keys, frozen in code) = union of
  fable_bench73_english_arm.REL_MENTION_CUES keys +
  fable_bench92_english_arm.REL_CUES92 keys + EXTRA_REL_CUES keys +
  fable_agent_loop.PERSON_RELATIONS, minus fable_fix135_office
  OFFICE_RELATIONS (officeholder / head_of_state / head_of_government /
  chairperson / chief_executive_officer / director_manager / head_coach /
  original_broadcaster). Includes mother father sister brother friend boss
  teacher wife husband neighbour neighbor partner child spouse capital author
  employer occupation founder creator developer genre sport performer
  continent manufacturer director_manager-excluded etc. (full list in code).
  Excludes: president/mayor/director/coach/... (office heads), king/uncle/...
  (not table keys), chairperson-family keys.
- Routing: base hear runs first. Any non-question/forget/ask base action
  other than clarify/teach/correct -> base untouched (asks, forgets, "?"-less
  questions like "who is ned's teacher" stay on the base path). A base
  non-officeholder teach/correct -> base wins byte-identical (bench73
  capital/author/official_language/founder patterns keep action+stage+audit).
  Else one-word X -> canonical twin "X's R is V." through the SAME
  super().hear (identical guards/audit/replies by construction), accepted
  only on exact (X, R, V) triple match, else base. Multi-word X (two-word
  names, "of"-names; FakeEars is one-word-only so no canonical exists) ->
  Bench73Stage-shaped structured teach/correct (is_person mirrored from
  FakeEars: key in PERSON_RELATIONS), returned only if the 121 value screen,
  the 102 hearsay-subject check and the 150 subject screen all pass, else
  base. Loop _act guards (139b value + 150 subject) still apply to all.
- Boundary (sealed, documented in doc 155): boss/teacher/friend invert to
  their correct triples (canonical teaches exist for them); president/mayor/
  king/governor/director/coach office phrases stay exactly on the base path.

## Sealed inputs

- I1 probe: artifacts/fable-inverted155-20260922/cases155.json (47 cases:
  35 must-write across 8 relations mother/father/sister/capital/author/
  spouse/child/friend x F1/F2/F3 x one-word/two-word/of-names, each with
  follow-up ask "Who is X's R?" wanting V; 12 must-not-write-wrong: 3 office
  phrases frozen to exact loop150 replies+triples, 1 non-table F1 nowrite, 1
  non-table F3 frozen to loop150 officeholder reply+triple, 2 hedged SPLIT
  nowrite, 2 two-fact nowrite, 1 hearsay-comma nowrite, 1 "?"-less question
  nowrite, 1 malformed-question nowrite).
- I2 probe: artifacts/fable-inverted155-20260922/cases155x135.json (5 cases
  on the 150+135 stack: 3 mother saves incl. multi-word X + asks; 2 office
  phrases frozen to exact loop135 replies+triples).
- Configs: loop155-config.json, loop155x135-config.json (this folder).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl) via
  scripts/fable_loop129b_bench.py run_item by import.
- G2 reference: sealed loop150 marks123 run
  (artifacts/fable-fix150-20260922/marks150) via scripts/fable_marks123_all.py.
- G3 reference: sealed exp-152 T-T session turns
  (artifacts/fable-session152-20260922/turns152-T-T-*.json) via
  scripts/fable_session152_run.py run_session/judge by import.
- Bench splits + scorer v2, 123 suites, 152 sessions: sealed in their own
  exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- I1 probe through loop155 (scripts/fable_fix155_probe.py --agent loop155):
  35 must-write -> >= 95 % exact triples (bar: >= 34/35 OK), 0 wrong writes
  over all 47, every must-write ask answers V (ask failure = ASK-FAIL, not
  OK); 12 must-not-write-wrong -> 0 wrong writes (stored outside the frozen
  expectation fails), office/non-table-F3 cases stored+reply exactly frozen
  base, nowrite cases no write with the frozen reply kind.
- I2 probe through loop155x135 (--agent loop155x135): 3/3 mother saves with
  exact triples + asks answering V; 2/2 office phrases stored+reply
  byte-identical to frozen loop135.
- G1 bench121 new + old fresh split + Fable-Edit per-item verdict AND reply
  identical to loop150's rows except predicted items (prediction: ZERO moves
  on all 600 items), 0 new wrong.
- G2 marks123 suites per-case identical to loop150's marks150 run except
  predicted cases (prediction: ZERO moves on every suite incl. soak/sleep/q4).
- G3 exp-152 phone sessions through loop155: every reply identical to the
  sealed T-T run except predicted turns (prediction: ZERO reply moves on all
  6 sessions), 0 new WRONG, 0 new writes except predicted (none).
- G4 each registered run (probe x2, bench, marks123, marks-diff, sessions)
  < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of all 600 bench teach sentences: 180 distinct firing
  sentences (F3 capital/author/official_language, F2 author/founder
  reverses); loop150-base ears hear on all 180 yields a non-officeholder
  teach/correct every time -> mixin returns base untouched -> 0 bench moves.
- Pure-function scan of 688 suite/session strings (redteam98 sealed v1,
  redteam110 cases, redteam81 results, loop102 dir, loop117 p2/p3/p4
  reports, sessions152.json): 27 firing strings; all bench-known (base
  teaches -> untouched) except "who is ned's teacher" / "who is rosa's
  friend", which are "?"-less questions the base answers as ask -> the
  question-lead guard + kinds-gate keep them on the base path (without the
  gate the canonical twin would have minted a wrong write; fixed pre-seal).
  Soak turns are canonical/"?" shapes with non-table relation "city" -> 0
  moves. Sleep suite has the same sleeper -> same SKIP.
- Base calibration on loop150 (frozen into case files): director 3-case
  behaviour reproduced; "=" (non-person) facts answer possessive asks
  (city/spouse/child/author); multi-word and lowercase-lead of-name entities
  store and answer ("The Birth of Tragedy", "Kingdom of the Netherlands",
  "the Republic of France"); hedged values SPLIT-refuse ("I think"/"Maybe"
  leads); "The mother of Ann is Rita and ..." SPLIT-refuses; hearsay-comma,
  two-fact, non-table-F1, "?"-less/malformed questions clarify with no
  write; office/non-table-F3 officeholder replies frozen verbatim.
- Base calibration on loop135 (frozen into cases155x135.json): president +
  mayor officeholder replies frozen verbatim.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix155_probe.py --agent loop155 --out artifacts/fable-inverted155-20260922/probe155-loop155.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix155_probe.py --agent loop155x135 --out artifacts/fable-inverted155-20260922/probe155-loop155x135.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix155_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop155_agent.py --config artifacts/fable-inverted155-20260922/loop155-config.json --out artifacts/fable-inverted155-20260922/marks155 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix155_marksdiff.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix155_sessions.py
