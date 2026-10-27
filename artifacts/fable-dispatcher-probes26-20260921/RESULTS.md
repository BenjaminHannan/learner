# Experiment 26 — dispatcher STOP probes (no training) — results

Fable (coordinator) · 20 September 2026 · run once under FREEZE-NOTE.md (sha 685a1864…), script revision 2
(f78ca888…), after AUDIT-26-delta (FREEZE-READY: YES). Source: `report-final.txt`, `probes/*.json`.
21 checkpoints probed (12 v4 control + 9 registered), about 11 s each. Nothing was trained.

## Verdict: positive control PASSED; decision rows D1, D3, D4 FIRED

| Row | Fired? | Meaning |
|---|---|---|
| D1 | **yes** | Same picture as v4: STOP is healthy; the *operation pointer* asks for the final attribute too early |
| D2a / D2b | no | No real premature STOP; long practice did not damage STOP |
| D3 | **yes** | Once practice pushes the operation pointer further out, the register/subject pointer becomes the limiter |
| D4 | **yes** | "Counts calls" is the accurate description |
| D4′ / D5 | no | Not "follows positions and loses them"; not "no single account" |

Reading rule (delta audit): D4/D4′/D5 need `reached_step_2` ≥ 48 on k8-held. It is 64/64 in all 12 probed
ctx/reg+ctx checkpoints, so every seed is evaluable.

## Every seed (strict correct out of 64; "op" = operation handed, "op+s" = operation and subject handed)

| Checkpoint | k4-held op / op+s | k6-held op / op+s | k8-held op / op+s | S3 asks attribute early | geometry ratio |
|---|---|---|---|---|---|
| 19-awake 1900 | 33 / 64 | 2 / 64 | 0 / 64 | 64/64 | 0.541 |
| 19-awake 1901 | 46 / 64 | 2 / 64 | 1 / 64 | 64/64 | 0.399 |
| 19-awake 1902 | 29 / 64 | 0 / 64 | 0 / 64 | 64/64 | 0.327 |
| 19b-U5 1900 | 44 / 64 | 21 / 64 | 1 / 64 | 64/64 | 0.502 |
| 19b-U5 1901 | 63 / 64 | 38 / 64 | 8 / 64 | 58/64 | 0.505 |
| 19b-U5 1902 | 59 / 64 | 31 / 64 | 8 / 64 | 43/64 | 0.591 |
| 19b-U8 1900 | 34 / 64 | 3 / 64 | 0 / 64 | 64/64 | 0.850 |
| 19b-U8 1901 | 37 / 64 | 4 / 64 | 0 / 64 | 64/64 | 0.146 |
| 19b-U8 1902 | 61 / 64 | 36 / 64 | 11 / 64 | 64/64 | 0.901 |
| v4-ctx 0 / 1 / 2 | — | — | — | 64/64 each | 0.118 / 0.258 / 0.344 |

With both pointers handed over, **every checkpoint scores 64/64 at every length, including 8 calls**: STOP and
the operator are never the problem.

## What it means

- The controller knows when to stop. What breaks is *what it asks*: at some call number it asks for the final
  attribute even though the chain still has links to follow. It behaves like something that counts calls, not
  something that reads where it is in the question.
- Handing it the right operation is not enough on reg+ctx: the subject pointer then fails (0–11/64 at 8 calls).
  reg+ctx, the arm used in experiments 19 and 19b, carries both defects.
- So: the stateless-STOP fix stays vetoed (it would fix a part that isn't broken), and no more
  practice-length waves on reg+ctx. The one licensed training experiment is 25b step 3 — the `ctx` arm with or
  without a self-written "already used" mark — registered separately, and its registration must forecast that
  a call-counter may simply ignore the mark.

## What it does not mean

- A forced action is never an autonomous success: 64/64 with pointers handed over says the *other* parts work,
  not that the dispatcher works.
- Probe C puts the controller in states it never practised; it is a diagnosis, not a score.
- Descriptive development evidence on throwaway units. It changes no registered result (19 and 19b remain
  FAIL) and licenses no system claim.
- "Counts calls" is a behavioural description, not a located mechanism. The geometry ratio did not give the
  clean separation forecast (P110 false).

## Predictions (hashed before the first probe; rows in `artifacts/fable-predictions-ledger.md`)

Reviewer P102–P111: 8 TRUE, 2 FALSE (P107 premature STOP 0.15 → false; P110 geometry ratio 0.40 → false),
mean Brier 0.125. Coordinator P112–P117: 5 TRUE, 1 FALSE, mean Brier 0.155. Biggest miss for both: R1(8)
holding in all three 19-awake checkpoints (forecast 0.35 / 0.30, came TRUE).

## Next

25b step 3 goes to a Fable reviewer for registration (2 arms × 3 seeds, about 16 min on the Mac). It is off the
demo path and yields to the talker and experiment 27.
