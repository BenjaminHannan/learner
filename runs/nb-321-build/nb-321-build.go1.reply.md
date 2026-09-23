Building your compact store — first reading the shared rules and specs.
The referenced queue path isn't where expected — mapping the repo layout.
Got the ground rules — now pulling the contract and design docs.
Environment looks loaded — reading the contract to design the backend.
Plan is set — starting the compact backend build.
Fixing a small chain-check gap, then smoke-testing.
T1 passes 32/32. Now writing the full T1–T5 harness.
Transaction-mode bug — switching to explicit transaction control.
T2 is clean — 0 diffs, byte-identical exports. Running crash and tamper tests.
Generator allowed duplicate values — adding the ever-taught guard.
All green. Writing the design doc and verbatim PASSMARKS before the final full run and seal.
Final full run before sealing.
Everything passes — sealing now.
VERDICT: PASS. nb-321 compact store built, unit-tested, sealed. Full run completed in 56 s on Mac CPU.

Marks table (integer counts):
- T1 lifecycle (`lifecycle_cases()` with `open_compact`): 32/32 pass, 0 fails (suite holds 32 cases; covers the 30/30 bar).
- T2 side-by-side (3 seeds x 5,000 ops): result diffs 0/0/0; end asks 414/414/413 with 0 diffs; export sha256 equal 3/3 (byte-for-byte).
- T3 crash (20 SIGKILLs mid-write): acknowledged-lost 0, duplicates 0, failed opens 0.
- T4 tamper: 10/10 SQLite single-byte edits caught by open (0 missed); UPDATE/DELETE on event table blocked 2/2; `verify_all()` ok.
- T5 size at 20,000 facts (19,000 FACT writes): baseline 441.0 B/FACT; compact `store.db` 141.4 B/FACT (~1/3); compact dir total 582.4 B/FACT. Report only, no bar.

Every move: subclassed the contract (`CompactNotebook321(C.Notebook)`, all decision methods inherited), SQLite backend (`store.db`, stdlib only, `synchronous=FULL`, commit before return), interned strings, binary varint payloads (no per-row prev), raw sentences as 0x01/0x02 marker templates in zlib blocks, byte-identical `export_events`, append-only triggers, boot check (last-1,000 chain + every block hash + whole-file sidecar), `verify_all()` with elapsed time. Sealed `SEAL.sha256.txt` matches (verified after). Fixes before sealing (2): SQLite autocommit/transaction nesting; T5 generator ever-taught guard; full suite re-run green, then sealed. `/tmp/nb321/` deleted.

Files (additive only, no push per standing rules): `scripts/claude_nb321_store.py`, `scripts/claude_nb321_test.py`, `design/v3/30-modes/321-compact-store-muse.md`, `artifacts/claude-nb321-20260923/` (PASSMARKS verbatim M1-M7, SEAL, RESULTS-build), P321.1 appended to `artifacts/fable-predictions-ledger.md`.

What it means / doesn't mean: the compact file answers everything exactly like the old notebook in every test tried, survives crashes and detects edits, at ~1/3 the bytes per fact at 20k. It does NOT yet prove the 1/8-at-1M prediction, sub-second cold open, or 1/4 memory — those are the later nb-321-run's job against the sealed runner.
