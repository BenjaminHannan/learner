# 43G / 43H results (2026-09-21) — outside reviewer's transport control, v1 exactly as specified

Label: the model is GIVEN the six readable places and two parity facts; output length is wired in; no carry.
208,680 parameters, 12,000 updates in ~70 s per seed.

43G v1, old skills [REV, ROTL1, INC3, SWAP, FOLD, REV+INC1]:
| seed | lengths 4–8 | length 12 | length 16 |
|---|---|---|---|
| 4102 | SWAP 0.00, rest 1.00 | 1,1,1,0,1,1 | 1,1,1,0,1,1 |
| 4103 | FOLD 0.00, rest 1.00 | 1,1,1,1,0,1 | 1,1,1,1,0,1 |
| 4104 | all 1.00 | all 1.00 | all 1.00 |

- T1 (fit, all seeds): FAIL — 2 of 3 seeds never fit one parity-dependent skill. Cause: the soft place-choice saturated
  at 1.0000 on one place for all parities (vanishing gradient). It is a failure to FIT, not to extrapolate:
  every skill that fit in range is 1.00 at lengths 12 and 16.
- T2: FAIL as registered (same two skills).
- 43H is therefore not interpreted as a registered result. Recorded only:
  4102 (CARDFOLD does not need SWAP): N=20 and N=50 -> installed, fresh 1.00, lengths 9–10/12/16 = 1.00.
  4104: N=20 and N=50 -> installed, fresh 1.00, lengths 9–10/12/16 = 1.00. Router found ROTL1 -> FOLD -> INC3 (weights 0.998+).
  4103 (FOLD broken): cross-validated match 0.00–0.04 -> installation correctly REJECTED at both N. No bad install.
  Old skills unchanged and weights-only reload identical in every installed run.

## v2 — one change: bounded address scores (10 x cosine). Marks in PASSMARKS-V2.md.
Development seeds 4102/4103/4104 and FRESH seeds 4111/4112/4113, one wave, nothing tuned in between.

- T1 fit: all six old skills 1.00 exact at lengths 4–8, correct-digit probability >= 0.9986 -> PASS 6/6 seeds.
- T2 length: all six old skills 1.00 at length 12 and at length 16 -> PASS 6/6.
- S1 N=20: installed, fresh 1.00 -> PASS 6/6.   S1 N=50: same -> PASS 6/6.
- S2: old skills unchanged (1.00 -> 1.00), weights-only reload identical -> PASS 12/12 runs.
- S3 (recorded): CARDFOLD at lengths 9–10, 12, 16 = 1.00 in all 12 runs.
- Cost: base ~70 s, sleep ~15 s, on one CPU thread.

Allowed sentence: "With the six readable places GIVEN by hand, a 209k-parameter model learns the six CardFold skills,
runs them perfectly at twice the trained length, and learns the new composed skill from 20 raw episodes by training
21 routing numbers over its frozen skills — 6/6 seeds, 3 of them fresh."
NOT shown: that a model can FIND those places itself (the transformer could not: 43A/C/D); anything about carrying,
noisy episodes, skills that are not compositions of known skills, language, or the 1.24M transformer.
This is an upper-bound control. The size of the gap between it and 43D/43E is the measured cost of not having
(a) length-free addressing and (b) callable, reusable skills.
