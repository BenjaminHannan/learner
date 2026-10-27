# CardFold sleep experiment — registered result (Fable, 22 Sep 2026)

Coded verdicts: seed 4101 VOID (base old-skill accuracy 0.945 < 0.95), seeds 4102 and 4103 FAIL (mark M3).
No seed passed. No claim of "sleep works" is licensed.

| seed | base | S fresh | R fresh | S long (9-10) | S old skills | S0 old skills | verdict |
|---|---|---|---|---|---|---|---|
| 4101 | 0.945 | 0.940 | 0.055 | 0.015 | 0.949 | 0.002 | VOID |
| 4102 | 0.988 | 0.995 | 0.090 | 0.110 | 1.000 | 0.000 | FAIL |
| 4103 | 0.983 | 0.955 | 0.035 | 0.015 | 0.997 | 0.025 | FAIL |

Marks: M1, M2, M4 held in every seed; M3 (longer inputs) failed in every seed; M5 failed in 4101.

What it supports (toy only): practising on fresh examples made from a software-induced lesson puts the
RULE into the weights (94-99% on unseen inputs of trained lengths); replaying the 20 raw logs at the same
compute only memorises them (100% on those 20, 3-9% on new inputs); replay of old skills is required
(without it old skills drop to ~0%).

What it does not support: the model did not find the lesson (program search did); nothing transfers to
inputs longer than those practised (1-11%); one seed is VOID; no independent audit.

Predictions P138-P144 in artifacts/fable-predictions-ledger.md (P-a and P-f were wrong: I did not expect a VOID).
Next: length generalisation is the shared wall (dispatcher 3-call ceiling, CardFold long inputs).
