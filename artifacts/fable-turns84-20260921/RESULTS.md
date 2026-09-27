# Exp 84 RESULTS — natural-turns acceptance (60 turns, template loop)

Single registered pass, sealed before the run (`SEAL.sha256.txt` verifies
PASSMARKS.md, turns.jsonl, driver). Fictional Harrow family of Willowmere;
no real people. Reproduce:

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
        python -B scripts/fable_turns84_run.py   # ~0.2 s, exit 0

## Marks (integer counts, no averages)

| mark | bar | observed | verdict |
|---|---|---|---|
| U1 0 wrong writes / 60 turns | 0 | 0 | PASS |
| U2 question turns exact-match, 0 wrong answers | ≥ 13/15 | 15/15 (11 OK + MISSING + UNKNOWN + 2 CLARIFY), 0 wrong | PASS |
| U3 messy turns clarify-or-correct, 0 wrong | 5/5 | 5/5 (4 CLARIFY + 1 correct SAVED), 0 wrong | PASS |
| U4 per-turn table with limit class | 60 rows | 60 rows, failing_turns=none | PASS |

Coverage: 25 teaches (13 person, 10 literal, 2 time-qualified as
`city_in_2019`/`job_in_2019`), 10 corrections (9 effective supersessions, 1
pronoun-form clarify at turn 34), 15 questions (11 taught incl. four 2-hop,
MISSING at 46, UNKNOWN at 47, 2 yes/no clarifies), 5 small-talk clarifies,
5 messy (typo/clarify, lowercase/SAVED, trailing-lol/clarify, two-facts/clarify,
question-as-statement/clarify). Old values stay in the log (e.g. Mira's
Willowmere row inactive after turn 26); later quizzes confirm corrections
(turn 37 → Cedar Hollow, turn 45 → Finn). 12 of the 60 turns are
`ears-template-limit`, all expected clarifies; zero doorway/contract failures.

## What it means

The doorway + notebook contract survive a realistic 60-turn session with zero
wrong writes and zero wrong answers: everything taught is answerable, every
correction supersedes cleanly, and everything untaught is refused.

## What it does not mean

It does not show a real user succeeding: 12/60 natural turns only clarify
because FakeEars is a template parser. Real ears replace it; the contract held.

## Deviations

Sleep threshold set to 1e9 in the driver so no SLEEP tick interrupts the
ordered transcript (StubSleeper changes nothing either way). No other deviation.

## Questions for Ben

None. Default kept: yes/no questions stay clarifications until real ears land.
