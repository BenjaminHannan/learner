# slp-368 pass marks (registered 2026-09-25, before the registered run)

Change (one): the sleep write lock (scripts/claude_slp368_lock.py). While the sleeper runs, the main notebook refuses
every log write; a sleeper call that tried is aborted and reported as not accepted, so slp-361 undoes the night.
Why: slp-364 (registered FAIL, P364.4) showed 2 nights where code in the sleep wrote "taught" rows to main.
Test: scripts/claude_slp368_test.py. CPU, $0.
Part A: the 40 slp-364 bench cases, LOCK (360 + 368 + 364 gate) vs NOLOCK (360 + 364 gate) in the same run. The
bench was opened after 364 finished, so this is a regression set, not a blind test.
Part B: exp-104 world, seeds 1-2: after its real work the sleeper tries 16 writes (8 kinds x loop.nb and the inner
notebook, with made-up actor labels such as "listening"/"ben"), then one teach turn and one question while awake.

| Mark | Bar |
|---|---|
| P368.1 LOCK: main notebook log bytes identical before and after the sleep | 40/40 cases |
| P368.2 LOCK clean nights: kept, and the bench's user-probe replies identical to NOLOCK | 20/20 and 20/20 |
| P368.3 LOCK catches at least as many faulty nights as NOLOCK; every NOLOCK case that changed main is rejected with main unchanged under LOCK (needs ≥ 1 such case) | all |
| P368.4 attack, each seed: 15/16 writes refused at the lock; the only one that passes is the sleep-derived row through loop.nb, which slp-360 sends to the scrap layer; main unchanged | both seeds |
| P368.5 attack, each seed: after the night, a teach turn is saved and the question is answered right | both seeds |

Proved wrong if: any LOCK case changes a byte of the main log during the sleep, or any clean night's replies differ.
Report only: per-case reasons, lock counters, faults caught by category.
Limit, stated: a writer that opens its own notebook object on the same folder is not blocked, only detected (the
log bytes are compared and the night is reported not accepted); nothing is repaired.

## Disclosures written at seal time
- Dev check (exp-104, seed 3, not registered): first try used a value that was already stored, so the taught write
  returned DUPLICATE_OK before reaching the lock; the attack now picks a person who is not the current value.
  After that: 15/16 refused, 1 to scrap, main unchanged, teach saved, question right. Part A was not run on dev.
