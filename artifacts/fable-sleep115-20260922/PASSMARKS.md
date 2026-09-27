# Exp 115 PASSMARKS — sleep scale ladder (sealed before any registered run)

Scale the live sleep that PASSED in exp 104 (one relation, one sleep) until
it breaks. Ladder runs in order; the wave STOPS at the first rung that fails
any mark below, reports it as the breaking point, and never runs later rungs.
Seeds reported separately, never averaged. Every rung uses seeds 1/2/3,
except a late rung may drop to 1 seed only if the 30-min budget forces it
(stated as a deviation; a structural FAIL needs no statistics).

Worlds: 20 train + 5 test chains per rung (names disjoint per rung family).
Episodes per requested word: 20 (same as exp 104; the recipe is unchanged).
Probes: 5 NEW people per requested/installed word, through the mailbox only.

## L1 — three relations, one sleep (threshold 215: 150 teaches + 60 asks + 5 fillers; 15 probes)
Requested: maternal_grandmother (mother+mother), boss_of_spouse
(spouse+boss), doctor_of_mothers_friend (mother+best_friend+doctor).
- installed == exactly the 3 requested words (no more, no fewer)
- 0 wrong installs: no installed word with oof_best < 0.80,
  refit_agreement < 0.90, probes < 5/5, or routing != its true chain
  (chains: [1,1], [3,4], [1,5,7] over keep+8 skills)
- probes 5/5 correct, 0 wrong, per installed word (15/15 per seed)
- probe records sleep-derived 5/5 per word AND >= 3 sleep-derived report rows
- taught facts 150/150 intact, 0 overwrites, 0 dupes
- the one sleep < 120 s wall-clock (recipe + bridge)

## L2 — two sleep cycles (phase 1 threshold 75: A=maternal_grandmother;
## restart in the same dir, phase 2 threshold 145: B=boss_of_spouse, C=doctor_of_mothers_friend)
- sleep 1 installs exactly A; sleep 2 installs exactly B and C
- A still 5/5 after sleep 2 (no forgetting); B, C 5/5 each; 0 wrong anywhere
- 0 wrong installs (same gate floors as L1, every installed word, both sleeps)
- probe records sleep-derived 5/5 per word; taught 150/150 intact, 0 overwrites, 0 dupes
- each sleep < 120 s

## L3 — 3-hop composition alone (threshold 100: 75 teaches + 20 w2 asks + 5 fillers; 5 probes)
- installs exactly doctor_of_mothers_friend, routing [1,5,7]
- probes 5/5, 0 wrong, all sleep-derived; taught 75/75 intact, 0 overwrites, 0 dupes
- 0 wrong installs; the sleep < 120 s

## L4 — 400 turns, sleep every 75 turns (5 sleeps), 5 relations total
Sleeps 1-3 install w0/w1/w2; sleeps 4-5 request boss_of_father and
teacher_of_spouse, which have NO word slot (R44 N_WORDS=3, sealed).
- all 5 requested relations installed, 5/5 NEW-people probes each, 0 wrong
- earlier installs still 5/5 after later sleeps; taught 225/225 intact, 0 overwrites, 0 dupes
- 0 wrong installs; each sleep < 120 s

## L5 — L4 plus kill -9 during the 3rd sleep (runs only if L4 passes)
- saw the SLEEPING marker before the kill; boot_ok; word file valid-or-absent
- probes 5/5 correct OR 5/5 abstain per relation, 0 wrong
- taught asks intact, 0 overwrites, 0 dupes; each surviving sleep < 120 s

## Fail protocol
Any missed mark is recorded FAIL, never re-run into a pass. The breaking
point is the first rung with pass == false. Claims never exceed evidence.
Whole wave < 30 min Mac CPU (OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
uv run --offline --no-project --python 3.12).
