# 84 — Natural-turns acceptance transcript (muse)

Milestone-1 acceptance: 60 natural English turns a real person might type while
teaching and quizzing a notebook assistant about a fictional family, run in
order through the glue loop's template stand-ins
(FakeEars/FakeMouth/LookupReasoner). Fictional Harrow family, fictional town
Willowmere; nothing about any real person.

## Transcript design (`data/open/turns84/turns.jsonl`)

Each line: `turn`, `kind`, `expected` (contract-vocabulary status, plus
`answer` for OK or `write` triple + `new_entities` for SAVED), `rationale`.

- 25 teaches (turns 1–25): 13 person relations (mother/father/sister/brother/
  husband/wife), 10 literals (city/job/pet/birth_year), 2 time-qualified.
  Qualifiers fold into the relation (`Mira's city in 2019 is Port Azure` →
  `city_in_2019`), so they stay quizable without any date logic in the doorway.
- 10 corrections (26–35): 9 `Actually, X's Y is Z` supersessions covering all
  later quiz paths; turn 34 is the brief's example verbatim
  (`actually her mother is Ana, not Mira`) — pronoun, no possessive chain.
- 15 questions (36–50): 11 taught (four 2-hop, incl. a person→literal ending at
  turn 40 and qualifier relations at 42–43), turn 46 MISSING_FACT (Mira's pet
  never taught), turn 47 UNKNOWN_ENTITY (Sol never introduced), 2 yes/no.
- 5 small-talk (51–55), 5 messy (56–60): typo `si`, all-lowercase teach,
  trailing `lol` on a yes/no, two facts joined by `and` with `lives in`
  (no `is` frame), `I wonder…` question-as-statement.

## Driver (`scripts/fable_turns84_run.py`)

Fresh loop state per run, sleep threshold 1e9 (no SLEEP ticks mid-transcript).
Per turn it asserts exactly one LISTENING tick, maps the record to a status
(SAVED/DUPLICATE_OK/CONFLICT/AMBIGUOUS from write text; record status for
answers; CLARIFY), checks OK answers field-for-field, and audits the notebook
delta: SAVED turns must add exactly the intended FACT triple with no surprise
entities; all other turns must add no FACT/ENTITY rows. Outputs
`per_turn.jsonl` (60 rows) and `summary.json`.

## Registered result (sealed; `shasum -c SEAL.sha256.txt` OK)

status_match 60/60, wrong_writes 0; questions 15/15 with 0 wrong answers;
messy 5/5 with 0 wrong writes. U1–U4 all PASS. Failing turns: none — so there
are no failing turns to quote; the nearest-to-failing cases are the 12
expected clarifies (turns 34, 49–56, 58–60), all classified
`ears-template-limit` in the per-turn table, e.g. turn 34 → `Please say it
like "Mira's city is Lisbon."`, turn 49 → `I didn't understand that…`.
Zero `doorway/contract` failures.

## What a real-ears model must handle that the template cannot (196 words)

Pronouns and elision: `actually her mother is Ana` requires resolving `her`
to a person in context, and `not Mira` must retract-or-replace rather than
become part of a value. Tense and qualifiers: `lived in Lisbon in 2019` and
`moved to` need mapping onto relations with time scope instead of clarifying.
Yes/no: `Is Mira's city Cedar Hollow?` needs a 1-hop ask plus a comparison
that answers yes/no with the stored value as evidence. Noise robustness:
typos (`si`), trailing filler (`lol`), and case variation must not create
misspelled relations or polluted values — clarify when unsure, normalise when
safe. Multi-fact utterances: `Mira lives in X and Rosa lives in Y` must split
into two frames or be refused atomically, never written as one mangled row.
Question-shaped statements (`I wonder what…`) need intent detection. Small
talk needs a polite no-write reply distinct from confused clarification.
Ambiguity policy stays: two people sharing a name, or a genuinely unclear
referent, must ask — never guess. None of this may weaken the current
guarantees: taught-only writes, corrections supersede, untaught stays
MISSING/UNKNOWN. The contract side already holds (0 wrong writes/answers
here); the work is ears precision without losing ears brakes.

## What it means / what it does not mean

It means the doorway+contract are ready for real ears: 60 natural turns, no
wrong writes, no wrong answers. It does not mean users will get answers to
pronoun, tense, yes/no, or multi-fact turns yet — those 12 clarify by design
until a real-ears model earns them.
