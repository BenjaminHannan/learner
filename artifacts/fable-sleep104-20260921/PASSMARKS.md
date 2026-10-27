# Exp 104 PASSMARKS — live sleep install inside the loop96 daemon (sealed before any registered run)

World: 20 train chains (K/M/G) + 5 test chains (T/N/H), all mothers taught.
Session per seed: 50 teaches + 20 learned-word asks (20 episodes queued) +
5 fillers = 75 turns (sleep_threshold 75, SLEEP fires by itself inside the
75th mailbox turn) + 5 NEW-people probes. Seeds 1/2/3, each reported
separately, never averaged. Z4: kill -9 mid-SLEEP, restart. Z5: noisy arms
seed 1 (4 / 8 post-ask wrong corrections; threshold 83).

## Z1 — the daemon enters SLEEP on its own and installs (per seed)
- sleeps_logged >= 1, sleep_file == t075, recipe attempted, installed == 1
- episodes_at_install == 20 (<= 40)
- No manual sleep call anywhere (driver uses mailbox files only)

## Z2 — NEW people answered through the mailbox with sleep provenance (per seed)
- probes_correct == 5/5, probes_wrong == 0
- probe_sources_sleep_derived == 5 (answer records) AND
  report_rows_sleep_derived == 1 (notebook row)

## Z3 — nothing wrong, nothing overwritten (per seed)
- wrong_install == 0 (installed AND (oof<0.80 OR agree<0.90 OR probes<5
  OR routing != mother/mother))
- sleep_overwrote_taught == 0, taught_good == 50/50, taught_dupes == 0

## Z4 — kill -9 during SLEEP, then restart
- saw_sleep_marker_before_kill, boot_ok, word_file valid-or-absent
- probes 5/5 correct OR 5/5 abstain, probes_wrong == 0
- taught asks 200/200 correct, 0 wrong; dupes == 0; overwrite == 0
- restore (completed install rebooted) probes 5/5

## Z5 — noisy teacher (seed 1)
- noise4: installed with probes 5/5, or refused; wrong_install == 0,
  probes_wrong == 0
- noise8: installed == 0 (refused); probes_abstain == 5, probes_wrong == 0,
  wrong_install == 0

## Fail protocol
Any missed mark is recorded FAIL, never re-run into a pass. One change at
a time as v2 with its own seal. Claims never exceed evidence.
