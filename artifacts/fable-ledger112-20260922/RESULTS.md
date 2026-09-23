# Exp 112 RESULTS — ledger backfill (bookkeeping only, 2026-09-22)

No training, no experiments. Re-ran the exp-82 static checker read-only on the
live ledger, backfilled 3 stale outcomes strictly from results-JSON numbers,
appended one backfill section (ledger lines 789–793). Mac CPU, offline.

## Marks (integers)

| mark | bar | got | verdict |
|---|---|---|---|
| L1 | parse whole ledger, list every id | 494 ids listed | PASS |
| L2 | flag P234–P237 + any new collisions | 4 known, 0 new ids | PASS |
| L3 | --selftest green | green | PASS |
| L4 | audit JSON with before/after counts + Brier | written | PASS |
| L5 | whole check < 60 s, OMP=1, offline | seconds | PASS |

SCORE PASS (L1–L5). P112.1–P112.5 all TRUE, Brier mean 0.011 (n=5).

## Backfill counts

TRUE 1 (P13) · FALSE 1 (P16) · VOID 0 · UNDECIDABLE 1 (P209).
Remaining open (MISSING): 24. Collisions: P234–P237 (known, unchanged).

- P13 TRUE (p=0.80, brier 0.04): A/seed-0,1,2 `completion.json` key
  `started=true` in all three; bar was 3/3 with no failing seed.
- P16 FALSE (p=0.15, brier 0.0225): D/seed-0,1,2 `completion.json` key
  `started=false` in all three; forecasted event (≥2/3 start) did not happen.
- P209 UNDECIDABLE: exp-47 `RESULTS.md` is finished but holds no
  loader-vs-reference diff number, so the under-1e-3 bar cannot be checked
  there. Left open, unscored.

## Still open (do not score)

Running (no finished RESULTS.md): P95.1–6 (single-seed partial probe/speed
JSONs), P101.1–4 (CPU smoke log only, GPU half missing), P104.1–6 (seed-3 +
report missing), P110.1–6 (cases only). Stale: P5 (PREREG only, no results
JSON), P209 (above). Note: P1/P2/P4 read parser-TRUE via line 745, but that
line scores exp-102's internal marks P1–P4, not the early predictions; those
09-20 runs have no results JSON, so they stay genuinely open.

## Ledger movement during this run

Sealed run: 769 lines → 483 ids, 436 scored, Brier 0.1530. Owners scored
P105.x and P111.x mid-run (verified identical to JSON numbers). After my
append (793 lines): 494 ids, 453 scored, Brier 0.1519. Order violations 0.

## What it means

Two 09-20 stale rows are now decided from sealed per-seed JSON flags, and the
ledger's open set is exactly the running experiments plus two stale rows with
no deciding artifact.

## What it does not mean

It does not mean P1/P2/P4 are resolved (parser cross-talk, still open), and it
does not re-judge any owner-scored row — P105/P111 values were the owners'.

## Deviations

None from the backfill rule. Live-ledger races (P105/P111 owner-scored
mid-run) handled by re-running the audit and backfilling only still-missing
ids. Reproduce: PASSMARKS reproduce lines (sealed
`fable_ledger112_SEAL.sha256.txt`), out path
`artifacts/fable-ledger112-20260922/ledger_status_after.json`.
