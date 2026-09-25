# slp-366 pass marks (registered 2026-09-25, before the registered run)

What: the multi-night scorecard (scripts/claude_slp366_scorecard.py), first registered run, on today's word-route
sleeper with slp-360 (scrap layer) + slp-361 (undo) + slp-364 (self-check). A world grows for 6 days (one new
compound word per day: maternal_grandmother, boss_of_father, doctor_of_mothers_friend, father_of_mother,
boss_of_mother, teacher_of_mother; 10 asked + 3 held people for the day's word; 3 transfer people for every
earlier word, taught but never asked; 1 broken-chain lure per day + 2 invented names; one correction per day from
day 2). Restart from the state folder every morning. Twin: NOSLEEP, the same turns, never sleeps. Seeds 1 and 2.
CPU, $0. Dev run (2 days, seed 1, SLEEP only) looked at before sealing: both nights kept, all probes right.

| Mark | Bar (each seed) |
|---|---|
| P366.1 taught one-hop facts right after every night | all |
| P366.2 made-up answers to lures, every night | 0 |
| P366.3 a word right on ≥ 90% of its people on its own night stays ≥ 95% on every later night (and ≥ 1 word learned) | yes |
| P366.4 words answered right for transfer people taught after the word's night, every night from 2 | ≥ 90% |
| P366.5 final night, all word questions: SLEEP right-rate minus NOSLEEP | ≥ +50 points |

Prediction, not a mark: the three words that need a grown slot (father_of_mother, boss_of_mother,
teacher_of_mother) may not all install (the sleeper can grow a limited number of slots); which ones do is reported.
Proved wrong if: any taught fact is lost, any made-up answer appears, or a kept word falls below 95% later.
