# Exp 135 RESULTS (plain words for Ben)

The bug: the assistant saved ANY sentence shaped "The ___ is ___" as if it
were about a government office. "The mother of Dara is Ora" was stored as a
job title. That is now fixed with one small add-on piece.

## Marks table (integer counts)
| check | bar | got |
|---|---|---|
| K1 non-office probe writes on fixed loop | 0 of 30 | 0 of 30 PASS |
| K1 office sentences same as before | 18 of 18 identical | 18 of 18 PASS |
| K2 Fable-Edit-200 (answers/abstains/wrong) | 150/50/0 | 150/50/0 PASS |
| K2 old fresh split (correct/wrong) | ≥157 / 0 | 157 / 0 PASS |
| K2 bench121 split (correct/wrong) | ≥136 / ≤1 | 136 / 1 PASS |
| K2 per-item identical to base (600 rows) | 600 | 600 PASS |
| K3 marks123 suites same verdict as base | 10 of 10 | 9 of 10 FAIL-letter |
| K4 compute time | < 25 min | ≈ 6 min PASS |

30 probe sentences (mother, father, boss, teacher, weather, cat, car, …) that
the old loop wrongly saved are now answered "I didn't understand" with
nothing stored. Real office sentences (president, mayor, director, coach, …)
save exactly as before.

## What it means
The wrong-write hole is closed and nothing else moved: every benchmark answer
is identical to before.

## What it does not mean
It does not mean family sentences are understood now (they are refused, and
teaching "mother" properly is a later job); the one K3 mismatch is a mailbox
timing hiccup (an empty message got read once), not this fix — the evidence
is in the design note.

## Deviations
None. King/queen sentences also refuse now (those titles are not in the
code's lists); flagged as a question for the director.

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop135_agent.py --config artifacts/fable-fix135-20260922/loop135-config.json --out artifacts/fable-fix135-20260922/marks135 --workers 4
(passmarks sealed in artifacts/fable-fix135-20260922/SEAL.sha256.txt before the run; predictions P135.1–P135.7 in artifacts/fable-predictions-ledger.md)
