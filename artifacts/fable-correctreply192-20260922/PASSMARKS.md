# Exp 192 PASSMARKS — correct-reply (sealed BEFORE any registered run)

Base agent: loop167e (scripts/fable_loop167e_agent.py,
artifacts/fable-label167e-20260922/loop167e-config.json).

Director probe 09:49 on loop167e: after "Kim's boss is Sam.", both
"No, Kim's boss is Lee." and "Actually, Kim's boss is Lee." reply
"Saved: Kim's boss is Lee." (the user is never told Sam was replaced);
the plain re-teach "Kim's boss is Lee." asks "I have Kim's boss as Sam.
Do you want me to change it to Lee?" (kept).

THE ONE CHANGE, behaviour (scripts/fable_fix192_correctreply.py,
CorrectReply192Mixin stacked OUTERMOST on the loop class in
scripts/fable_loop192_agent.py; no 167e/167c/loop/agent-loop/contract/
listening file edited): reply text only. A turn the USER marked as a
correction -- an explicit correction form (No, / Actually, /
Correction: / Sorry-I-meant, verb twins included; all arrive as
act=correct) or a yes to the change question (line "yes") -- that
REPLACES an existing current value of a single-valued relation (its
notebook write appended a FACT with `supersedes` set) replies with one
fixed sealed template naming both values:

  Updated: Kim's boss is Lee (it was Sam).

i.e. `Updated: {Subject}'s {relation-spaced} is {New} (it was {Old}).`
with the 167e relation surface (`replace("_", " ")`). Old/new displays
are read from the superseded/fresh FACTs (entity name or literal), so
both names are right by construction; a consistency gate requires the
record's Saved text to equal exactly the confirmation that FACT would
have produced, else the base reply is kept.

Deliberately OUT of scope (sealed): silent bench73-stage auto-corrects
(a plain re-teach the template ears upgrade to act=correct with no user
correction marking) keep loop167e's "Saved:" -- the discriminator is
the turn text (explicit ⟺ sealed F3 correction prefix,
`fable_loop102_agent.strip_correction_prefix`); sealed harnesses judge
those teach replies literally (redteam143's `teach_accepted()` takes
only "Saved:"/"I already have that."). First teaches keep "Saved:",
repeats keep "I already have that.", declined changes keep "Okay, I
left it as it was.", the change question is untouched, multi-valued
additions never set `supersedes` (contract accumulates them).

## Sealed inputs

- C1/C2 case file: artifacts/fable-correctreply192-20260922/cases192.json
  (40 turns, all fictional names: 11 explicit corrections [No, x3 /
  Actually, x5 / Correction: x2 / Sorry-I-meant x1], 4 yes-to-change,
  25 traps [first teach, repeat, duplicate-correct-same-value, declined
  change, second-value conflict, pretend/hearsay, questions, no-pending
  yes, Forgotten, post-forget ask]).
- Config: artifacts/fable-correctreply192-20260922/loop192-config.json.
- Code: scripts/fable_fix192_correctreply.py,
  scripts/fable_loop192_agent.py; drivers scripts/fable_fix192_probe.py,
  scripts/fable_fix192_suites.py, scripts/fable_fix192_bench.py,
  scripts/fable_fix192_marksdiff.py.
- C3 references: loop167e's frozen rows redteam136-loop167e.json,
  redteam143-loop167e.json, sessions152-loop167e.json; plus sealed
  cases136.json, fable_redteam143_cases.json, sessions152.json;
  bench rows fable_bench167e_loop167e_*_rows.jsonl; marks167e
  (artifacts/fable-label167e-20260922/marks167e, all suites completed).

## Marks (integer counts, every seed/case reported, never averaged)

- C1 probe (scripts/fable_fix192_probe.py): 40/40 turns OK -- every
  `want: updated` turn replies EXACTLY the sealed template with the
  case file's old/new values; every trap byte-identical to loop167e;
  stored triples identical; counts correction=11, yes=4, trap=25.
- C2: scrubbed notebook events (drop volatile event_id/prev uuid+hash
  fields) identical to loop167e on all 40 turns.
- C3 suites (scripts/fable_fix192_suites.py) vs frozen loop167e rows:
  redteam136 0 moves of any kind; redteam143 Q1-Q7 teach replies move
  Saved->Updated by the shared rule (their teaches ARE explicit
  "Actually,"/"No,"/"Correction:" forms) and their verdicts move to
  HARNESS-ERROR by the sealed harness's teach_accepted gate (stored
  triples identical, 0 new WRONG-ANSWER); all other 143 cases 0 moves;
  sessions152 exactly 2 reply moves, both explicit "Actually,"
  corrections (S3-teachers-correction turn 7: "Saved: Rao's city is
  Denver." -> "Updated: Rao's city is Denver (it was seattle).";
  S6-pronouns-corrections turn 16: "Saved: Vera's city is Quito." ->
  "Updated: Vera's city is Quito (it was Lima)."), 0 verdict moves, 0
  fact_writes moves, 0 new WRONG.
- Bench (scripts/fable_fix192_bench.py, the base agent's driver shape)
  vs frozen loop167e rows: verdict 0 moves on all 600 items, 0 reply
  moves, 0 teach_replies moves, 0 new wrong (dev scan: bench edits are
  silent re-teaches; no explicit-correction Saved confirmations occur
  on any of the 600 items).
- marks123 (scripts/fable_marks123_all.py --workers 2) per-case vs
  marks167e (scripts/fable_fix192_marksdiff.py): identical except (a)
  reply strings moved ONLY by the shared correctreply_move rule --
  pre-seal dev marks123 to scratch-dev-marks192 (200.5 s wall) observed
  exactly these moves, every one a Saved confirmation of an
  explicit-correction replacement moved to the sealed Updated template
  with correct old/new values, all other suites' replies byte-identical:
  rt81 cases 8, 11, 34, 53, 69 move verdict OK->UNCLEAR by the sealed
  harness's [wanted 'Saved'] gate (counts ok 61->56, unclear 13->18);
  soak's 40 Actually-correction turns move reply Saved->Updated so the
  sealed harness (Saved-prefix gate) counts wrong 0->40, every
  wrong_detail entry an Actually->Updated pair (dev: 20-entry detail
  list, all Actually with Updated replies), lost/doubled 0, audit
  lost/dup/wrong 0; p3/l5z1 turns 26-33 and 35 (9 Actually replacements,
  e.g. "Updated: Mira's city is Cedar Hollow (it was Willowmere).")
  move observed SAVED->WRITE_OTHER by the sealed
  text.startswith("Saved") gate in
  fable_turns84_run.observed_status, wrong_writes 0; p2/p4/q1/bench/
  rt110 per-case byte-identical, 0 reply moves; (b) loop167e->loop192 /
  marks167e-> marks192 path renames; (c) volatile seconds/statuses
  ignored (same rule as 167e); (d) q4 identical (leaks=[], PASS,
  unchanged -- the 192 change touches no relation-key label); sleep
  verdict identical (SKIP) with reason naming loop192; summary numbers
  identical except p3 FAIL with l5z1:F (l1-l4/l5z2/l6 unchanged), rt81
  ok 56 / unclear 18, soak wrong 40 FAIL; 0 new stored-fact WRONG /
  WRONG-WRITE / junk writes anywhere (every verdict-count delta is a
  sealed-harness Saved-shape gate sitting on a predicted reply move;
  stored triples and fact-write counts identical); soak/rt110 flakes
  under load are the known mailbox race -> re-run that suite once in
  the open and report both.
- Each registered run (probe, suites, bench, marks123, diffs) < 25 min
  wall-clock (< 1500 s) Mac CPU (export OMP_NUM_THREADS=1
  MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12
  --with torch --with numpy python -B ...); daemon wrappers take
  idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs)

- All 40 sealed turns verified end-to-end in dev (temp dirs): 15/15
  Updated-exact, 25/25 traps byte-identical, scrubbed events identical.
- Director probe verbatim in dev: 192 "Updated: Kim's boss is Lee (it
  was Sam)." for No,/Actually,; plain re-teach still asks the change
  question; yes -> Updated.
- Dev suites scan (temp dirs): redteam136 zero moves; redteam143 only
  Q1-Q7 move (teach reply + harness verdict, stored identical);
  sessions152 exactly the 2 predicted reply moves, 0 verdict/write
  moves. Dev bench scan: 0 moves on all 600 items.
- Dev marks123 to scratch-dev-marks192 (200.5 s): comparator vs
  marks167e gives p2/p4/q1/bench/rt110/q4 PASS identical, sleep SKIP
  naming loop192, and exactly the predicted deltas above (rt81 5 cases
  OK->UNCLEAR; soak wrong 40, all Actually->Updated; p3/l5z1 9 turns
  WRITE_OTHER, wrong_writes 0).
- Daemon check (pre-seal): Loop192Daemon stores idle_seconds as given
  (12.5 in, 12.5 out); mouth chain
  Label167eMouth(Label167cMouth(...)); "Updated:" shapes pass the 167e
  renderer byte-identical.
- correctreply_move unit checks: Saved->Updated same
  subject/relation-surface/new-value (+ non-empty old) true; identical
  true; cross-value/wrong-shape false.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code/case/config/driver edits after the seal;
any edit is reported and the affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_probe.py --out artifacts/fable-correctreply192-20260922/probe192-loop192.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_suites.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop192_agent.py --config artifacts/fable-correctreply192-20260922/loop192-config.json --out artifacts/fable-correctreply192-20260922/marks192 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix192_marksdiff.py
