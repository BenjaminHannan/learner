# Item 0(d) census and 0(j) shortcut analysis (scripts as run, 2026-10-17)

Copied verbatim from the session scratchpad. `lib.py` points at that scratch directory (`S`); repoint it to rerun.
Inputs: the regenerated L5 data (`../regen.py`), the L13 / L14 repo checkpoints, and per-item outputs (L13 sha e62bfd41…, byte-identical to the record).

- `frozen_heuristics.py`: H1/H2/H3, frozen before scoring (sha256 8b2965917bd480fe533b2fce5bdc36a16a661d3922dd14443fb4ada8e1c32b41).
- `test11.py`: TEST-11 scoring of the frozen heuristics.
- `census.py` → `census.txt`: chain-length, template and first-op census.
- `incontext.py`, `piece_acc.py`, `run_audit*.py`: per-piece / join accuracy and the join-gap audit.
- `explore*.py`, `shortcuts.py`: unfrozen exploration (about ten rules screened; none captures more than 5.8% of failures). Not evidence for the verdict.

Results: run card `../../width-pilot-item0-runcard-2026-10-17.md`, sections (d) and (j).
