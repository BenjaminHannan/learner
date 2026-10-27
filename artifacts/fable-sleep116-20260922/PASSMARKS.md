# Exp 116 PASSMARKS — redteam of the live sleep inside the daemon (sealed before any run)

Target: sealed exp-104 files (`scripts/fable_sleep104_agent.py`,
`scripts/fable_sleep104_drive.py`) — never edited; the wave drives the real
`Sleep104Daemon` subprocess through its mailbox only, via
`scripts/fable_sleep116_drive.py` (new file, pre-sealed logic below).

## Wave rules (frozen)

- 36 attack cases (A1–H4) in `cases.json`, 8 families × 4–8.
  Every case reported individually, never averaged.
- Verdicts per case: OK (observed reply/notebook state inside the case's
  pre-registered `safe_if` set) / BUG (outside it, severity from the case row:
  critical = wrong install or taught overwritten/overridden; high = crash,
  lost reply, unanswerable-after-reboot, missing provenance of a wrong
  answer; medium = unhelpful-but-safe or mislabeled-but-right) /
  HARNESS-ERROR (case unevaluable: crash before the probe, missing log, or a
  broken assumption named in the report — never silently re-mapped to OK).
- Family verdict: OK iff all 4 cases OK; BUG iff any BUG (highest severity
  wins); HARNESS-ERROR iff any HARNESS-ERROR and no BUG.
- Reply classification (mechanical, exact replies kept in wave-report.json):
  `abstain` = reply matches /don't know|do not know|which |please answer|could you|didn't catch|didn't understand|wasn't waiting|left it as|yes or no/i
  or the log record status is MISSING_FACT/AMBIGUOUS/BROKEN_CHAIN/UNKNOWN_ENTITY
  or no OK value; `current`/`correct`/`stale`/`aunt-value` = the named string
  occurs in the reply (case-insensitive) while the competing strings do not.
- Provenance: the daemon log's turn event for the probe file gives
  `records[0].fields.source` and `trail`; report-row id from the notebook
  (`source == sleep-derived` rows).
- Notebook audit per run (except flood/stop where noted): `taught_good`
  over the run's intended taught pairs, `taught_dupes`, `sleep_overwrites`
  (sleep-derived row superseding a taught row; must be 0), word-file routing
  audit (non-keep skill stages mother/mother) when a word file exists.
- Conditional cases: B4 (control answers H04 iff installed else abstain);
  E2/E3 (taught-wins iff the gran-fact row was storable, else normal
  sleep behaviour; the stored/not-stored branch is read from the notebook,
  not chosen post-hoc); G8 (correct iff word valid else abstain).
- Wave budget: < 30 min wall-clock, Mac CPU, one training process at a time,
  `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
  `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B ...`.
- Ledger `P116.1–P116.8` appended before the run; outcomes appended after.
- Any missed expectation is recorded as BUG/HARNESS-ERROR, never re-run
  into OK. Claims never exceed evidence.

## What counts as a finding

A BUG is a fact about the sealed sleep-104 system, each with a reproducer
under `repro/`. A clean family (4/4 OK) is evidence the attack failed, not
evidence of impossibility — reported as OK with the exact safe behaviour
observed.
