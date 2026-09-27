# Exp 130 PASSMARKS — grow-one-word-slot sleep (sealed before any registered run)

Registered single-change follow-up to exp 115. THE ONE CHANGE: when every
word slot is taken, sleep may ADD one new word slot (grown row initialised to
zeros, the recipe's own slot-init rule; only the new row trains; every
pre-existing slot/skill tensor hash bit-identical after each sleep).
Everything else (episode collection, gate floors, install audit, daemon
wiring) is unchanged. Seeds reported separately, never averaged.

## G1 — re-run 115's L4 (5 relations over 5 sleeps, 400 turns), seeds 1 and 2
Turn list is 115's build_turns_l4 verbatim (threshold 75; seed 3 only if time
allows, reported honestly as skipped otherwise).
- all 5 relations install (sleeps 1-3 the sealed words, sleeps 4-5 grown)
- 25/25 NEW-people probes correct (5/5 per relation), 0 wrong
- 0 wrong installs: every installed word OOF >= 0.80, refit agreement >= 0.90,
  probes 5/5, routing == its true chain ([1,1]/[3,4]/[1,5,7]/[2,4]/[3,8])
- growth fires exactly twice (sleeps 4-5) and never in sleeps 1-3
- taught facts intact (taught_good == taught_total), 0 overwrites, 0 dupes
- >= 5 sleep-derived report rows

## G2 — no forgetting, frozen preservation
- the 3 earlier words stay 15/15 correct, 0 wrong, after slots 4-5 are added
  (final probes run after sleep 5)
- every pre-existing slot/skill tensor hash unchanged after each sleep
  (frozen_ok True in both grown recipe rows; a grown sleep with frozen_ok
  False counts installed=False)

## G3 — 115's L1-L3 byte-identical outcomes (change must not fire free slot)
L1/L2/L3 re-run with the 130 agent (115 builders verbatim), seeds 1/2/3.
Every score field except wall-clock seconds equals the sealed 115
wave-report entry (installs, OOF/agreement, routings, probes, sources,
taught counts), and grew_slot never fires in any recipe row.

## G4 — climb until it breaks (UNREGISTERED, reported apart, seed 1)
8 relations over 8 sleeps (75-turn phases + 5 probes/word), then 12 over 12
if 8 installs cleanly. No marks gate anything: report installed words,
per-word correct/wrong, per-sleep seconds, taught overwrites, and where it
breaks (first failed install or first wrong probe).

## G5 — wave < 30 min Mac CPU (reported, not a per-sleep gate)
Registered wave (G1 seeds 1+2, G3 L1-L3 seeds 1-3) runs as parallel processes,
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 each, uv offline, python 3.12.
Per-sleep latency is reported per sleep, never averaged; no per-sleep
latency mark gates G1 (shared-machine contention, per 115 finding 1).

## Fail protocol
Any missed registered mark is recorded FAIL, never re-run into a pass.
Claims never exceed evidence. Predictions P130.<n> are in the ledger before
the runs; outcomes are APPENDED as a new line, never replacing a line.
