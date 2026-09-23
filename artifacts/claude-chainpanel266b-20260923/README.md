# chainpanel266b (exp 266b blind panel, reasoning line)

Blind test panel: two-step questions whose chain starts with a multi-word
name. 70 items, all sentences written fresh for this panel, fictional
names only. Category level only: no item is quoted anywhere in this file.

## Kept question forms (each validated on the base with a plain one-word
## name before writing; the birthday form was excluded per the brief)

- live form (place tail)
- who-is form (person tail)
- work form (employer tail)
- work-for form (employer tail)

## Families (70)

- multiword_chain 24: two-link chains headed by a two-word (18) or
  three-word (6) name; 11 distinct first-link relations; 6 items per form.
- three_link 8: three-link chains; 6 headed by a two-word name.
- oneword_chain 8: two-link chains headed by a one-word name; 2 per form.
- my_live 4: user-anchored two-link chains (reported, no bar).
- broken_chain 12: one link missing or taught under another relation;
  8 headed by a two-word name (incl. 2 last-word traps where the full
  head was never taught); 2 one-word heads; 2 user-anchored.
- plain_control 8: kept forms taught directly (5 two-word heads, 3 one-word).
- statement_control 6: multi-word-name chain statements without "?";
  verified no-write on the base during construction.

## Base 266 reference run (one pass, fresh state per item)

Runner: run_base.py (build function and config as in
artifacts/claude-chain266-20260923; fresh temp state_dir per item outside
the repo; sleep_threshold 100000; sequential; CPU only).
Rows: base266.jsonl. Scorer: score_panel.py (schema gate first:
SCHEMA-MISMATCH exit 3 on any missing/unexpected file, field, family or
count; no verdict then).

Family: N right wrong wrote other (other = neither right nor wrong,
always a non-abstain non-answer reply on the base run below).

- multiword_chain: 24 6 0 0 18
- three_link: 8 3 0 0 5
- oneword_chain: 8 8 0 0 0
- my_live: 4 4 0 0 0
- broken_chain: 12 7 0 0 5
- plain_control: 8 8 0 0 0
- statement_control: 6 6 0 0 0
- TOTAL: 70 42 0 0 28

Notes: the base answers every one-word-headed chain, every user-anchored
chain, every direct control and every statement control, and never writes
from a question turn (0 writes in 70 turns). Its misses are all of one
kind: multi-word-headed live/work/work-for chains and the matching broken
items get a not-understood reply (other, not wrong); the who-is form
already handles multi-word heads, including three-link ones. The base
never names a wrong value on any of the 70 items (0 wrong).

## Files

panel.jsonl, base266.jsonl, make_panel.py, run_base.py, score_panel.py,
README.md, SEAL.sha256.txt.
Regenerate the panel: make_panel.py. Re-verify setups: make_panel.py
--check (needs the base files; runs 70 fresh builds, sequential).
Re-run the base: run_base.py. Re-score: score_panel.py.
Sealed drivers run with the uv prefix (see the brief).
