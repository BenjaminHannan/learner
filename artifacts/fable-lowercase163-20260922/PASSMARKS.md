# Exp 163 PASSMARKS — case-insensitive names at the entity layer (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; RESULTS.md and the 150
doc read first). Director probes: after "Omar's sister is Priya.",
"Is Priya Omar's sister?" answers Yes but "is priya omar's sister?" falls
back to "I only know that omar's sister is Priya." (lowercase echo);
"who is tom's boss?" after "Tom's boss is Ann." answers with a lowercase
echo ("tom's boss is Ann."); a first-mention lowercase teach ("tom's boss
is ann.") stores lowercase display forms verbatim. Phone users type
lowercase constantly.

THE ONE CHANGE (scripts/fable_fix163_lowercase.py, Lowercase163Mixin;
thin loop163 = loop150 + mixin in scripts/fable_loop163_agent.py with
--daemon entry incl. idle_seconds; loop150 imported read-only, no file
edited): teach/correct actions under a person-relation key
(scripts/fable_agent_loop.py PERSON_RELATIONS) and every ask action's name
span are canonicalised through the notebook's own case-insensitive resolve
at ears hear() and again at loop _act() just before the write:
(a) an all-lowercase span resolving to exactly one known entity is replaced
by its stored display form (replies always print the display form);
(b) an all-lowercase NEW person-name span is stored capitalised per token
("tom" -> "Tom") and a later capitalised mention resolves to it;
(c) teaches under any other relation (cities, sports, positions, office
phrases, incl. the exp-102 legal all-lowercase common-noun entities) are
byte-identical -- lookup already merges them via _norm;
(d) inner-capital/mixed-case spans (McDonald, DeShawn, iPhone, TOM, eBay)
keep their typed form; spans resolving AMBIGUOUS (two stored entities
differing only by case, both typed capitalised and differently) are left
untouched so the base "which one?" clarify owns the turn (never merge).

Step 1 file:line map -- names MATCHED on lookup:
scripts/fable_notebook_contract.py:116-117 (_norm), :235-242 (resolve),
:390-421 (ask hop loop); scripts/fable_fix77_core.py:208-228 (reasoner
answer via nb.resolve); scripts/fable_agent_loop.py:122-129 (FakeEars ask),
scripts/fable_bench73_english_arm.py:215-237 + :246-314 (mentions/compose),
scripts/fable_bench92_english_arm.py:145 + :198-243; scripts/fable_loop90_agent.py:153-170
(Bench73Stage teach/correct detect). Names WRITTEN:
scripts/fable_listening_m1.py:46-58 (_person), :106-127 (_teach),
scripts/fable_notebook_contract.py:268-277 (new_entity stores typed
display); scripts/fable_agent_loop.py:344-350 (_act line),
scripts/fable_loop90_agent.py:353-373 (structured write),
:155-172 (FakeMouth echoes record["name"], the typed span -- the echo bug).

Sealed inputs:
- T1/T2 probe: artifacts/fable-lowercase163-20260922/cases163.json
  (53 dialogues: 26 lowerQ + 12 lowerTeach + 8 innerCaps + 7 noMerge; exact
  stored-triple + exact-last-reply expectations).
- loop163-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: sealed marks150 + scripts/fable_marks123_all.py suites.
- G3 reference: sealed T-T session run
  (artifacts/fable-session152-20260922/turns152-T-T-*.json).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 new probe of 53 dialogues through loop163
  (scripts/fable_fix163_probe.py): 26 lowercase-Q after capitalised teaches
  (16 1-hop + 10 2-hop, 10 relations: boss/sister/teacher/mother/city/
  friend/father/brother/wife/husband) -> exact answer with display form;
  12 lowercase teaches then capitalised (or lower) questions -> exact
  answer, incl. 2 later-capitalised-mention DUPLICATE rows; 8
  mixed/inner-capital names (McDonald, DeShawn, iPhone, LeBron, TOM,
  Mary-Kate, eBay) unchanged incl. 3 lowercase-Q resolving to the
  inner-capital display; 7 must-not-merge cases (Tom/TOM, Ann/ANN person
  collisions incl. lowercase teach/ask and a forget control) -> 0 wrong
  writes, 0 wrong answers (base clarify owns each turn).
- T2 >= 95% of the 53 must-cases exact (>= 51/53), full triple + reply.
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts AND
  replies identical to the sealed loop150 rows
  (scripts/fable_fix163_bench.py reusing fable_loop129b_bench.run_item by
  import), ZERO predicted moves, 0 new wrong.
- G2 marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop163_agent.py --config
  artifacts/fable-lowercase163-20260922/loop163-config.json --out
  <this-dir>/marks163 --workers 4) per-case identical to marks150
  (scripts/fable_fix163_marksdiff.py, timing keys scrubbed, summary
  agent/config paths mapped), ZERO predicted per-case moves; predicted:
  sleep-report reason names the new agent file (verdict identical).
- G3 the exp-152 phone sessions (scripts/fable_fix163_session.py importing
  fable_session152_run and swapping the target to Loop163Daemon): every
  reply identical to the sealed T-T run except the 8 predicted turns
  (S2-casual-friends turns [18, 23]: lowercase ask owners -> display form;
  S5-robustness turns [4, 10, 12, 13, 14, 25]: lowercase ask owners ->
  display form, turn 12 also stores person value Quinn capitalised, echoed
  in 13/14/25), 0 new WRONG, 0 write moves. Zero moves in S1/S3/S4/S6.
- G4 each registered run (probe, bench, marks123, marksdiff, sessions)
  < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan (base loop150 ears.hear only, throwaway notebook, no
  turn() calls) over every sealed input string: bench 600 items (3 G1
  splits) + bench113 A/B (G2 bench suite) -> 0 actions with an
  all-lowercase person-relation teach span or lowercase ask owner;
  sessions152 180 turns -> only S2 [T7 ask june (MISSING both),
  T13 ask wren (MISSING both), T18, T23] and S5 [T4, T10, T12 teach quinn,
  T13] flag, plus knock-on answers T14/T25 (capitalised turns echoing
  Quinn); R98 64 cases -> 0; R110 62 cases -> 0; R81 74 cases -> 1
  over-approx ("Who is her mother's city?", UNKNOWN owner -> provable
  no-op); p4-innocent-30 -> 0; q1 fixed ("WHO IS MIRA'S CITY?" is ALL-CAPS,
  untouched) -> 0; soak shapes (SoakP###/SoakV###) -> 0; p3 SEQS +
  turns84 l5z1 + l6 D2 names + l3/l4 programmatic -> 0 (fullwidth "ｍｉｒａ"
  teach is a city relation, out of scope by design).
- Base-loop spot checks (dev only): "Tom's boss is Ann." then
  "who is tom's boss?" answers with lowercase owner echo; "tom's boss is
  ann." first-teach stores lowercase "tom"/"ann" displays; capitalised
  re-mentions merge via _norm (no duplicate entities).
- Design boundary (deliberate, documented): literal attribute values
  ("reno", "lima", "brown") and non-person-relation subjects keep typed
  form; only person names are display-normalised. Replies still answer
  every case-insensitive question correctly via the notebook's _norm.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_probe.py --out artifacts/fable-lowercase163-20260922/probe163-loop163.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop163_agent.py --config artifacts/fable-lowercase163-20260922/loop163-config.json --out artifacts/fable-lowercase163-20260922/marks163 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_marksdiff.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix163_session.py
