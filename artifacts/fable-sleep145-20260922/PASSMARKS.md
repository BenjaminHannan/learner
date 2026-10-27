# Exp 145 PASSMARKS — merge grown slots (130) + taught-beats-sleep (131), no new behaviour (sealed before any run)

The one change lives in NEW files only: `scripts/fable_sleep145_agent.py`
(`Sleep145Reasoner(S130.Sleep130Reasoner)` + `Sleep145Sleeper(S130.Sleep130Sleeper)`
+ `Sleep145Daemon(S130.Sleep130Daemon)`, 130 sleeper/recipe/logging verbatim,
taught-first answer rule generalised from 131's 1 word to all `WORDS130`),
`scripts/fable_sleep145_drive.py` (reuses 130 builders + 116 logic read-only
with the daemon class swap to 145), `scripts/fable_sleep145_rescore.py`
(read-only, corrected `.txt` record lookup as in 131's rescore).
Artifact dir `artifacts/fable-sleep145-20260922/`. Every seed/case reported,
never averaged. Sealed files are never edited.

## The one change (frozen)

When a question asks a bare sleep-installed word (`relations == [w]`, `w` in
`WORDS130`) for an entity AND the notebook has an ACTIVE TAUGHT row for that
(entity, w) — via `notebook.resolve` / `notebook.current` exactly as existing
code does — answer from that row with source `taught` and its own trail (the
row's fact_id; `multi` form for several rows). The 130 episode feed
(`_queue130`) runs exactly once on that path. Otherwise behave exactly as 130
(same queueing, derivation, sleep-derived relabel). No qualifier questions
take the shortcut (fall through to 130). Sleeper, recipe, gate, bridge,
per-turn logging: 130 verbatim (own word/marker filenames).

## M1 — 130's G1 (seeds 1-2) and G3 (115's L1-L3, seeds 1/2/3) re-run on 145

- Turn lists are 115's builders verbatim via the 130 drive (threshold 75 for
  G1; 215 / 75+145 / 100 for G3-L1/L2/L3).
- M1 PASS iff for every run: installed words, per-word correct/abstain/wrong
  totals, per-word sources, OOF/agreement per installed word, grew_slot flags,
  taught_good/total, dupes, overwrites, and report_rows_sleep_derived all equal
  `artifacts/fable-sleep130-20260922/wave-g1s1.json`, `wave-g1s2.json` and
  `wave-g3.json` (wall-clock seconds excluded). Growth fires exactly in G1
  sleeps 4-5 and never in G3.

## M2 — 131's T1-T5 re-run on 145 (same answers/sources as 131's report)

- e116 through Sleep145Daemon; z104 (seeds 1-3 + Z4 + Z5 noise4/noise8)
  through the daemon class swap into the 145 artifact dir; t4 teach-after-sleep
  (seed 31) verbatim via the 116 helpers.
- T1 PASS iff installed, gran rows stored taught 3/3, E1 OK, E2/E3/E4 answer
  Z01/Z02/Z03 with source `taught` (as in 131's `t-marks.json`).
- T2 PASS iff the 34 non-E verdict keys match 131's
  `wave-report-116-rescored.json` verdict-for-verdict.
- T3 PASS iff every listed seed field (timing excluded) equals sealed 104's
  `artifacts/fable-sleep104-20260921/wave-report.json` (installed, episodes 20,
  probes 5/5 sleep-derived, taught 50/50, 0 dupes, 0 overwrites, 0 wrong
  installs; Z4 and Z5 fields as in 131's compare).
- T4 PASS iff TA taught Z01 source `taught` trail [taught fact] ow 0 AND TB
  control H02 source `sleep-derived`.
- M2 PASS iff T1+T2+T3+T4 all PASS (T5 is folded into M5).

## M3 — new check T6: taught value for a GROWN word wins

- Run `grownafter` (seed 41): 20 father/boss train chains (J-kid/B/C) + 5
  disjoint test chains (Y-kid/B/C) taught, 20 episode asks on J kids,
  2 fillers, sleep installs word index 3 (`boss_of_father`, grown slot);
  then teach "Y01's boss of father is Z01." (differs from the derived C),
  probe Y01, control-probe Y02.
- TA: installed (grew_slot true for `boss_of_father`), taught row stored,
  Y01 probe answers Z01 (not the derived value) with source `taught`,
  overwrites == 0.
- TB: untaught control Y02 answers the derived value with source
  `sleep-derived` (the grown install still serves derivations).
- M3 PASS iff TA and TB both hold.

## M4 — full 116 red-team set through the 145 daemon mailbox

- All 11 runs (contra/coinc/collide/twomom/taughtwin/wrongpre/flood/few5/
  few10/few15) via the 116 builders through Sleep145Daemon, rescored
  read-only with the corrected `.txt` lookup; raw driver verdicts kept.
- M4 PASS iff no case verdict is worse than the corresponding verdict in
  131's `wave-report-116-rescored.json` (every case reported; OK-vs-OK with
  a taught source where 131 has taught is not worse).

## M5 — wave budget

- Whole registered wave (M1 G1s1+G1s2+G3x9 in parallel + e116/z104 in two
  parallel processes + t4 + t6, Mac CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`
  each, `uv run --offline --no-project --python 3.12 --with torch --with numpy
  python -B …`) < 1800 s wall-clock.
- M5 PASS iff wall-clock < 1800 s.

## Fail protocol

Any missed bar is recorded FAIL with one diagnosis note, never re-run into a
pass. Ledger `P145.1–P145.6` appended before the run; outcomes appended after.
Claims never exceed evidence.
