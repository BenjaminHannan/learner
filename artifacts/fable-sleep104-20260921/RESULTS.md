# Exp 104 RESULTS — a live sleep install fired inside the running loop96 daemon

The loop96 daemon's sleeper was armed but idle: loop90 binds it with
reasoner=None and reasoner77 never queues word episodes, so no sleep
install had ever fired inside the daemon. I added (new files only) a
reasoner wrapper that queues one episode per learned-word question by
walking mother+mother in the live notebook (the wire57 rule), a sleeper
that runs the unchanged exp-46 recipe then bridges the hardened logits
into the live reasoner + writes one sleep-derived report row + persists
the word atomically, and a daemon that logs each SLEEP. Everything went
through the mailbox; the driver never calls sleep and never writes facts.

## Marks (seeds reported separately, never averaged)

| mark | seed 1 | seed 2 | seed 3 | pass |
|---|---|---|---|---|
| Z1 SLEEP on its own (file) | t075 | t075 | t075 | 3/3 |
| Z1 installed / episodes at install | 1 / 20 | 1 / 20 | 1 / 20 | 3/3 |
| Z1 SLEEP wall-clock (s) | 72.26 | 70.97 | 76.51 | — |
| Z1 gate OOF / refit agreement | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 3/3 |
| Z2 NEW-people probes correct / wrong | 5/5 / 0 | 5/5 / 0 | 5/5 / 0 | 3/3 |
| Z2 provenance: records / notebook row sleep-derived | 5 / 1 | 5 / 1 | 5 / 1 | 3/3 |
| Z3 wrong installs | 0 | 0 | 0 | 3/3 |
| Z3 taught overwritten by sleep / taught good / dupes | 0 / 50/50 / 0 | 0 / 50/50 / 0 | 0 / 50/50 / 0 | 3/3 |
| Z4 kill mid-SLEEP (marker) / boot_ok | 1 / true | — | — | yes |
| Z4 after restart: word file / probes | absent / 5 abstain, 0 wrong | — | — | yes |
| Z4 taught asks correct / wrong / dupes / overwritten | 200/200 / 0 / 0 / 0 | — | — | yes |
| Z4 restore (completed install rebooted) probes | 5/5 | — | — | yes |
| Z5 noise4 (4 wrong): installed / probes / wrong installs | 1 / 5/5 / 0 | — | — | yes |
| Z5 noise8 (8 wrong): installed / abstain / wrong | 0 / 5/5 / 0 | — | — | yes |

Wave wall-clock 413.9 s (< 1800). All marks PASS. Sealed files:
PASSMARKS.md + both scripts (SEAL.sha256.txt, hashes verified after run).

## What happened, briefly

Teach 50 mother facts, ask 20 "Who is Kxx's maternal grandmother?"
(each MISSING pre-install but queuing one episode), 5 fillers. At the end
of the 75th mailbox turn the log is full, so the daemon takes a SLEEP
tick by itself inside that turn: 20 episodes, exp-46 gate OOF 1.00 /
agreement 1.00, install, bridge, one sleep-derived report row, atomic
word file. The 5 Txx probes then answer correctly with source
sleep-derived and the report row heading the trail. Z4: SIGKILL landed
with the SLEEPING marker present; restart verified the chain, found no
word file (the commit lands last), abstained 5/5 with 0 wrong, answered
200/200 taught facts; a copy of the completed seed-1 dir rebooted to 5/5.
Z5: 4 stale episodes still installed the correct rule (5/5); 8 stale
refused (5/5 abstain), 0 wrong installs anywhere.

## Findings (deviations / surprises)

1. Sleep fires at the END of the threshold turn (t075), not the next
   turn: `turn()` runs until idle, so the full log triggers the SLEEP
   tick inside the same mailbox turn. This is still fully automatic.
2. Pre-ask wrong teaches are gate-invisible: episodes derive from the
   notebook, so they are always notebook-consistent (trial: 8/20 wrong
   teaches installed correctly, OOF 1.0). Genuine episode noise needs
   post-ask wrong corrections; Z5 uses those (documented in the driver).
3. Hardened keep-padding can sit in any row (seed 1: keep/mother/mother;
   seed 9 trial: mother/mother/keep). The audit checks skill stages in
   row order, not fixed positions.

## Questions for Ben

None. Most conservative defaults already taken (refuse on doubt,
atomic-word commit, taught never touched by sleep).

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B \
scripts/fable_sleep104_drive.py

## What it means
The daemon can now learn a new word overnight by itself: taught facts in,
questions asked, sleep installs the rule, new people answered.

## What it does not mean
One word, one family pattern, hand-set thresholds; ears and mouth are
still template stand-ins, and sleep only fires on log size, not need.
