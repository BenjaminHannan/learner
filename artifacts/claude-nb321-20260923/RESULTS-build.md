# nb-321 BUILD result (2026-09-23, builder, CPU only)

VERDICT: PASS. Compact store built, unit-tested T1-T5, sealed. All
behavioural tests show 0 differences vs the contract notebook; exports are
byte-identical; crash/tamper bars met; size reported (no bar in this task).

## T1 lifecycle: 32/32 pass (task bar: 30/30)

`fable_notebook_contract.lifecycle_cases()` with `open_compact`: 32/32,
0 fails. (The suite holds 32 cases c01-c32; the "30" in the task text is the
suite's original name. Every case passes, including torn-tail survival and
tamper detection.)

## T2 side-by-side: 0 differences, 3/3 seeds

3 seeds x 5,000 random ops (teach, correction, forget, alias, promote,
conflict attempts, duplicate event ids, inferred with approved rule, plus
invalid writes) on contract Notebook vs CompactNotebook321:

- seed 0: result_diffs=0, end asks 414 with 0 diffs, export sha256 equal (84c3d349482f, 1,117,512 bytes)
- seed 1: result_diffs=0, end asks 414 with 0 diffs, export sha256 equal (93ae70bc1dac, 1,137,356 bytes)
- seed 2: result_diffs=0, end asks 413 with 0 diffs, export sha256 equal (f0c8715f0191, 1,129,696 bytes)

Every Result (status + full detail) identical; every end ask on every touched
(subject, relation) identical; export_events byte-for-byte equal (same sha256).

## T3 crash: 20 kills, 0/0/0

20 SIGKILLs at random moments mid-write (ack file fsynced only after a write
returns): acknowledged-lost 0, duplicates 0, failed opens 0. (0 torn tails
observed; kills landed inside SQLite transactions that rolled back, with the
JSON-prefix replay covering the rest.)

## T4 tamper: 10/10 caught, 2/2 blocked

10 random single-byte changes to synced SQLite copies: 10 caught by open, 0
missed (whole-file sidecar hash). 2 attempted UPDATE/DELETE on the event
table blocked by triggers: 2/2. `verify_all()` on the 300-fact store: ok,
0.00 s.

## T5 size at 20,000 facts: report only

19,000 FACT writes, varied raw sentences: baseline 441.0 bytes/FACT write;
compact `store.db` 141.4 bytes/FACT write (~1/3); compact dir total 582.4
(dir holds the byte-identical JSON compat cache alongside the db).

## Byte layout summary

`store.db`: interned strings; binary varint event payloads (no per-row prev
hash); raw sentences as subject/value-marker templates, zlib-blocked (256);
sha256 per 500-event block + per JSON-byte-block; derived current-fact index;
append-only triggers; whole-file sidecar hash. Boot verifies the last 1,000
chain links + every block hash; `verify_all()` re-verifies everything.

## Fixes before sealing (2)

1. SQLite transaction nesting (`cannot start a transaction within a
   transaction`): string-intern INSERTs left implicit transactions open, so
   `_append`'s explicit `BEGIN IMMEDIATE` failed. Fixed with
   `isolation_level=None` (autocommit) + explicit BEGIN/COMMIT only. Re-ran
   all tests.
2. T5 workload generator re-taught an ever-taught value to the same pair
   (DUPLICATE_OK broke the replay assert). Fixed with an ever-taught guard
   mirroring the nb-320 generator. Re-ran all tests, then sealed.

Sealed: `artifacts/claude-nb321-20260923/SEAL.sha256.txt` (store, test,
PASSMARKS). Design: `design/v3/30-modes/321-compact-store-muse.md`.
Prediction P321.1 appended to `artifacts/fable-predictions-ledger.md`.
Test notebooks under /tmp/nb321/ deleted.

What this means in plain English: the new filing cabinet gives the same
answers as the old notebook for every question tried, keeps a tamper-proof
copy of everything, survives crashes, and its compact file uses about a
third of the bytes per fact at 20k facts. Whether it hits 1/8 at a million
facts is still untested; that is the later nb-321-run's job.
