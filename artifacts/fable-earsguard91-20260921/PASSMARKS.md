# Exp 91 pass marks — FakeEars guard (sealed BEFORE the registered run, 2026-09-22)

Under test (new files only, everything else imported read-only, never edited):
`scripts/fable_earsguard91.py` (`GuardedEars`: wraps any Ears; a teach/correct
write whose value contains "?", packs a second fact (another possessive
relation phrase `X's <word> is`, a second copula, ` and <Name>'s`, or `;`),
or exceeds 6 words becomes a single clarify; all else passes through
unchanged). Fixes red-team-81 FakeEars limitations 1–2 without touching
`scripts/fable_agent_loop.py` or any other existing file.

Registered run (Mac CPU, offline, one process at a time):

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy \
        python -B scripts/fable_earsguard91_run.py --out artifacts/fable-earsguard91-20260921

| id | mark | pass bar (integer counts) |
|----|------|---------------------------|
| G1 | both reproducers now clarify | 2/2 clarify with the documented message, 0 writes total |
| G2 | all 74 red-team-81 cases re-run through GuardedEars (case list imported from `scripts/fable_redteam81_probe.py`) | every case whose outcome changed is listed; 0 cases become a wrong write (no write on a nowrite turn; no written literal contains `?`, a packed second fact, or > 6 words) |
| G3 | 60-turn acceptance `data/open/turns84/turns.jsonl` through GuardedEars (scoring pieces imported from `scripts/fable_turns84_run.py`) | 60/60 status match, 0 wrong writes |
| G4 | daemon74 selftest with `GuardedEars(FakeEars)` via the `build_ears` hook (`scripts/fable_earsguard91_daemon.py` launcher) | selftest exit 0 (D1–D4 PASS in seeds 1, 2, 3, every seed reported) |

Predictions: ledger P91.1–P91.4.
Every seed/case reported, never averaged. A registered FAIL is recorded as
FAIL, never re-run into a pass. Claims never exceed evidence.
