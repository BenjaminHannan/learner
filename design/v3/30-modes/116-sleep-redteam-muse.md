# 116 — Sleep redteam (Muse, 2026-09-22)

## Problem

Exp 104 proved the daemon can install `maternal_grandmother` from 20 clean
episodes and survive a kill-9. It left open whether sleep can install
something WRONG, override a taught fact, or break the daemon. Exp 116
attacks the sealed sleep-104 system (imported read-only, never edited)
through its mailbox only, with 36 pre-registered attack cases in 8
families (contradictory episodes; coincidental aunt pattern; name
collisions; two mothers; taught-vs-derived conflict; gate-invisible wrong
teaches; mailbox abuse during sleep; too few episodes).

## Design (additive only)

- `scripts/fable_sleep116_drive.py` (new): 11 mailbox-only runs of the
  real `Sleep104Daemon` subprocess (helpers imported from the sealed
  `fable_sleep104_drive`). Each run teaches, asks (queuing episodes via
  the unchanged Sleep104Reasoner walk), lets the threshold sleep fire
  inside the trigger turn, then probes. Verdicts per sealed case:
  OK / BUG (critical/high/medium) / HARNESS-ERROR.
- `artifacts/fable-sleep116-20260922/cases.json`: the 36 cases with exact
  safe sets; `PASSMARKS.md`: frozen verdict rules, mechanical reply
  classifier, provenance and notebook audits, conditional branches
  (B4 control, E2/E3 stored-or-not, G8 valid-or-absent). Both sealed with
  `shasum -a 256` before the wave and never edited after.
- Key mechanics under test: episodes derive from the live notebook (so
  pre-ask lies are gate-invisible — family F measures the damage and the
  provenance); post-ask corrections make episodes stale (family A);
  same-name teaches collapse to one entity and conflict to a yes/no
  confirm (families C/D); `aunt`/`maternal_grandmother` teach as literals
  (families B/E read what the hop loop and the word route do with them);
  STOP is honored between turns, so mid-sleep STOP must finish the turn
  then exit (family G).

## Evidence

Sealed wave report (`wave-report.json`); per-case verdicts in RESULTS.md
with a reproducer under `repro/` per BUG. (To be filled after the run.)

## Limits

One word slot, template ears/mouth, small families; the flood's 200 files
are smalltalk + 1-hop asks, not 200 competing teaches. A clean family is
evidence the attack failed here, not proof it cannot succeed.

## What it means / does not mean

Means: the concrete ways sleep can and cannot be made to lie or break,
with reproducers. Does not mean sleep is safe in general: only the listed
attacks were tried, at these sizes, on this seed set.
