# Exp 154 PASSMARKS — yes/no questions (sealed BEFORE any registered run)

Registered single-change stage on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard). Director probe on loop150: after
"Ann's mother is Rita.", "Is Rita Ann's mother?" and "Is Bob Tom's boss?"
get "I didn't understand that".

THE ONE CHANGE (scripts/fable_fix154_yesno.py, YesNo154Mixin; thin
loop154 = loop150 + mixin in scripts/fable_loop154_agent.py with --daemon
entry incl. idle_seconds; loop150 imported read-only, no file edited): a
yes/no stage that runs ONLY when the forward path did not understand (the
single "didn't understand that" clarify). It rewrites "Is V X's R?" /
"Is V the R of X?" / "Is X's R1's R2 V?" into the wh-question the loop
already answers, runs it through the UNCHANGED forward path (same ears
hear + same _act/_ask, read-only), and compares the answered value with V
(exact, after the loop's own normalisation: whitespace collapse + exp-129
strip on both sides, relation keys via FakeEars._relation). Replies: same
value -> "Yes — Ann's mother is Rita."; different value with a
single-valued last hop (sealed table) -> "No — Ann's mother is Rita.";
different value on a multi-valued relation -> "I only know that Ann's
friend is Bob." (never "No"); forward abstains (any non-OK) -> its own
honest reply (never "No"). The stage never writes (wh run executes only
ask/clarify; any write-shaped wh action aborts to the base clarify).
Non-shapes ("Is Bob a doctor?") pass through untouched.

Sealed parser limits: turn must start with "Is" and end with "?"; X/V are
single tokens in the possessive shapes; the "the R of" shape needs an R
without "of" (place of birth uses the possessive shape); two-hop only as
"Is X's R1's R2 V?"; ambiguous double splits stay clarify.

## Sealed single-valued table (SINGLE_VALUED_154, code before any panel)

- "mother": one mother slot; a correction supersedes her.
- "father": one father slot; same supersession rule.
- "capital": one capital per country by definition.
- "place_of_birth": born in exactly one city.
- "date_of_birth": born on exactly one date.
- "city": one current city per person in this loop.
- "spouse": one active spouse; corrections supersede.
- "wife": same as spouse (surface variant).
- "husband": same as spouse (surface variant).
- "boss": one current boss per person in this loop.
- "teacher": one current teacher per person in this loop.
Every other relation is multi-valued (friend, child, sibling, sister,
brother, notable_work, ...): a different known value never licenses "No".

## Sealed inputs

- Y1/Y2 probe: artifacts/fable-yesno154-20260922/cases154.json (54 cases:
  17 yes one-hop + 4 two-hop yes + 12 single-valued no + 8 multi-valued
  differing + 8 unknown = 49 Y1 dialogues, each fresh daemon dir, teaches
  verbatim; 5 Y2 no-write shapes). Every N/M dialogue teaches X TWO facts:
  the single-chain N-hop composer answers cued single-chain Is-questions
  directly (dev: bare "Peru's capital is Lima."), so the second fact forces
  the miss path the stage owns; the wh-answer is unaffected (1-hop asks
  ignore the extra fact).
- loop154-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: sealed loop150 marks123 run
  (artifacts/fable-fix150-20260922/marks150).
- G3 reference: sealed T-T session turns
  (artifacts/fable-session152-20260922/turns152-T-T-*.json).
- 123 suites, bench splits + scorer v2, 152 runner + judge: sealed in
  their own exps, read-only, reused by import.

## Marks (integer counts, every seed/case reported, never averaged)

- Y1 new probe of 49 dialogues through loop154
  (scripts/fable_fix154_probe.py --agent loop154): 21 yes (17 one-hop +
  4 two-hop) -> "Yes — ... <want>"; 12 single-valued no -> "No — ...
  <want>"; 8 multi-valued differing -> "I only know that ... <want>",
  never No; 8 unknown -> never No (honest forward reply); 0 wrong yes/no
  answers over all 49; 0 writes on every question turn.
- Y2 the 5 no-write shapes + every Y1 question turn -> 0 writes from any
  yes/no question, incl. unknowns like "Is Bob a doctor?".
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts
  identical to loop150's rows (scripts/fable_fix154_bench.py, bench150
  pattern by import): ZERO verdict/reply moves predicted; 0 new wrong.
- G2 marks123 suites per-case identical to loop150's run
  (scripts/fable_marks123_all.py --agent scripts/fable_loop154_agent.py
  --config artifacts/fable-yesno154-20260922/loop154-config.json --out
  artifacts/fable-yesno154-20260922/marks154 --workers 4): ZERO per-case
  moves predicted (sleep SKIP reason text names the agent file, verdict
  identical, as in 139b/150).
- G3 the exp-152 phone sessions (scripts/fable_fix154_session152.py,
  imports scripts/fable_session152_run.py, target swapped to loop154):
  every reply identical to the T-T run, ZERO reply/verdict moves
  predicted (no session turn is an "Is ...?" question); 0 new WRONG,
  0 new writes except predicted (none).
- G4 each registered run (probe, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrappers take idle_seconds.

## Predictions P154.1-P154.6 (ledger, appended before any registered run)

- P154.1: Y1 49/49 verdicts OK, 0 wrong yes/no answers. 0.80.
- P154.2: Y2 0 question-turn writes over all 54 cases. 0.90.
- P154.3: G1 600/600 per-item verdicts identical to loop150 rows. 0.75.
- P154.4: G2 every marks123 suite per-case identical to marks150. 0.75.
- P154.5: G3 0 reply moves vs the sealed T-T session turns. 0.80.
- P154.6: G4 every registered run < 1500 s Mac CPU. 0.90.

## Pre-seal evidence (dev only, NOT registered runs)

- loop150: 3/3 sampled yes/no turns ("Is Rita Ann's mother?",
  "Is Ann's mother Rita?", "Is Rita the mother of Ann?") get
  didn't-understand (director probe reproduces).
- loop150 single-fact cued chains answer Is-questions directly with the
  bare fact ("Is Quito the capital of Peru?" -> "Peru's capital is
  Lima."): pre-existing N-hop behaviour, hence two facts per N/M dialogue.
- mixin dev (scratchpad only): Yes / No / only-know / unknown-relay
  ("I don't know Ann's father.") / two-hop Yes / two-hop-unknown relay
  ("I don't know Lisa's teacher.") / non-shape clarify, all with 0 writes.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154_probe.py --agent loop154 --out artifacts/fable-yesno154-20260922/probe154-loop154.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop154_agent.py --config artifacts/fable-yesno154-20260922/loop154-config.json --out artifacts/fable-yesno154-20260922/marks154 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154_session152.py
