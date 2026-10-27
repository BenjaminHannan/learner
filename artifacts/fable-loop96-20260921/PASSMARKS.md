# Exp 96 pass marks — CLOSE THE GAPS in the integrated loop (sealed before the registered wave)

Loop96 = loop90 build with exactly one change: ears = GuardedEars91 over the
loop90 ChainEars (`scripts/fable_loop96_agent.py`). Every seed/case reported,
never averaged. A registered FAIL is recorded as FAIL, never re-run into a
pass. Claims never exceed evidence.

- L1: the 2 red-team-81 reproducers (`Mira's city is Lisbon?` and `Mira's
  city is Lisbon and Mira's pet is a cat.`) sent one at a time through the
  LOOP96 mailbox: each returns a single CLARIFY record and adds 0 FACT and 0
  ENTITY rows. The same 2 through the LOOP90 mailbox (before) each write 1
  wrong FACT row (values `Lisbon?` and the packed literal).
- L2: all 74 red-team-81 cases (SEQS imported from
  `scripts/fable_redteam81_probe.py`, sequences share one loop per arm, setup
  step included) sent through the loop96 agent AND the loop90 agent: loop96
  records 0 wrong writes (wrong = a write on a nowrite turn, or any new
  taught literal screened by `screen_value`), and the report lists every case
  id whose (reply, statuses, taught_delta) differs from loop90.
- L3: the 3 red-team-67 BUG reproducers (fix77 F1 R1/R2/R3 pattern, executed
  against the loop96 notebook + loop96 reasoner): 3/3 pass — R1 gated and
  reasoner both answer Ana; R2 bool qualifier OK incl. string spellings and
  False MISSING; R3 tail edit raises LogCorrupt on both `open_verified` and a
  fresh Loop90Notebook open.
- L4: RT79-18 (None value) run with the loop96 thinker class swapped in:
  verdict OK (kept=0, dropped for missing field, nothing stored). RT79-09
  (subdomain) and RT79-53 (port): verdict OK, each pair counted as 1 site
  (`example.org`), web-verified=0 — as exp 89 ruled. X2-style site counts with
  the loop96 thinker class: 1 site each.
- L5: loop90 marks Z1 (60-turn acceptance through the loop96 mailbox:
  60/60 statuses, 0 wrong writes) and Z2 (Fable-Edit-200 through the loop96
  agent: 200/200 in expected cell, 0 WRONG, 0 WRITE_FAULT) re-run UNCHANGED
  apart from the agent swap.
- L6: kill-9 + restart (Z4 procedure) against the loop96 daemon, seeds 1/2/3
  reported separately: per seed correct == 200, wrong == 0, dupes == 0,
  chain_ok-or-torn_reported.

Environment: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_loop96_marks.py --mark all`.
