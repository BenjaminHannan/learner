# Exp 130 RESULTS — sleep grows one word slot: PASS

Exp 115 installed 3 relations then stopped where the architecture ended (no
slot for relations 4-5, honest abstain). The one change: when every slot is
taken, sleep adds one zero-initialised row and trains only it with the
certified recipe. New files only: a grow-slot sleeper/agent, a drive reusing
115's turn builders, this folder, one design doc. No existing file edited
(SEAL.sha256.txt verifies after the runs).

## Marks (every seed reported, never averaged)

| mark | G1 s1 | G1 s2 | G2 | G3 (L1/L2/L3 x s1/s2/s3) | G5 |
|---|---|---|---|---|---|
| relations installed | 5/5 | 5/5 | — | 3 / 1+2 / 1 (identical) | — |
| probes correct/wrong | 25/25, 0 wrong | 25/25, 0 wrong | first 3 stay 15/15 | 15/15, 15/15, 5/5 x3 | — |
| OOF / agreement per word | 1.00/1.00 x5 | 1.00/1.00 x5 | — | 1.00/1.00 (identical) | — |
| wrong installs / overwrites / dupes | 0 / 0 / 0 | 0 / 0 / 0 | — | 0 (identical) | — |
| growth fires | sleeps 4-5 only | sleeps 4-5 only | — | never | — |
| frozen hashes bit-identical | 4 then 5 tensors | 4 then 5 tensors | frozen_ok True x4 rows | n/a (sealed path) | — |
| sleep seconds | 70,73,9,15,20 | 70,73,9,15,19 | — | identical outcomes | wave 477 s < 1800 |
| verdict | PASS | PASS | PASS | PASS 9/9 identical | PASS |

Seed 3 skipped by the brief's time rule (reported, not run).

## What happened

G1 re-ran 115's L4 verbatim (400 turns, 5 sleeps): sleeps 1-3 reused sealed
slots via the untouched 115 path; sleeps 4-5 grew one zero row each for
boss_of_father [2,4] and teacher_of_spouse [3,8] (OOF 1.00, agreement 1.00,
routing exact), all 25 probes correct and sleep-derived, taught 225/225.
G3: all 9 L1-L3 runs byte-identical to sealed 115 (timing excluded), growth
never fired with a free slot. G4 (unregistered, apart): 8/8 installed, 40/40
probes, per-sleep 9-72 s. The 12-climb first broke at 9/12 — my climb driver
reused (kid, spouse/mother) pairs with new values, so the notebook's
no-overwrite guard clarified, no episodes queued, honest no-ops, 0 wrong.
A disjoint-family rerun (new file fable_sleep130_climb.py, sealed files
untouched): 12/12 installed, 60/60 probes, 0 wrong, taught 575/575,
per-sleep 9-188 s. The recipe never failed a gate; all 26 installs across the
wave read OOF 1.00 / agreement 1.00 with frozen_ok True.

## Deviations

1. No per-sleep latency mark gates G1 (PASSMARKS choice, stated before the
   runs): per-sleep seconds reported, never averaged; contention is real
   (identical fits took 9 s alone, 175 s beside other agents).
2. G3 scope is L1-L3 seeds 1-3 (all of 115's passing rungs).
3. G4-12b is an extra unregistered variant diagnosing the 9/12 break; both
   climbs are reported, neither replaces the other.

## Reproduce (registered G1, one seed)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B \
scripts/fable_sleep130_drive.py --root artifacts/fable-sleep130-20260922/runs-repro \
--report artifacts/fable-sleep130-20260922/wave-report-repro.json \
--only g1 --seed 1

Expect: 5 sleeps install w0-w4 (growth exactly in sleeps 4-5, frozen_ok
True), 25/25 probes, 0 wrong, taught intact. ~4 min solo.

## What it means

Sleep can extend its own vocabulary past its sealed slot count without
touching what it already knows — one frozen-preserving row at a time, with
the same gate that certified the first three words.

## What it does not mean

Growth is not scheduled by need (still a turn counter); the 12-climb's first
break was my world reusing taught pairs, not the recipe; and latency on a
shared Mac varies 10x for identical fits, so per-sleep seconds are evidence,
not promises.
