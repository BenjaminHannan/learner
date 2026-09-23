# Exp 84 pass marks — natural-turns acceptance (sealed BEFORE the registered run)

Registered run: 60 turns in `data/open/turns84/turns.jsonl`, in order, through
`AgentLoop(FakeEars/FakeMouth/LookupReasoner)` via `scripts/fable_turns84_run.py`.
Single ordered pass, no seeds or sampling; every turn reported, never averaged.
Reproduce:

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
        python -B scripts/fable_turns84_run.py

Scoring per turn (driver-enforced): exact status match vs `expected.status`
(SAVED / OK / MISSING_FACT / UNKNOWN_ENTITY / CLARIFY in the notebook contract's
vocabulary, CLARIFY for ears-level clarifications); answer match for OK turns;
no wrong writes (every new FACT row must equal the intended
(subject, relation, value) triple; non-write turns must add no FACT/ENTITY rows).

## Marks (all must hold; integer counts)

- U1: wrong_writes_total == 0 over all 60 turns.
- U2: question turns with exact status match and no wrong write >= 13/15,
  AND question_wrong_answers == 0 (an OK with a non-matching answer, or any
  invented answer on a refuse-turn, fails the mark even at 15/15 match).
- U3: messy_ok == 5/5 (each messy turn ends in its expected CLARIFY or its
  intended correct SAVED write) AND messy_wrong_writes == 0.
- U4: per_turn.jsonl lists all 60 turns with observed status, said text, added
  rows, and a limit_class per turn: `ears-template-limit` (expected clarify;
  real ears replaces FakeEars) vs `parsed-ok`. Any mismatch would be classed
  here as doorway/contract failure, not an ears limit.

## Predictions (ledger P84.1–P84.4, appended before the run)

- P84.1: U1 holds (0 wrong writes / 60). p=0.85.
- P84.2: U2 holds (>= 13/15, 0 wrong answers). p=0.85.
- P84.3: U3 holds (5/5 messy, 0 wrong). p=0.90.
- P84.4: whole invocation < 30 min wall-clock, Mac CPU, offline. p=0.97.
