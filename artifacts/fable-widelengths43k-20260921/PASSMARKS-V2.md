# Experiment 43K-v2 — pass marks (fixed before any registered v2 run). 43K v1 stands as FAIL (5/6).

One change from 43K: balanced counter start (in each direction 2 counters lean "change state", 2 lean "stay"; +/-2
logits plus half-size jitter). Disclosed: one run on throwaway seed 9999 scored 1.00 at all lengths to 64.
Seeds: the six used before (4102/4103/4104/4111/4112/4113) AND three fresh, never-used seeds 4121/4122/4123.
Marks K1–K4 exactly as in PASSMARKS.md, but required on all 9 seeds. The fresh-seed rows are the confirmation;
a pass that holds only on the six reused seeds is reported as "not confirmed".
Honest limit: leaning some counters toward "change state" is a design hint that alternation may matter. It does not
tell the model which skills need it, or what to read when.
