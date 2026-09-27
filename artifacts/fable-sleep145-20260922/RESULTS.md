# Exp 145 RESULTS — sleep merge (grown slots + taught-wins): PASS

One sleep agent now does both: 130's grow-one-frozen-slot sleep with 131's
taught-beats-sleep answer rule generalised to every word. No new behaviour
beyond the union. **MARKS M1–M5 PASS, 5/5. Ledger P145.1–P145.6 all TRUE.**
Sealed files never edited (SEAL.sha256.txt still matches).

## The merge in one paragraph

`Sleep145Reasoner(S130.Sleep130Reasoner)` overrides only `answer`: on a bare
installed-word question with no qualifiers it checks
`notebook.current(eid, word)` for an ACTIVE TAUGHT row (131's calls,
generalised from 1 word to all 12 in `WORDS130`). On a hit it runs the 130
episode feed exactly once and answers from that row with source `taught`;
otherwise `super().answer` (identical queueing, derivation, sleep-derived
relabel). `Sleep145Sleeper` inherits 130's grow logic verbatim with renamed
serving files (`sleep145-words.json`, own marker) so 145 state never touches
sealed files. `Sleep145Daemon` inherits `process_file` verbatim.

## Marks (every seed/case reported, never averaged)

| mark | result |
|---|---|
| M1 G1 s1/s2 vs 130 JSONs | PASS: zero field diffs; 5/5 installs, 25/25 probes, 0 wrong, growth exactly sleeps 4–5, taught 225/225, g1/g2 true both seeds |
| M1 G3 L1/L2/L3 x s1/s2/s3 | PASS: 9/9 byte-identical to sealed 130 (timing excluded), growth never fired |
| M2 T1 E-family (seed 15) | PASS: installed, 3/3 rows stored; E1 OK; E2/E3/E4 answer Z01/Z02/Z03, source `taught` 3/3 |
| M2 T2 other 116 cases | PASS: 34/34 verdicts identical to 131's rescored report |
| M2 T3 104 marks (class swap) | PASS: zero field diffs vs sealed 104 (seeds 1–3, Z4, Z5 noise4/noise8) |
| M2 T4 teach-after-sleep (s31) | PASS: TA Z01 `taught` ow 0; TB H02 `sleep-derived` |
| M3 T6 grown-word teach (s41) | PASS: `boss_of_father` installed with `grew_slot` true; taught Z01 wins (`taught`, ow 0); control Y02 derives CK02 (`sleep-derived`) |
| M4 full 116 set (38 cases) | PASS: 38/38 OK, none worse than on 131 |
| M5 wave budget | PASS: 1697 s wall (< 1800), Mac CPU, OMP=1/MKL=1 per process |

Batches: M1 (3 parallel, 470 s) → e116+z104 (2 parallel, 1114 s; e116 alone
slower than 131's 735 s under shared-machine contention) → t4+t6 (2 parallel,
76 s) → read-only rescore.

## Deviations

- D1 (checker, not daemon): raw e116/t4 show the inherited 116-D3/131-D1
  record-lookup gap (bare probe names vs `.txt` mailbox names) — rescored
  read-only from frozen logs with the corrected lookup; raw files kept.
- D2 (filenames, by design): serving files renamed to `sleep145-*`, so raw
  stop-run G5 reads BUG (old marker name never sighted). Rescored OK on
  frozen sleep evidence (exit 0 + stopped event + recipe attempted); H4
  rechecked against the 145 word path. No daemon behaviour in doubt.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project \
--python 3.12 --with torch --with numpy python -B \
scripts/fable_sleep145_drive.py --only m1g1s1   # + m1g1s2,m1g3,e116,z104,t4,t6
Rescore (read-only): `python -B scripts/fable_sleep145_rescore.py`
Seal: `shasum -a 256 artifacts/fable-sleep145-20260922/PASSMARKS.md`
(hash 3c9ddab5… in SEAL.sha256.txt, sealed pre-run).

## What it means

A grown sleep vocabulary and taught-fact priority compose without
interference: grown words install exactly as on 130 and taught values win
on them exactly as on 131, with every previously passing verdict unchanged.

## What it does not mean

Sleep still never chooses what to learn (turn counter); taught rows never
block an install (answer-time only); growth past the 12 defined words and
qualifier interplay were not tested.
