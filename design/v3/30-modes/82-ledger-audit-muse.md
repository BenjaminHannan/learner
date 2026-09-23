# 82 — Ledger audit (Muse): static checker over the predictions ledger

Snapshot: ledger had 617 lines at 2026-09-22T03:22:48Z. The ledger is live
(other agents append during the audit), so counts below are that snapshot.
Tool: `scripts/fable_ledger82_check.py` (stdlib only, read-only on the ledger),
`--selftest` green (Brier math, duplicates, order violations, open handling).

## Counts (integers, from `artifacts/fable-ledger82-20260921/ledger_status.json`)
392 ids, 385 with a stated probability; outcomes TRUE 237, FALSE 108, VOID 2,
NOT SCORABLE 11, MISSING 34; 342 scored for Brier. Duplicates 4, stale opens 7,
order violations 0.

## Brier (lower is better; always-50 % scores 0.25)
Overall mean 0.1537 over 342 scored. Per experiment (n, mean): 43J (4, 0.2306),
43K (6, 0.1817), 45 (4, 0.0519), 46 (8, 0.1459), 47 (2, 0.0812), 50 (5, 0.0195),
51 (4, 0.0406), 52 (5, 0.0197), 54 (4, 0.2069), 55 (6, 0.0173), 55b (6, 0.3662),
56 (4, 0.0144), 60 (4, 0.1594), 61 (5, 0.1085), 62 (5, 0.0170), 64 (4, 0.4201),
65 (4, 0.0212), 67 (5, 0.1285), 73 (4, 0.0112), 74 (4, 0.0313), 76 (4, 0.3407),
77 (4, 0.0237), 78 (7, 0.4480), 79 (5, 0.0810), 80 (5, 0.1365), 81 (4, 0.2612),
82 (5, 0.0110), 84 (4, 0.0140), 86 (4, 0.0406), 89 (4, 0.0262),
early-table block (203, 0.1701). Worst calibrated: exps 78, 64, 76
(high-confidence FALSEs). Best: 82, 73, 56, 84 (all near 0.01).

## Duplicates, stale, order
Duplicates (same id, 2+ prediction lines): P234, P235, P236, P237, each defined
in 55b/57/58/59 (pred lines 365-368, 377-380, 393-396, 400-403). P238/P239 were
used once (55b only) — no collision. The P200 "collision" is namespace-only:
exp-45 P200 (N4, TRUE) vs redteam-67 P200.1–P200.5 (distinct dotted ids, 4/5 TRUE).
Stale opens (>1 day, still no outcome): P1, P2, P4, P5, P13, P16 (09-20 table rows
with empty outcome cells) and P209 (ears rung-2 PAPER arm). Fresh opens (27):
P53.1–5, P66.1–6, P85.1–3, P88.1–5, P91.1–4, P94.1–4. Order violations: none —
no outcome line precedes its prediction line.

## Experiment verdicts found in ledger
PASS-type marks for 51, 52, 54, 55, 55b, 56, 62, 65, 67 (4/5), 73, 74, 77, 79
(4/5), 81 (via exp-89 section tail), 82, 84, 86; registered FAIL for 57 (wiring)
and 58 (loader M2 bar); early block ends "final verdict too-hard". No verdict
line yet for 43J/K, 45, 46, 47, 53, 59, 60, 61, 64, 66, 76, 78, 80, 85, 88, 91, 94.

## Limits (claims stop here)
Collided P234–P237 are scored once each (first p, last outcome), so 55b's 0.3662
absorbs exp-59's FALSEs — read each block's own Outcomes lines instead
(55b 6/6 TRUE; 57 4/4; 58 3/4; 59 1/4). Verdict mining is regex-based and
approximate. Exp grouping follows section headings; a few outcome blocks sit
under a later heading (e.g. Outcomes 81 under 89).

## Own run (exp 82)
PASSMARKS sealed before the run (`fable_ledger82_SEAL.sha256.txt`); P82.1–5
logged before, outcomes after. L1–L5 all TRUE: full listing, dup report,
selftest, JSON written, seconds-long offline Mac-CPU run. 5/5 TRUE, Brier 0.0110.
Deviation: reworded my own seconds-old Outcomes-82 line to drop bare P-numbers
after the checker showed they self-attributed outcomes to the collided ids.
Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_ledger82_check.py --ledger artifacts/fable-predictions-ledger.md
--out artifacts/fable-ledger82-20260921/ledger_status.json`.
