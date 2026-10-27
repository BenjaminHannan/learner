# RESULTS — Experiment 132: question-phrasing coverage (2026-09-22)

Registered single-change follow-up to exp 121. THE ONE CHANGE (question side
only; teach path byte-identical to loop121, wrapped never edited): a
deterministic rewriter (`scripts/fable_qrewrite132.py`) turns relative-clause
/ inverted multi-hop questions into the canonical nested-possessive form the
composers already accept, using only the notebook's own relation vocabulary
(plain software, tiny grammar, no model). Uncertain rewrites pass through
unchanged -- never a guess. Wrapper (`scripts/fable_loop132_agent.py`,
subclasses loop121; the 113d folder held only PASSMARKS.md at build time, no
PASS) returns every base ASK untouched and only reconsider base clarifies.
Ledger P132.1–P132.5: all TRUE (5/5).

## Marks table (sealed `PASSMARKS.md`, sha `62c0b392…`)

| Mark | Result |
|---|---|
| Q1 misunderstood drop ≥ 50 % vs base, same split | **PASS**: 59 → 1 (drop 0.983) |
| Q2 wrong ≤ 3, new split | **PASS**: 2 (items 022, 162 — both wrong under base too) |
| Q3 base correct all stay correct (0 correct→wrong) | **PASS**: 0 moves; 58 fixed abstain→correct |
| Q4 P2/P3/P4 + redteam124 unchanged vs base | **PASS** (see note): P2 64/64 rows identical to base; P3 7/7; P4 30/30; RT124 62/62 identical verdicts+reasons, 0 OK→BUG, 0 new wrong writes |
| Q5 whole wave < 1500 s Mac CPU | **PASS**: 40.4 s (bench 11.8 + marks 25.6 + base-P2 3.0) |

## Evidence

Blind split (STEP 1): 200 items, seed 132, 0 case_id overlap with
bench103-fresh + bench121 + bench65, sealed
`data/open/bench132/SEAL.sha256.txt` (`eb97d7aa…`) before the rewriter's
final version; never opened until PASSMARKS was sealed and the rewriter
frozen (hashes in PASSMARKS).

Bench (scorer v2, paired per item): base loop121 139 correct / 59 abstain /
2 wrong (misunderstood 59, contains_gold 142, 2 teach-reject items);
loop132 197 correct / 1 abstain / 2 wrong (misunderstood 1, contains_gold
198, same 2 teach rejects). The 2 wrongs (022, 162) are full-walk asks on
teach gaps -- the same residual class as exp-121's item-069, asked (not
rewritten) by the base, hence preserved untouched.

Q4 detail: P2 loop132 rows are verdict+reason identical to the paired base
loop121 run on all 64 cases (inherited vs sealed-102: ok_to_bug B7/D8,
still_bug B7/C2/C5/D8 -- the base's own moves, zero new). P3 L1-L6 all pass;
P4 30/30 with 0 false refusals. RT124: every one of the 62 cases has the
same verdict AND the same reasons under loop121-before and loop132-after
(incl. 13 turns where the rewriter fires but the base already asks, so the
wrapper returns the base reply byte-identically).

## Note on the Q4 bar (deviation from the sealed letter)

The sealed Q4 row asks "identical outcomes vs the base loop" and then lists
"RT124 ... 0 prefix-after" -- but the base loop itself has 14 prefix-after
cases (inherited loop113b question-side behavior), so "identical to base"
and "0 prefix-after" contradict each other. The brief's Q4 ("unchanged vs
the base loop") governs: 62/62 identical verdicts+reasons, 0 OK→BUG, 0 new
wrong writes. The absolute sub-clause is recorded here as unmet-as-written
and mis-specified, not as a behavior change.

## Deviations

1. One-line harness fix before any completed registered run: the first
frozen wrapper crashed only in `--daemon` subprocess mode (missing
`self.idle_seconds`, P3 harness) while in-process paths were identical. Line
added, PASSMARKS hash updated + re-sealed, whole wave re-run from scratch;
the earlier bench-only pass is DISCARDED, not reported. The rewriter module
is byte-identical to the first freeze.
2. Q4 uses the unchanged marks123 P2/P3/P4 suites called directly (same
code the `--suite` CLI drives) plus a redteam124 before/after runner with
only the daemon class swapped -- the brief's "--suite p2,p3,p4 style".

## What it means

Relative-clause and inverted multi-hop questions now parse end to end:
misunderstood replies fell 59 → 1 with zero correct answers lost and zero
new wrongs, and every prior safety suite is bit-identical to the base loop.

## What it does not mean

The last abstain, the 2 wrongs, and the 2 teach rejects are teach-side gaps
(compound subjects, unparsed sentences), not phrasing -- no question-side
change can fix them; the 14 redteam prefix cases are likewise inherited,
not introduced.

## Questions for Ben

None.

## Reproduce (Mac CPU, offline)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench132_run.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop132_marks.py --mark all
```
