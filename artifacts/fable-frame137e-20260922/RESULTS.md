# RESULTS — Exp 137e: one hearsay reply (Muse, 2026-09-22)

Result first: the one-change mixin reunites hearsay to a single
reply -- every 137d-caught framing now answers loop102's existing
HEARSAY_MSG byte-for-byte ("Do you know that yourself, or did you
hear it somewhere? ...", `scripts/fable_loop102_agent.py:70-71`).
Probe 107/107 (76 reused 137d cases + 31 new), 0 framed writes, and
every regression matches loop137c per-case: bench 800 0 moves, all
marks123 suites identical (sleep reason names new file only), the 7
checks 137d broke return to identical (cases150 57/57, rt110 T6 OK),
sessions/rt143/rt136/f1/139b 0 moves. One post-seal driver fix is
disclosed below; affected marks re-ran in the open.

## Marks (every seed/case reported; deterministic, no seeds)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (76) | 76/76 OK | S-say 16/16 byte-identical to 137d (echo+parenthetical); S-hear 24/24 exact HEARSAY_MSG; C 6/6 real-wins; N 12/12 + O 18/18 identical to 137d | PASS |
| T1b probe (31) | 31/31 OK | H 19/19 (leading/trailing/lower-case/filler/base-path) HEARSAY_MSG + 0 writes + follow-up finds nothing; E 12/12 (5 Say + 7 plain) identical to 137d | PASS |
| T2 wrong writes | 0 | 0 writes on all 43 framed turns (24 + 19 hearsay; Say echo never writes) | PASS |
| G1 bench (800) | 0 new wrong, moves predicted (none) | new 194/4, old 198/0, edit200 150/50/0, bench132 196/2; 0 verdict + 0 reply moves | PASS |
| G2 marks123 | per-case = marks137c except predicted (sleep reason only) | p2 64/64, p4 30/30, q1 F5+M5, bench 400/400, q4 leaks [], soak 2000/0/0-0-0 clean, sleep SKIP (reason names new file, predicted), rt81 60/0/14 + p3 L5-Z1 58/60 inherited FAILs identical, l1-l4/l6/L5-Z2 pass; rt110 T6 OK (restored), S1 inherited OK->BUG on both arms | PASS (inherited FAILs identical) |
| G3 junk/sessions | 0 new WRONG, moves predicted (none) | rt136 145 0 moves (C101/C102 HEARSAY_MSG, 0 writes); cases150 57/57 0 moves (6 restored); f1 45/46+1, 139b 101/101, 0 moves; sessions 129 OK/2 WRONG both arms 0 moves; rt143 106/7/11 0 moves | PASS |
| G4 time | each run < 1500 s | probe 1.4, junk 2.4, sessions 3.3, rt143 4.0, bench 69.1, marks123 297.3 | PASS |

Cosmetic-only diffs (verdicts + reply texts identical): rt110-L1
`statuses []` vs `["UNKNOWN_ENTITY"]` (receipt metadata, same reply);
p3-l6 `replied_before_kill` 5 vs 6 (correct 200/200, wrong 0 both --
known mailbox race); p3 `seconds` fields. Soak needed no re-run.

## Deviations

1. Post-seal driver fix (reported): generated drivers referenced
`L137E.DEFAULT_CONFIG137D` (missed uppercase-D name); first junk run
went HARNESS-ERROR on f1/cases139b (BOOT-FAILED, 0.1 s, discarded).
Fixed the name in 4 drivers, re-ran junk/sessions/rt143/bench/
marks123 in the open. Probe ran BEFORE the fix on files never edited,
so it stands as sealed. `shasum -c SEAL.sha256.txt` now fails on
those 4 driver files only; the other 6 sealed files pass.
2. "my friend says ..." declines identically on both agents (never
hearsay-shaped), so it sits in T1b-E, not T1b-H, by sealed design.
3. All six ledger predictions held as written.

## What it means

Leading, trailing, and base-path hearsay all get one fixed reply and
store nothing; pretend-Say keeps its echo; every frozen check matches
loop137c per-case again.

## What it does not mean

Not a change to what counts as evidence (framed content is refused,
never modelled); "my friend says" is still a plain decline, not
hearsay, on both agents.

Seal `SEAL.sha256.txt` (10 files; 4 drivers edited post-seal as
above), ledger P137e.1-6 pre-run + outcomes appended post-run. Mac
CPU, offline, OMP/MKL=1. Reproduce: `… python -B
scripts/fable_fix137e_probe.py`; `… python -B
scripts/fable_fix137e_bench.py`; `… python -B
scripts/fable_fix137e_junk.py`; `… python -B
scripts/fable_fix137e_sessions.py`; `… python -B
scripts/fable_fix137e_redteam143.py`; `… python -B
scripts/fable_marks123_all.py --agent scripts/fable_loop137e_agent.py
--config artifacts/fable-frame137e-20260922/loop137e-config.json --out
artifacts/fable-frame137e-20260922/marks137e --workers 4`.
Questions for Ben: none.
