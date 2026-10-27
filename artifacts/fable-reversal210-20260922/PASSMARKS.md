# PASSMARKS — Exp 210: TRUE REVERSAL SPLIT (benchmark repair; no agent change)

Split: `data/open/reversal210/fable_reversal210.jsonl` (70 items: 50
reversal, 20 control; fictional names only). Each fact taught with ONE
sentence only (`X is the ROLE of Y.` S_FIRST / `Y's ROLE is X.` O_FIRST);
reversal asked in the other direction with grammatical verb questions
(`Who PAST Y?` / `What did X BASE?`); controls asked in the taught
direction. Checker: `scripts/fable_reversal210_check.py`.
Run: `scripts/fable_reversal210_run.py --run` (arms: loop138i fresh
daemon per item; smollm-incontext = bench125 arm). Config:
`artifacts/fable-reversal210-20260922/loop138i-config.json`.
No agent code, config, or case file is changed by this experiment.

## R1 — checker proves a true reversal test
Bar: `python -B scripts/fable_reversal210_check.py` prints VIOLATIONS 0:
gold never inside its question (C1/C4), exactly one taught sentence per
item (C2), asked direction never taught (C6 pairings), persons/works
unique (C7), grammatical Who/What questions (C8). 50 reversal + 20 control.

## R2 — every item reported for every arm, none dropped
Bar: `fable_reversal210_loop138i_rows.jsonl` and
`fable_reversal210_smollm_incontext_rows.jsonl` each contain all 70 ids
with verdict in {right, wrong, abstain}; summary flags
`coverage_all_reported: true` for both arms. Loop rows also record teach
replies (ACCEPTED/REJECTED), stored FACT triples from events.jsonl, and
`n_inverse_stored` (must be 0 everywhere: taught facts only).

## R3 — broken-split note
Bar: `design/v3/30-modes/210-reversal-muse.md` carries a short note that
exp 66/125 reversal numbers come from the broken bench65 split (50
reversal rows teach BOTH directions and leak/ungrammaticalize the
question). No bench65 or other sealed file is edited.

Verdict VALID iff R1–R3 hold.

## Common rules
Seal: `shasum -a 256 PASSMARKS.md` + case file + checker + run script +
config > SEAL.sha256.txt BEFORE any registered run. Ledger P210.n
appended to `artifacts/fable-predictions-ledger.md` before the run
(append-only, outcomes in a new line after). Each run < 25 min Mac CPU
(`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, `uv run --offline`, HF
offline); daemon use is per-item fresh dirs (no long-lived wrapper).
Post-seal change to sealed files => registered FAIL, reported, never
re-sealed. Valid verdicts: right/wrong/abstain per item per arm.
