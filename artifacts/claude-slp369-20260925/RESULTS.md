# slp-369 results: PASS 5/5 (blind recount agrees, VERIFY.md), with thin evidence on one mark

Run 2026-09-25 ~06:45-07:30 UTC, CPU, $0, sealed code (SEAL.sha256.txt checks OK). 80 bench nights + 2 attacks, 0 errors.

| Mark | Bar | Result |
|---|---|---|
| P369.1 all 60 faulty nights of the three opened benches: main log bytes unchanged | 60/60 | 60/60 |
| P369.2 restored nights: the after sequence (teach, ask, correct, ask) all right | all, ≥ 1 | 1/1 (slp364c-05) |
| P369.3 20 honest 364c nights: kept, replies identical to 364c's v3 arm | 20/20, 20/20 | 20/20, 20/20 (611 replies) |
| P369.4 direct-file attack, seeds 1-2: main and event count back, not kept, after sequence 6/6 | both | both |
| P369.5 changed file kept aside in undo361/main369-* | all | 3/3 |

## Limits (blind recount)
- Thin: only 1 bench night reached the restore (the case found in dev); all 3 restores are the same one-file append.
- Shown (code): 369 acts only when notebook FILE bytes change; an in-memory-only change is undone by neither 369 nor 361.
  Function attributes swapped on the notebook are not restored. If the sleeper raises, the check is skipped
  (no try/finally). Nested containers come back as copies (suggested risk, one level below the fixed bug).
- 8 of 60 faulty nights failed the after sequence with 369 doing nothing; the bench faults stay installed on the loop
  after an undo (shown on 6, suggested on 2). Not a 369 effect.

## Also found
The first version of this restore reproduced slp-364b's damage ("Belvoria's mother is Belvoria."): a plain deep copy
of the outer notebook's state also copies the inner notebook it points to. Keeping the inner object fixed it. This is
very likely what broke 364b's sandbox (inferred; 364b used the same plain deep copy).

## What it means
If sleep ever changes the notebook file by any route, the file is put back byte for byte and the night is thrown out,
and the assistant still learns and answers correctly afterwards.
