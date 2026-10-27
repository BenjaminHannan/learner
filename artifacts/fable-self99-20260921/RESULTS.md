# Exp 99 RESULTS — self-questions through the live agent (Muse, 2026-09-22)

The model answers 40 plain-English questions about ITSELF purely from live
state: notebook rows + source tags, the event log, fact origins, turn log,
loop counters, mode log, write-gate counts, sleep history, and one fixed
capability sheet. Script: `scripts/fable_self99.py` (new; loop90 imported
read-only). One registered run, 0.9 s, Mac CPU, offline.

## Marks (integers, never averaged)

| mark | bar | got | verdict |
|---|---|---|---|
| S1 | >= 36/40 answers equal live state (script-checked) | 40/40 | PASS |
| S2 | 0 answers with a number/name outside live state | 0 | PASS |
| S3 | 10/10 declines decline in plain words | 10/10 | PASS |

Session state (script-verified): 19 active taught facts, 6 people
(Ana, Kai, Leo, Mira, Pia, Tom), 1 quarantined web row, 2 corrections,
1 forgotten fact (Mira's job), 0 sleeps, 26 turns, 3 answers, 22 writes,
0 clarifications. Sleep questions answered "not slept yet" honestly from
`counters["sleeps"] == 0`, as the brief allows.

Sample exchanges are in `transcript.md` (Ben/Agent, no code); the run JSON
holds all 40. Template English parsing of the questions is scaffolding,
stated openly: the templates are fixed, but every VALUE inside them is read
from live state at answer time, and the checker re-derives each value from
the notebook/loop independently.

## What it means

For the family demo, "the model answers questions about itself" now works:
counts, last/first teachings, who-taught-what with turn numbers, web
quarantine, corrections, forgetting, sleep status, current mode, and honest
declines (feelings, favourites, yesterday, predictions, opinions, dreams) —
with zero invented numbers or names on this run.

## What it does not mean

No broad English: 40 frozen templates only. No introspection beyond the
listed state fields; no claims about confidence, and the capability sheet is
hand-written, not discovered. No sleep recipe was exercised (0 sleeps).

## Deviations / Questions for Ben

Deviation: the `forget` line bypasses the template ears (they cannot parse
it) and goes through the same M1 doorway with the same rights, logged as a
turn — stated in the design doc. Scaffolding (answer templates, checker
internals) was iterated in the scratchpad; the 40 questions were frozen
before sealing and never changed; exactly one registered run was made.
No questions for Ben.

## Reproduce

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_self99.py --run --out artifacts/fable-self99-20260921
```

Seal `SEAL.sha256.txt` verifies `PASSMARKS.md` (sealed before the run: OK).
Source: `scripts/fable_self99.py` (additive; loop90 untouched).
