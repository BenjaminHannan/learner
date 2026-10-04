# Stiffness test v1 result: NOT STIFF (marks fixed in ../STIFFNESS-TEST-v1.md before training)

Ran 2026-10-04 15:00-16:01 UTC on one Vast RTX 5090 (box 54162899, $0.36/hr; an earlier box 54162664 failed the
smoke run on a model-path guard and was replaced after ~3 min). Code: branch claude/project-thread-aya9pk @ fe22d7ebf,
pipeline from claude/real-pipeline-checkpoints @ 7f800f09b. main2 sha256 e82bd12b..., seed-0 parent 49a35023...
(matches the pin). torch 2.11.0+cu128, transformers 5.17.0, safetensors 0.8.0 (the pinned versions).

Score = exact match on the 200 fixed test rows (clock_date + string_transform, families no skills run trained on), %.

| seed | A main2 start | A final | B parent start | B final | A-B |
|---|---|---|---|---|---|
| 1 | 3.5 | 21.5 | 0.0 | 7.0 | +14.5 |
| 2 | 3.5 | 20.5 | 0.0 | 10.0 | +10.5 |
| 3 | 3.5 | 20.5 | 0.0 | 16.0 | +4.5 |
| 4 | 3.5 | 23.0 | 0.0 | 7.0 | +16.0 |
| 5 | 3.5 | 23.5 | 0.0 | 8.0 | +15.5 |
| 6 | 3.5 | 16.5 | 0.0 | 14.5 | +2.0 |

mean A 20.9, mean B 10.4, mean A-B +10.5, A behind on 0 of 6 seeds. VERDICT (registered rule): **NOT STIFF**.

Curves (correct of 200 at 0/1k/2k/3k/4k updates, from the box log; final = the table's final_dev):
A1 7 27 34 35 43 | A2 7 34 33 42 41 | A3 7 36 36 40 41 | A4 7 34 31 48 46 | A5 7 28 38 49 (4k 47) | A6 7 31 25 41 (4k 33)
B1 0 10 18 10 14 | B2 0 7 18 29 20 | B3 0 12 20 21 32 | B4 0 12 16 16 14 | B5 0 6 12 14 16 | B6 0 8 19 26 29
(A5/A6 4k curve points were cut from the log tail; their 4k values above are the final_dev numbers, which are the same evaluation.)

Shown: the skills-trained core learns two unseen skills faster and better than its pre-skills parent in 4000 updates,
on every seed. Most of A's lead is made in the first 1000 updates (+~25/200 vs +~9/200); from 1k to 4k both arms gain
roughly 10-12/200. Suggested: the 65-72 skills plateau is not plasticity loss; selective reinitialization (Test 2) is
not indicated now. Untested: stiffness after much longer training; other families; other seeds of the parent.

Copy-back: the results tarball pull returned sha_ok false (0 parts read) and a shell chain destroyed the box anyway
(my error: a pipe hid the failed check). Everything above is from the box's own log (box54162899-log.txt here),
which holds the scorer output and the per-check evals. The 12 SKILLS-RESULT.json files are lost; no checkpoints were
involved (--no-checkpoint). Spend: about $0.40 total.
