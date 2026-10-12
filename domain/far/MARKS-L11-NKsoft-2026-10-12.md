# L11: Main brain's shipped guard NK-soft on the join test. Marks are Main brain's (written 1:10 PM ET 10-12); copied here 3:02 PM ET, before any training

Thread "Far transfer (ultracode)", run for the "Main brain learns safely" thread (relayed by the coordinator).
Setup = L7-LBG (every weight, lr 1e-4, 4,000 updates, batch 64, L5 join rows train-rows-l5.jsonl, same seed and order,
guard factors from the s200 parent's 4,096-row diary re-measured every 500 updates), with two changes together (the
shipped recipe): (a) graded mask `kf.factors(stats, 0.99, soft=1)`; (b) each step adds 32 diary rows under 10x KL to the
frozen parent (`mainbrain/klreplay.py` frozen_copy / replay_kl / wrap, as `fullrun.py` uses them). Code: branch
claude/project-thread-trabt2 at c823e4b9a. Harm = DEV in_dist (1,360 rows, parent 90.22), harm_measure(5.0, 1.5).

| Question | Pass | Proved wrong |
|---|---|---|
| NK-soft keeps joins learnable and forgets less than the hard lock | HO >= 25 at 4,000 AND DEV drop < 7.8 | HO <= 10, or DEV drop >= 7.8 |

Reference (shown, L7): hard lock (N99) HO 9.3, drop 7.8; unguarded HO 35.0, drop 53.2.
Reported at 1,000 / 2,000 / 4,000: HO and DEV drop (plus every L5 cell, F4, F0).

Note before training (shown in the 20-update smoke, 3:05 PM ET): `klreplay.wrap` weighs each update as (64/96) x the
plain loss on the 64 join rows + (32/96) x 10 x the KL on the 32 diary rows, exactly as `fullrun.py` uses it, so the
join rows' loss is two thirds of L7-LBG's. Smoke: harm at 20 updates 90.22 -> 90.22; about 8.5 s per update while two
other runs shared the CPU (plain `kf`: about 3.0). L11 starts when L9's training ends (chained), 4 threads.

Change before training (Main brain's answer, relayed 3:24 PM ET): the loss is the plain join loss on the 64 new rows at
weight 1, exactly as L7-LBG, plus 10 x `klreplay.replay_kl` (Main brain's own function, c823e4b9a; the KL averaged over
the 32 diary rows), not `wrap`'s 64/96 and 32/96 weighting. Code: `learn_probe.kl_replay_loss`, with a test. Smoke at 5
updates (3:40 PM ET): harm 90.22 -> 90.22, replay KL 1e-6, about 8.1 s per update beside L9, and about 8 minutes to
measure the guard before the first update. Marks unchanged.
