# Exp 220 PASSMARKS — RESTART MUST NOT DOUBLE THE FAST INDEX (sealed before any registered run)

Agent: scripts/fable_loop220_agent.py (loop138i + FixedIndexedLoopNotebook).
Config: artifacts/fable-restartindex220-20260922/loop220-config.json.
Cases: artifacts/fable-restartindex220-20260922/cases220.json (20 histories h01-h20,
11 ghost cases g01-g11; all names fictional).
Base for comparison: loop138i (scripts/fable_loop138i_agent.py) +
artifacts/fable-agent138i-20260922/loop138i-config.json.
Sleep-path question is answered in RESULTS.md from code inspection + R2 probes.

## R1 index equality (scripts/fable_fix220_marks.py --mode r1)
20 histories (teaches, confirmed corrections, forgets, user-name facts mixed).
Per history 3 comparisons of the full index state
(_sr, _rel, _rel_known, _triples, _triples_pos, _sro, _srel, _rev, _ment_ref):
fresh-vs-fresh determinism, 0-vs-1 restarts, 0-vs-2 restarts.
PASS: 60/60 equal on the new agent. Base-138i count reported alongside.

## R2 ghost case (--mode r2)
g01 = spec history (Kim's boss Lee; Lee's city Oslo; restart; Forget Lee's city)
plus g02-g11 (same shape, other fictional names). After restart + forget, ask
"Whose city is V?", "What is B's city?", "What is A's boss's city?".
PASS: 11/11 cases where all three replies abstain ("don't know"-shaped, never a
positive answer naming the forgotten link) AND notebook_triples never lists
(B, city, V). (Abstain templates echo the question's value -- that echo is
correct behaviour, not a leak.) Base 138i must fail the same cases (reported).

## R3 answers (--mode r3)
20 histories x fixed list of 10 questions each (200 questions x 3 restart arms).
PASS: 20/20 histories byte-identical replies with 0, 1 and 2 restarts.

## R4 frozen suites (scripts/fable_suitediff.py, one suite at a time)
--agent scripts/fable_loop220_agent.py --config <loop220-config> --base 138i
--only rt136 | rt143 | sessions152 | bench (bench covers all 4 splits).
PASS: 0 moves on every suite (any move reported case by case from its detail line).

## R5 sleep smoke (scripts/fable_sleepsmoke206.py)
PASS: same marks as the 138i reference run (sleeps=1, installed=1, 5/5 new-people
probes right, 0 wrong, broken-chain abstains, taught 50/50 dupes 0, overwrites 0).

## R6 load time (--mode r6 --agent both, 6002-event log, warmup + interleaved reps)
PASS: fixed <= base + 10% on every rep (all rep times reported, never averaged).

## Verdict
PASS iff R1-R6 all pass. Any miss is FAIL with one diagnosis note.
Each run < 25 min Mac CPU, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
daemon wrappers idle_seconds (5.0 for smoke pilots/runs).
Sealed files: PASSMARKS.md, cases220.json, loop220-config.json,
scripts/fable_fix220_restartindex.py, scripts/fable_loop220_agent.py,
scripts/fable_fix220_marks.py.
