# Experiment 73 — RESULTS (Fable-Edit-200 English-input arm, pluggable ears)

## Result

PASS 3/3. The template arm reproduces the structured-arm table exactly
(100/100 MQuAKE two-hop, 50/50 reversal, 25/25 abstain-absent, 25/25
abstain-broken, 0 wrong, 0.5 s); 5/5 garbled items abstain with 0 wrong; the
ears47 smoke test skips cleanly (no checkpoint exists yet).

## Marks table (integer counts, template arm)

| Type | n | correct | wrong | miss |
|------|---|---------|-------|------|
| mquake-twohop | 100 | 100 | 0 | 0 |
| reversal | 50 | 50 | 0 | 0 |
| abstain-absent | 25 | 25 (abstain) | 0 | 0 |
| abstain-broken | 25 | 25 (abstain) | 0 | 0 |
| garbled (separate file) | 5 | 5 (abstain) | 0 | 0 |

Reference (structured, recomputed in-memory): identical cell-for-cell
(`TABLES IDENTICAL`). Wall-clock: 0.5 s for 200 items (< 5 min). Selftest:
PASS (35 teach patterns + 6 garbled rejects + composer/reversal/correction
checks). Garbled verdicts: 2 MISSING_FACT (unparsed question), 3
UNKNOWN_ENTITY (novel name, nothing taught) — all abstain_ok, 0 WRONG.

## What was built

`scripts/fable_bench73_english_arm.py` (new, prefix `fable_bench73_`): feeds
ONLY English strings through an Ears object, then the same notebook +
QualifierAwareReasoner + scoring as exp 65 (imported read-only). Corrections
are inferred from English-derived triples — a repeated (subject, relation)
with a new object is taught with correction=True, matching exp 65's edit
flags on this file. Unparseable input is never written and never guessed:
teach failures are skipped, question failures yield MISSING. The question
composer (`compose_question`) is shared arm code; the pluggable part is the
per-sentence mapper, so ears47 drops in without new code. `--ears template`
(registered) vs `--ears ears47:<ear.pt>` (smoke only) vs `--smoke-ears47`.

## What it means

English teaching sentences install exactly the same facts as hand-fed
triples, and every English question in the file resolves to the right query —
the notebook + reasoner behave identically on English-derived input.

## What it does not mean

Not general English understanding: templates cover only this file's patterns,
and two-hop order comes from the taught chain (mention-gated), not from
parsing question paraphrases. The neural ears is exp 47's job.

## Deviations

1. Script fixed between the first passing run and the registered run (garbled
   mode skipped the structured reference; main-bench path untouched) and the
   main run was re-executed; the re-run is the registered one.
2. Broken-chain frames use undeclared `never_taught_rel` (the per-item
   `bN` suffix is unknowable from English); behaviorally identical
   (structural MISSING, 25/25 abstain_ok).

## Reproduce

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench73_english_arm.py --selftest
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench73_english_arm.py --run --ears template
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench73_english_arm.py --run-garbled --ears template
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench73_english_arm.py --smoke-ears47
```

Once an exp-47 checkpoint exists (`artifacts/fable-ears47-20260921/runs/<seed>/ear.pt`):

```
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench73_english_arm.py --run --ears ears47:artifacts/fable-ears47-20260921/runs/<seed>/ear.pt
```

## Questions for Ben

None. (Assumption recorded: edit boundaries follow file order with
correction inferred from repeated subject+relation — the sentences carry no
correction markers, so pure-English correction detection is impossible.)
