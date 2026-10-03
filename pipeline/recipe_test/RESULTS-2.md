# Round 2: contextual reader for the calculator decision (2026-10-03, marks in PASS-MARKS-2.md fixed before training)

**Verdict by the fixed marks: PASS.** On a fresh held-out set, letting the reader see the frozen LM's contextual states (instead of word-by-word embeddings) lifts new-wording calculator calls from 59% to 91%, with all six seeds up.

Setup: RECIPE (copy path + half composed wording) with and without `--ctx`, real modules, fresh weights, 6 paired seeds, 3000 x 16. Fresh set (RT_ROUND=2): new answer split (seed 20261201),
6 newly authored new-wording families with new names/nouns (disjointness report in DISJOINTNESS-REPORT-r2.json), 192 questions. 12 runs, rows in `results2/` (sha-checked, 0 mismatches). `score2.py` prints the tables.

| (mean over 6 seeds, SD) | RECIPE (lexical reader) | CTX (contextual reader) | paired gain (95% interval) |
|---|---|---|---|
| train fit | 96.2 (1.8) | 100.0 (0.0) | |
| new-wording right-call (headline) | 59.2 (7.2) | 91.0 (2.9) | **+31.8 (+22.3 to +41.2)**, seeds +16.7 to +43.8 |
| train-wording right-call | 95.3 (1.7) | 100.0 (0.0) | +4.7 |
| unseen-answer final | 71.4 (3.3) | 95.5 (1.7) | +24.1 (+19.2 to +29.0) |
| all-question final | 72.5 (3.5) | 95.5 (1.5) | +23.0 (+18.2 to +27.8) |

Marks: gain >= +8 (met), interval lower bound > 0 (met, +22.3), CTX train-wording call >= 95% (100%, met), CTX unseen final not >5 below RECIPE (+24, met). Gate (RECIPE train fit >= 90%): 96.2%, met.

- Shown: the round-1 failure (ADD questions in new wording called as SUB) is largely gone: new-wording ADD calls 56% -> 100%, SUB 62% -> 82%; train-wording ADD and SUB both 100%. The remaining misses are SUB on new wording (about 18%).
- Shown: with the copy path, final accuracy equals the right-call rate in CTX (0 rows with a right call but a wrong final, 0 with a right final but no right call, 1152 rows). So the LM's contextual states did not hand the answer to the exit; the calculator result still does the answering. (Check on this run's rows only.)
- Caveats: the 6 new eval families were authored by the model that designed the test and not independently checked; the set is fresh but a single authoring pass. 3000 updates, one task kind (two-number add/subtract), two-digit answers. This changes the reader input for the whole model, not only the call head, so it does not isolate "call head sees context" from "core sees context". The LM is run once more per step (no gradient), so the reader is no longer a pure lexical thin projection: it consumes a 1.2B-parameter context encoder's states, which is a bigger architectural claim than the round-1 setup.
- Untested: starting from the trained parent checkpoints; reading only the call head from contextual states; bigger numbers or multi-step problems; the pointer exit / wider entry from the info-flow thread (different change, stand-in model).

Cost round 2: about $0.6 (4 boxes ~36 min, plus one aborted launch where I forgot to ship the new eval file, ~$0.03). See LEDGER.md.
