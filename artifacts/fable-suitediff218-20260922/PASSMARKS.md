# Exp 218 PASSMARKS — SUITE-DIFF CLASSES + ANY BASE (sealed BEFORE any registered run)

Tool: `scripts/fable_suitediff218.py` (NEW file; imports
`scripts/fable_suitediff.py` read-only, reuses its runners; the 214
files are never edited). THE ONE CHANGE: the move classes and the base
lookup. Usage future pieces will copy:
`python -B scripts/fable_suitediff218.py --agent <agent.py> --config <config.json> --base 138i --out <dir> [--only ...]`
or `--base-dir <any sealed agent artifact folder>` instead of `--base`.

Move classes, checked in this order for every moved case:
new WRONG-WRITE, new WRONG, new junk write (all three as 214), then
lost OK (base OK, new not OK), then fixed (base not OK, new OK), then
write change (stored triples or fact-write count differ), then
reply-only move ONLY when verdict and stored triples are both identical
and only the reply text changed. Per-suite summary line lists the count
of every class; final line "GATE: clean" iff new WRONG + new
WRONG-WRITE + new junk write + lost OK = 0 over all suites run, else
"GATE: NOT clean (<counts>)".

## C1 classifier table (P218.1)
`python -B scripts/fable_suitediff218.py --check-table artifacts/fable-suitediff218-20260922/classifier-cases218.json`:
12 hand-made (base row, new row) pairs, expected classes:
T01-newwrongwrite new WRONG-WRITE; T02-newwrong new WRONG (OK->WRONG);
T03-junk-clause-a new junk write; T04-junk-clause-b new junk write;
T05-lostok lost OK (OK->MISSED, save lost); T06-lostok-clarify lost OK;
T07-fixed fixed (MISSED->OK); T08-fixed-from-wrong fixed;
T09-writechange write change (OK->OK, different stored triples);
T10-writechange-fw write change (fact-write count differs);
T11-replyonly reply-only move; T12-replyonly-saved reply-only move.
Bar: 12/12 match.

## C2 plant (P218.2)
Scratch-only wrapper `artifacts/fable-suitediff218-20260922/wrap218_capitol.py`
(replaces "capital"->"capitol", "Capital"->"Capitol" in the input text
before loop138i's turn; agent code untouched):
`--agent .../wrap218_capitol.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --base 138i --only rt136,sessions152`:
exactly 6 rt136 moves: C002 C105 C118 = "lost OK", C075 C096 C121 =
"reply-only move"; sessions152 0 moves; GATE line NOT clean (lost OK 3).

## C3 reproduce (P218.3, P218.4)
Loop138i vs base 138i AND vs --base-dir
artifacts/fable-agent138i-20260922, over rt136,rt143,sessions152,bench:
0 moves and "GATE: clean" both ways.

## C4 time (P218.5)
Each C3 run < 15 min wall-clock (900 s), Mac CPU, OMP_NUM_THREADS=1
MKL_NUM_THREADS=1, one suite at a time.

## Verdict rule
PASS iff C1-C4 all pass; any miss is FAIL with one diagnosis note.
Registered FAIL is recorded as FAIL, never re-run into a pass.

## No-tune sets (never opened, printed, or tuned on)
reading94, reading94b, artifacts/fable-naturalpanel208-20260922/.
