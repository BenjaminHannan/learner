# 321-compact-store (nb-321 builder note, Muse)

Same decisions, same answers, same history as the contract notebook
(`scripts/fable_notebook_contract.py`), fewer bytes per fact, readable
without loading everything into memory.

## What changed (one change only: the storage backend)

`scripts/claude_nb321_store.py:CompactNotebook321` subclasses
`fable_notebook_contract.Notebook`. Every decision method is inherited
untouched (`declare_relation`, `new_entity`, `add_alias`, `approve_rule`,
`assert_fact`, `retract`, `promote`, `propose_merge`, `resolve`, `ask`,
`_show`). Only persistence and indexed reads are overridden:

- `_append` — binary-encode the event, append the canonical JSON line to
  `events.jsonl` (fsync + read-back, exactly like the contract), then commit
  the SQLite transaction (`synchronous=FULL`). A write returns only after
  both are durable.
- `_apply_sqlite` — insert the event row plus derived-index updates.
- `_load`/`_open_sync` — boot verification + crash recovery (replay).
- `current()` — indexed `(subject, relation)` query returning the same rows
  in the same order (same filter, same `(source-priority, -n)` sort, same
  best-source rule).
- `active()` — same logic over the derived `fact_state` table (no full scan).
- `export_events(path)` — rebuilds `events.jsonl` from SQLite content,
  byte-identical to the contract's file (same `json.dumps` settings, `n` /
  `prev` / `v` recomputed from content).
- `verify_all()` — re-verifies everything, returns elapsed seconds.

Factory: `open_compact(root) -> CompactNotebook321` (for
`scripts/claude_nb320_scale.py --factory ...:open_compact`).

## Byte layout (`store.db`, stdlib `sqlite3`/`zlib`/`hashlib`/`json`/`struct` only)

- `strings(id, text UNIQUE)` — every display name, alias, literal value and
  relation text stored once, referenced by small integer (varint).
- `events(n PK, kind, event_id UNIQUE, payload BLOB)` — one row per event.
  Payload is binary: 1 kind byte, then varints (entity/fact/string ids,
  0 = None for supersedes), 1-byte source/actor codes, length-prefixed utf-8
  for the rare free texts (rule bodies, reasons, provenance JSON). The 64-char
  `prev` hash is NOT stored per row; it is recomputed from content on export.
- `raw_blocks(block_id, blob, hash, count)` — raw sentences templated first:
  subject display name -> `0x01`, value text -> `0x02` (`0x00`-escaped, so
  lossless), grouped 256 FACTs per block, `zlib` level 9. FACT payloads hold
  only `(block_id, index)`.
- `ev_hashes(block_id, hash, n_start, n_end)` — sha256 over the raw
  `(n, kind, event_id, payload)` bytes of each completed 500-event block.
- `json_hashes(...)` — sha256 over the raw bytes of each completed 500-line
  block of the on-disk `events.jsonl` compatibility file.
- Derived (may change; rebuilt from events): `fact_state(...)` +
  `INDEX(subject_num, rel_id)`, `alias_map` + index, `entity_names`,
  `relations`, `rules`, `merges`, `meta(last_sha, count)`.
- `store.sha256.json` sidecar `{"n": count, "sha256": hex-of-store.db}`,
  synced at the end of every clean open.
- `events.jsonl` in the notebook dir is kept as a byte-identical
  compatibility/export cache (crash-recovery source); the compact figures
  below count `store.db`.

Append-only: `BEFORE UPDATE` / `BEFORE DELETE` triggers on `events` raise,
so both statements fail. Derived tables use upserts and are unaffected.

## Boot checks (every `open_compact`)

1. JSON tail scan: torn last line -> `torn_tail = True` (repair path).
2. Streaming pass over the good prefix: line count + per-500-line byte
   hashes vs `json_hashes` (any flip caught, no full parse needed).
3. Replay into SQLite any fully-written JSON lines missing after a crash
   between the JSON fsync and the SQLite commit (chain-checked).
4. Every `ev_hashes` + `raw_blocks` hash re-verified.
5. Chain re-verified over the last 1,000 events (parsed `prev` links).
6. Sidecar: same count but different whole-file hash -> `LogCorrupt`.
7. Sidecar re-synced. Nothing is fully loaded into RAM: reads are indexed
   single-row SELECTs plus small string caches.

## `verify_all()` checks

All of the above, plus the FULL hash chain recomputed from SQLite-decoded
events, plus a line-by-line comparison of every JSON line against the
SQLite reconstruction. Returns `{"ok", "n_events", "elapsed_s"}`.

## Bytes per fact at 20,000 facts (measured, T5)

Workload: 20,000 ops (17,000 teach + 2,000 correction + 1,000 forget),
varied raw sentences (12 templates x subjects/values + 10 correction
openers), 2,000 fictional entities. 19,000 FACT writes.

- Baseline `events.jsonl`: 441 bytes per FACT write (8.38 MB total).
- Compact `store.db`: 141 bytes per FACT write (2.69 MB total), ~1/3.
- Compact dir total (db + json compat cache + sidecar): 582 per FACT write.

The db file alone is already ~1/3 of baseline at 20k; the per-fact cost is
dominated by event ids (~21 chars, stored exactly for idempotency) and
SQLite row/index overhead. The 1M-fact ratio is for nb-321-run to measure.
