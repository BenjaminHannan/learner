# Exp 150b PASSMARKS — clause-in-subject guard on loop150 (sealed BEFORE any registered run)

Registered single-change follow-up to exp 150 (subject guard) and exp 144's
F1 FAIL. Base: loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard; RESULTS.md and docs 139/139b/150 read
first). Bug, director re-checked on loop129b, loop144 AND loop150: "Ann is
famous for Cats and Tom died in the city of Oslo" saves ("Ann is famous
for Cats and Tom", place_of_death, "Oslo") -- the SUBJECT span swallows a
whole teach clause; 150's guard only looks for hedge/filler words
(scripts/fable_fix150_subjectguard.py:152-163). The value-side twin ("Bea
was born in the city of Lima and Tom died in Oslo" -> value "Lima and Tom
died in Oslo") is already refused by 139b's value guard on loop150.

THE ONE CHANGE (scripts/fable_fix150b_subject150b.py, Subject150BMixin;
thin loop150b = loop150 + mixin in scripts/fable_loop150b_agent.py with
--daemon entry incl. idle_seconds; loop150 imported read-only, no file
edited): on the subject span of every teach/correct action AFTER the
exp-129 strip and the 150 screen, at ears hear() and again at loop _act()
just before the write, refuse with the existing SPLIT reply ("I can take
one fact at a time -- could you split that?", 0 writes) when the subject
contains (a) a relation cue from the loop's own relation tables
(REL_CUES_150B) or (b) a lower-case finite verb/copula token (VERBS_150B).
This guard never rewrites; values, relation keys, forget/ask/clarify paths
untouched. Untouched by design: single-token subjects (one token cannot
swallow a clause); capitalised title words (matching is case-sensitive,
only lowercase fires); bare role nouns and verbless of-phrases ("author",
"director", "city of", "country of", "capital of" are NOT cues: no finite
verb, and they occur in legit single-fact subjects such as possessive
tails and role phrases).

## Sealed lists (exact; case-sensitive; cue = word-boundary substring that
is all-lowercase in the original span; verb = whole token that .islower()
after stripping .,;:'"() edges; one-line reason each)

REL_CUES_150B (multi-word, every phrase holds a finite verb; source in
brackets: B73 = STATEMENT_PATTERNS scripts/fable_bench73_english_arm.py:73-127,
B92 = EXTRA_STATEMENT_PATTERNS scripts/fable_bench92_english_arm.py:58-68,
Q = REL_MENTION_CUES / EXTRA_REL_CUES question tables of the same files):
- "died in" [B73 died-in-the-city-of]: the swallowed clause's death verb.
- "is a citizen of" [B73]: swallowed citizenship clause.
- "is affiliated with" [B73]: swallowed affiliation clause.
- "is associated with" [B73]: swallowed sport clause.
- "is employed by" [B92 employer]: swallowed employer clause.
- "is famous for" [B73/Q]: the t14 clause itself.
- "is from" [Q country_of_origin]: swallowed origin clause.
- "is home" [Q]: swallowed origin clause variant.
- "is located in" [B73 continent/headquarters]: swallowed location clause.
- "is married to" [B73/Q]: swallowed marriage clause.
- "is the apprentice/composer/discoverer/envoy/founder/herald/inventor/keeper/mentor/rival/scout/warden/author of"
  (13 phrases) [B73 is-the-X-of]: swallowed craft clauses.
- "was born in" [B73]: swallowed birth clause.
- "was composed/created/developed/discovered/educated/founded/invented/performed/written by"
  (9 phrases) [B73]: swallowed passive clauses.
- "was created in" [B73 country_of_origin]: swallowed origin clause.
- "was founded in" [B73 location_of_formation]: swallowed founding clause.
- "was written in" [B92 language_of_work_or_name]: swallowed language clause.
- "works in the field of" [B92 occupation]: swallowed occupation clause.
- "worked in" [B73 work_location]: swallowed work clause.
- "works for" [Q employer]: swallowed employer clause variant.
- "holds citizenship" [Q]: swallowed citizenship clause variant.
- "gave birth" [Q]: swallowed birth clause variant.
- "known for" [Q notable_work]: swallowed fame clause variant.
- "that produced" [B73 manufacturer]: swallowed producer clause.
- "company that employs" [Q employer]: swallowed employer clause variant.
- "'s child is" [B92 child]: swallowed child clause (possessive + copula).
VERBS_150B (lowercase finite verbs/copulas/auxiliaries + relation verbs):
- is/are/was/were/am/be/been/being: copulas -- every swallowed clause has one.
- has/have/had/do/does/did: auxiliaries -- clause scaffolding.
- will/would/can/could/shall/should/may/might/must: finite modals -- clause.
- died/die/dies/born: death/birth verbs -- clause cores.
- lives/live/lived, works/work/worked, plays/play/played,
  speaks/speak/spoke/spoken: relation verbs of the tables.
- married/marry, employs/employ/employed, creates/create/created,
  founded, invents/invent/invented, discovers/discover/discovered,
  composes/compose/composed, writes/write/wrote/written,
  performs/perform/performed, develops/develop/developed,
  produces/produce/produced, educates/educate/educated,
  locates/locate/located, affiliates/affiliate/affiliated,
  associates/associate/associated: relation verbs of the tables.
- renowned/known: fame participles of the tables.
TITLE EXEMPTION (why "Gone with the Wind", "Who Framed Roger Rabbit",
"Is This It", "The Lives of Others", "Born to Run" still teach): both
checks are case-sensitive -- "Gone"/"Framed"/"Stood"/"Is"/"May"/"Lives"/
"Born" are capitalised, so no cue and no verb token ever fires on them;
bare nouns ("author", "director") are not cues, so possessive tails pass.

Sealed inputs:
- S1 probe: artifacts/fable-subject150b-20260922/cases150b.json (49 cases:
  23 refuse incl. exact f1 t14 text as 150b-t14; 14 must-write plain;
  10 must-write capitalised titles with verbs/'is'; 2 brief-literal
  possessive titles expecting nowrite/any-reply via the base one-word-names
  clarify; full-triple expectations).
- S2: artifacts/fable-fix150-20260922/cases150.json re-run through loop150b,
  diffed per-case vs sealed probe150-loop150.json (read-only).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: loop150's marks123 run
  (artifacts/fable-fix150-20260922/marks150) via scripts/fable_marks123_all.py.
- G3 reference: sealed T-T session turns
  (artifacts/fable-session152-20260922/turns152-T-T-*.json) via importing
  scripts/fable_session152_run.py with the target swapped to loop150b.
- loop150b-config.json (loop150 config + 2 renamed plug strings).

## Marks (integer counts, every seed/case reported, never averaged)

- S1 NEW probe of 49 cases through loop150b
  (scripts/fable_fix150b_probe.py --cases cases150b): 23 two-clause
  subject-swallows across 14 frames (famous/citizen/married/born/created/
  employed/worked/speaks/plays/founded/invented/occupation/child/director)
  -> 0 wrong writes (refuse-empty with SPLIT); 24 must-writes incl. 10
  capitalised titles -> >= 90 % exact triples, 0 wrong writes; exact t14
  text refuses; 2 possessive-title literals no-write.
- S2 exp 150's cases150.json re-run through loop150b identical per-case to
  the sealed loop150 run (57/57 verdicts, replies identical): ZERO moves
  predicted (R02/R03/R06 template subjects hit the 150b screen but are
  pre-empted by 150's earlier hearsay screen with the identical reply).
- G1 bench121 new + old-s2fresh + Fable-Edit per-item verdicts identical to
  the sealed loop150 rows (scripts/fable_fix150b_bench.py): ZERO moves
  predicted, 0 new wrong.
- G2 marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop150b_agent.py --config
  artifacts/fable-subject150b-20260922/loop150b-config.json --out
  <this-dir>/marks150b --workers 4): every suite per-case verdict identical
  to loop150's marks150 run: ZERO moves predicted (sleep SKIP reason text
  names the agent file, verdict identical, as in 139b/150).
- G3 the 6 exp-152 phone sessions through loop150b
  (scripts/fable_fix150b_session152.py): every reply identical to the T-T
  run: ZERO diffs predicted, 0 new WRONG, 0 new writes.
- G4 each registered run (probe x2, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0, 3600.0 in runners).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of all 3775 bench teach subjects (edit200 + bench103
  s2fresh + bench121 via hear_teach_template/hear_teach92):
  screen_subject_150b fires NOWHERE (0/3775).
- Pure-function parse of all 49 probe texts: 23 refuse subjects parse to
  the predicted swallowed span + relation and screen split; 24 must-writes
  parse to the expected (subject, relation) and screen store; X01/X02 match
  no template pattern (base FakeEars one-word-names clarify, no write).
- cases150.json parse: only R02/R03/R06 fire ("Rumor/Rumour has it Kip
  Dune", "Word is Kip Dune") -- all pre-empted on-loop by 150's earlier
  hearsay screen with the byte-identical reply; L10/L12/A03 match no
  template pattern (FakeEars paths the guard never touches).
- f1-cases.json (144) parse: fires ONLY on f144-t14
  ("Ann is famous for Cats and Tom", place_of_death); all 26 must-writes
  screen store.
- sessions152.json: 0 template-parsed teaches (all session teaches are
  one-word possessives via FakeEars -> single-token subjects, exempt by
  construction).
- redteam98-sealed (p2 source): 84 parsed subjects, 0 fires. rt110: 24
  parsed, 0 fires. cases136: 72 parsed, 0 fires.
- "Bea was born in the city of Lima and Tom died in Oslo" (no "the city
  of" in clause 2) parses via born (value-side, already 139b-refused);
  R21 with "the city of" parses via died (subject-side, this guard's fix).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150b_probe.py --cases cases150b --out artifacts/fable-subject150b-20260922/probe150b-loop150b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150b_probe.py --cases cases150 --out artifacts/fable-subject150b-20260922/probe150b-s2-loop150b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop150b_agent.py --config artifacts/fable-subject150b-20260922/loop150b-config.json --out artifacts/fable-subject150b-20260922/marks150b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix150b_session152.py
