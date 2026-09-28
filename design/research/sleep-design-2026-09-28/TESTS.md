# Three single-change tests for the Director (DRAFT marks; not sealed)

Setup common to all: the sleep test harness from slp-358n3 / distill test (loop reasoner, 4 checkpoints, seeds as H6), code-made sums and Latin grids, old kinds = sums and grids after a maze day. Store 16 per kind unless stated (the size where every arm collapsed, so there is room to gain). Comparator for every test = the higher of (R16 uniform sleep) and (no-sleep after mazes).
Small card experiments and the village model are out of scope. Training data code-made only.

## T1 Fresh-question replay (piece 3 + 4)
Change: replace the stored old-kind inputs with fresh code-made old-kind questions each step, labels = the pre-maze net's own answers (no true labels, no store). One change against the distill test's D arm (same teacher, same steps). Disclosed as a stand-in: real generative replay needs the model to write its own questions, which this net cannot yet do. If T1 fails, generated replay is dead for this net at any cost; if it passes, the next step is a question-writing head (needs Ben's yes).
Passes if: old kinds beat R16 by at least 20 of 200 on both kinds, mean of 3 sleep draws, margin max(6, 2xSE), on every seed; maze F_eq within 10 of no-sleep; plain-net row not able to do it.
Proved wrong if: no gain over R16 on any seed for either kind.

## T2 The model picks its own replay (piece 2)
Change: which 16 items per kind go in the store. Arm A random 16. Arm B the model's own choice: 8 it got wrong and 8 it got right (by its own answer check on the day), from the same pool. Same steps, same sleep code.
Passes if: B beats A by at least 15 of 200 on both kinds on every seed (3 draws, margin as above) with at most 6 loss on days' kinds.
Proved wrong if: B is at or below A on every seed. Controls: a hardest-16 arm C, to tell "picks failures" from "picks something".

## T3 Newer-weighted rehearsal (piece 3, second branch)
Change: rehearsal sampling weight across 3 nights: uniform vs weights 1:2:4 favouring the newest night. Reuse H6's 3-night design (arm S, 300 steps).
Passes if: newest-night skills gain at least 20 of 400 on day tests with harm_* tests not worse than N - 6 on every seed. Proved wrong if: no gain on every seed.

## Marks self-check (Ben's list) - status
1. Noise: NOT DONE. The sealing helper must quote the S versus S re-run spread from H6 before fixing any bar; bars above (15, 20) are draft and were taken from the distill test's 20 bar, not from a measured noise.
2. Every-seed rejection: written above.
3. Fair comparator: written above (higher of R16 and no-sleep).
4. Plain-net row: named for T1, must be added for T2 and T3 by the sealer.
5. F_few (k=1..64) as its own required row: NOT DONE, to add.
6. 3-draw sleep gates, margin max(6, 2xSE): written above.
So these are proposals with draft marks; the running helper must close items 1, 4, 5 before sealing.
