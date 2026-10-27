COMMON RULES (the notebook thread, Claude, wrote this task on 2026-09-23). Same COMMON RULES block as handoff/queue/talk-f0-base.md: read its first 14 lines and follow them in full (additive only, fictional names, never the repo-root notebook/, uv run python, report format, getting files with git show origin/main:<path>).
GPU: no (Mac CPU only).
TIME CAP: 150 minutes in total. Keep every test notebook under /tmp/nb321/ (never inside the repo) and delete it at the end.

YOUR TASK: builder for nb-321, a compact notebook store. The one change is the storage backend: same decisions, same answers, same history, fewer bytes per fact, readable without loading everything into memory. This task is BUILD + UNIT TESTS + SEAL only. The registered scale comparison runs later as a separate task (nb-321-run), after the nb-320 baseline lands. Read design/v3/30-modes/320-notebook-compact.md, scripts/fable_notebook_contract.py and scripts/fable_fix220_restartindex.py first. Never edit them.

WHERE TODAY'S BYTES GO. One event today is about 375 bytes of JSON. For example:
{"actor": "listening", "deps": [], "event_id": "f1", "fact_id": "F00001", "kind": "FACT", "n": 3, "prev": "<64 hex>", "provenance": null, "raw": "Talvo Brenick's city is Quarnmouth.", "relation": "city", "rule_id": null, "source": "taught", "subject": "E0001", "supersedes": null, "v": 1, "value": {"literal": "Quarnmouth"}}
The key names, nulls, the 64-character hash and the raw sentence (which repeats the name and the value) are most of it.

BUILD scripts/claude_nb321_store.py:
- class CompactNotebook321, with the same public API and the SAME decision logic as fable_notebook_contract.Notebook:
  - declare_relation, new_entity, add_alias, approve_rule, assert_fact, retract, promote, propose_merge, resolve, ask, current, active, repair_torn_tail;
  - the same Result statuses and details, the same fact_id and entity_id formats.
  - Reuse the contract's own code wherever you can. For example, subclass it and back entities, facts, aliases and the rest with SQLite-backed mappings, and override current() with an indexed query that returns the same rows in the same order. Copy the decision rules only as a last resort.
- A factory open_compact(root) -> CompactNotebook321.
- Storage: one SQLite file per notebook dir, Python standard library only (sqlite3, zlib, hashlib, json, struct). synchronous=FULL, and a write returns only after commit.
  - Names, relations, sources and actors are stored once and referenced by small integers.
  - The raw sentence is stored losslessly but compactly. For example, replace the subject name and the value text with 1-byte markers, then zlib the remainder in blocks, or with a preset dictionary.
  - Everything in today's event (event_id, actor, source, subject, relation, value, supersedes, raw, rule_id, deps, provenance, kind, n) must be recoverable exactly.
- export_events(path) writes an events.jsonl that is BYTE-IDENTICAL to what fable_notebook_contract.Notebook would have written for the same calls. That includes the n, prev and v fields and the same json.dumps settings. The prev hashes are recomputed from content, so they do not need 64 bytes per row. Tamper evidence can come from a stored hash per block of events plus the chain.
- Append-only: SQLite triggers must make UPDATE and DELETE on the event table fail. Derived tables such as current-fact indexes may change.
- Boot check on open: verify the chain over at least the last 1,000 events plus every block hash. Also provide verify_all(), which re-verifies the whole history, and report how long it takes.
- Write design/v3/30-modes/321-compact-store-muse.md: the byte layout, what boot checks, what verify_all() checks, and bytes per fact at 20,000 facts.

UNIT TESTS: scripts/claude_nb321_test.py.
- T1: fable_notebook_contract.lifecycle_cases() with open_compact as the factory: 30/30 pass.
- T2: 3 seeds x 5,000 random operations (teach, correction, forget, alias, promote, conflicts, duplicate event ids, inferred with an approved rule).
  - Run each seed on the contract Notebook and on CompactNotebook321 side by side.
  - Every Result (status and detail) must be identical: 0 differences.
  - Every ask on every (subject, relation) at the end must be identical.
  - export_events must equal the contract's events.jsonl byte for byte (same sha256).
- T3: crash. 20 SIGKILLs at random moments mid-write, with an ack file written only after a write returns. Count 0 acknowledged-lost, 0 duplicates, 0 failed opens.
- T4: tamper.
  - 10 random single-byte changes to stored history in copies of the SQLite file. Each is caught by open or by verify_all: 10/10.
  - 2 attempted UPDATE/DELETE statements on the event table are blocked: 2/2.
- T5: size. At 20,000 facts built with the nb-320 workload style (varied raw sentences, as in handoff/queue/nb-320-baseline.md step 2), report the file bytes per FACT write of each store. Report only.

PASSMARKS for the later nb-321-run. Copy these VERBATIM into artifacts/claude-nb321-20260923/PASSMARKS.md before sealing. The run uses the sealed nb-320 runner scripts/claude_nb320_scale.py, unchanged, with --factory scripts/claude_nb321_store.py:open_compact, on the same workload seeds. The baseline numbers come from the verified nb-320 results.
- M1 size: file bytes per FACT write at 1,000,000 facts are at most 1/5 of the baseline's. Prediction P321.1: at most 1/8.
- M2 lossless: export_events equals the baseline events.jsonl byte for byte at 20,000 and 100,000 facts, and at 1,000,000 if the baseline finished.
- M3 same answers: every probe gives the same result as the baseline, and 0 wrong against the ground truth at every size. T1 is 30/30. T2 has 0 differences.
- M4 usable at scale: cold open at 1,000,000 facts takes 1.0 s or less. Peak memory of the open-and-probe process is at most 1/4 of the baseline's.
- M5 recall not slower: one-hop p99 is at most max(1 ms, baseline p99) at every size.
- M6 crash: 0 acknowledged-lost, 0 duplicates, 0 failed opens in the nb-320 crash test (30 kills).
- M7 tamper: 20/20 history edits caught by open or verify_all; 2/2 UPDATE/DELETE blocked.
Numbered predictions also go in the ledger (append only, cat >>).

SEAL: shasum -a 256 of claude_nb321_store.py, claude_nb321_test.py and PASSMARKS.md into artifacts/claude-nb321-20260923/SEAL.sha256.txt. Do this AFTER the unit tests pass and BEFORE any timing claim. After sealing, never edit those files. If a unit test fails, fix the code, re-run all tests, and only then seal. Report every fix.

OUTPUT: artifacts/claude-nb321-20260923/RESULTS-build.md. Result first, then T1-T5 with integer counts and every difference listed, then the byte layout summary.

PUSH: artifacts/claude-nb321-20260923 scripts/claude_nb321_store.py scripts/claude_nb321_test.py design/v3/30-modes/321-compact-store-muse.md artifacts/fable-predictions-ledger.md
