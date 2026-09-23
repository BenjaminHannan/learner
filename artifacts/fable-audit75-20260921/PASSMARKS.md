# Audit 75 — pass marks for OUR re-runs (fixed before any audit re-run)

Scope: independent audit of Exp 29 (new names) and Exp 46 (harden-before-gate).
Read-only over other agents' files; all audit outputs use the `fable_audit75_`
prefix or live in `artifacts/fable-audit75-20260921/`.

## Audit predictions (made before any audit re-run)

- Paudit75.1: re-running Exp 46 seed 4102 into our own folder reproduces every
  row of `runs/hard-seed4102.json` exactly (installed, fresh_accuracy,
  audit_disagree_of_60, chosen_updates, routed_chain). 80%.
- Paudit75.2: re-deriving the Exp 29 RESULTS table from `gates.json` matches
  all 30 F cells, the worst paired delta (-11, 2106, p12-3), control 512s,
  and the L 1/3 / F6 1/3 split. 90%.

## Audit marks

- A1: every number in Exp 29 RESULTS.md traces to a JSON path, or is marked
  UNSUPPORTED.
- A2: every number in Exp 46 RESULTS.md traces to a JSON path, or is marked
  UNSUPPORTED.
- A3: seal + timing check passes for both experiments (PASSMARKS sealed before
  runs; wave-1 verdict sealed before wave-2 trains for Exp 29).

## Deviations from the task template

- The task template asks for ledger predictions appended to
  `artifacts/fable-predictions-ledger.md` before the run. That file belongs to
  other agents and both the brief (rule 1: never touch ledgers) and this audit's
  read-only rule forbid editing it, so predictions live here instead (Paudit75.x
  above), sealed below before the re-run.
