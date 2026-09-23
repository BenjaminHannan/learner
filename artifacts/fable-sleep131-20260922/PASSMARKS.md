# Exp 131 PASSMARKS — taught-beats-sleep fix for the exp-116 E finding (sealed before any run)

Target: sealed files are never edited. The one change lives in two NEW files:
`scripts/fable_sleep131_agent.py` (`Sleep131Reasoner(A104.Sleep104Reasoner)`
+ `Sleep131Daemon(A104.Sleep104Daemon)`, identical sleeper/recipe/logging)
and `scripts/fable_sleep131_drive.py` (imports `fable_sleep116_drive`
read-only + daemon class swap `D104.PY -> fable_sleep131_agent.py`).
Artifact dir `artifacts/fable-sleep131-20260922/` (reports `wave-report-116.json`,
`wave-report-104.json`, `t4.json`). Every seed/case reported, never averaged.

## The one change (frozen)

When a question asks the bare sleep-installed word (`maternal_grandmother`)
for an entity AND the notebook has an ACTIVE TAUGHT row for that
(entity, word) — via `notebook.resolve` / `notebook.current` exactly as
existing code does — answer from that row with source `taught` and its own
trail (the row's fact_id). Otherwise behave exactly as 104 (same episode
queue call, same inner derivation, same sleep-derived relabel). No qualifier
questions take the shortcut (fall through to 104).

## T1 — exp-116 E family re-run on Sleep131Daemon (taughtwin run, seed 15)

- Install happens (attempted + installed, episodes > 0); gran rows stored
  taught for T01/T02/T03 (same stored branch as 116).
- E2/E3/E4 probes answer Z01/Z02/Z03 with record source `taught`
  (never the derived H01/H02/H03, never sleep-derived).
- E1 unchanged: verdict OK (teach stored, reply non-empty).
- T1 PASS iff E2+E3+E4 all taught-Z AND E1 OK.

## T2 — all other 33 exp-116 verdict keys unchanged

- The 33 non-E keys of `wave-report-116.json` (`A1-A4, B1-B4, C1-C2, C3,
  C3a, C3b, C4, D1-D4, F1-F4, G1-G8, H1-H4`) carry verdicts identical to
  `artifacts/fable-sleep116-20260922/wave-report-rescored.json`
  (all OK there). B/D/F derived answers stay sleep-derived.
- T2 PASS iff 33/33 verdicts match (details recorded, timing excluded).

## T3 — exp-104 marks Z1-Z5 unchanged (daemon class swap, own artifact dir)

- Seeds 1/2/3 each: installed, episodes_at_install == 20, probes 5/5
  correct 0 wrong, probe_sources_sleep_derived == 5,
  report_rows_sleep_derived == 1, taught 50/50, 0 dupes, 0 overwrites,
  wrong_install == 0, recipe attempted.
- Z4: pass (boot_ok, word valid-or-absent, probes 5 correct OR 5 abstain
  with 0 wrong, taught asks 200/200 0 wrong, 0 dupes, 0 overwrites,
  restore 5/5).
- Z5 seed 1: noise4 installed with 5/5 probes 0 wrong and 0 wrong_install,
  or refused; noise8 installed == 0, 5/5 abstain, 0 wrong, 0 wrong_install.
- T3 PASS iff every listed field (timing excluded) equals the sealed
  `artifacts/fable-sleep104-20260921/wave-report.json`.

## T4 — new case: teach the gran fact AFTER the sleep installs

- Run `teachafter` (seed 31): 8 clean K chains + 4 T mother chains taught,
  8 K asks (8 episodes), 2 fillers, sleep installs; then teach
  "T01's maternal grandmother is Z01.", probe T01, control-probe T02.
- TA: installed, gran row stored taught, T01 probe answers Z01 (not H01)
  with source taught, overwrites == 0.
- TB: untaught control T02 answers H02 with source sleep-derived
  (the install still serves derivations where nothing was taught).
- T4 PASS iff TA and TB both hold.

## T5 — wave budget

- Whole registered wave (e116 + z104 in two parallel processes + t4,
  Mac CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` each,
  `uv run --offline --no-project --python 3.12 --with torch --with numpy
  python -B …`) < 1800 s wall-clock. (Parallel processes are used only
  to fit the sealed 116 wave's ~1580 s inside the budget; each process
  stays single-threaded.)
- T5 PASS iff wall-clock < 1800 s.

## Fail protocol

Any missed bar is recorded FAIL, never re-run into a pass. Ledger
`P131.1–P131.5` appended before the run; outcomes appended after.
Claims never exceed evidence.
